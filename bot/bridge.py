#!/usr/bin/env python3
"""Serve XEMO's phone UI and proxy its local LM Studio brain."""
import argparse
import gc
import gzip
import hmac
import json
import mimetypes
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

# Keep direct launches (`python3 bot/bridge.py`) on the same dependency
# environment as the supported web launcher.
_local_python = Path(__file__).resolve().parents[1] / ".venv" / "bin" / "python"
if _local_python.is_file() and Path(os.path.realpath(os.sys.executable)) != Path(os.path.realpath(_local_python)):
    os.execv(str(_local_python), [str(_local_python), *os.sys.argv])

try:
    from life_state import LifeStateStore
except ImportError:
    from .life_state import LifeStateStore
try:
    from life_coordinator import LifeCoordinator
except ImportError:
    from .life_coordinator import LifeCoordinator

_whisper = None
_whisper_name = None
_whisper_lock = threading.Lock()
_brain_lock = threading.Lock()
_brain_cancel_lock = threading.Lock()
_brain_cancel_generation = 0
_brain_active_lock = threading.Lock()
_brain_active_response = None
_brain_active_kind = ""
KOKORO_URL = os.getenv("XEMO_KOKORO_URL", "http://127.0.0.1:8881").rstrip("/")
DEFAULT_BRAIN_MODEL = "qwen/qwen3-vl-8b"


def acquire_brain_slot(autonomous):
    """Let a human turn take over while an older autonomous request unwinds."""
    if autonomous:
        return _brain_lock.acquire(blocking=False)
    return _brain_lock.acquire(timeout=12.0)


def brain_cancel_generation():
    with _brain_cancel_lock:
        return _brain_cancel_generation


def brain_request_superseded(generation):
    return brain_cancel_generation() != generation


def brain_transport_failure(exc, autonomous, generation):
    if autonomous and brain_request_superseded(generation):
        return {"skipped": True, "reason": "autonomous thought superseded by a newer turn"}, 200
    if brain_request_superseded(generation):
        return {"error": "human thought superseded before a complete answer was returned", "retryable": True}, 409
    return {"error": f"LM Studio unavailable: {exc}", "retryable": True}, 503


def cancel_autonomous_brain():
    global _brain_cancel_generation
    with _brain_cancel_lock:
        _brain_cancel_generation += 1
        generation = _brain_cancel_generation
    with _brain_active_lock:
        response = _brain_active_response if _brain_active_kind == "autonomous" else None
    if response is not None:
        try:
            response.close()
        except Exception:
            pass
    return generation


def cancel_active_brain():
    """Close any older upstream generation before a newer human turn starts."""
    global _brain_cancel_generation
    with _brain_cancel_lock:
        _brain_cancel_generation += 1
    with _brain_active_lock:
        response = _brain_active_response
    if response is not None:
        try:
            response.close()
        except Exception:
            pass


def set_active_brain_response(response, autonomous):
    global _brain_active_response, _brain_active_kind
    with _brain_active_lock:
        _brain_active_response = response
        _brain_active_kind = "autonomous" if autonomous else "person"


def clear_active_brain_response(response):
    global _brain_active_response, _brain_active_kind
    with _brain_active_lock:
        if _brain_active_response is response:
            _brain_active_response = None
            _brain_active_kind = ""


