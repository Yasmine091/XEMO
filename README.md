# XEMO

XEMO is my little robot person project.

It has two parts:

- gui/ is the phone and browser face. It handles the senses, conversation, memory, speech, goals, and the live brain view.
- bot/ is the local bridge plus the small-body firmware for the wheeled robot.

The idea is simple: XEMO should be able to notice things, talk naturally, remember what matters, choose small goals, and act carefully when the body is connected.

## What it uses

- a local OpenAI-compatible model server
- Kokoro for the story voice
- a browser for the face, camera, microphone, touch, and memory
- a small Wi-Fi robot body with wheels, arms, and distance sensing

The bridge uses `http://127.0.0.1:8881` for Kokoro by default. Set
`XEMO_KOKORO_URL` when the voice service runs elsewhere; the speech proxy and
deep-health check use the same setting.

## Run the browser app

Start the local bridge:

    ./scripts/run-web.sh

Then open the address printed by the bridge. The model server should be available at the local OpenAI-compatible endpoint, or set XEMO_BRAIN_URL.

### Check the local services

The bridge has a shallow health check for the web server and a deep check for
the brain, Kokoro, and life journal separately:

    curl http://127.0.0.1:8765/api/health
    curl 'http://127.0.0.1:8765/api/health?deep=1'

When opening XEMO from another device, replace `127.0.0.1` with the computer's
LAN address. The deep check is useful before testing speech or autonomy because
it distinguishes an unavailable dependency from a broken browser path.

The focused local checks are:

    python3 -m unittest bot.test_bridge bot.test_health bot.test_body_hardware bot.test_firmware_contract bot.test_life_state bot.test_life_coordinator bot.test_aliveness_eval -q
    node gui/build-gui.mjs
    node gui/check-runtime-contract.mjs
    PYTHONDONTWRITEBYTECODE=1 python3 scripts/browser-cdp-smoke.py http://127.0.0.1:8765

### Optional background continuity

To let the bridge prepare one bounded initiative while the browser is
suspended, configure a private token and the exact model id from LM Studio:

    export XEMO_LIFE_TOKEN='choose-a-private-local-token'
    export XEMO_INSTANCE_ID='xemo-bedroom'   # use a different stable id for each XEMO
    export XEMO_LIFE_MODEL='the-exact-model-id-from-lm-studio'  # optional; defaults to the brain model
    ./scripts/run-web.sh

The service may queue one short grounded initiative, but it never speaks,
opens the camera or microphone, or drives the wheels. When the browser returns,
it claims the initiative once and remains the only owner of speech, sensors,
and physical actions. With a token present, background autonomy enables
automatically; set `XEMO_LIFE_AUTONOMY=0` to keep the journal while disabling
model calls. Without the token, it only keeps the bounded checkpoint and does
not call the model. If `XEMO_LIFE_MODEL` is omitted, the configured brain model
is used. The life journal is instance-scoped:
set a different stable `XEMO_INSTANCE_ID` for every robot. If omitted while a life
token is present, the bridge derives a non-secret journal namespace from that token.

## Body

The firmware expects MicroPython and the hardware modules in bot/. The current
arm wiring is direct PWM: left TS90M signal on GPIO12 and right TS90M signal
on GPIO14, with a shared ground and a suitable external 5–6 V servo supply.
These are configured as positional 270° servos using the 500–2500 µs PWM
range, with 135° as the nominal center.
Copy `pico_robotics.py`, `body.py`, `action_engine.py`, and
`wheels_config.py` and `firmware_main.py` to the board, add a local `secrets.py`
with Wi-Fi settings, and run `firmware_main.py` as `main.py` on boot. The
wheel adapter now accepts both the relay's JSON `pose` messages and the classic
GrowBot raw walk frames, applies the configured L298N stiction floor, and
converts the legacy mirrored leg gait into bounded forward differential-drive
motion.

There are two different GrowBot connection paths. The normal `growbot.dev` body
URL expects an HTTPS tunnel to a body server exposing `/act` and `/ws`; it is not
the LM Studio URL and it cannot reach this relay-client firmware directly. The
relay build instead connects outbound to `growbot-relay.growbot.workers.dev` and
is paired with its printed `gb-xxxxxx` code in a relay-aware GrowBot page. Use
one path consistently; do not enter `llm.malaxit.eu` as the body URL.

The body page now has independent 0–270° sliders, reverse switches, center,
release, and guarded sweep controls. Start with the linkages disconnected or
lifted clear, center both servos at 135°, then fit the horns so the mechanical
midpoint matches the GUI midpoint.

The pairing code is intentionally entered by the person using the app. It is not stored in this repository.

### Body acceptance check

With the robot on a clear floor and a hand ready over the power switch:

1. Start the firmware and enter the printed `gb-xxxxxx` pairing code in XEMO.
2. Confirm the body panel reports the ESP32 as ready and shows live telemetry.
3. Check the distance reading against a nearby object before enabling automatic movement.
4. Test each arm at its limits, then test one short left and right wheel command.
5. Test forward, reverse, and a turn at low power; verify the ramp is smooth and the robot stops when the command stream is interrupted.
6. Press XEMO's stop control and confirm both wheels stop and both arm servos release.

Keep automatic movement disabled until the range sensor and stop behavior are confirmed in the actual room.

## Notes

XEMO keeps its personal memories in the browser that runs it. This repository contains the code, not anyone's private memories, pairing codes, local paths, or machine settings.
