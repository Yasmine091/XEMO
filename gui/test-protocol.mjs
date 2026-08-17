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
