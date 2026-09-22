# XEMO cleanup checklist

This is the working checklist for simplifying the runtime without resetting XEMO state or replacing working behavior blindly. Each item is checked only after its evidence is recorded below.

## Rules

- [x] Preserve the current worktree and all existing memories, goals, personality, voice settings, and pairing data.
- [x] Do not delete legacy code until its imports and runtime reachability are checked.
- [ ] Do not commit or push unless explicitly requested.
- [ ] Stop at the verification gate for user testing before optional enhancements.

## 1. Baseline

- [x] Record branch, commit, dirty files, service command, ports, and runtime entrypoint.
- [x] Confirm the running project is `/home/Public/Documents/growbot/XEMO`.
- [x] Record browser cache/storage and state locations.
- [x] Record current test and syntax-check results.

Evidence:

```text
Branch: `xemo-ui-brain-reorg`
Commit: `56f68c7` (`Add bounded durable life journal`)
The worktree already contains user changes; they remain untouched.
The local entrypoint is `scripts/run-web.sh`, which starts `bot/bridge.py` on port `8765` and proxies LM Studio at `http://127.0.0.1:1234/v1` by default. After the latest restart, `fuser` confirmed the repository bridge owns port `8765` and the LAN deep-health request succeeds.
`node --check gui/xemo/js/app-runtime-947.js`, `node gui/check-runtime-contract.mjs`, `node gui/test-protocol.mjs`, and `python3 -m unittest bot.test_bridge bot.test_life_state -q` all passed. A repository `.eslintrc.json` now makes the previously unconfigured ESLint invocation meaningful; it caught and the runtime fixed a duplicate `relationship.commitmentOutcomes` key, and the targeted ESLint pass is clean.
Chromium storage inspection at `http://127.0.0.1:8765` found the XEMO state in localStorage keys `xemo_app_v1`, `xemo_bfable_default_v1`, and `xemo_voice_v2`; IndexedDB and the service worker are enabled. Values were not read or changed.
```

## 2. Ownership map

- [x] Identify the authoritative GUI/runtime entrypoint.
- [x] Identify every brain/LLM owner and wrapper.
- [x] Identify every hearing/transcription owner.
- [x] Identify every speech/audio owner.
- [x] Identify every movement/body owner.
- [x] Identify every autonomy/life scheduler.
- [x] Mark legacy and archive paths that must not run.

Evidence:

```text
The browser runtime is `gui/xemo/js/app-runtime-947.js`; it contains 88 direct reassignment sites for core names and 147 timer registrations. The bridge owns `/api/chat/completions`, `/api/chat/stream`, and `/api/transcribe`; `LifeCoordinator` is also instantiated by the bridge. The firmware owns drive, arms, range, telemetry, and the wheel dead-man. The alias audit found the legacy `_think*`, `_sendChat*`, and `_transcribe*` bindings referenced only by their wrapper chain, not by the final exported owners; all legacy `_speak*` assignments and the extra voice-flight wrapper have now been removed after their useful filtering, language, duplicate, interruption, and lease behavior was moved into `speech-controller.js`. The self-test now asserts `think === xemoAuthoritativeThink`. The rebuilt runtime is `v1217`; no remaining legacy block has been deleted until its reachability and behavior are covered by a focused regression test. The latest review found that `fetchTimed()` selected its abort signal through ambiguous `&&`/`||`/`?:` precedence, and that a human turn could remain queued behind an autonomous flight; both boundaries are now explicit and tested by the runtime contract. A real-model browser run also reproduced autonomous delivery overwriting a fresh human answer; the authoritative path now holds autonomous generation and delivery for 45 seconds after human input. Placeholder autonomous goals now normalize to honest rest/silence, and all autonomous callers share a 30-second rest cooldown.
```

## 3. Brain and thought process

- [x] Keep one cancellable LLM request owner.
- [x] Keep one parser/repair/timeout path.
- [x] Prevent stale, empty, scrambled, or superseded replies reaching the UI.
- [x] Separate user requests from XEMO's own initiatives.
- [x] Prevent repeated phrases, repeated goals, and stalled thought loops.

Evidence:

```text
The bridge now centralizes transport failure classification: autonomous supersession remains a deliberate `skipped` response, while a superseded human turn returns retryable HTTP 409 instead of a false successful 200 response. Focused bridge tests cover both cases. The browser-side authoritative controller now owns one cancellable flight; pause, panic, reset, tab hide, and a new human turn abort it, and `window.xemoBrain.cancel()` exposes the same owner for diagnostics. `xemoAuthoritativeCall()` gives the final path one deadline, one bounded transport retry, one schema-to-object parser, one malformed-content repair path, and rejects empty thoughts. Chromium loaded runtime `v1202`, reported no page errors, cancelled a hanging request with `busy=false`, and rendered a clean answer when the mocked response contained `<think>` braces and a Markdown code fence. Historical wrappers still exist behind the final controller and remain a later cleanup target.
The same final path distinguishes `autonomous` from human turns in its prompt, transport header, admission lease, execution rules, and repetition evidence; passive waiting requests and unchanged autonomous decisions are held or repaired instead of spoken as new initiative.
```

## 4. Hearing

- [x] Keep one microphone/VAD state machine.
- [x] Allow only one Whisper request per recording.
- [x] Implement one abort and recovery path.
- [x] Reject duplicate or stale transcripts.
- [x] Verify hearing can recover after errors.

Evidence:

```text
`gui/xemo/js/hearing-controller.js` now owns the final transcription admission boundary, coalescing concurrent recordings and exposing one stop path while preserving the existing Whisper/VAD implementation underneath. Controller tests pass for duplicate admission, cancellation, and recovery after a rejected transcription.
```

## 5. Speech

- [x] Keep one speech output queue.
- [x] Guarantee one active audio source at a time.
- [x] Support cancellation without overlapping playback.
- [x] Keep speed and pitch independent.
- [x] Verify Kokoro boundary and independent speed/pitch payload.
- [x] Verify browser fallback boundary.

Evidence:

```text
`gui/xemo/js/speech-controller.js` now owns the final speech boundary. It explicitly reports start/end to the runtime, and pause, panic, and human-turn interruption call its stop method. Its shared localStorage lease prevents another XEMO tab from owning audio at the same time; cleanup releases the old lease before replacement and stale requests cannot release a newer lease. GUI pitch `1.4` and speed `0.8` produce Kokoro generation speed `0.571428…` while preserving playback pitch compensation. Controller tests cover duplicate suppression and clean idle state after cancellation. The extracted controller also owns the former internal-leak and dream-no-op filters.
```

## 6. Body and movement

- [x] Keep one movement command stream.
- [x] Preserve wheels, arms, distance sensing, and telemetry.
- [x] Preserve dead-man and emergency-stop behavior.
- [x] Restore motor-effective power and decisive movement ramps.
- [x] Connect movement goals to the autonomy loop safely.
- [x] Verify capability detection and acknowledgements.

Evidence:

```text
The browser and current XEMO firmware contracts match for `wheels`, `arms`, `arms_release`, `range`, `lidar`, `stop`, capability hello, acknowledgements, telemetry, and the 500ms firmware dead-man. `bot/test_body_hardware.py` passes 3/3 with fake hardware and verifies clamping, smooth wheel ramping, arm limits, emergency stop/release, and HC-SR04 conversion; `bot/test_firmware_contract.py` passes 2/2 for the firmware/browser command boundary. All bot Python source passes AST syntax checks without importing hardware modules. The browser movement boundary uses named motor-effective limits (`0.48–0.68`) instead of the previous low `0.22–0.38` floor. The archived `growbot-wheels-kit.zip` was also inspected: it is a separate Pico 2 W HTTP/keyframe firmware using `PicoRobotics.servoWrite`, while current XEMO is an ESP32/L298N text-protocol body with distance sensing and arm ports. No firmware was overwritten. The latest serial and LAN-neighbor check still finds no `/dev/ttyUSB*`, `/dev/ttyACM*`, or serial-by-id device and no identifiable body endpoint, so hardware execution remains pending until the actual body is connected.
```

## 7. Autonomy and continuity

- [x] Keep one foreground life scheduler.
- [x] Prevent background journaling from competing with live brain, speech, sensors, or movement.
- [x] Preserve learning, memories, acquaintances, emotions, needs, goals, and personality.
- [x] Add migrations only; never silently reset state.
- [x] Keep instances separated while preserving the original device access.

Evidence:

```text
The browser migration for `personaV3` now fills only missing personality/instruction fields instead of replacing an existing saved identity. The runtime contract checks this preservation rule. The foreground life beat is named `runAutoBeat()` and is admitted by one five-second scheduler; physical locomotion has a separate safety-step timer, not a second life decision loop. The bridge's `life_brain_call()` takes the same non-blocking `_brain_lock` as the live brain, so background reflection yields instead of competing with a human turn. The life-state tests prove distinct sanitized instance namespaces, client instance-id override rejection, state merge, and preserved continuity. A deliberate pause is cleared by the final human-submit fence, while a real pause still cancels the authoritative brain and speech owners. Live backup/restore remains pending.
```

## 8. Tests and verification

- [x] Run JavaScript syntax checks for every changed runtime file.
- [x] Run focused protocol, bridge, state, brain, hearing, speech, movement, and autonomy checks available in the repository.
- [x] Restart the local service after edits.
- [x] Assemble generated GUI partials from the source HTML.
- [x] Test LM Studio connectivity.
- [x] Use Chromium with code cache cleared but site data preserved.
- [x] Collect console and network evidence.
- [x] Test live text and speech through the running LAN bridge.
- [x] Test live dependency health and the real-model response contract.
- [ ] Test live hearing, autonomous goals, and initiative delivery in a user session.
- [ ] Test live wheels, arms, distance sensing, telemetry, and stop behavior with the ESP32.

Evidence:

```text
Direct Chromium verification reached the local GUI with HTTP 200, loaded runtime `v1212`, speech `v2`, hearing `v1`, protocol `v98`, the SF Pixelate font, and the service worker. It exposed `window.xemoBrain` and `window.xemoSpeech` with zero page-level JavaScript errors. LM Studio's existing extracted bundle was started, its daemon/API came up on `127.0.0.1:1234`, and `/v1/models` exposed `qwen/qwen3-vl-8b` and `qwen/qwen3-vl-4b`.

