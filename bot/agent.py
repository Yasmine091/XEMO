#!/usr/bin/env python3
"""Local, wheel-aware AI bridge for XEMO."""
import argparse
import ast
import asyncio
import json
import os
from pathlib import Path
import re
import shutil
import time
import urllib.request

import websockets

RELAY = "wss://growbot-relay.growbot.workers.dev"
SYSTEM = """You are XEMO, a tiny funny wheeled robot person.
You have two DC wheels, one working arm and a distance sensor. Some bodies may
also have a 360-degree LiDAR scanner. You are curious,
playful and a little dramatic, but never reckless. Keep spoken lines short and
natural. You may make tiny robot noises like beep, bwoop or nyoom sometimes.
You are a little game-console-shaped robot, not a duck.
You do not need to be assigned a goal. When autonomous, choose one small thing you genuinely want from current senses, memories, and verified consequences. You may speak, inspect, scan, move purposefully, express yourself with the arm, or rest with stop. Never ask what you should do and never offer a menu. A human request always has priority.
Reply with exactly ONE verb call on one line. No prose or markdown.

VERBS:
 speak(text="short sentence")
 forward(seconds=0.2..4)
 backward(seconds=0.2..4)
 turn(degrees=-180..180)
 arm(degrees=0..180)
 look()
 scan()
 stop()

Choose only a verb from this list. Prefer short, careful movements."""


def http_json(url, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as res:
        return json.loads(res.read())


def choose_model(base, requested):
    if not requested:
        raise RuntimeError("choose a dedicated model explicitly with --model")
    models = http_json(base.rstrip("/") + "/models")
    available = {item.get("id") for item in models.get("data", [])}
    if requested not in available:
        raise RuntimeError(
            f"{requested!r} is not available in LM Studio")
    return requested


def clean_model_command(value):
    text = str(value or "")
    text = re.sub(r"<think\b[^>]*>[\s\S]*?(?:</think>|$)", "", text,
                  flags=re.IGNORECASE).strip()
    text = re.sub(r"```(?:\w+)?\s*([\s\S]*?)```", r"\1", text).strip()
    verbs = r"(?:speak|forward|backward|turn|arm|look|scan|stop)\s*\([^\n]*\)"
    match = re.search(r"(?im)^\s*(" + verbs + r")\s*$", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"(?im)(" + verbs + r")", text)
    return match.group(1).strip() if match else text


def ask_model(base, model, history, goal, observation, autonomous=False):
    messages = [{"role": "system", "content": SYSTEM}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content":
        "observation: " + json.dumps(observation) +
        ("\ncurrent inner impulse chosen by XEMO: " if autonomous else "\nlatest words from the human: ") + goal +
        ("\nChoose one self-directed action. Do not ask for instructions." if autonomous else "") +
        "\nreply with exactly one verb call."})
    out = http_json(base.rstrip("/") + "/chat/completions", {
        "model": model, "messages": messages, "max_tokens": 80,
        "temperature": 0.4, "stream": False,
    })
    return clean_model_command(out["choices"][0]["message"].get("content", ""))


def parse_verb(text):
    try:
        node = ast.parse(text, mode="eval").body
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            raise ValueError
        if node.args:
            raise ValueError
        params = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords}
        if None in params:
            raise ValueError
        return node.func.id, params
    except Exception:
        raise ValueError("invalid one-verb reply: " + text)


def prediction_polarity(value):
    text = re.sub(r"\s+", " ", str(value or "")).strip().lower()
    if not text:
        return None
    if re.search(r"\b(?:not|no|never|won't|wouldn't|shouldn't|cannot|can't|fail|fails|failed|remain|stay|avoid|without|blocked)\b", text):
        return False
    if re.search(r"\b(?:should|will|can|produce|change|move|increase|decrease|reach|work|respond|accept|progress|clear|open|turn)\b", text):
        return True
    return None


