import test from "node:test";
import assert from "node:assert/strict";
import { createHearingController } from "./xemo/js/hearing-controller.js";
import { createSpeechController } from "./xemo/js/speech-controller.js";

test("hearing admits one transcription flight and can stop it", async () => {
    let calls = 0;
    let release;
    const pending = new Promise(resolve => { release = resolve; });
    const controller = createHearingController({
        transcribe: async () => { calls += 1; await pending; },
        getAbortController: () => ({ abort() {} })
    });
    const first = controller.transcribe({ id: 1 });
    const second = controller.transcribe({ id: 2 });
    assert.strictEqual(first, second);
    await Promise.resolve();
    assert.equal(calls, 1);
    controller.stop();
    release();
    await first;
});

test("hearing releases a failed flight so the next recording can recover", async () => {
    let calls = 0;
    const controller = createHearingController({
        transcribe: async () => {
            calls += 1;
            if (calls === 1) throw Error("temporary whisper failure");
            return "recovered";
        },
        getAbortController: () => ({ abort() {} })
    });
    await assert.rejects(controller.transcribe({ id: 1 }), /temporary whisper failure/);
    assert.equal(controller.isTranscribing(), false);
    assert.equal(await controller.transcribe({ id: 2 }), "recovered");
    assert.equal(calls, 2);
});

test("speech suppresses an exact duplicate while the first utterance is active", async () => {
    let spoken = 0, started = 0, ended = 0;
    globalThis.window = {
        speechSynthesis: {
            cancel() {},
            speak(utterance) {
                spoken += 1;
                setImmediate(() => utterance.onend?.());
            }
        }
    };
    globalThis.SpeechSynthesisUtterance = class {
        constructor(text) { this.text = text; }
    };
    const audio = {
        pause() {}, currentTime: 0,
        removeAttribute() {}, load() {},
        play() { return Promise.resolve(); }
    };
    const controller = createSpeechController({
        audio,
        getSettings: () => ({ engine: "browser", pitch: 1, speed: 1 }),
        getVoice: () => "bm_fable",
        getSpanish: () => false,
        onStart: () => { started += 1; },
        onEnd: () => { ended += 1; }
    });
    const first = controller.speak("hello there");
    const second = controller.speak("hello there");
    await first;
    await second;
    assert.equal(spoken, 1);
    assert.equal(started, 1);
    assert.equal(ended, 1);
});