Focused controller tests: `node gui/test-controllers.mjs` passed 3/3. Protocol tests passed 3/3. The complete focused Python run now passes 142 tests, including the body simulator, firmware contract, and dependency health probes. ESLint, JavaScript syntax, and `git diff --check` also pass.

`node gui/build-gui.mjs` completed successfully and the regenerated GUI passed `node gui/check-runtime-contract.mjs`. The service-worker cache was bumped to `xemo-static-v1097`; the live server served `/xemo/js/app-runtime-947.js?v=1212` and `/xemo/js/speech-controller.js?v=2`. After the live-model browser run exposed a human reply waiting behind autonomous work, the runtime now preempts an autonomous flight on a new human turn, clears its ownership state, and lets the human request start immediately. `fetchTimed()` now names its brain/dream ownership booleans before selecting the signal, avoiding accidental cancellation caused by operator precedence.

With `/api/models` and `/api/chat/completions` mocked in Chromium, the authoritative controller made one chat request and rendered `I understand the test and I will answer directly.` with zero page errors. This proves the browser request → parser → answer-render path independently of LM Studio availability.

The rebuilt runtime also passed a live cancellation smoke test: a deliberately pending chat request was cancelled through `window.xemoBrain.cancel()`, returned `busy=false`, and produced zero page errors. A fresh-profile Chromium flow with test-only wake state loaded v1212 and sent a real human turn through the local bridge and Qwen3. Qwen3 initially returned passive-wait filler twice; the new anti-wait/relevance gate rejected both, removed private repair context, and the third bounded repair rendered `Right now I’m warm and still, listening to the quiet hum of the room.` The final state was `busy=false`, `isSpeaking=false`, zero page errors, zero failed requests, and three successful `/api/chat/completions` responses. A separate TTS-failure route left speech idle without hiding the answer. The running Kokoro service on port 8881 accepted the exact XEMO `/v1/audio/speech` payload with voice `bm_fable` and returned a valid 24 kHz mono WAV; the deep-health probe now checks its `/health` endpoint. No ESP32/serial device is connected in this environment; physical body behavior remains unverified despite the passing simulator.