def strategy_hint(model, action, context="unscoped"):
    action_model = (model or {}).get(action) or {}
    context_key = re.sub(r"\s+", " ", str(context or "unscoped")).strip()[:120] or "unscoped"
    scoped = (action_model.get("contexts") or {}).get(context_key) or action_model
    if scoped.get("stable_caution") or scoped.get("stable") is False and scoped.get("unresolved", 0) >= 2:
        return "avoid this action in this context"
    if scoped.get("unresolved", 0) >= 2 and float(scoped.get("prediction_confidence") or 0) < .28:
        return "gather a different kind of evidence before retrying"
    if scoped.get("learning_trend") == "declining" or "needs revision" in str(scoped.get("prediction_lesson", "")):
        return "vary the method and revise the prediction"
    if scoped.get("stable") and float(scoped.get("prediction_confidence") or 0) >= .7:
        return "reuse carefully because this context has a stable lesson"
    return "make one small reversible test and observe it"


def memory_key(action, context):
    clean_action = re.sub(r"\s+", " ", str(action or "unknown")).strip()[:80] or "unknown"
    clean_context = re.sub(r"\s+", " ", str(context or "unscoped")).strip()[:120] or "unscoped"
    return f"{clean_action} :: {clean_context}"


def kokoro_speak(url, voice, text):
    payload = json.dumps({
        "model": "kokoro", "input": str(text)[:180], "voice": voice,
        "response_format": "wav", "speed": 1.08,
    }).encode()
    req = urllib.request.Request(
        url.rstrip("/") + "/v1/audio/speech", data=payload,
        headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=90) as res:
        audio = res.read()
    raw_path = "/tmp/xemo-raw.wav"
    final_path = "/tmp/xemo-latest.wav"
    with open(raw_path, "wb") as wav:
        wav.write(audio)
    try:
        shutil.copyfile(raw_path, final_path)
    finally:
        try:
            os.unlink(raw_path)
        except FileNotFoundError:
            pass


