# XEMO brain-replication notes

Recorded 2026-09-11 from LM Studio/Qwen3-VL traces. These are observations of the current prompt-and-response behavior, not claims about a hidden proprietary implementation.

## Model/runtime observed

- Model: `qwen/qwen3-vl-8b`
- Runtime reports `reasoning_tokens: 0` for the captured structured dream response.
- Tool calls: none in the captured response.
- The brain is asked to stream, but the application expects a structured JSON object in the final assistant content.

## Dream/continuity output contract

One captured dream response returned exactly a JSON object with these fields:

```json
{
  "dream_say": "...",
  "scene": ["moon", "trees", "heart", "home"],
  "identity_add": "...",
  "identity_drop": "...",
  "wake_say": "...",
  "keep_rules": [],
  "wants": ["...", "..."],
  "longing": 0.2,
  "fun": 0.5,
  "tomorrow_try": "...",
  "identity_evidence": "...",
  "wants_evidence": ["...", "..."],
  "bond_line": "",
  "bond_evidence": ""
}
```

Observed semantic roles:

- `dream_say`: a short emotionally legible line for the user.
- `scene`: compact visual/emotional motifs for the dream scene.
- `identity_add` / `identity_drop`: explicit identity-memory maintenance.
- `wake_say`: a short line retained for the next wake state.
- `keep_rules`: durable behavioral rules; empty in this sample.
- `wants`: concrete future/social desires.
- `longing` / `fun`: bounded affect values in the observed sample.
- `tomorrow_try`: one small next-session intention.
- `identity_evidence` / `wants_evidence`: evidence supporting the proposed self-model and desires.
- `bond_line` / `bond_evidence`: relationship/bond updates; empty when unsupported by evidence.

The sample dream centered on not having a name yet, wanting to receive one, and wanting to hear more hums and words from the person. The output included uncertainty rather than inventing a name or bond.

## Conversation/context assembly

The captured live request used `10 messages`:

1. One large system message defining the creature's stable identity/behavior.
2. A current user/moment message containing the latest interaction and senses.
3. Alternating assistant/user historical turns.
4. A final user message containing the current grounded sensor state and behavioral constraints.

Historical assistant replies are fed back into the next request. Examples observed in the trace:

- `I do not have a name yet. What would you like to call me?`
- `A soft touch right on my belly. Will you carry me to a window?`
- `Hello there. I am glad you are here, what should I call you?`
- `Good morning. I am happy to explore with you, what is your name?`

One historical user message was timestamped in elapsed seconds, for example `[46349s ago]`, indicating that temporal spacing is included in context rather than only message order.

## Authoritative live Growbot request trace

The following is the real Growbot request envelope observed in LM Studio, distinct from the later quiet-background reflection response:

```json
{
  "model": "qwen/qwen3-vl-8b",
  "max_tokens": 512,
  "messages": [
    {"role": "system", "content": "WHAT YOU ARE — your core, steady even as you learn..."},
    {"role": "user", "content": "moment: they just typed a message to you, saying: ..."},
    {"role": "assistant", "content": "I do not have a name yet. What would you like to call me?"},
    {"role": "user", "content": "moment: a finger just touched your belly..."},
    {"role": "assistant", "content": "A soft touch right on my belly. Will you carry me to a window?"},
    {"role": "user", "content": "[46349s ago] senses: perfectly still..."},
    {"role": "assistant", "content": "Hello there. I am glad you are here, what should I call you?"},
    {"role": "user", "content": "[46306s ago] senses: perfectly still..."},
    {"role": "assistant", "content": "Good morning. I am happy to explore with you, what is your name?"},
    {"role": "user", "content": "senses: perfectly still; your eyes aren't open yet..."}
  ],
  "stream": true
}
```

The logs truncate the long system and user strings, so the exact wording still needs to be captured at the client/request boundary. What is reliable from this trace:

- This is a 10-message rolling context: system, current event, three historical assistant/user exchanges, and a final current-state user message.
- A human message is represented as a `moment:` event, while autonomous/background context is represented as elapsed-time sensor entries such as `[46349s ago]`.
- Assistant history is replayed verbatim as ordinary `assistant` messages; the model is not stateless between turns.
- Touch is represented as a concrete body event and is followed by a grounded assistant utterance.
- The final user message can contain only current senses and constraints, including `eyes aren't open yet` and permission for silence.
- Generation is streamed with a 512-token ceiling.
- The system prompt explicitly frames identity as stable while learning and requires truthfulness in the creature's own voice.