def prepare_brain_body(body):
    """Require JSON output while preserving an app-supplied schema.

    The local Qwen/LM Studio endpoint rejects ``json_object`` and accepts
    ``json_schema`` (or ``text``).  XEMO and GrowBot use different command
    fields, so the bridge supplies a permissive object schema only when the
    caller did not provide its own schema.
    """
    try:
        payload = json.loads(body.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return body
    if not isinstance(payload, dict):
        return body
    response_format = payload.get("response_format")
    if (not isinstance(response_format, dict)
            or response_format.get("type") in (None, "json_object")):
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "robot_command",
                "strict": False,
                "schema": {
                    "type": "object",
                    "additionalProperties": True,
                },
            },
        }
    if "qwen3" in str(payload.get("model", "")).lower() and "chat_template_kwargs" not in payload:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def life_brain_call(model, prompt):
    """Ask LM Studio for one queued initiative without bypassing brain ownership."""
    if not _brain_lock.acquire(blocking=False):
        return ""
    response = None
    try:
        request_body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 220,
            "temperature": .75,
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "robot_command",
                    "strict": False,
                    "schema": {"type": "object", "additionalProperties": True},
                },
            },
        }
        if "qwen3" in str(model).lower():
            request_body["chat_template_kwargs"] = {"enable_thinking": False}
        body = json.dumps(request_body, ensure_ascii=False).encode("utf-8")
        req = Request(
            XemoWeb.brain.rstrip("/") + "/chat/completions",
            data=body,
            method="POST",
            headers={"content-type": "application/json"},
        )
        with urlopen(req, timeout=brain_timeout_seconds(body, autonomous=True)) as response:
            set_active_brain_response(response, True)
            payload = json.loads(response.read(64_000).decode("utf-8"))
        content = str(((payload.get("choices") or [{}])[0].get("message") or {}).get("content", ""))
        if not content.strip():
            print("xemo life brain: empty model content", flush=True)
        return content
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
        print(f"xemo life brain: {type(exc).__name__}: {exc}", flush=True)
        return ""
    finally:
        clear_active_brain_response(response)
        _brain_lock.release()


