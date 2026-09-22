import network, socket, ssl, os, json, time, binascii, select, machine
try:
    from body import XemoBody
except ImportError:
    from XemoBody import XemoBody
try:
    from action_engine import ActEngine
except ImportError:
    from act_engine import ActEngine

HOST = "growbot-relay.growbot.workers.dev"
DEVID = "gb-" + binascii.hexlify(machine.unique_id()).decode()[-6:]
PATH = "/d/" + DEVID
FIRMWARE_VERSION = "xemo-growbot-compatible-4-positional270"

print("RESET_CAUSE", machine.reset_cause())
print("\n========================================")
print("  XEMO — GrowBot wheeled body")
print("  PAIRING CODE:  " + DEVID)
print("  Enter this code in the GrowBot app.")
print("========================================\n")

body = XemoBody()
DEADMAN_MS = 500
POLL_MS = 20
NET_TIMEOUT_S = 6
PING_MS = 10000
LINK_DEAD_MS = 25000
WIFI_RESET_EVERY = 3
HARD_RESET_AFTER = 10
WDT_MS = 8000
# Normal GrowBot remains the arm/servo path. The official wheel-kit path is
# explicit: it uses the `pose`/`act` lanes, which are handled below by the
# wheel driver. XEMO's GUI can still select its own wheel adapter explicitly.
BODY_PROFILE = "xemo-full"
ARM_POSITIONS = [135.0, 135.0]
_trace_at = 0
_wdt = None
wlan = network.WLAN(network.STA_IF)

def feed():
    if _wdt:
        _wdt.feed()

def sleep_fed(ms):
    while ms > 0:
        feed()
        time.sleep_ms(min(ms, 200))
        ms -= 200

def trace_command(text):
    global _trace_at
    now = time.ticks_ms()
    if time.ticks_diff(now, _trace_at) >= 1000:
        _trace_at = now
        print("CMD", text)

def ensure_wifi():
    wlan.active(True)
    if not wlan.isconnected():
        try:
            import secrets
            password = getattr(secrets, "WIFI_PASSWORD", None) or getattr(secrets, "WIFI_PASS", "")
            wlan.connect(secrets.WIFI_SSID, password)
        except Exception as e:
            print("wifi err", e)
        for _ in range(150):
            if wlan.isconnected():
                break
            feed(); time.sleep_ms(100)
    ok = wlan.isconnected()
    if ok:
        print("WIFI_OK", wlan.ifconfig()[0])
    else:
        print("WIFI_FAIL")
    print("wifi:", ok, wlan.ifconfig()[0] if ok else "-")
    return ok

def wifi_reset():
    print("wifi: bouncing the radio")
    try: wlan.disconnect()
    except Exception: pass
    try: wlan.active(False)
    except Exception: pass
    sleep_fed(1000)
    wlan.active(True)

