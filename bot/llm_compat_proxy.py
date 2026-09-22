#!/usr/bin/env python3
"""OpenAI-compatible shim for clients that still send response_format=json_object.

Run LM Studio on one port and this shim on the port used by the client:
    python3 llm_compat_proxy.py --listen-port 1235 --upstream-port 1234
"""
import argparse
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def permissive_json_schema():
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "robot_command",
            "strict": False,
            "schema": {
                "type": "object",
                "properties": {
                    "say": {"type": "string"},
                    "walk": {
                        "type": "object",
                        "properties": {
                            "gait": {"type": "string"},
                            "dir": {"type": "string"},
                            "secs": {"type": "number", "minimum": 0.5, "maximum": 15},
                            "gain": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                        "required": ["secs"],
                        "additionalProperties": True,
                    },
                },
                "additionalProperties": True,
            },
        },
    }


def rewrite_payload(raw):
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        return raw
    response_format = payload.get("response_format")
    if isinstance(response_format, dict) and response_format.get("type") == "json_object":
        payload["response_format"] = permissive_json_schema()
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def movement_intent(raw):
    """Infer only an explicit latest-user movement request for repair."""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None
    messages = payload.get("messages") if isinstance(payload, dict) else None
    users = [m for m in (messages or []) if isinstance(m, dict) and m.get("role") == "user"]
    latest = users[-1] if users else None
    content = latest.get("content", "") if latest else ""
    if isinstance(content, list):
        content = " ".join(str(x.get("text", "")) for x in content if isinstance(x, dict))
    text = str(content).lower()
    # GrowBot follows an action with a synthetic "continue current activity"
    # turn. In that case retain only the recent movement context, not an old
    # command from the whole conversation.
    if re.search(r"\bcontinue\s+(?:your\s+)?current\s+activity\b", text):
        recent = []
        for message in users[-4:]:
            value = message.get("content", "")
            if isinstance(value, list):
                value = " ".join(str(x.get("text", "")) for x in value if isinstance(x, dict))
            recent.append(str(value).lower())
        text = " ".join(recent)
    if re.search(r"\b(?:stop|halt|cancel)\b", text):
        return {"stop": True}
    if re.search(r"\bwiggle\b[^.\n]{0,30}\barms?\b|\barms?\b[^.\n]{0,30}\bwiggle\b", text):
        return {"gesture": "wiggle"}
    if re.search(r"\bwave\b[^.\n]{0,30}\barms?\b|\barms?\b[^.\n]{0,30}\bwave\b", text):
        return {"gesture": "wave"}
    if re.search(r"\b(?:roll|move|go|drive)\b[^.\n]{0,30}\bforward\b|\bforward\b", text):
        return {"walk": {"gait": "official", "dir": "fwd", "secs": 3}}
    if re.search(r"\b(?:roll|move|go|drive)\b[^.\n]{0,30}\bbackward\b|\bbackward\b|\breverse\b", text):
        return {"walk": {"gait": "official", "dir": "back", "secs": 3}}
    if re.search(r"\bturn\b[^.\n]{0,20}\bleft\b|\bleft\b", text):
        return {"walk": {"gait": "official", "dir": "left", "secs": 1}}
    if re.search(r"\bturn\b[^.\n]{0,20}\bright\b|\bright\b", text):
        return {"walk": {"gait": "official", "dir": "right", "secs": 1}}
    return None