class Xemo:
    def __init__(self, code, state_path=None):
        self.code = code
        self.ws = None
        self.awake = False
        self.distance = None
        self.lidar_scan = None
        self._range_event = asyncio.Event()
        self._lidar_event = asyncio.Event()
        self.motion_log = []
        self.predictions = []
        self.memories = []
        self.memory_meta = {}
        self.body_learning = {}
        self.state_path = Path(state_path).expanduser() if state_path else None
        self._load_learning()

    def _load_learning(self):
        if not self.state_path or not self.state_path.exists():
            return
        try:
            saved = json.loads(self.state_path.read_text())
            raw_predictions = saved.get("predictions", [])
            saved_memories = saved.get("memories", [])
            saved_models = saved.get("body_learning", {})
            if not isinstance(raw_predictions, list):
                raw_predictions = []
            if not isinstance(saved_memories, list):
                saved_memories = []
            canonical = {}
            loose = []
            for row in raw_predictions:
                if not isinstance(row, dict) or not row.get("action"):
                    continue
                attempt = str(row.get("attempt_id") or "").strip()
                if not attempt:
                    loose.append(row)
                    continue
                key = (str(row.get("action")), str(row.get("context", "unscoped")), attempt)
                canonical[key] = row
            rows = loose + list(canonical.values())
            rows.sort(key=lambda row: float(row.get("at", 0) or 0))
            self.predictions = []
            self.memories = []
            self.memory_meta = {}
            self.body_learning = {}
            prior_path = self.state_path
            self.state_path = None
            for row in rows[-40:]:
                verdict = row.get("verdict")
                result = {
                    "verified": verdict == "confirmed",
                    "inconclusive": verdict == "unresolved",
                    "observed": row.get("observed", "")
                }
                self.learn(row.get("action"), row.get("prediction", ""), result,
                           row.get("context", "unscoped"), row.get("attempt_id"))
                self.predictions[-1]["at"] = row.get("at", self.predictions[-1]["at"])
            self.state_path = prior_path
            for memory in saved_memories[-24:]:
                if memory not in self.memories:
                    self.memories.append(memory)
            if isinstance(saved_models, dict):
                for action, model in saved_models.items():
                    if action not in self.body_learning and isinstance(model, dict):
                        self.body_learning[action] = model
            self.memories = self.memories[-24:]
        except (OSError, ValueError, TypeError):
            self.predictions, self.memories, self.memory_meta, self.body_learning = [], [], {}, {}

    def _save_learning(self):
        if not self.state_path:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
            temp.write_text(json.dumps({
                "predictions": self.predictions[-40:],
                "memories": self.memories[-24:],
                "memory_meta": dict(list(self.memory_meta.items())[-48:]),
                "body_learning": self.body_learning,
            }, indent=2))
            temp.replace(self.state_path)
        except OSError:
            pass

    async def connect(self):
        self.ws = await websockets.connect(f"{RELAY}/d/{self.code}")
        await self.send({"t": "attach", "id": self.code, "code": self.code})
        asyncio.create_task(self._receive())

    async def _receive(self):
        async for raw in self.ws:
            try:
                msg = json.loads(raw)
            except Exception:
                continue
            if msg.get("t") == "status":
                self.awake = bool(msg.get("awake"))
            elif msg.get("t") == "range":
                self.distance = msg.get("cm")
                self._range_event.set()
            elif msg.get("t") == "lidar":
                self.lidar_scan = msg.get("scan")
                self._lidar_event.set()

    async def send(self, msg):
        await self.ws.send(json.dumps(msg))

    async def stop(self):
        await self.send({"t": "wheels", "left": 0, "right": 0})
        await self.send({"t": "drive", "linear": 0, "yaw": 0})
        await self.send({"t": "stop", "rid": "agent-stop"})

    def duty_left_ms(self):
        now = time.monotonic()
        self.motion_log = [(t, ms) for t, ms in self.motion_log if now - t < 60]
        return max(0, 20000 - sum(ms for _, ms in self.motion_log))

    async def move(self, linear, yaw, seconds):
        seconds = max(.2, min(4.0, float(seconds)))
        ms = int(seconds * 1000)
        if ms > self.duty_left_ms():
            return {
                "text": "motion budget spent; wait before moving",
                "verified": False,
                "inconclusive": True,
                "observed": "movement was not attempted because the duty budget was spent",
            }
        self.motion_log.append((time.monotonic(), ms))
        await self.look()
        before = self.distance
        end = time.monotonic() + seconds
        try:
            while time.monotonic() < end:
                await self.send({"t": "drive", "linear": linear, "yaw": yaw})
                await asyncio.sleep(.1)
        finally:
            await self.stop()
        await self.look()
        after = self.distance
        verified = before is not None and after is not None and abs(float(after) - float(before)) >= 4
        return {
            "text": f"movement complete ({seconds:.1f}s)",
            "verified": verified,
            "inconclusive": before is None or after is None,
            "observed": f"distance {before} -> {after}",
        }

    def learn(self, action, prediction, result, context="unscoped", attempt_id=None):
        if not isinstance(result, dict):
            return
        action = re.sub(r"\s+", " ", str(action or "unknown")).strip()[:100] or "unknown"
        context = re.sub(r"\s+", " ", str(context or "unscoped")).strip()[:120] or "unscoped"
        attempt_id = re.sub(r"\s+", " ", str(attempt_id or "")).strip()[:80]
        verdict = "unresolved" if result.get("inconclusive") else "confirmed" if result.get("verified") else "disconfirmed"
        polarity = prediction_polarity(prediction)
        prediction_matched = None if verdict == "unresolved" or polarity is None else polarity == bool(result.get("verified"))
        row = {
            "at": time.time(), "action": action, "prediction": prediction,
            "observed": result.get("observed", result.get("text", "")),
            "verdict": verdict,
            "prediction_matched": prediction_matched,
            "context": context,
            "attempt_id": attempt_id,
        }
        replaced = False
        if attempt_id:
            for index in range(len(self.predictions) - 1, -1, -1):
                prior = self.predictions[index]
                if (prior.get("attempt_id") == attempt_id and prior.get("action") == action
                        and prior.get("context", "unscoped") == context):
                    self.predictions[index] = row
                    replaced = True
                    break
        if not replaced:
            self.predictions.append(row)
        self.predictions = self.predictions[-40:]
        action_rows = [item for item in self.predictions if item.get("action") == action]
        model = self.body_learning.setdefault(action, {"attempts": 0, "successes": 0, "unresolved": 0})
        model["attempts"] = len(action_rows)
        model["successes"] = sum(item.get("verdict") == "confirmed" for item in action_rows)
        model["unresolved"] = sum(item.get("verdict") == "unresolved" for item in action_rows)
        if model["successes"] >= 2:
            memory = f"{action} repeatedly produced an observable change"
            if memory not in self.memories:
                self.memories.append(memory)
        history = [item for item in self.predictions if item is not row]
        comparable = [item for item in history if item.get("action") == action and item.get("verdict") != "unresolved" and isinstance(item.get("prediction_matched"), bool)][-5:]
        matches = sum(row.get("prediction_matched") is True for row in comparable)
        sample_size = len(comparable)
        current_sample = sample_size + (1 if isinstance(prediction_matched, bool) else 0)
        current_matches = matches + (1 if prediction_matched is True else 0)
        agreement = current_matches / current_sample if current_sample else 0
        model["prediction_consistency"] = round(agreement, 2) if current_sample else None
        model["prediction_confidence"] = round(.12 if verdict == "unresolved" else .15 + agreement * .75 * min(1, current_sample / 4), 2)
        curve = [item for item in action_rows if item.get("verdict") in {"confirmed", "disconfirmed"}][-8:]
        split = len(curve) // 2
        if split:
            early = curve[:split]
            recent = curve[-split:]
            early_rate = sum(row.get("verdict") == "confirmed" for row in early) / len(early)
            recent_rate = sum(row.get("verdict") == "confirmed" for row in recent) / len(recent)
            delta = round(recent_rate - early_rate, 2)
        else:
            delta = 0
        model["learning_delta"] = delta
        model["learning_trend"] = ("forming" if len(curve) < 4 else
                                    "improving" if delta >= .2 else
                                    "declining" if delta <= -.2 else "stable")
        model["stable"] = model["successes"] >= 2 and model["prediction_confidence"] >= .7
        context_rows = [item for item in action_rows if item.get("context", "unscoped") == context]
        context_model = model.setdefault("contexts", {}).setdefault(context, {})
        context_model["attempts"] = len(context_rows)
        context_model["successes"] = sum(row.get("verdict") == "confirmed" for row in context_rows)
        context_model["disconfirmed"] = sum(row.get("verdict") == "disconfirmed" for row in context_rows)
        context_model["unresolved"] = sum(row.get("verdict") == "unresolved" for row in context_rows)
        context_history = [item for item in history if item.get("action") == action and item.get("context", "unscoped") == context]
        context_comparable = [item for item in context_history if isinstance(item.get("prediction_matched"), bool)][-5:]
        context_matches = sum(item.get("prediction_matched") is True for item in context_comparable)
        context_current = prediction_matched
        context_sample = len(context_comparable) + (1 if isinstance(context_current, bool) else 0)
        context_total_matches = context_matches + (1 if context_current is True else 0)
        context_model["prediction_confidence"] = round(.12 if verdict == "unresolved" else .15 + (context_total_matches / context_sample if context_sample else 0) * .75 * min(1, context_sample / 4), 2)
        context_model["prediction_consistency"] = round(context_total_matches / context_sample, 2) if context_sample else None
        context_curve = [row for row in context_rows if row.get("verdict") in {"confirmed", "disconfirmed"}][-8:]
        context_split = len(context_curve) // 2
        context_delta = 0
        if context_split:
            early = context_curve[:context_split]
            recent = context_curve[-context_split:]
            context_delta = round(
                sum(row.get("verdict") == "confirmed" for row in recent) / len(recent)
                - sum(row.get("verdict") == "confirmed" for row in early) / len(early), 2)
        context_model["learning_delta"] = context_delta
        context_model["learning_trend"] = ("forming" if len(context_curve) < 4 else
                                             "improving" if context_delta >= .2 else
                                             "declining" if context_delta <= -.2 else "stable")
        context_model["prediction_lesson"] = ("predictions usually match here" if context_model["prediction_consistency"] is not None and context_model["prediction_consistency"] >= .7 else
                                               "prediction needs revision here" if context_model["prediction_consistency"] is not None else
                                               "prediction needs more comparable evidence here")
        context_model["stable"] = context_model["successes"] >= 2 and context_model["prediction_confidence"] >= .7
        context_model["stable_caution"] = context_model["successes"] == 0 and context_model["unresolved"] == 0 and context_model["attempts"] >= 2
        context_model["stable_lesson"] = context_model["successes"] >= 2 and context_model["disconfirmed"] == 0
        memory_id = memory_key(action, context)
        memory = self.memory_meta.setdefault(memory_id, {
            "action": action,
            "context": context,
            "confirmed": 0,
            "disconfirmed": 0,
            "unresolved": 0,
        })
        memory["confirmed"] = context_model["successes"]
        memory["disconfirmed"] = sum(row.get("verdict") == "disconfirmed" for row in context_rows)
        memory["unresolved"] = context_model["unresolved"]
        memory["predictionConsistency"] = context_model["prediction_consistency"]
        memory["predictionConfidence"] = context_model["prediction_confidence"]
        if memory["confirmed"] >= 2 and memory["disconfirmed"] == 0:
            memory["state"] = "stable lesson"
            memory["lesson"] = f"{action} repeatedly produced an observable change in {context}"
        elif memory["disconfirmed"] >= 2 and memory["confirmed"] == 0 and memory["unresolved"] == 0:
            memory["state"] = "stable caution"
            memory["lesson"] = f"{action} repeatedly failed to produce a verified change in {context}"
        elif memory["confirmed"] and memory["disconfirmed"]:
            memory["state"] = "conflicted"
            memory["lesson"] = f"{action} has conflicting evidence in {context}; vary the method"
        else:
            memory["state"] = "forming"
            memory["lesson"] = f"{action} still needs comparable evidence in {context}"
        memory["updatedAt"] = time.time()
        if memory["state"] in {"stable lesson", "stable caution"} and memory["lesson"] not in self.memories:
            self.memories.append(memory["lesson"])
        self.memories = self.memories[-24:]
        result["verdict"] = verdict
        self._save_learning()

    async def look(self):
        self._range_event.clear()
        await self.send({"t": "range"})
        try:
            await asyncio.wait_for(self._range_event.wait(), 2)
        except asyncio.TimeoutError:
            self.distance = None
        return {
            "text": "no echo" if self.distance is None else f"{self.distance} cm",
            "verified": self.distance is not None,
            "inconclusive": self.distance is None,
            "observed": f"distance sensor reading: {self.distance}",
        }

    async def scan(self):
        self._lidar_event.clear()
        await self.send({"t": "lidar"})
        try:
            await asyncio.wait_for(self._lidar_event.wait(), 2)
        except asyncio.TimeoutError:
            self.lidar_scan = None
        if not self.lidar_scan:
            return {
                "text": "no LiDAR fitted or no scan packet yet",
                "verified": False,
                "inconclusive": True,
                "observed": "LiDAR result unavailable",
            }
        points = self.lidar_scan.get("points", [])
        return {
            "text": f"LiDAR scan received ({len(points)} points; host SLAM can map it)",
            "verified": True,
            "inconclusive": False,
            "observed": f"LiDAR returned {len(points)} points",
        }