def ws_open():
    feed()
    ai = socket.getaddrinfo(HOST, 443)[0][-1]
    raw = socket.socket()
    try:
        raw.settimeout(NET_TIMEOUT_S)
        raw.connect(ai)
        feed()
        s = ssl.wrap_socket(raw, server_hostname=HOST)
    except Exception:
        raw.close()
        raise
    key = binascii.b2a_base64(os.urandom(16)).strip().decode()
    req = ("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n") % (PATH, HOST, key)
    s.write(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        feed()
        c = s.read(1)
        if not c:
            break
        resp += c
    ok = b" 101 " in resp
    print("handshake:", "OK" if ok else "FAIL", resp.split(b"\r\n")[0])
    if not ok:
        try:
            s.close()
        except Exception:
            pass
        try:
            raw.close()
        except Exception:
            pass
        return (None, None)
    return s, raw

def send_text(s, txt):
    feed()
    p = txt.encode()
    n = len(p)
    mask = os.urandom(4)
    if n < 126:
        hdr = bytes([0x81, 0x80 | n])
    else:
        hdr = bytes([0x81, 0x80 | 126, (n >> 8) & 0xFF, n & 0xFF])
    mp = bytearray(n)
    for i in range(n):
        mp[i] = p[i] ^ mask[i & 3]
    s.write(hdr + mask + bytes(mp))

def recvn(s, n):
    b = b""
    while len(b) < n:
        feed()
        c = s.read(n - len(b))
        if not c:
            return None
        b += c
    return b

def _frame_after(s, b0):
    b1 = recvn(s, 1)
    if not b1:
        return (None, None)
    op = b0[0] & 0x0F
    ln = b1[0] & 0x7F
    if ln == 126:
        e = recvn(s, 2); ln = (e[0] << 8) | e[1]
    elif ln == 127:
        e = recvn(s, 8); ln = 0
        for b in e:
            ln = (ln << 8) | b
    masked = b1[0] & 0x80
    mask = recvn(s, 4) if masked else None
    pl = recvn(s, ln) if ln else b""
    if masked and pl:
        pl = bytes(pl[i] ^ mask[i & 3] for i in range(ln))
    return (op, pl)

def apply_pose(l, r):
    body.write_arms(l, r)

def _act_write(l, r):
    body.write_arms(l, r)
def _act_release():
    body.release_arms()
eng = ActEngine(_act_write, _act_release, time.ticks_ms, time.ticks_diff)
def _wheelkit_write(left, right):
    body.wheelkit_write(1, left)
    body.wheelkit_write(3, right)
def _wheelkit_release():
    body.wheelkit_release()
wheel_eng = ActEngine(_wheelkit_write, _wheelkit_release, time.ticks_ms, time.ticks_diff)
ROUTINES = {"wiggle": [{"l": 60, "r": 120, "ms": 400}, {"l": 120, "r": 60, "ms": 400},
                       {"l": 60, "r": 120, "ms": 400}, {"l": 120, "r": 60, "ms": 400},
                       {"l": 90, "r": 90, "ms": 300}]}

def _handle(s, pl):
    """Dispatch one text frame. Returns the lane kind so serve() can manage the dead-man."""
    # The current growbot.dev wheel walker sends the canonical pose as raw
    # WebSocket text (`"L,R"`), while relay/test clients may wrap the same
    # pair in JSON. Accept both forms; never drop the official raw lane.
    raw_pose = False
    try:
        m = json.loads(pl)
    except Exception:
        try:
            raw = pl.decode().strip()
            left, right = raw.split(",", 1)
            float(left); float(right)
            # The classic growbot.dev /ws lane is a leg gait, not a wheel
            # throttle pair. Keep the marker so the body can convert it to
            # forward differential-drive motion instead of alternating turns.
            m = {"t": "pose", "lr": raw, "_raw_walk": True}
            raw_pose = True
        except Exception:
            return None
    global BODY_PROFILE
    t = m.get("t")
    if t == "attach":
        # The hosted GrowBot harness identifies itself through the canonical
        # pose/act lanes. An explicit profile is also accepted for local XEMO.
        requested = str(m.get("profile", "")).lower()
        if requested in ("growbot", "growbot-wheels", "wheelkit"):
            BODY_PROFILE = "growbot-wheels"
        elif requested in ("xemo", "xemo-full", "full"):
            BODY_PROFILE = "xemo-full"
        trace_command("attach profile=%s id=%s code=%s" %
                      (requested or "(none)", m.get("id", ""), m.get("code", "")))
        if "rid" in m:
            send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"),
                                     "ok": 1, "queued_ms": 0,
                                     "fw": FIRMWARE_VERSION,
                                     "profile": BODY_PROFILE}))
        return "control"
    if t == "drive":
        trace_command("drive")
        try:
            body.drive(m.get("linear", 0), m.get("yaw", 0))
        except Exception:
            body.stop_wheels()
        return "drive"
    if t == "wheels":
        wheel_eng.clear()
        trace_command("wheels %s %s" % (m.get("left", 0), m.get("right", 0)))
        ok = True
        try:
            body.wheels(m.get("left", 0), m.get("right", 0))
        except Exception:
            ok = False
            body.stop_wheels()
        if "rid" in m:
            send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1 if ok else 0,
                                     "queued_ms": 0}))
        return "drive"
    if t == "arms":
        BODY_PROFILE = "xemo-full"
        wheel_eng.clear()
        eng.clear()
        ok = True
        try:
            # Partial arm packets are intentional: a one-arm movement omits
            # the other side, which must hold its last commanded position.
            # Do not default an omitted side to 90° or it will visibly move.
            if "left" in m:
                ARM_POSITIONS[0] = float(m["left"])
            if "right" in m:
                ARM_POSITIONS[1] = float(m["right"])
            body.write_arms(ARM_POSITIONS[0], ARM_POSITIONS[1])
        except Exception:
            ok = False
        if "rid" in m:
            send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1 if ok else 0,
                                     "queued_ms": 0}))
        return "arms"
    if t == "arms_release":
        BODY_PROFILE = "xemo-full"
        wheel_eng.clear()
        eng.clear()
        body.release_arms()
        return "arms"
    if t == "range":
        cm = body.distance_cm()
        send_text(s, json.dumps({"t": "range", "cm": cm}))
        return "range"
    if t == "walk":
        # Accept the high-level GrowBot walk contract as well as raw wheel-kit
        # poses.  The relay may forward walk directly; older firmware silently
        # discarded it because it only knew the pose/act lanes.
        BODY_PROFILE = "growbot-wheels"
        eng.clear()
        wheel_eng.clear()
        direction = str(m.get("dir", "fwd")).lower()
        try:
            secs = max(0.5, min(15.0, float(m.get("secs", 3))))
        except (TypeError, ValueError, OverflowError):
            secs = 3.0
        poses = {
            "fwd": (0, 180),
            "back": (180, 0),
            "left": (180, 180),
            "right": (0, 0),
        }
        left, right = poses.get(direction, poses["fwd"])
        trace_command("walk %s %.1f" % (direction, secs))
        ok, queued = wheel_eng.enqueue([
            {"l": left, "r": right, "ms": int(secs * 1000)},
            {"l": 90, "r": 90, "ms": 120},
        ], "replace")
        if "rid" in m:
            send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"),
                                     "ok": 1 if ok else 0,
                                     "queued_ms": queued if ok else 0}))
        return "act" if ok else None
    if t == "lidar":
        scan = body.lidar_snapshot()
        send_text(s, json.dumps({"t": "lidar", "scan": scan}))
        return "lidar"
    if t == "pose":
        BODY_PROFILE = "growbot-wheels"
        eng.clear()
        wheel_eng.clear()
        try:
            lr = m.get("lr", None)
            if lr is None:
                if "l" in m or "r" in m:
                    lr = [m.get("l", 90), m.get("r", 90)]
                else:
                    lr = "90,90"
            if isinstance(lr, (list, tuple)):
                ls, rs = lr[0], lr[1]
            else:
                ls, rs = str(lr).split(",", 1)
            if m.get("_raw_walk"):
                body.wheelkit_gait_pose(float(ls), float(rs))
            else:
                body.wheelkit_write(1, float(ls))
                body.wheelkit_write(3, float(rs))
            snapshot = body.motion_snapshot()
            if abs(float(ls) - 90.0) > 1.0 or abs(float(rs) - 90.0) > 1.0:
                print("POSE", ls, rs, "->", snapshot["target"], snapshot["output"])
            else:
                trace_command("pose %s %s -> %s" % (ls, rs, snapshot["target"]))
        except Exception as e:
            print("pose parse error:", repr(e), repr(m))
        if "seq" in m or "rid" in m:
            reply = {"t": "ack", "ok": 1, "ts": m.get("ts", 0)}
            if "seq" in m:
                reply["seq"] = m["seq"]
            if "rid" in m:
                reply["rid"] = m["rid"]
            send_text(s, json.dumps(reply))
        return "pose"
    if t == "act":
        BODY_PROFILE = "growbot-wheels"
        eng.clear()
        trace_command("act %s" % len(m.get("steps", [])))
        ok, q = wheel_eng.enqueue(m.get("steps", []), m.get("mode", "replace"))
        send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1 if ok else 0,
                                 "queued_ms": (q if ok else 0)}))
        return "act"
    if t == "routine":
        BODY_PROFILE = "growbot-wheels"
        eng.clear()
        ok, q = wheel_eng.enqueue(ROUTINES.get(m.get("name", ""), []), "replace")
        send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1 if ok else 0,
                                 "queued_ms": (q if ok else 0)}))
        return "act"
    if t == "stop":
        eng.clear(); wheel_eng.clear(); body.stop_all()
        send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1, "queued_ms": 0}))
        return "stop"
    trace_command("unknown t=%s keys=%s" % (t, ",".join(m.keys())))
    return None

