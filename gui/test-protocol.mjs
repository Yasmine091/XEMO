import assert from "node:assert/strict";
import test from "node:test";
import { parseThought, responseNeedsCorrection } from "./xemo/js/protocol.js";

test("ignores reasoning braces before the final thought", () => {
  assert.deepEqual(parseThought('<think>internal {"not":"final"}</think>{"say":"hello"}'), { say: "hello" });
});

test("recovers a final thought after an unclosed reasoning block", () => {
  assert.deepEqual(parseThought('<think>internal reasoning {not final}\n{"say":"still here"}'), { say: "still here" });
});

test("does not accept a human turn without actual speech", () => {
  assert.equal(responseNeedsCorrection('{"emotion":"curious"}'), true);
  assert.equal(responseNeedsCorrection('{"say":"I noticed something new."}'), false);
});

test("preserves the Growbot fast-loop fields for the XEMO adapter", () => {
  const thought = parseThought(JSON.stringify({
    say: "",
    sound: "chirp",
    burst: "sparkle",
    sing: [{ hz: 330, ms: 300 }],
    body: { steps: [{ l: 0, r: 270, ms: 400 }] },
    walk: { secs: 2 },
    log: "a meaningful moment",
    glow: "warmth",
    ladder: ["notice", "try"],
    rung_done: 1,
    identity_proposal: "I am learning."
  }));
  assert.equal(thought.sound, "chirp");
  assert.deepEqual(thought.body.steps[0], { l: 0, r: 270, wl: 0, wr: 0, ms: 400 });
  assert.equal(thought.walk.secs, 2);
  assert.equal(thought.rung_done, 1);
});

test("preserves bounded body composition choices", () => {
  const thought = parseThought(JSON.stringify({
    say: "",
    sequence: ["wave", "sway", "victory"],
    arms: { left: 250, right: 30 }
  }));
  assert.deepEqual(thought.sequence, ["wave", "sway", "victory"]);
  assert.deepEqual(thought.arms, { left: 250, right: 30 });
});

test("normalizes Growbot-style wheel strings into bounded local movements", () => {
  assert.equal(parseThought('{"say":"I will move.","move":"right_wheel_once"}').moveName, "right_wheel_once");
  assert.equal(parseThought('{"say":"I will move.","move":"turn_left_wheel_once"}').moveName, "left_wheel_once");
  assert.equal(parseThought('{"say":"I will move.","move":"forward_short"}').moveName, "forward_short");
  assert.equal(parseThought('{"say":"I will move.","move":"roll forward 30cm"}').moveName, "forward_short");
  assert.equal(parseThought('{"say":"I will move.","move":"turn wheels slowly clockwise"}').moveName, "pivot_right");
  assert.equal(parseThought('{"say":"I will stop.","move":"stop"}').stop, true);
});