An isolated persistent Chromium profile stored a marker in localStorage, cleared the browser code cache through the DevTools protocol, reloaded the page, and retained the marker while loading runtime `v1202`; no page errors occurred.

After the bridge restart, the live LAN route `http://192.168.1.171:8765` returned deep health with `brain: ok`, `kokoro: ok`, and `life_journal: ready`. Direct Chromium loading of the rebuilt route returned HTTP 200, runtime `v1215`, 61 interactive buttons, a passing `window.xemoSelfTest()`, exposed `window.xemoBrain` and `window.xemoSpeech`, and zero console errors, page errors, or failed requests. The exact Kokoro browser boundary was exercised through `/api/tts` with `bm_fable`; both the direct service and the XEMO bridge returned HTTP 200 and valid 24 kHz mono WAV files. The isolated chat flow reached the bridge and produced successful chat responses; the remaining physical-body actions still require the ESP32.

The deep brain-health contract now parses `/v1/models` and requires the configured chat model (`qwen/qwen3-vl-8b`, accepting LM Studio instance suffixes) instead of treating any responsive model endpoint as a healthy brain. Regression tests cover embedding-only model lists and instance suffixes. After restarting the repository bridge, the live deep-health response reported `brain: ok` with the configured model, plus `kokoro: ok` and `life_journal: ready`.