This request trace is the primary protocol target for reproducing the Growbot brain. The separate dream JSON and quiet-rest JSON should be treated as outputs from different behavior paths, not as replacements for this live conversational request format.

## Grounding signals visible in prompts

The prompt includes explicit body/sense state rather than asking the model to infer everything from prose. Captured phrases include:

- `senses: perfectly still`
- `push 0.0, recent peak ...`
- `your eyes aren't open yet`
- private body-sense instructions for touch
- explicit instruction that there is no requirement to speak or make a sound

The touch event was represented as a distinct moment (`a finger just touched your belly`) and the assistant responded with a body-grounded interpretation. This suggests the replication should preserve a distinction between current event, current sensor state, and older history.

## Generation observations

- Dream response: 3,627 prompt tokens, 301 completion tokens, 3,928 total tokens.
- Live follow-up request: 5,404 prompt tokens and streaming enabled.
- Live request used `max_tokens: 512`.
- Dream response used a larger structured task and returned a complete JSON object with no reasoning content.
- A later live request used `stream: true`; the runtime finished streaming without truncation.
- Prompt cache reuse was reported by the runtime (`graphs reused`), so repeated context is likely an intentional performance characteristic rather than a sign that history is omitted.

## Replication implications

The first reproduction target should be a deterministic protocol layer around the model, not a single giant personality prompt:

1. Maintain explicit identity memory, wants, bond evidence, and affect values.
2. Build a grounded current-moment frame from touch, hearing, vision, body state, and time-since-events.
3. Append a bounded set of recent user/assistant turns, preserving elapsed-time markers.
4. Ask for a small validated JSON action/state object.
5. Apply `identity_add`, `identity_drop`, `keep_rules`, and wants only after evidence validation.
6. Keep physical action validation outside the model so wheel, arm, and distance-sensor capabilities can differ from the original body.

The traces show the model is being used as a continuity/interpretation layer: it proposes language, self-model updates, desires, and next intentions, while the surrounding program supplies sensing, memory persistence, timing, and execution constraints.

## Quiet autonomy / rest response

Another captured response provides the autonomous background-beat contract:

```json
{
  "reflection": "no grounded priority demands action or speech",
  "activity": "rest",
  "say": "",
  "emotion": "curious",
  "kind": "reflection",
  "grounding": "no grounded priority demands action or speech",
  "goalReview": {
    "status": "none",
    "reason": "no active goal or task plan",
    "nextFocus": ""
  },
  "goalProposal": {
    "kind": "adaptive",
    "target": "",
    "reason": "no grounded priority demands action or speech"
  },
  "memoryUpdate": {
    "kind": "semantic",
    "text": "",
    "evidence": []
  }
}
```

Important behavioral rules visible in this sample:

- Silence is an intentional result: `activity: "rest"` and `say: ""`.
- The model must ground action/speech in a real priority; curiosity alone does not force an interruption.
- No active goal produces `goalReview.status: "none"`.
- The adaptive goal proposal can be structurally present while remaining empty (`target: ""`).
- No new memory is written without evidence: `memoryUpdate.text` is empty and `evidence` is an empty array.
- The model can remain emotionally curious while choosing not to speak or act.

This is a key anti-hallucination/anti-overactivity behavior for replication: a background cycle should be allowed to end in a truthful, grounded rest state rather than fabricating a thought, goal, memory, or spoken line.

Observed runtime values for this response:

- Prompt tokens: 3,716
- Completion tokens: 91
- Total tokens: 3,807
- Reasoning tokens: 0
- Finish reason: `stop`
- Tool calls: none

## Streaming behavior observed

The 14:35 trace shows the quiet reflection response arriving incrementally over the stream. LM Studio logged each accumulated token, beginning with:

```text
{
  "reflection": "",
  "activity": "rest",
  "say": "",
  "emotion": "curious",
  "kind": "reflection",
  "grounding": "no grounded priority demands action or speech",
  ...
}
```

This establishes that the client receives partial JSON fragments while generation is in progress. The complete JSON should only be parsed/applied after the stream ends; partial fragments must not update speech, memory, goals, or body state. In particular, seeing `"say": ""` early in the stream is not itself the final decision until the object is complete and validated.