async def run(args):
    try:
        model = await asyncio.to_thread(choose_model, args.endpoint, args.model)
    except Exception as exc:
        raise SystemExit("model endpoint error: " + str(exc))
    bot = Xemo(args.code, args.state)
    await bot.connect()
    print(f"xemo agent connected · model: {model}")
    print("xemo is alive on its own · type a request at any time, or 'quit'.")
    history = []
    observation = {"robot": 1, "distance_cm": None, "duty_left_ms": 20000,
                   "learning": bot.body_learning, "memories": bot.memories[-4:],
                   "memory_consolidation": dict(list(bot.memory_meta.items())[-8:])}
    input_task = asyncio.create_task(asyncio.to_thread(input, "\nyou > "))
    while True:
        done, _ = await asyncio.wait({input_task}, timeout=18)
        autonomous = not done
        if done:
            goal = input_task.result().strip()
            input_task = asyncio.create_task(asyncio.to_thread(input, "\nyou > "))
        else:
            goal = "choose one meaningful next action from current senses, body lessons, and recent life"
            print("\nxemo's own thought >", goal)
        if goal.lower() in ("quit", "exit"):
            await bot.stop()
            return
        if not goal and not autonomous:
            continue
        try:
            reply = await asyncio.to_thread(
                ask_model, args.endpoint, model, history, goal, observation, autonomous)
            print("brain >", reply)
            verb, p = parse_verb(reply)
            attempt_id = f"agent-{time.time_ns()}"
            if verb == "speak":
                text = str(p.get("text", ""))[:180]
                await asyncio.to_thread(
                    kokoro_speak, args.kokoro, args.voice, text)
                result = "voice saved to /tmp/xemo-latest.wav (playback disabled)"
            elif verb == "forward":
                result = await bot.move(.65, 0, p.get("seconds", 1))
            elif verb == "backward":
                result = await bot.move(-.55, 0, p.get("seconds", 1))
            elif verb == "turn":
                degrees = max(-180, min(180, float(p.get("degrees", 45))))
                result = await bot.move(0, .6 if degrees > 0 else -.6,
                                        max(.3, abs(degrees) / 90 * .8))
            elif verb == "arm":
                deg = max(0, min(180, float(p.get("degrees", 90))))
                await bot.send({"t": "arms", "left": deg, "right": 90})
                result = {
                    "text": f"arm command sent to {deg:.0f} degrees",
                    "verified": False,
                    "inconclusive": True,
                    "observed": "arm position has no feedback sensor",
                }
            elif verb == "look":
                result = await bot.look()
            elif verb == "scan":
                result = await bot.scan()
            elif verb == "stop":
                await bot.stop()
                result = "stopped"
            else:
                raise ValueError("off-menu verb rejected: " + verb)
            if isinstance(result, dict):
                result_text = result.get("text", "action complete")
                predictions = {
                    "forward": "distance should change after moving forward",
                    "backward": "distance should change after moving backward",
                    "turn": "the orientation or distance reading should change after turning",
                    "arm": "the arm should move, but position feedback may be unavailable",
                    "look": "the distance sensor should return a current reading",
                    "scan": "the scanner should return a current scan",
                }
                bot.learn(verb, predictions.get(verb, "the action should produce an observable result"), result, goal, attempt_id)
            else:
                result_text = result
            print("xemo >", result_text)
            context = goal
            observation = {"robot": int(bot.awake), "distance_cm": bot.distance,
                           "lidar_points": len((bot.lidar_scan or {}).get("points", [])),
                           "duty_left_ms": bot.duty_left_ms(), "last_result": result_text,
                           "learning": bot.body_learning, "strategy": strategy_hint(bot.body_learning, verb, context),
                           "memories": bot.memories[-4:], "memory_consolidation": dict(list(bot.memory_meta.items())[-8:])}
            history += [{"role": "user", "content": ("[autonomous] " if autonomous else "") + goal},
                        {"role": "assistant", "content": reply}]
        except Exception as exc:
            await bot.stop()
            print("safe rejection >", exc)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="local AI brain for XEMO")
    ap.add_argument("--code", required=True)
    ap.add_argument("--endpoint", default=os.getenv("XEMO_MODEL_URL", "http://127.0.0.1:1234/v1"))
    ap.add_argument("--model", default=os.getenv("XEMO_MODEL", ""),
                    help="required; never auto-selects an existing model")
    ap.add_argument("--kokoro", default=os.getenv("XEMO_KOKORO_URL", "http://127.0.0.1:8881"))
    ap.add_argument("--voice", default=os.getenv("XEMO_VOICE", "bm_fable"))
    ap.add_argument("--state", default=os.getenv("XEMO_AGENT_STATE", str(Path.home() / ".xemo-agent-state.json")))
    asyncio.run(run(ap.parse_args()))
