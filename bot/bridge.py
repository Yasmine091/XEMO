#!/usr/bin/env python3
"""Serve XEMO's phone UI and proxy its local LM Studio brain."""
import argparse
import gc
import gzip
import json
import mimetypes
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

_whisper = None
_whisper_name = None
_whisper_lock = threading.Lock()
_brain_lock = threading.Lock()
_brain_cancel_lock = threading.Lock()
_brain_cancel_generation = 0
_brain_active_lock = threading.Lock()
_brain_active_response = None
_brain_active_kind = ""


def acquire_brain_slot(autonomous):
    """Never let a human conversation queue behind a dead model forever."""
    if autonomous:
        return _brain_lock.acquire(blocking=False)
    return _brain_lock.acquire(timeout=1.25)


def brain_cancel_generation():
    with _brain_cancel_lock:
        return _brain_cancel_generation


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
    """Preserve the caller/model's reasoning policy; never force fast mode."""
    return body


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

    def send_xemo_headers(self, status=200, content_type="application/json", content_encoding=None, content_length=None):
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("cache-control", "no-store")
        if content_encoding:
            self.send_header("content-encoding", content_encoding)
        if content_length is not None:
            self.send_header("content-length", str(content_length))
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "content-type, x-xemo-kind, x-xemo-whisper-model")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")
        self.send_header("permissions-policy", "camera=(self), microphone=(self), accelerometer=(self), gyroscope=(self)")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_xemo_headers(204)

    def do_GET(self):
        request_path = urlsplit(self.path).path
        if request_path == "/api/health":
            return self.reply({"ok": True, "service": "xemo-web"})
        if request_path == "/api/models":
            return self.proxy("GET", "/models")
        name = "xemo-remote.html" if request_path in ("/", "/index.html") else request_path.lstrip("/")
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
        self.reply({"error": "not found"}, 404)

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
                "http://127.0.0.1:8881/v1/audio/speech",
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
                segments, info = _whisper.transcribe(
                    path, language=None, beam_size=3, best_of=3,
                    vad_filter=True, condition_on_previous_text=False,
                    vad_parameters={
                        "min_speech_duration_ms": 280,
                        "min_silence_duration_ms": 650,
                        "speech_pad_ms": 180,
                        "max_speech_duration_s": 8,
                    },
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
        except (URLError, TimeoutError, OSError) as exc:
            self.reply({"error": f"LM Studio unavailable: {exc}"}, 503)
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
            return self.reply({"error": "brain busy; autonomous beat skipped"}, 409)
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
            if autonomous and brain_cancel_generation() != generation:
                return self.reply({"error": "autonomous thought superseded"}, 409)
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
                    if autonomous and brain_cancel_generation() != generation:
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
        except (URLError, TimeoutError, OSError) as exc:
            try:
                self.reply({"error": f"LM Studio unavailable: {exc}"}, 503)
            except Exception:
                pass
        finally:
            clear_active_brain_response(locals().get("res"))
            _brain_lock.release()

    def reply(self, payload, status=200):
        data = json.dumps(payload).encode()
        self.send_xemo_headers(status)
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("xemo web:", fmt % args)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--brain", default="http://127.0.0.1:1234/v1")
    args = ap.parse_args()
    XemoWeb.brain = args.brain
    server = BoundedThreadingHTTPServer((args.host, args.port), XemoWeb, max_workers=8)
    print(f"XEMO web ready on http://{args.host}:{args.port}")
    print(f"brain proxy -> {args.brain}")
    server.serve_forever()