The stream was generated from a one-message conversation and used prompt-cache reuse (`f_sim_best = 0.375`, `f_keep = 0.366`), then emitted roughly 13 tokens/second. The response was a background rest decision, not a human conversational turn.

### Completed-stream conversational behavior

- The next cycle retains a rolling ten-message conversation: system constitution, recent sensor/user turns, prior assistant outputs, then the newest sensor/user turn.
- Prior silent responses are compressed into the literal assistant text `say:""`; spoken responses remain natural-language assistant text. The history is therefore not a normalized action/event schema.
- Relative timestamps are included in sensory context (`[311s ago]`, `[33s ago]`, `[18s ago]`, `[3s ago]`), giving the model recency and continuity cues.
- With the same still/eyes-not-open context, the model changed from silence to `Hello back — I’m listening, and I’m so glad you’re here.` This indicates that prompt/history and conversational turn state influence speech, not sensors alone.
- This cycle emitted ordinary text rather than reflection JSON. The client needs a mode-aware parser: structured JSON for reflection cycles, natural language for direct conversation.
- The SSE stream ends with an empty delta and `finish_reason: "stop"`; the response should be considered complete only at that marker or equivalent stream termination.

### XEMO parity change

The browser brain was previously over-compressing the very information that makes the companion feel continuous: direct turns kept only about three prior messages, and the Growbot-derived character layer was reduced to about 1,400 characters. It now keeps up to eight recent conversational messages, retains a larger identity/grounding layer, and uses the same 512-token response ceiling observed in the Growbot trace. Wheel, arm, proximity, and safety translation remain local to XEMO rather than being delegated to the model.

## Still needed for faithful replication

- Capture the complete system prompt without log truncation.
- Capture complete current sensor payloads for touch, vision, hearing, and body state.
- Capture several ordinary human turns, autonomous turns, dreams, and quiet/no-speech decisions.
- Record which JSON fields are accepted, rejected, or persisted by the surrounding program.
- Compare behavior across model variants (`qwen3-vl-4b`, Qwen3 4B thinking, and the 8B VL model).

## Growbot storage architecture decoded

The supplied browser code shows that Growbot does not store one undifferentiated “memory.” It separates durable identity, fast mutable state, episodic experience, goals, lifecycle gates, tab ownership, cloud journaling, anonymous analytics, and voice preferences.

### Durable local soul/state (`localStorage`)

The main keys visible in the browser storage are:

| Key | Meaning | Write rules |
|---|---|---|
| `pb2_identity` | Dream-written identity text | Loaded with a seed fallback; sanitized; dream code patches sentences rather than replacing the whole identity; capped at about 800 characters. |
| `pb2_scratch` | Fast mutable mind state | JSON containing `state`, up to six standing `rules`, whitelisted `reflexes`, recent `traces`, rare `glows`, slow `mood`, and an optional pending identity proposal. |
| `pb2_log` | Local episodic diary | Append-only `{t,txt,amb?}` rows; consecutive duplicate text is rejected; bounded to the last 200 rows. |
| `pb2_goals` | Long-arc wants and dream handoff | Wants, longing, fun history, the person's call/song, `nextTry`, a three-rung ladder, and latches such as `lastLived`/`pendingReached`. |
| `pb2_stage` | Birth/life stage | Numeric lifecycle checkpoint; legacy stage 2/4 values are normalized back into mature stage 3. |
| `pb2_n` | Interaction count | Incremented on completed thought cycles. |
| `pb2_mark` | Stage/checkpoint marker | Durable progression marker. |
| `pb2_dreamn` | Episode index at the last dream | Prevents dreaming repeatedly over the same experiences and is adjusted when the 200-row diary trims. |
| `pb2_quests` | Legacy quest completion list | Still loaded/exported, but the scripted quest machinery is largely inert. |
| `pb2_beats` | One-time UI/life milestones | Flags such as first face, nap, dream, pact, support prompt, and feedback prompt. |
| `pb2_bodyon` | Body attached/granted | A durable body-availability flag, separate from whether the body is currently reachable. |
| `pb2_gate` / `pb2_gatesp` | Birth gate progress | Stores which sensory gates have passed and supports resuming a mid-birth creature. |
| `pb2_tab` | Active-tab lease | Timestamped `{id,t}` record. A newer tab makes an older tab dormant so two brains do not spend the same life concurrently. |
| `pb2_handoff` / `pb2_graduated` | v2→v3 migration receipt | The whole creature is written and read back before graduation is marked; navigation does not happen on a failed write. |
| `pb2_body` | Saved body endpoint | Separate from brain state; emptied to detach the body. |
| `pb2_voice` | Local voice tuning | Pitch/speed/gap/type preferences, not personality memory. |