def serve(s, raw):
    global _wdt
    poll = select.poll(); poll.register(raw, select.POLLIN)
    caps = ["drive", "wheels", "arms", "range", "pose", "act", "walk", "stop"]
    if body.lidar:
        caps.append("lidar")
    send_text(s, json.dumps({"t": "hello", "id": DEVID,
                             "fw": FIRMWARE_VERSION,
                             "body": "differential-drive",
                             "caps": caps}))
    print("hello sent; wheels + arms ready (dead-man %dms)" % DEADMAN_MS)
    if _wdt is None:
        _wdt = machine.WDT(timeout=WDT_MS)
        print("hw watchdog armed (%dms)" % WDT_MS)
    eng.clear()
    wheel_eng.clear()
    walk_on = False
    now = time.ticks_ms()
    last_pose = now
    last_rx = now
    last_ping = now
    drive_on = False
    last_drive = now
    last_telemetry = time.ticks_ms()
    n = 0; nlast = 0; last = now
    while True:
        feed()
        b0 = None
        try:
            if poll.poll(POLL_MS):
                b0 = s.read(1)
        except OSError as e:
            print("read err:", e); return
        if b0 == b"":
            print("conn closed by relay"); return
        if b0:
            op, pl = _frame_after(s, b0)
            if op is None or op == 0x8:
                print("conn closed by relay"); return
            last_rx = time.ticks_ms()
            if op == 0x9:
                s.write(bytes([0x8A, 0x80]) + os.urandom(4))
            elif op == 0x1:
                kind = _handle(s, pl)
                if kind == "drive":
                    drive_on = True; last_drive = time.ticks_ms()
                if kind == "pose":
                    walk_on = True; last_pose = time.ticks_ms()
                    n += 1
                    now = time.ticks_ms()
                    if time.ticks_diff(now, last) >= 1000:
                        print("poses", n, "rate", n - nlast, "Hz"); nlast = n; last = now
                elif kind in ("act", "stop"):
                    walk_on = False
                    if kind == "stop":
                        drive_on = False
        else:
            now = time.ticks_ms()
            if not wlan.isconnected():
                print("wifi dropped"); return
            if time.ticks_diff(now, last_rx) > LINK_DEAD_MS:
                print("link dead: nothing heard for %ds, re-dialing" % (LINK_DEAD_MS // 1000)); return
            if (time.ticks_diff(now, last_rx) > PING_MS and
                    time.ticks_diff(now, last_ping) > PING_MS):
                s.write(bytes([0x89, 0x80]) + os.urandom(4))
                last_ping = now
        body.lidar_poll()
        body.motion_tick()
        eng.tick()
        wheel_eng.tick()
        now = time.ticks_ms()
        if time.ticks_diff(now, last_telemetry) >= 400:
            last_telemetry = now
            try:
                motion = body.motion_snapshot()
                send_text(s, json.dumps({"t": "body", "id": DEVID, "v": 1,
                                         "fw": FIRMWARE_VERSION,
                                         "drive": 1 if drive_on else 0,
                                         "target": motion["target"],
                                         "output": motion["output"],
                                         "deadman_ms": DEADMAN_MS}))
            except Exception:
                pass
        if walk_on and not wheel_eng.active and time.ticks_diff(time.ticks_ms(), last_pose) > DEADMAN_MS:
            _wheelkit_release(); walk_on = False
            print("dead-man: walk limp (silence)")
        if drive_on and time.ticks_diff(time.ticks_ms(), last_drive) > DEADMAN_MS:
            body.stop_wheels(); drive_on = False
            print("dead-man: wheels stopped")

def main():
    sleep_fed(2000)
    fails = 0
    while True:
        s = raw = None
        t0 = time.ticks_ms()
        try:
            if ensure_wifi():
                s, raw = ws_open()
                if s:
                    serve(s, raw)
                    if time.ticks_diff(time.ticks_ms(), t0) > 30000:
                        fails = 0
        except Exception as e:
            print("loop err:", e)
        for x in (s, raw):
            try:
                if x:
                    x.close()
            except Exception:
                pass
        eng.clear()
        wheel_eng.clear()
        try:
            body.stop_all()
        except Exception:
            pass
        fails += 1
        if fails >= HARD_RESET_AFTER:
            print("self-heal: machine.reset()")
            sleep_fed(200)
            machine.reset()
        if fails % WIFI_RESET_EVERY == 0:
            try:
                wifi_reset()
            except Exception as e:
                print("wifi reset err:", e)
        wait = min(30000, 1000 << min(fails, 5))
        print("re-dial in %ds (fail %d)" % (wait // 1000, fails))
        sleep_fed(wait)

def boot_calibration():
    body.stop_all()

boot_calibration()
main()
