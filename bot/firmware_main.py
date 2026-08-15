import network, socket, ssl, os, json, time, binascii, select, machine
from body import XemoBody
from action_engine import ActEngine

HOST = "growbot-relay.growbot.workers.dev"
DEVID = "gb-" + binascii.hexlify(machine.unique_id()).decode()[-6:]
PATH = "/d/" + DEVID

print("RESET_CAUSE", machine.reset_cause())
print("\n========================================")
print("  XEMO — GrowBot wheeled body")
print("  PAIRING CODE:  " + DEVID)
print("  Enter this code in the GrowBot app.")
print("========================================\n")

body = XemoBody()
DEADMAN_MS = 500
POLL_MS = 20

def ensure_wifi():
    w = network.WLAN(network.STA_IF)
    w.active(True)
    if not w.isconnected():
        try:
            import secrets
            w.connect(secrets.WIFI_SSID, secrets.WIFI_PASSWORD)
        except Exception as e:
            print("wifi err", e)
        for _ in range(150):
            if w.isconnected():
                break
            time.sleep_ms(100)
    ok = w.isconnected()
    if ok:
        print("WIFI_OK", w.ifconfig()[0])
    else:
        print("WIFI_FAIL")
    print("wifi:", ok, w.ifconfig()[0] if ok else "-")
    return ok

def ws_open():
    ai = socket.getaddrinfo(HOST, 443)[0][-1]
    raw = socket.socket()
    raw.connect(ai)
    s = ssl.wrap_socket(raw, server_hostname=HOST)
    key = binascii.b2a_base64(os.urandom(16)).strip().decode()
    req = ("GET %s HTTP/1.1\r\nHost: %s\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
           "Sec-WebSocket-Key: %s\r\nSec-WebSocket-Version: 13\r\n\r\n") % (PATH, HOST, key)
    s.write(req.encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        c = s.read(1)
        if not c:
            break
        resp += c
    ok = b" 101 " in resp
    print("handshake:", "OK" if ok else "FAIL", resp.split(b"\r\n")[0])
    return (s, raw) if ok else (None, None)

def send_text(s, txt):
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
ROUTINES = {"wiggle": [{"l": 60, "r": 120, "ms": 400}, {"l": 120, "r": 60, "ms": 400},
                       {"l": 60, "r": 120, "ms": 400}, {"l": 120, "r": 60, "ms": 400},
                       {"l": 90, "r": 90, "ms": 300}]}

def _handle(s, pl):
    """Dispatch one text frame. Returns the lane kind so serve() can manage the dead-man."""
    try:
        m = json.loads(pl)
    except Exception:
        return None
    t = m.get("t")
    if t == "drive":
        try:
            body.drive(m.get("linear", 0), m.get("yaw", 0))
        except Exception:
            body.stop_wheels()
        return "drive"
    if t == "wheels":
        try:
            body.wheels(m.get("left", 0), m.get("right", 0))
        except Exception:
            body.stop_wheels()
        return "drive"
    if t == "arms":
        eng.clear()
        ok = True
        try:
            body.write_arms(float(m.get("left", 90)), float(m.get("right", 90)))
        except Exception:
            ok = False
        if "rid" in m:
            send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1 if ok else 0,
                                     "queued_ms": 0}))
        return "arms"
    if t == "arms_release":
        eng.clear()
        body.release_arms()
        return "arms"
    if t == "range":
        cm = body.distance_cm()
        send_text(s, json.dumps({"t": "range", "cm": cm}))
        return "range"
    if t == "lidar":
        scan = body.lidar_snapshot()
        send_text(s, json.dumps({"t": "lidar", "scan": scan}))
        return "lidar"
    if t == "pose":
        eng.clear()
        try:
            ls, rs = m.get("lr", "90,90").split(",")
            apply_pose(float(ls), float(rs))
        except Exception:
            pass
        if "seq" in m:
            send_text(s, json.dumps({"t": "ack", "seq": m["seq"], "ts": m.get("ts", 0)}))
        return "pose"
    if t == "act":
        ok, q = eng.enqueue(m.get("steps", []), m.get("mode", "replace"))
        send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1 if ok else 0,
                                 "queued_ms": (q if ok else 0)}))
        return "act"
    if t == "routine":
        ok, q = eng.enqueue(ROUTINES.get(m.get("name", ""), []), "replace")
        send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1 if ok else 0,
                                 "queued_ms": (q if ok else 0)}))
        return "act"
    if t == "stop":
        eng.clear(); body.stop_all()
        send_text(s, json.dumps({"t": "ack", "rid": m.get("rid"), "ok": 1, "queued_ms": 0}))
        return "stop"
    return None

def serve(s, raw):
    poll = select.poll(); poll.register(raw, select.POLLIN)
    caps = ["drive", "arms", "range"]
    if body.lidar:
        caps.append("lidar")
    send_text(s, json.dumps({"t": "hello", "id": DEVID,
                             "body": "differential-drive",
                             "caps": caps}))
    print("hello sent; wheels + arms ready (dead-man %dms)" % DEADMAN_MS)
    eng.clear()
    walk_on = False
    last_pose = time.ticks_ms()
    drive_on = False
    last_drive = time.ticks_ms()
    n = 0; nlast = 0; last = time.ticks_ms()
    while True:
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
        body.lidar_poll()
        eng.tick()
        if walk_on and not eng.active and time.ticks_diff(time.ticks_ms(), last_pose) > DEADMAN_MS:
            _act_release(); walk_on = False
            print("dead-man: walk limp (silence)")
        if drive_on and time.ticks_diff(time.ticks_ms(), last_drive) > DEADMAN_MS:
            body.stop_wheels(); drive_on = False
            print("dead-man: wheels stopped")

def main():
    time.sleep(2)
    while True:
        try:
            if not ensure_wifi():
                time.sleep(2); continue
            s, raw = ws_open()
            if s:
                serve(s, raw)
        except Exception as e:
            print("loop err:", e)
        body.stop_all()
        time.sleep(2)

def boot_calibration():
    body.stop_all()

boot_calibration()
main()