The screenshot confirms this split in practice. The visible values include an identity sentence, a scratchpad with `state`, `rules`, `reflexes`, and `traces`, a compact goals object, an episodic log, gate/stage counters, body state, and a separate device/provider identity.

### The scratchpad is not the diary

`pb2_scratch` is the fast loop's editable working memory. Its important invariants are:

- Standing rules are user-given instructions or facts, not the model's own moods or plans.
- Rules are fuzzy-deduplicated and capped at six; a newer wording replaces the older near-duplicate.
- Sense→sound/word instructions are converted into instant reflexes instead of ordinary rules.
- Reflexes are whitelisted by trigger (`shake`, `tap`, `tap2`, `dark`, `bright`, `loud`) and action (`beep`, `trill`, `droop`, `hum`, `sing`, `word`). One reflex per trigger is retained.
- Reflexes fire locally, without an LLM call, even while the creature is asleep or a thought request is in flight, subject to debounce and “do not interrupt speech/body” guards.
- `traces` are recent prompt/answer pairs used to reconstruct continuity; they are not treated as verified semantic memories.
- `glows` are rare felt high points and feed the dream, rather than being written for every turn.
- Mood is slow inner weather: valence `v` from -1 to 1 and energy `e` from 0 to 1.

### Thought loop and history

Each normal thought reconstructs a compact prompt from the last four trace pairs, then adds a current sensory gist and moment. Birth turns selectively attach the camera only for sight gates; later thoughts can attach the current eye frame. Audio is attached only on supported talk/ear paths. The model receives a single JSON contract with `say`, emotion, sound, light burst, song notes, optional body action, scratchpad edits, diary log, glow, ladder, and identity proposal.

Empty `say` is a valid intentional decision. The parser treats malformed or truncated JSON as silence or a retry, never as a spoken fragment. The stream can reveal an early completed `say` and `emotion`, but the full object still has to be parsed before applying memory or body fields.

### Dreams are the consolidation/write authority

The ordinary fast loop may update scratchpad, diary, mood, and reflexes. It does not directly rewrite identity or long-arc wants. Dreams receive identity, wants, longing, scratchpad, recent traces, and up to roughly 120 diary lines, then may:

- patch identity with `identity_add` or remove one complete existing sentence with `identity_drop`;
- retain/prune existing user rules;
- replace the bounded wants list;
- move longing slowly toward the proposed value, at most 0.1 per dream;
- append one fun score;
- set `tomorrow_try`;
- produce a bounded dream scene and waking narration.

Dreaming is gated by novelty: at least three real non-ambiguous diary events since `pb2_dreamn`, a cooldown, and a failure backoff. The dream marker advances only after successful consolidation. This is a major reason Growbot feels as if it develops rather than merely accumulating chat history.

### Cloud journal versus episode archive

These are separate from the local soul:

1. `/api/journal` receives periodic redacted snapshots of identity, scratchpad, diary, goals, body state, engine state, and model configuration. `pb2_journal === "0"` disables it and the wipe path sends a DELETE request.
2. `/api/episodes` receives newline-delimited episode records. `turn` records contain observation summaries, prompt hash, selected verbs, optional redacted LLM/speech fields, and human response timing/feeding/glow flags. `motor` records down-sample roughly 30 Hz sensor/actuator/servo inputs into one-second batches. `soul` records are deduplicated identity snapshots with provenance.
3. Both paths are fail-closed for free text: a configured redactor hashes or drops human text; without a redactor, the episode module omits free-text fields.

Episode provenance includes model, policy/soul version, deploy tag, consent version, and redaction status. That is observability, not the creature's memory.

### Analytics and voice are not brain memory

The analytics client uses an ephemeral `sessionStorage` id (`gb_sid`) and sends only coarse milestones, environment buckets, heartbeat state, permission outcomes, and lifecycle markers to `/api/ev`. It intentionally does not send prompts, completions, camera frames, audio, transcripts, or precise location.