def repair_content(content, intent):
    if not intent:
        return content
    try:
        value = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        value = {"say": str(content or "")}
    if not isinstance(value, dict):
        value = {"say": str(content or "")}
    if "stop" in intent:
        value["stop"] = True
    elif "gesture" in intent:
        value.pop("body", None)
        value.pop("move", None)
        value.pop("walk", None)
        value["gesture"] = intent["gesture"]
        value.pop("error", None)
    elif "walk" in intent and "walk" not in value:
        # Qwen often follows the long GrowBot prompt by emitting the arm-style
        # `body.steps` lane even when the latest request is a wheel walk.  The
        # wheel-kit consumer does not execute that lane.  Make the explicit
        # movement request authoritative and expose the official walk contract.
        value.pop("body", None)
        value.pop("move", None)
        value.pop("gesture", None)
        value["walk"] = intent["walk"]
        value.pop("error", None)
    elif not any(key in value for key in ("walk", "body", "move", "gesture", "stop")):
        value.update(intent)
    elif "walk" in intent and isinstance(value.get("walk"), dict):
        if float(value["walk"].get("secs", 0) or 0) <= 0:
            value["walk"] = intent["walk"]
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def immediate_movement_response(intent, stream):
    value = {"say": "", **intent}
    content = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    packet_id = "chatcmpl-growbot-movement"
    created = int(time.time())
    if stream:
        event = json.dumps({"id": packet_id, "object": "chat.completion.chunk",
                            "created": created, "model": "qwen/qwen3-vl-8b",
                            "system_fingerprint": "growbot-compat",
                            "choices": [{"index": 0,
                                         "delta": {"role": "assistant", "content": content},
                                         "finish_reason": "stop"}]},
                           ensure_ascii=False)
        return ("text/event-stream", ("data: " + event + "\n\ndata: [DONE]\n\n").encode())
    packet = {"id": packet_id, "object": "chat.completion", "created": created,
              "model": "qwen/qwen3-vl-8b",
              "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                            "finish_reason": "stop"}]}
    return ("application/json", json.dumps(packet, ensure_ascii=False).encode())


class Proxy(BaseHTTPRequestHandler):
    upstream = "http://127.0.0.1:1234"

    def _headers(self, content_type="application/json"):
        self.send_header("content-type", content_type)
        self.send_header("access-control-allow-origin", "*")
        self.send_header("access-control-allow-headers", "content-type, authorization")
        self.send_header("access-control-allow-methods", "GET, POST, OPTIONS")

    def do_OPTIONS(self):
        self.send_response(204)
        self._headers()
        self.end_headers()

    def do_GET(self):
        self._forward("GET", None)

    def do_POST(self):
        length = min(int(self.headers.get("content-length", "0")), 2_000_000)
        raw = self.rfile.read(length)
        try:
            is_chat = self.path.endswith("/chat/completions") or self.path.endswith("/chat/stream")
            body = rewrite_payload(raw) if is_chat else raw
            if is_chat:
                intent = movement_intent(body)
                if intent and ("walk" in intent or "gesture" in intent or "stop" in intent):
                    payload = json.loads(body.decode("utf-8"))
                    stream = bool(payload.get("stream"))
                    content_type, data = immediate_movement_response(intent, stream)
                    self.send_response(200)
                    self._headers(content_type)
                    self.send_header("content-length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    self.wfile.flush()
                    return
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self._reply({"error": f"invalid JSON request: {exc}"}, 400)
            return
        self._forward("POST", body)

    def _forward(self, method, body):
        try:
            req = Request(
                self.upstream.rstrip("/") + self.path,
                data=body,
                method=method,
                headers={
                    "content-type": self.headers.get("content-type", "application/json"),
                    "accept": self.headers.get("accept", "application/json"),
                    **({"authorization": self.headers["authorization"]}
                       if self.headers.get("authorization") else {}),
                },
            )
            with urlopen(req, timeout=180) as response:
                content_type = response.headers.get("content-type", "application/json")
                intent = movement_intent(body or b"")
                self.send_response(response.status)
                self._headers(content_type)
                streaming = "text/event-stream" in content_type.lower()
                if not streaming:
                    data = response.read()
                    try:
                        packet = json.loads(data.decode("utf-8"))
                        message = packet.get("choices", [{}])[0].get("message", {})
                        if isinstance(message, dict) and "content" in message:
                            message["content"] = repair_content(message["content"], intent)
                            data = json.dumps(packet, ensure_ascii=False).encode("utf-8")
                    except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, IndexError, TypeError):
                        pass
                    self.send_header("content-length", str(len(data)))
                self.end_headers()
                if streaming:
                    # Preserve streaming latency. Explicit movement is handled
                    # above; all other streams should reach the browser as the
                    # model produces them instead of being buffered to EOF.
                    while True:
                        chunk = response.read(4096)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
                else:
                    self.wfile.write(data)
        except HTTPError as exc:
            detail = exc.read(4096).decode("utf-8", "replace")
            self._reply({"error": f"LM Studio HTTP {exc.code}", "detail": detail}, 502)
        except (URLError, TimeoutError, OSError) as exc:
            self._reply({"error": f"LM Studio unavailable: {exc}"}, 503)

    def _reply(self, payload, status):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._headers()
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print("llm-compat:", fmt % args, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, default=1235)
    parser.add_argument("--upstream", default="http://127.0.0.1:1234")
    args = parser.parse_args()
    Proxy.upstream = args.upstream
    server = ThreadingHTTPServer((args.listen_host, args.listen_port), Proxy)
    print(f"GrowBot JSON shim listening on {args.listen_host}:{args.listen_port}", flush=True)
    print(f"Forwarding to LM Studio at {args.upstream}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