def brain_timeout_seconds(body, autonomous=False, requested_ms=None):
    """Give each local generation a deadline sized to its actual context."""
    try:
        payload = json.loads(body.decode("utf-8")) if body else {}
        messages = payload.get("messages") or []
        model = str(payload.get("model", ""))
        chars = len(json.dumps(messages, ensure_ascii=False))
        base = 45 if autonomous else 30
        context = min(30, max(5, ((chars + 5999) // 6000) * 5))
        model_cost = 15 if "8b" in model.lower() else 10
        vision = 20 if "image_url" in json.dumps(messages) else 0
        reasoning = 30 if "qwen3" in model.lower() else 0
        computed = min(180, base + context + model_cost + vision + reasoning)
        requested = max(10, min(180, int(requested_ms) / 1000)) if requested_ms else 0
        return max(computed, requested)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return 90 if autonomous else 60


def probe_http_service(base_url, path="/models", timeout=1.5):
    """Return a small, JSON-safe health result without exposing upstream errors."""
    url = base_url.rstrip("/") + path
    try:
        req = Request(url, method="GET", headers={"accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            return {"status": "ok" if 200 <= status < 300 else "error", "http": status}
    except HTTPError as exc:
        return {"status": "error", "http": int(exc.code)}
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        return {"status": "offline", "error": type(exc).__name__}


def _model_id_matches(expected, available):
    expected = str(expected or "").strip().lower()
    available = str(available or "").strip().lower()
    if not expected or not available:
        return False
    if expected == available:
        return True
    return available.startswith(expected + ":")


def probe_brain_service(base_url, expected_model="", timeout=1.5):
    """Check that the upstream exposes the configured chat model, not just any model."""
    url = base_url.rstrip("/") + "/models"
    try:
        req = Request(url, method="GET", headers={"accept": "application/json"})
        with urlopen(req, timeout=timeout) as response:
            status = int(getattr(response, "status", 200))
            if not 200 <= status < 300:
                return {"status": "error", "http": status}
            payload = json.loads(response.read(64_000).decode("utf-8"))
            models = payload.get("data") if isinstance(payload, dict) else None
            ids = [item.get("id", "") for item in models or [] if isinstance(item, dict)]
            if not expected_model:
                return {"status": "ok", "http": status, "models": ids}
            if any(_model_id_matches(expected_model, model_id) for model_id in ids):
                return {"status": "ok", "http": status, "model": expected_model}
            return {"status": "error", "http": status, "error": "configured chat model is not loaded", "model": expected_model, "available": ids}
    except HTTPError as exc:
        return {"status": "error", "http": int(exc.code)}
    except (URLError, TimeoutError, OSError, ValueError, TypeError, UnicodeDecodeError) as exc:
        return {"status": "offline", "error": type(exc).__name__}


def deep_health_snapshot(handler):
    """Describe local dependencies separately so one missing service is diagnosable."""
    brain = probe_brain_service(handler.brain, getattr(handler, "brain_model", ""))
    tts = probe_http_service(getattr(handler, "kokoro_url", KOKORO_URL), "/health")
    coordinator = getattr(handler, "life_coordinator", None)
    life_status = "ready" if handler.life_store else "disabled"
    autonomy_status = "enabled" if coordinator and coordinator.enabled else "disabled"
    return {
        "ok": brain["status"] == "ok",
        "service": "xemo-web",
        "dependencies": {
            "brain": brain,
            "kokoro": tts,
            "life_journal": {"status": life_status, "autonomy": autonomy_status},
        },
    }


class BoundedThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 8

    def __init__(self, *args, max_workers=8, **kwargs):
        self._slots = threading.BoundedSemaphore(max_workers)
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        self._slots.acquire()
        try:
            super().process_request(request, client_address)
        except Exception:
            self._slots.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._slots.release()


class XemoWeb(BaseHTTPRequestHandler):
    root = Path(__file__).resolve().parent.parent / "gui"
    brain = "http://127.0.0.1:1234/v1"
    brain_model = os.environ.get("XEMO_BRAIN_MODEL", DEFAULT_BRAIN_MODEL)
    kokoro_url = KOKORO_URL
    life_store = None
    life_token = ""
    life_coordinator = None

    def send_xemo_headers(self, status=200, content_type="application/json", content_encoding=None, content_length=None):
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("cache-control", "no-store")
        if content_encoding:
            self.send_header("content-encoding", content_encoding)
        if content_length is not None:
            self.send_header("content-length", str(content_length))
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "content-type, x-xemo-kind, x-xemo-whisper-model, x-xemo-life-token")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
        self.send_header("permissions-policy", "camera=(self), microphone=(self), accelerometer=(self), gyroscope=(self)")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_xemo_headers(204)

    def do_GET(self):
        request_path = urlsplit(self.path).path
        if request_path == "/api/health":
            if parse_qs(urlsplit(self.path).query).get("deep") == ["1"]:
                return self.reply(deep_health_snapshot(self))
            return self.reply({"ok": True, "service": "xemo-web"})
        if request_path == "/api/life":
            if not self.life_authorized():
                return self.reply({"error": "life journal is not authorized"}, 404)
            return self.reply(self.life_store.snapshot() if self.life_store else {"schema": 1})
        if request_path == "/api/models":
            return self.proxy("GET", "/models")
        name = "index.html" if request_path in ("/", "/index.html") else request_path.lstrip("/")
        path = (self.root / name).resolve()
        if self.root not in path.parents or not path.is_file():
            return self.reply({"error": "not found"}, 404)
        data = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        encoded = None
        if content_type in ("text/javascript", "application/javascript", "text/css", "text/html") and "gzip" in self.headers.get("accept-encoding", "").lower():
            encoded = gzip.compress(data, compresslevel=6, mtime=0)
        payload = encoded if encoded is not None else data
        self.send_xemo_headers(200, content_type, "gzip" if encoded is not None else None, len(payload))
        self.wfile.write(payload)

    def do_POST(self):
        if self.path == "/api/chat/completions":
            return self.proxy_chat()
        if self.path == "/api/chat/stream":
            return self.proxy_chat_stream()
        if self.path == "/api/tts":
            return self.proxy_audio()
        if self.path == "/api/transcribe":
            return self.transcribe()
        if self.path == "/api/life":
            return self.update_life_state()
        if self.path == "/api/life/claim":
            return self.claim_life_initiative()
        if self.path == "/api/life/initiative/outcome":
            return self.complete_life_initiative()
        if self.path == "/api/life/goal/claim":
            return self.claim_life_goal()
        if self.path == "/api/life/goal/outcome":
            return self.complete_life_goal()
        self.reply({"error": "not found"}, 404)

    def update_life_state(self):
        if not self.life_authorized():
            return self.reply({"error": "life journal is not authorized"}, 404)
        try:
            length = min(int(self.headers.get("content-length", "0")), 32_000)
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(payload, dict):
                return self.reply({"error": "life checkpoint must be an object"}, 400)
            if not self.life_store:
                return self.reply({"error": "life journal unavailable"}, 503)
            return self.reply(self.life_store.update(payload))
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            return self.reply({"error": f"invalid life checkpoint: {exc}"}, 400)
        except OSError as exc:
            return self.reply({"error": f"life checkpoint could not be saved: {exc}"}, 503)

    def life_authorized(self):
        expected = str(self.life_token or "")
        supplied = self.headers.get("x-xemo-life-token", "")
        return bool(expected) and bool(supplied) and hmac.compare_digest(supplied, expected)

    def claim_life_initiative(self):
        if not self.life_authorized():
            return self.reply({"error": "life journal is not authorized"}, 404)
        try:
            length = min(int(self.headers.get("content-length", "0")), 4_000)
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            initiative_id = payload.get("id") if isinstance(payload, dict) else ""
            claimed = self.life_store.claim_initiative(initiative_id) if self.life_store else None
            return self.reply(claimed or {"claimed": False}, 200)
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            return self.reply({"error": f"invalid initiative claim: {exc}"}, 400)

    def complete_life_initiative(self):
        if not self.life_authorized():
            return self.reply({"error": "life journal is not authorized"}, 404)
        try:
            length = min(int(self.headers.get("content-length", "0")), 4_000)
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            initiative_id = payload.get("id") if isinstance(payload, dict) else ""
            outcome = payload.get("outcome") if isinstance(payload, dict) else ""
            result = payload.get("result") if isinstance(payload, dict) else ""
            evidence = payload.get("evidence") if isinstance(payload, dict) else []
            completed = self.life_store.complete_initiative(initiative_id, outcome, result, evidence) if self.life_store else None
            return self.reply(completed or {"completed": False}, 200)
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            return self.reply({"error": f"invalid initiative outcome: {exc}"}, 400)

    def claim_life_goal(self):
        if not self.life_authorized():
            return self.reply({"error": "life journal is not authorized"}, 404)
        try:
            length = min(int(self.headers.get("content-length", "0")), 4_000)
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            proposal_id = payload.get("id") if isinstance(payload, dict) else ""
            claimed = self.life_store.claim_goal_proposal(proposal_id) if self.life_store else None
            return self.reply(claimed or {"claimed": False}, 200)
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            return self.reply({"error": f"invalid goal proposal claim: {exc}"}, 400)

    def complete_life_goal(self):
        if not self.life_authorized():
            return self.reply({"error": "life journal is not authorized"}, 404)
        try:
            length = min(int(self.headers.get("content-length", "0")), 4_000)
            payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            proposal_id = payload.get("id") if isinstance(payload, dict) else ""
            outcome = payload.get("outcome") if isinstance(payload, dict) else ""
            result = payload.get("result") if isinstance(payload, dict) else ""
            completed = self.life_store.complete_goal_proposal(proposal_id, outcome, result) if self.life_store else None
            return self.reply(completed or {"completed": False}, 200)
        except (ValueError, TypeError, UnicodeDecodeError) as exc:
            return self.reply({"error": f"invalid goal outcome: {exc}"}, 400)

    def proxy_audio(self):
        try:
            length = min(int(self.headers.get("content-length", "0")), 32_000)
            body = self.rfile.read(length)
            payload = {}
            try:
                payload = json.loads(body.decode("utf-8"))
                payload.pop("pitch", None)
                body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            except (ValueError, TypeError, UnicodeDecodeError):
                pass
            req = Request(
                self.kokoro_url.rstrip("/") + "/v1/audio/speech",
                data=body, method="POST",
                headers={"content-type": "application/json"},
            )
            input_chars = len(str(payload.get("input", ""))) if isinstance(payload, dict) else 0
            with urlopen(req, timeout=min(30, max(12, 12 + input_chars * .09))) as res:
                data = res.read()
                content_type = res.headers.get_content_type()
            self.send_xemo_headers(200, content_type)
            self.wfile.write(data)
        except HTTPError as exc:
            self.reply({"error": f"Kokoro HTTP {exc.code}"}, 502)
        except (URLError, TimeoutError, OSError) as exc:
            self.reply({"error": f"Kokoro unavailable: {exc}"}, 503)

    def transcribe(self):
        global _whisper, _whisper_name
        length = int(self.headers.get("content-length", "0"))
        if length < 800 or length > 5_000_000:
            return self.reply({"error": "audio clip must be 0.8KB–5MB"}, 400)
        content_type = self.headers.get("content-type", "")
        suffix = ".wav" if "wav" in content_type else ".mp4" if "mp4" in content_type else ".ogg" if "ogg" in content_type else ".webm"
        path = ""
        try:
            with tempfile.NamedTemporaryFile(prefix="xemo-stt-", suffix=suffix, delete=False) as audio:
                path = audio.name
                audio.write(self.rfile.read(length))
            with _whisper_lock:
                requested = self.headers.get(
                    "x-xemo-whisper-model",
                    os.environ.get("XEMO_WHISPER_MODEL", "base"),
                ).lower()
                if requested not in ("base", "small"):
                    requested = "base"
                if _whisper is None or _whisper_name != requested:
                    _whisper = None
                    gc.collect()
                    from faster_whisper import WhisperModel
                    _whisper = WhisperModel(
                        requested,
                        device="cpu", compute_type="int8",
                        cpu_threads=max(2, min(4, os.cpu_count() or 2)),
                        num_workers=1,
                    )
                    _whisper_name = requested
                command_mode = self.headers.get("x-xemo-stt-mode", "").lower() == "command"
                # The browser already performs bounded VAD for command clips.
                # A greedy decode plus no second VAD pass removes most CPU
                # latency on the robot host while preserving model choice.
                segments, info = _whisper.transcribe(
                    path, language=None,
                    beam_size=1 if command_mode else 3,
                    best_of=1 if command_mode else 3,
                    vad_filter=not command_mode, condition_on_previous_text=False,
                    vad_parameters=None if command_mode else {
                        "min_speech_duration_ms": 280,
                        "min_silence_duration_ms": 650,
                        "speech_pad_ms": 180,
                        "max_speech_duration_s": 8,
                    },
                    temperature=0,
                    no_speech_threshold=0.55,
                    log_prob_threshold=-1.0,
                    compression_ratio_threshold=2.2,
                )
                segments = list(segments)
                text = " ".join(seg.text.strip() for seg in segments).strip()
                no_speech = (
                    sum(float(getattr(seg, "no_speech_prob", 0.0)) for seg in segments)
                    / len(segments) if segments else 1.0
                )
                avg_logprob = (
                    sum(float(getattr(seg, "avg_logprob", -2.0)) for seg in segments)
                    / len(segments) if segments else -2.0
                )
                if no_speech > 0.72 or avg_logprob < -1.35:
                    text = ""
            self.reply({
                "text": text,
                "language": getattr(info, "language", None),
                "language_probability": round(float(getattr(info, "language_probability", 0.0)), 3),
                "no_speech_probability": round(no_speech, 3),
                "avg_logprob": round(avg_logprob, 3),
            })
        except Exception as exc:
            self.reply({"error": f"transcription failed: {exc}"}, 500)
        finally:
            if path:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass

    def proxy(self, method, suffix, autonomous=False):
        request_generation = brain_cancel_generation()
        try:
            body = None
            if method == "POST":
                length = min(int(self.headers.get("content-length", "0")), 256_000)
                body = prepare_brain_body(self.rfile.read(length))
            req = Request(
                self.brain.rstrip("/") + suffix,
                data=body,
                method=method,
                headers={"content-type": "application/json"},
            )
            timeout = brain_timeout_seconds(body, autonomous, self.headers.get("x-xemo-timeout-ms"))
            with urlopen(req, timeout=timeout) as res:
                set_active_brain_response(res, autonomous)
                data = res.read()
                self.send_xemo_headers(res.status, "application/json")
                self.wfile.write(data)
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read(4096).decode("utf-8", "replace").strip()
            except Exception:
                pass
            self.reply({
                "error": f"LM Studio HTTP {exc.code}",
                "detail": detail[:1000],
            }, 502)
        except (BrokenPipeError, ConnectionResetError):
            return
        except (URLError, TimeoutError, OSError) as exc:
            payload, status = brain_transport_failure(exc, autonomous, request_generation)
            self.reply(payload, status)
        finally:
            clear_active_brain_response(locals().get("res"))

    def proxy_chat(self):
        """Keep XEMO to one LM Studio slot; stale autonomous beats never queue."""
        autonomous = self.headers.get("x-xemo-kind", "") == "autonomous"
        if not autonomous:
            cancel_active_brain()
            cancel_autonomous_brain()
        acquired = acquire_brain_slot(autonomous)
        if not acquired:
            if autonomous:
                return self.reply({"skipped": True, "reason": "brain busy; autonomous beat skipped"}, 200)
            return self.reply({"error": "brain busy; human turn could not take the slot"}, 409)
        try:
            self.proxy("POST", "/chat/completions", autonomous)
        finally:
            _brain_lock.release()

    def proxy_chat_stream(self):
        """Forward LM Studio SSE without buffering it, keeping the single brain slot."""
        autonomous = self.headers.get("x-xemo-kind", "") == "autonomous"
        generation = brain_cancel_generation()
        if not autonomous:
            cancel_active_brain()
            generation = cancel_autonomous_brain()
        acquired = acquire_brain_slot(autonomous)
        if not acquired:
            return self.reply({"error": "brain busy; autonomous beat skipped"}, 409)
        try:
            if autonomous and brain_request_superseded(generation):
                return self.reply({"skipped": True, "reason": "thought superseded by a newer turn"}, 200)
            length = min(int(self.headers.get("content-length", "0")), 256_000)
            body = prepare_brain_body(self.rfile.read(length))
            req = Request(
                self.brain.rstrip("/") + "/chat/completions",
                data=body,
                method="POST",
                headers={"content-type": "application/json", "accept": "text/event-stream"},
            )
            timeout = brain_timeout_seconds(body, autonomous, self.headers.get("x-xemo-timeout-ms"))
            with urlopen(req, timeout=timeout) as res:
                set_active_brain_response(res, autonomous)
                self.send_xemo_headers(res.status, "text/event-stream")
                while True:
                    if autonomous and brain_request_superseded(generation):
                        try:
                            res.close()
                        except Exception:
                            pass
                        break
                    reader = getattr(res, "read1", None)
                    chunk = reader(4096) if reader else res.read(4096)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except HTTPError as exc:
            detail = ""
            try:
                detail = exc.read(4096).decode("utf-8", "replace").strip()
            except Exception:
                pass
            self.reply({"error": f"LM Studio HTTP {exc.code}", "detail": detail[:1000]}, 502)
        except (BrokenPipeError, ConnectionResetError):
            return
        except (URLError, TimeoutError, OSError) as exc:
            payload, status = brain_transport_failure(exc, autonomous, generation)
            self.reply(payload, status)
        finally:
            clear_active_brain_response(locals().get("res"))
            _brain_lock.release()

    def reply(self, payload, status=200):
        data = json.dumps(payload).encode()
        try:
            self.send_xemo_headers(status)
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return False
        return True

    def log_message(self, fmt, *args):
        print("xemo web:", fmt % args)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--brain", default="http://127.0.0.1:1234/v1")
    ap.add_argument("--life-model", default=os.environ.get("XEMO_LIFE_MODEL") or os.environ.get("XEMO_BRAIN_MODEL", DEFAULT_BRAIN_MODEL))
    ap.add_argument("--life-autonomy", action="store_true", default=os.environ.get("XEMO_LIFE_AUTONOMY", "1" if os.environ.get("XEMO_LIFE_TOKEN", "").strip() else "0") == "1")
    args = ap.parse_args()
    XemoWeb.brain = args.brain
    XemoWeb.brain_model = os.environ.get("XEMO_BRAIN_MODEL", DEFAULT_BRAIN_MODEL)
    XemoWeb.life_store = LifeStateStore(instance_id=os.environ.get("XEMO_INSTANCE_ID", ""))
    XemoWeb.life_token = os.environ.get("XEMO_LIFE_TOKEN", "").strip()
    XemoWeb.life_coordinator = LifeCoordinator(
        XemoWeb.life_store,
        brain_call=life_brain_call,
        model=args.life_model,
        enabled=args.life_autonomy and bool(XemoWeb.life_token),
    )
    XemoWeb.life_coordinator.start()
    server = BoundedThreadingHTTPServer((args.host, args.port), XemoWeb, max_workers=8)
    print(f"XEMO web ready on http://{args.host}:{args.port}")
    print(f"brain proxy -> {args.brain}")
    try:
        server.serve_forever()
    finally:
        XemoWeb.life_coordinator.stop()