The broad `technicalCaption()` filter was causing valid replies containing ordinary words such as “browser,” “model,” or “API” to disappear from the face while remaining in the brain log. It now suppresses only unmistakable structured error/debug leakage. Runtime cache keys were bumped to app `v1218` and service worker `v1103`. The isolated live browser test then rendered a real Qwen answer (`It’s sunny and warm today.`) with zero console/network failures, `window.xemoBrain` and `window.xemoSpeech` present, and a successful fake microphone stream.

A fresh isolated Chromium run after the rebuild loaded the cache-busted route and completed the real human submission path with a single HTTP 200 chat response, a rendered Qwen answer (`It’s warm and quiet outside.`), zero console errors, zero network failures, `brainBusy: false`, and a successful fake microphone stream. The same trace showed an autonomous request yielding to the human turn, confirming the ownership fence under concurrent wake activity.

A separate direct human-turn request through the live bridge returned HTTP 200 and one clean model sentence (`The quiet stillness holds everything in balance.`), confirming the raw bridge → LM Studio → response contract independently of UI rendering and audio playback.

A separate live autonomous request through the same bridge returned HTTP 200 with a specific self-originated goal (`notice the texture of the windowpane as light filters through`) and no waiting language. This verifies the service/model autonomy contract, while browser delivery and physical execution remain separate acceptance gates.

The repeatable health and validation commands are now documented in `README.md`, including the quoted deep-health URL needed by shells that interpret `?` as a pattern.

The bridge now reads `XEMO_KOKORO_URL` once and uses that same configured base for both `/api/tts` and deep health, defaulting to port 8881. After restarting the live bridge, deep health reported all three local dependencies ready and a configured-route `bm_fable` request returned a valid 24 kHz mono WAV.

The bridge now defaults life autonomy to the configured brain model when a private life token is present, so omitting `XEMO_LIFE_MODEL` no longer silently disables independent continuity. Deep health reports the operational autonomy state without exposing life data; after the final restart it reported `autonomy: enabled` alongside the loaded brain, Kokoro, and ready life journal.

The authenticated live life snapshot confirms `coordinator.enabled: true`, `lastError: ""`, and the instance namespace `default`. No pending initiative or reflection was claimed during this short check; the coordinator's next-wake/timing gate remains authoritative, so this is evidence of an active scheduler rather than fabricated activity.

A later sanitized live snapshot confirms the enabled coordinator has completed background work: two private reflections and two bounded private activities are persisted, with no coordinator error and no pending unsolicited initiative. This verifies the service-side continuity loop is actually running; it does not substitute for browser delivery or sensor/body evidence.

The background parser now rejects present sight, hearing, touch, and body-sensation claims when the browser is asleep, while retaining supported historical reflection and bounded rest/activity decisions. A regression fixture containing invented sunlight, room-hearing, and skin sensations is reduced to no false speech/reflection/grounding; the full bot suite passes 144 tests. The restarted live bridge reports the same loaded brain, Kokoro, ready journal, and enabled autonomy.