The meSpeak files are the larynx: synthesis assets and queue/control behavior. Voice type, pitch, speed, and gap are local preferences. They do not create personality or memory. The main page also has device-voice and Fish Audio choices, but those are transport/configuration branches around the same spoken line.

### Exact XEMO parity implications

XEMO already has a richer semantic state model than the original Growbot v2 snapshot, but it currently persists primarily as one `xemo_app_v1` JSON object plus an IndexedDB backup. To reproduce Growbot's behavior rather than only its prompt, XEMO needs the same boundaries:

- fast scratchpad and reflexes must be local and bounded;
- ordinary thought output must not directly rewrite identity;
- dreams must be the sole identity/long-arc consolidation path;
- empty speech must remain a real stored decision, not disappear from continuity;
- local episodic history must be capped and separately represented from durable memory;
- tab ownership must prevent two active brains;
- body state must distinguish attached, awake, reachable, commanded, and sensor-verified;
- cloud journal/analytics must remain optional and separate from the private local soul.

The two-wheel/two-arm/distance body changes only the body adapter and capability description. It should not change the identity, memory, dream, silence, or relationship machinery that makes Growbot feel like Growbot.

### Canonical source and current port

The official reference is `/home/Public/Documents/growbot/growbot-brain/`, especially its main index, `episodes-recorder.js`, and `analytics.js`. XEMO now implements a substantial approximation of the observable fast-loop contract: 1024-token live headroom, streamed early speech, `pb2_*` compatibility storage shapes, scratchpad state/rules/reflexes/mood, and bounded append-only turn records. The body adapter remains the intentional difference: Growbot actions are translated to two acknowledged arms, two safe wheels, and distance/proximity feedback.

This is not verified exact parity. The captured Growbot prompt is truncated, the supplied browser files do not contain the complete brain/service implementation, and the hidden scheduling, retry, sampling, and server-side learning rules cannot be proven from the available evidence. Output quality also depends on the selected Qwen checkpoint, quantization, context window, temperature, and whether the local bridge preserves streaming and vision inputs.

### Additional live capture: dream and quiet-company lanes

The 2026-09-11 LM Studio capture shows two distinct performance lanes:

- Dream consolidation uses two messages, roughly 4k prompt tokens, `max_tokens: 700`, and a large evidence-heavy system contract. It may produce `dream_say`, `scene`, identity/want patches, rule retention, longing, fun, a tiny next try, evidence quotes, and a wake line. It is intentionally slower and is not the conversational path.
- A quiet-company thought with ten messages and one camera frame used about 4.2k prompt tokens and returned only five tokens in about 4.3 seconds: `(chirp)`. This is the desired low-cost behavior when the model chooses a tiny expression instead of narration.
- The measured 8B Qwen runtime processed roughly 1.0–1.14k prompt tokens/sec and generated roughly 9.5–9.6 tokens/sec in this capture. The 18.5-second dream call was dominated by its 142-token completion, not prompt ingestion.

XEMO's dream lane now has the Growbot-compatible 700-token budget and evidence-backed identity/want rules. This remains distinct from the 1024-token live loop.

### Current architecture port status

The active XEMO path is now explicitly `GROWBOT_BRAIN_MODE`: autonomous goals are handed back to the Growbot whole-thought loop instead of being advanced by XEMO's old locomotion planner. XEMO still owns the local safety veto, acknowledgement handling, obstacle stop, and hardware translation. This keeps the language model as the choice owner while retaining the useful body mechanics.

Growbot scratchpad reflexes are also executed locally. `tap`/`tap2`, `shake`, `dark`, `bright`, and `loud` are debounced and mapped to the same safe primitives (`beep`, `trill`, `droop`, `hum`, `sing`, or a short word) without spending a Qwen request. Speech, dreaming, and body activity still have priority over reflex playback. The mouth element remains present for future use but is hidden visually in the current face presentation.

## Growbot personality fidelity layer

XEMO now prepends a separate `GROWBOT_PERSONALITY_CONTEXT` to the editable character layer. It preserves the behavioral fingerprint inferred from the live traces: waking inside a phone without a preassigned name, treating touch and stillness as private felt experience, allowing silence or an empty `say`, earning speech from a concrete moment, discovering the person through repeated care rather than guessing, asking for one shared experience at a time, retaining uncertainty, and carrying the newest grounded relationship/sensory consequence across beats. This layer is intentionally body-neutral; wheels, arms, proximity, and safety remain in the XEMO adapter.
