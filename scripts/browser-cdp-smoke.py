#!/usr/bin/env python3
"""Run a small isolated Chromium smoke check against the XEMO web app."""

import json
import sys
import time
import urllib.request

import websocket

_next_id = 1


def command(socket, method, params=None, ident=None):
    global _next_id
    if ident is None:
        ident = _next_id
        _next_id += 1
    socket.send(json.dumps({"id": ident, "method": method, "params": params or {}}))
    while True:
        message = json.loads(socket.recv())
        if message.get("id") == ident:
            return message


def evaluate(socket, expression, ident=None):
    result = command(socket, "Runtime.evaluate", {
        "expression": expression,
        "awaitPromise": True,
        "returnByValue": True,
    }, ident)
    return result.get("result", {}).get("result", {}).get("value")


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765"
    targets = json.load(urllib.request.urlopen("http://127.0.0.1:9223/json", timeout=3))
    target = next(item for item in targets if item.get("type") == "page")
    socket = websocket.create_connection(target["webSocketDebuggerUrl"], origin="http://127.0.0.1:9223", timeout=10)
    errors = []
    failures = []
    responses = []
    command(socket, "Runtime.enable")
    command(socket, "Log.enable")
    command(socket, "Network.enable")
    command(socket, "Page.enable")
    command(socket, "Browser.grantPermissions", {"origin": base, "permissions": ["audioCapture"]})
    command(socket, "Page.navigate", {"url": base + "/?xemo_test=cdp-smoke"})
    deadline = time.time() + 8
    while time.time() < deadline:
        socket.settimeout(max(.1, deadline - time.time()))
        try:
            event = json.loads(socket.recv())
        except (TimeoutError, websocket.WebSocketTimeoutException):
            break
        method = event.get("method", "")
        params = event.get("params", {})
        if method == "Runtime.exceptionThrown":
            errors.append(params.get("exceptionDetails", {}).get("text", "runtime exception"))
        elif method in {"Runtime.consoleAPICalled", "Log.entryAdded"}:
            entry = params.get("entry", params)
            if entry.get("type") in {"error", "assert"} or entry.get("level") == "error":
                errors.append(entry.get("text", "console error"))
        elif method == "Network.loadingFailed":
            failures.append(params.get("errorText", "network failure"))
        elif method == "Network.responseReceived" and "/api/chat/" in params.get("response", {}).get("url", ""):
            response = params["response"]
            responses.append({"url": response.get("url"), "status": response.get("status")})
    socket.settimeout(60)
    result = evaluate(socket, """(async () => {
        document.querySelector('#birthResume')?.click();
        document.querySelector('#typeBtn')?.click();
        const input = document.querySelector('#chatInput');
        const send = document.querySelector('#chatSend');
        const before = document.querySelector('#caption')?.textContent || '';
        if (input && send) {
            input.value = 'Please answer this test in one short natural sentence about the weather.';
            input.dispatchEvent(new Event('input', {bubbles: true}));
            send.click();
        }
        const started = Date.now();
        while (Date.now() - started < 30000) {
            await new Promise(resolve => setTimeout(resolve, 250));
            const caption = document.querySelector('#caption')?.textContent || '';
            if (caption && caption !== before && !/^thinking[.…]*$/i.test(caption.trim()) && !/^waking[.…]*$/i.test(caption.trim())) break;
        }
        const checks = {
            title: document.title,
            runtimeScript: document.querySelector('script[src*="app-runtime"]')?.src || '',
            serviceWorker: navigator.serviceWorker?.controller?.scriptURL || '',
            runtime: typeof window.xemoBrain === 'object',
            speech: typeof window.xemoSpeech === 'object',
            buttons: document.querySelectorAll('button').length,
            mediaDevices: !!navigator.mediaDevices,
            answer: document.querySelector('#caption')?.textContent || '',
            brainBusy: !!window.xemoBrain?.busy,
            liveState: window.render_game_to_text?.() || null,
            pageLog: (document.querySelector('#brainLog')?.textContent || '').slice(-1000),
        };
        try {
            const stream = await navigator.mediaDevices.getUserMedia({audio: true});
            checks.microphone = stream.getAudioTracks().length > 0;
            stream.getTracks().forEach(track => track.stop());
        } catch (error) {
            checks.microphone = false;
            checks.microphoneError = error.name;
        }
        return checks;
    })()""")
    print(json.dumps({"result": result, "consoleErrors": errors, "networkFailures": failures, "chatResponses": responses}, sort_keys=True))
    socket.close()
    return 1 if errors or failures or not result or not result.get("runtime") or not result.get("speech") else 0


if __name__ == "__main__":
    raise SystemExit(main())