The README now also contains the physical acceptance sequence for pairing, telemetry, range, arm limits, smooth wheel commands, interrupted-command dead-man behavior, and emergency stop. It remains intentionally unchecked until those steps are performed on the actual body.

Added `scripts/browser-cdp-smoke.py` as a repeatable isolated Chromium check. It captures runtime console exceptions and network failures, verifies `window.xemoBrain` and `window.xemoSpeech`, and requests a fake microphone without touching the real browser profile. Against the live LAN route it reported zero console/network failures and correctly reported media APIs unavailable on insecure HTTP; against the live localhost route it reported zero failures with `mediaDevices: true` and `microphone: true`. This verifies the JavaScript permission path, while real phone hearing remains a separate acceptance gate.

The cache-aware version of the harness loaded `http://127.0.0.1:8765/xemo/js/app-runtime-947.js?v=1218`, rendered a fresh Qwen answer (`It’s a quiet, cool evening—perfect for a slow walk.`), recorded one successful chat response, zero console errors, zero network failures, and a successful fake microphone stream. The fresh profile had no service-worker controller yet, so service-worker activation remains separately observable on an established profile; the shell cache key and service-worker shell both point to `v1218`/`v1103`.

The final corrected CDP harness run loaded the same cache-busted runtime, rendered `It’s warm and quiet outside.`, recorded one HTTP 200 `/api/chat/completions` response, zero console errors, zero network failures, `brainBusy: false`, and a successful fake microphone stream. The harness itself briefly had an invalid wait on `serviceWorker.ready`; that wait was removed after the test caught it, and the corrected harness now completes cleanly. Browser-side service-worker activation remains a separate cache/profile observation, not an application failure.

After the bridge restart, the current repository audit still passes: 144 Python tests, hearing/speech controller tests, protocol tests, runtime contract, ESLint, JavaScript syntax, and `git diff --check`. The host process is confirmed to be `/home/Public/Documents/growbot/XEMO/bot/bridge.py`, and deep health reports the configured brain, Kokoro, life journal, and enabled autonomy.

The autonomy/body audit found two behavior issues: the 35–42cm wander/explore branch could turn indefinitely instead of making progress, and the final authoritative controller bypassed older autonomous-choice bookkeeping. That branch now makes a short forward clearance probe; repeated look-only or rest-only autonomous thoughts request a different meaningful choice; and the authoritative executor records the autonomous thought timestamp and choice itself. The assembled GUI and live Chromium run still pass with zero console/network failures and a real Qwen answer.
```

## 9. Verification gate

- [x] Compare behavior against the baseline.
- [ ] Pause for user testing.
- [ ] Only after user confirmation, add optional personality/liveliness enhancements.
- [ ] Mark the cleanup complete only when every required item has direct evidence.

Evidence:

```text
Static/runtime and real-model browser gates are passed. The running LAN bridge has now exercised both text and Kokoro speech successfully. The v1214 real-model run reproduced the overwrite race; v1215 loaded through a new service-worker/runtime cache key and holds autonomous work before it can disturb a fresh human answer. A v1215 Chromium acceptance run sent a real human message, waited 35 seconds through the autonomy interval, and found exactly one persisted XEMO reply with no autonomous overwrite and zero console errors. The caption later returned to its normal resting state, while the answer remained in the conversation moments. A v1217 Chromium cadence run loaded the new cache-busted runtime, waited 20 seconds, and recorded one autonomous rest request with no second scheduler request; the console remained clean. A later UI smoke run initially exposed 503 responses because LM Studio had unloaded the model; `lms ps` confirmed no LLM was loaded, so those were dependency responses rather than JavaScript errors. After loading `qwen/qwen3-vl-8b` with a one-hour TTL, the live route returned 200 for models, health, and chat; direct DOM clicks traversed all five tabs (`creature`, `body`, `soul`, `brain`, `technical`) and ended on `technical` with 54 buttons and zero console errors. Live microphone/autonomous-session acceptance and wheel/arm/sensor execution still require the user's active device session and connected ESP32. User testing is still required before deleting more historical wrappers or adding optional personality/liveliness features.
```
