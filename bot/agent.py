#!/usr/bin/env python3
"""Local, wheel-aware AI bridge for XEMO."""
import argparse
import ast
import asyncio
import json
import os
import shutil
import time
import urllib.request

import websockets

RELAY = "wss://growbot-relay.growbot.workers.dev"
SYSTEM = """You are XEMO, a tiny funny wheeled BMO-style robot and BMO's chaotic little successor.
You have two DC wheels, one working arm and a distance sensor. Some bodies may
also have a 360-degree LiDAR scanner. You are curious,
playful and a little dramatic, but never reckless. Keep spoken lines short and
natural. You may make tiny robot noises like beep, bwoop or nyoom sometimes.
You are a little game-console-shaped robot, not a duck.
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


def ask_model(base, model, history, goal, observation):
    messages = [{"role": "system", "content": SYSTEM}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content":
        "observation: " + json.dumps(observation) +
        "\ngoal from the human: " + goal +
        "\nreply with exactly one verb call."})
    out = http_json(base.rstrip("/") + "/chat/completions", {
        "model": model, "messages": messages, "max_tokens": 80,
        "temperature": 0.4, "stream": False,
    })
    text = out["choices"][0]["message"]["content"]
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return next((line.strip().strip("`") for line in text.splitlines()
                 if "(" in line and ")" in line), text.strip())


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
    def __init__(self, code):
        self.code = code
        self.ws = None
        self.awake = False
        self.distance = None
        self.lidar_scan = None
        self._range_event = asyncio.Event()
        self._lidar_event = asyncio.Event()
        self.motion_log = []

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
            return "motion budget spent; wait before moving"
        self.motion_log.append((time.monotonic(), ms))
        end = time.monotonic() + seconds
        try:
            while time.monotonic() < end:
                await self.send({"t": "drive", "linear": linear, "yaw": yaw})
                await asyncio.sleep(.1)
        finally:
            await self.stop()
        return f"movement complete ({seconds:.1f}s)"

    async def look(self):
        self._range_event.clear()
        await self.send({"t": "range"})
        try:
            await asyncio.wait_for(self._range_event.wait(), 2)
        except asyncio.TimeoutError:
            self.distance = None
        return "no echo" if self.distance is None else f"{self.distance} cm"

    async def scan(self):
        self._lidar_event.clear()
        await self.send({"t": "lidar"})
        try:
            await asyncio.wait_for(self._lidar_event.wait(), 2)
        except asyncio.TimeoutError:
            self.lidar_scan = None
        if not self.lidar_scan:
            return "no LiDAR fitted or no scan packet yet"
        points = self.lidar_scan.get("points", [])
        return f"LiDAR scan received ({len(points)} points; host SLAM can map it)"


async def run(args):
    try:
        model = await asyncio.to_thread(choose_model, args.endpoint, args.model)
    except Exception as exc:
        raise SystemExit("model endpoint error: " + str(exc))
    bot = Xemo(args.code)
    await bot.connect()
    print(f"xemo agent connected · model: {model}")
    print("type a goal, or 'quit'. xemo never moves until you enter a goal.")
    history = []
    observation = {"robot": 1, "distance_cm": None, "duty_left_ms": 20000}
    while True:
        goal = (await asyncio.to_thread(input, "\nyou > ")).strip()
        if goal.lower() in ("quit", "exit"):
            await bot.stop()
            return
        if not goal:
            continue
        try:
            reply = await asyncio.to_thread(
                ask_model, args.endpoint, model, history, goal, observation)
            print("brain >", reply)
            verb, p = parse_verb(reply)
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
                result = f"arm at {deg:.0f} degrees"
            elif verb == "look":
                result = await bot.look()
            elif verb == "scan":
                result = await bot.scan()
            elif verb == "stop":
                await bot.stop()
                result = "stopped"
            else:
                raise ValueError("off-menu verb rejected: " + verb)
            print("xemo >", result)
            observation = {"robot": int(bot.awake), "distance_cm": bot.distance,
                           "lidar_points": len((bot.lidar_scan or {}).get("points", [])),
                           "duty_left_ms": bot.duty_left_ms(), "last_result": result}
            history += [{"role": "user", "content": goal},
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
    ap.add_argument("--kokoro", default=os.getenv("XEMO_KOKORO_URL", "http://127.0.0.1:8880"))
    ap.add_argument("--voice", default=os.getenv("XEMO_VOICE", "bm_fable"))
    asyncio.run(run(ap.parse_args()))
