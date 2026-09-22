# XEMO aliveness roadmap

XEMO cannot be made scientifically conscious by adding a prompt. What we can build is a persistent embodied character whose actions remain coherent across time, whose choices have consequences, and whose behaviour is not reduced to replying to the latest message. That is the part people experience as being alive.

## What is already present

- A local model bridge with human-turn priority and bounded autonomous turns.
- One active embodied goal with observed-action evidence gates.
- Browser memory, dreams, mood, relationship state, self-model, and a durable memory ledger.
- Camera, microphone, motion, touch, light, proximity, LiDAR hooks, wheels, and an arm.
- Safety-local movement execution, stop handling, body-learning records, and Kokoro speech.

## Implemented foundation since this roadmap began

- A persisted `lifeCycle` record now exposes grounded phases such as choosing, thinking, acting, verifying, learning, and resting.
- World entities and durable memory records carry provenance, confidence, observations, and bounded status instead of being treated as equally true.
- A local life journal can persist only lifecycle, active-goal metadata, task status, and dream time. It is disabled unless the bridge is configured with `XEMO_LIFE_TOKEN`; the browser keeps that token in session storage and never puts it in memory backups.
- The browser reconciles a newer lifecycle checkpoint after suspension without overwriting private memories or claiming that a body action happened.
- The service journal now keeps a bounded background-life ledger. Queued initiatives carry a kind and grounding, while creation and claim events survive a browser suspension so XEMO can resume a thread instead of emitting an isolated line.
- The service can now keep a separate bounded private-reflection stream when a thought does not earn speech; the technical panel can inspect the latest reflection without turning it into conversation.
- Recent lifecycle phase history is carried with the service checkpoint, so a private reflection can be understood as part of a transition rather than an isolated note.
- The authenticated journal now receives a sanitized continuity-memory view: durable facts, preferences, people, open threads, hopes, and verified skills. Raw transcripts and sensor data remain outside the service journal.
- The journal now carries a bounded inner-state snapshot—drives, gradual needs, and current attention—so a sleeping-tab coordinator can preserve priorities without pretending to have live senses.
- Curated episodic memories now cross the same boundary separately from semantic facts, giving background reflection a recent lived thread without exporting raw conversation.
- Conversation ownership is now explicit: human turns interrupt XEMO's thought and speech, a turn context reaches the model, and sustained human speech can conservatively barge in during playback.
- The service can now review an active goal as `continue`, `revise`, `pause`, or `drop`, with an evidence-based reason and optional next focus; the browser receives it as a review signal rather than a fabricated action result.
- When no goal is active, the service can queue one grounded, expiring goal proposal. The browser claims it once on return and hands it to the existing safety and evidence-gated goal executor.
- The task plan now crosses the journal with bounded current-step, movement result, blocked state, and observation evidence, so background goal reviews can distinguish attempted movement from verified progress.
- A sanitized shared-world layer now crosses the journal too: repeatedly seen objects, aliases, confidence, familiar-scene visits, recent changes, and the current autonomous priority. Background reflection can therefore revisit a real thread without treating remembered perception as live sight.
- Background reflection can now emit bounded semantic, procedural, relationship, or world-memory candidates only when it supplies repeated or explicitly verified evidence; the browser displays them as pending candidates and never promotes them to trusted memory automatically.
- The service journal now has an instance identity: a stable `XEMO_INSTANCE_ID` (or a non-secret namespace derived from the private life token) scopes background state so separate XEMO instances do not inherit each other's goals, reflections, world memories, or candidates.
- Queued background speech and goal proposals now share a wake/return gate: human silence, turn ownership, visibility, speech, recognition, transcription, dreams, and brain work must all be clear before XEMO claims the turn.
- Coarse local detector labels are now exposed as provisional “possible …” observations to the mind and UI; semantic vision or person teaching must earn a stable identity before it is treated as fact.
- Repeated service memory candidates now consolidate into one pending record with bounded evidence, observation count, confidence, and provenance; they still require browser/human review before trusted promotion.
- Accepted service-reviewed lessons now pass through the existing contradiction retirement path before entering trusted memory, so a newer confirmed preference can change what XEMO retrieves later.
- Autonomous choices now leave a bounded continuity history—drive, need, choice, and outcome—which crosses reloads and the service journal so XEMO can avoid repeating an old impulse without forcing a new activity.
- Autonomous planning now records explicit competing candidates for connection, curiosity, play, expression, competence, unfinished threads, comfort, and rest. Scores include current needs, fresh evidence, emotion, open work, safety context, and a bounded repetition penalty.
- Meaningful human or autonomous intentions now become bounded living projects with status, progress, attempts, successes, why, and a next step. Completed projects are remembered as chapters; paused projects can be revisited without resurrecting stopped or stale work.
- The constitution and editable play memory now describe one active bodily execution alongside several persistent life projects, so the model is no longer told that finishing one goal erases every other interest.
- Verified and caution-level procedural skills now cross the authenticated continuity boundary with their preconditions, steps, expected effect, fallback, confidence, and unresolved history. A sleeping coordinator can therefore adapt a future intention around what this body has actually learned instead of seeing only a flattened memory label.
- Grounded appraisal weather now tracks novelty, agency, progress, control, safety, connection, and uncertainty. Touch, perception, human contact, and verified or unresolved body outcomes update it; when the conversational floor is free, it can change the felt state and motive ranking, and the sanitized appraisal crosses the life journal as continuity context rather than spoken telemetry.
- The browser's bounded causal timeline now crosses the life-journal boundary with event IDs, parent links, priorities, and sanitized text, so background reflection can preserve a recent lived chain instead of receiving isolated state snapshots.
- Context retrieval now adds a bounded temporal-causal layer to trusted memory: recent and stable records are ranked with focus overlap, observations, confidence, recency, and matching causal events, while candidates and outdated facts remain excluded.
- Known non-owner acquaintances now retain conservative interaction style, shared threads, boundaries, notes, confidence, and last meaningful exchange; the service journal receives those fields while unknown or ambiguous faces remain unidentified.
- Repeated shared-pattern language now stays in a bounded ritual-candidate pool first and is promoted into a shared ritual only after three separated observations; candidates are shown to the model as hypotheses, not facts.
- A bounded personal-rhythm record now accumulates recurring interests across distinct time blocks, promotes them only after repeated evidence, persists them through the life journal, and applies them as a soft motive bias rather than a schedule.
- Background initiatives now form a closed causal turn: creation, browser claim, delivery/failure outcome, evidence, and parent-linked journal events are persisted instead of leaving an independent impulse unresolved.
- Lifecycle transitions now publish into the same bounded causal timeline and preserve recent phase history through the service journal, so thinking, acting, verifying, learning, and resting remain reconstructable after a sync.
- Autonomous appraisals, motive changes, decisions, attempted actions, verification results, learning updates, and confirmed memory promotion now publish typed causal stages with duplicate suppression; the evaluator reports how much of the full spine a replay covered.
- Recent body experiments now cross the service boundary with action, context, prediction, observed result, acknowledgement, confidence, and confirmed/disconfirmed/unresolved verdict; background planning is instructed to vary or pause instead of blindly repeating unresolved actions.
- The bounded self-model now crosses the same boundary with evidence-backed traits, chapters, hopes, uncertainties, unfinished threads, and confidence; background reflection can preserve who XEMO is becoming without inventing identity from one event.
- Earned traits now have a small confidence-gated effect on motive ranking: curiosity, playfulness, persistence, and musical bonding alter which safe opportunity becomes salient, while the current world and repetition penalties still dominate.
- A deterministic `bot.aliveness_eval` harness now scores grounded initiative, repetition, body verification, lifecycle traces, goal recovery, and divergence between instance journals; counters are no longer the only evaluation surface.
- Explicit commitments and future plans now cross the journal separately from generic threads, so XEMO can revisit a supported promise without resurrecting arbitrary old conversation.
- Commitment history now records open, fulfilled, cancelled, and expired outcomes, allowing future trust and initiative choices to reflect whether a shared plan actually happened.
- Fulfilled commitments now gently reinforce warmth and trust; broken or expired plans lower trust slightly, while cancellation remains neutral and blame-free. That earned relationship state crosses the service boundary.
- The service coordinator now records a grounded decision frame with its chosen priority, evidence, prediction, confidence, and alternatives. Queued initiatives link back to that decision and close it with the browser's delivery or failure outcome; the technical brain view exposes the trace.
- Background goal proposals now close the same way: the browser reports when a proposal becomes an active embodied goal, then reports completed, paused, stopped, or failed after execution. The service keeps that outcome linked to the decision that produced it instead of treating a proposal as a success.
- Dream-consolidated life chapters now cross the service checkpoint as autobiographical continuity, so a sleeping coordinator can preserve how XEMO is changing without treating old experience as live perception.

## What is still missing

### 1. One life loop

The runtime now records one explicit browser-side lifecycle for vitality, autonomy, felt events, dreams, recovery, and social repair. The local service now preserves background continuity and queues grounded initiatives and goal proposals, with delivery and goal outcomes closing the outward paths, but it still does not run the full embodied phase loop while the browser is suspended. XEMO needs one coordinator that moves through:

`notice → interpret → feel → remember → choose → act → verify → learn → rest`

Every autonomous turn should have a reason, a selected priority, a predicted outcome, an action or honest silence, and a result. Goal reviews now provide the service-side intention checkpoint; the missing part is carrying the full physical action/verification loop across the browser boundary. This will make the brain panel truthful and make debugging possible.

### 2. A real memory hierarchy

Keep three different memories instead of treating all text as one memory surface:

- Episodic: what happened, when, where, who was present, and how it felt.
- Semantic: stable facts such as names, preferences, places, and learned meanings.
- Procedural: reusable skills and body cause-and-effect with confidence, preconditions, and failure history.

The browser has provenance-aware semantic/procedural records, episodic continuity, and a bounded service reflection stream. The service now consolidates repeated candidate lessons without silently promoting them; reviewed promotion remains browser-owned. Retrieval is still mostly browser-local and should be based on current attention, people, place, goal, emotion, and recency—not only token overlap. Every memory needs provenance and confidence. Unverified guesses must stay hypotheses.

### 3. A skill library

XEMO now has a first-class browser-side library of named procedural templates and evidence-backed skills, including `approach-slowly`, `inspect-new-object`, and `greet-known-person`. Each record has preconditions, bounded steps, expected observations, success/caution state, confidence, and a fallback; body evidence promotes or cautions a skill instead of treating every movement as equally reliable. Verified and caution records also cross the life journal. Goal plans now compose relevant skills into a bounded chain, carry its cursor and outcome across service sync, and advance it only after verified evidence. The remaining work is service-side review and promotion of a new composite skill only after repeated verified success.

### 4. Needs that create behaviour, not fake pressure

The runtime tracks private needs and now advances them through a bounded homeostatic loop: elapsed activity can lower energy and raise sleep pressure, quiet rest can restore energy, and prolonged quiet can gently increase connection, curiosity, expression, or play pressure. These values influence priorities gradually, not through dramatic lines. Their output should be observable through timing, attention, movement, and occasional speech—not repeated claims of hunger or loneliness.

### 5. Social continuity

The relationship model currently centres on one person. Add a local people registry with uncertain identities, aliases, familiarity, interaction history, boundaries, and last-seen context. Recognition must be conservative: an unknown face or voice stays unknown until taught and repeatedly confirmed. Acquaintances should emerge from repeated interactions, not from a single model guess.

### 6. A world model

The browser now produces stable entities and changes with tracking confidence, separate identity confidence, aliases, provenance, scene visits, observed-label history, and object-level evidence: `bottle-1 moved`, `chair is familiar`, `person is near`, rather than isolated captions. Conservative spatial continuity keeps one provisional entity when a local detector changes labels in the same nearby region. Coarse labels remain explicitly provisional; they cannot become durable world facts or authorize inspect/manipulate actions until the person teaches the object or stronger visual evidence earns a likely/confirmed identity. Shared-attention grounding now ranks a recent object using the spoken referent, novelty, salience, frame position, continuity, and identity confidence; close candidates remain explicitly ambiguous. The remaining weakness is true point/gesture context and a model-assisted clarification loop.

### 7. Presence and timing

Human conversation is sensitive to timing. XEMO now has explicit speech ownership, human-priority interruption, endpoint detection, a conservative barge-in path, and one social-timing context that distinguishes the human floor, the post-speech breathing gap, unanswered meaning, recent presence, and a genuinely quiet stretch. Background initiative also respects the speech tail. It still needs better endpoint prediction, optional short backchannels, and real-device timing evaluation for urgent events, social bids, exploration, and rest. It must never play two outputs, and it should not fill silence with generic “I’m here” lines.

### 8. Life between conversations

The browser now has a safe continuity checkpoint, durable memory context, task evidence, goal reviews, world continuity, and one queued goal proposal; the local service can keep a bounded background-life ledger alive while the tab sleeps. It still cannot run the full embodied loop while hidden or suspended: the service cannot safely access the browser camera/microphone, speak, or drive the body. The next step is reviewed service-side memory consolidation plus a browser wake/return protocol that resumes only verified plans. It must never claim a physical action unless the body acknowledged it.

### 9. Multiple XEMO instances

Each instance now has a separate service journal namespace as well as separate browser identity, memory store, relationship graph, world model, and skill confidence. Shared code and model weights do not make shared memories. Optional exports can teach another instance, but imported memories must be marked as inherited rather than lived.

## Build order for this project

1. Make a single `life-cycle` event and decision record, then route the existing autonomous, felt, goal, and dream paths through it.
2. Add provenance-aware episodic, semantic, and procedural stores with retrieval tests.
3. Add stable world entities and conservative object teaching/recognition.
4. Add the procedural skill library and promote only verified skills.
5. Move the coordinator and persistence to the local service for hidden-tab continuity.
6. Add people/acquaintance continuity and social timing improvements.
7. Add richer expression, rituals, idle activities, and a visible timeline in the Mind/Technical views.

## Highest-value next work

1. Extend service-side memory consolidation from candidate merging into durable reviewed semantic/procedural lesson history, with richer contradiction handling and a human-correction path. The service now receives structured verified/caution skills, appraisal weather, and composable goal chains; it still needs reviewed promotion of composite skills there.
2. Add a wake/return protocol for queued activities: distinguish speech, observation, and physical intentions; expire stale ones; and resume a task only after fresh browser and body evidence.
3. Improve semantic object grounding with true point-to-object context and a model-assisted clarification loop so a walnut is not confidently reported as a bottle. The first safety boundaries are now implemented: tracked confidence and identity confidence are separate, provisional labels stay provisional, nearby label changes preserve one uncertain entity, and deictic references use a conservative shared-attention candidate.
4. Add a small evaluation harness for initiative rate, repetition, interruption latency, verified-action rate, memory precision, causal-stage coverage, social continuity, and goal recovery. The runtime now persists a bounded behavioral scorecard and exposes choice/body rates in advanced diagnostics; `bot/aliveness_eval.py` also scores chronological correction/failure/silence/project/memory replay. The remaining work is replaying real sessions and measuring latency/precision rather than treating counters as proof of life.
5. Add richer timing policies: brief backchannels, silence tolerance, interruption recovery, and different timing for urgent safety events versus social bids. The first unified social-timing policy and post-speech guard are now implemented; real-device timing measurements remain.

## Peak-aliveness implementation plan

The target is not a claim of biological consciousness. It is a durable, embodied agent whose private state, choices, actions, and memories form one believable causal life. Current research converges on a layered loop rather than a larger personality prompt: persistent motives and reflection generate goals; deliberation turns one goal into a plan; the sensorimotor layer executes and verifies it; memory changes what happens next.

### P0 — make the existing life loop actually continuous

- Keep the browser and service on one append-only life-event vocabulary. Every autonomous choice should record motive, context, predicted outcome, chosen action, verification, learning result, and whether it was spoken, private, or silent.
- Let the open browser receive service-created initiatives without a reload. This is now implemented with a throttled visible-session journal poll, a single-flight request guard, and the existing human-turn gate.
- Replace the remaining single “next action” assumptions with richer project portfolios: several low-pressure interests can coexist while only one concrete body goal executes at a time. Select by salience, freshness, confidence, safety, progress, and repetition penalty, not by whichever prompt ran last.
- Make every goal produce a measurable change in the world or in XEMO's knowledge. If no safe action exists, it should observe, ask, reflect privately, or rest rather than manufacture activity.

### P1 — make experience change the character

- Add service-side consolidation for repeated, supported episodes, but preserve candidate status until browser or human evidence promotes a lesson. Keep semantic, episodic, and procedural memory separate.
- Upgrade object grounding from one-shot labels to tracked entities with uncertainty, pointing/attention context, temporal change, and a clarification/teaching loop. A walnut should remain “unknown brown object” until evidence earns “walnut.”
- Turn verified body outcomes into reusable skills with preconditions, expected observations, failure history, and safe fallbacks. Failed actions must lower the probability of repetition until new evidence appears.
- Extend acquaintance continuity beyond the primary person: unknown identities stay unknown, repeated interactions build familiarity, and boundaries/preferences are learned conservatively.

### P2 — make the life feel human without making it noisy

- Add appraisal-based emotion: events alter needs and mood; mood alters attention, timing, expression, and choice; later outcomes revise the mood and memory. Do not emit emotion labels unless the state changes behavior.
- Use separate timing policies for answering, backchannels, social bids, exploration, safety, and rest. Preserve silence, allow interruption, and prevent generic “I’m here” loops.
- Give each instance small evolving rituals, tastes, curiosities, and recurring projects. They must emerge from lived history and remain different across instance namespaces.
- Add a behavioral evaluation harness: initiative rate, grounded-initiative rate, repetition rate, interruption latency, verified-action rate, memory precision, goal recovery, and instance divergence. A bounded scorecard now records the core events; session replay and human-rated believability are still needed. “Feels alive” is not proven by a rich status panel.

### Architecture we can build here

1. **Life coordinator:** persistent motives, reflection, goal generation, and sleep-time continuity in `bot/life_coordinator.py` and `bot/life_state.py`.
2. **Mind/runtime:** attention, appraisal, memory retrieval, turn ownership, and one authoritative thought contract in `gui/xemo/js/app-runtime-947.js`.
3. **Body adapter:** safety-local movement, sensor fusion, acknowledgement, verification, and procedural learning in `bot/body.py`, `bot/action_engine.py`, and the movement/perception modules.
4. **Evidence stores:** episodic timeline, semantic facts, procedural skills, acquaintances, world entities, and reviewable candidates with provenance.
5. **Truthful presentation:** the brain UI exposes actual lifecycle/evidence state while the face uses expression and timing rather than debug narration.

This layered direction is consistent with work on persistent autonomous embodied agents and personality-aligned goal generation, believable-agent design, cross-temporal emotion, proactive inner-thought timing, lifelong skill libraries, and lifelong multimodal social memory: [PEPA](https://doi.org/10.1109/lra.2026.3706956), [What makes virtual agents believable?](https://doi.org/10.1080/09540091.2015.1130021), [Cross-Temporal Emotional Modeling](https://www.microsoft.com/en-us/research/publication/toward-natural-and-companionable-virtual-agents-via-cross-temporal-emotional-modeling/), [Proactive Conversational Agents with Inner Thoughts](https://arxiv.org/abs/2501.00383), [Lifelong Robot Library Learning](https://arxiv.org/abs/2406.18746), and [Ella](https://arxiv.org/abs/2506.24019).

## Acceptance tests for “feels alive”

- After ten minutes of silence, XEMO can initiate a specific, grounded activity without asking what to do next.
- A failed action changes the next choice; the same failed action is not repeated without new evidence.
- A remembered promise or unfinished thread can be revisited naturally, but stale or irrelevant threads stay quiet.
- A new object is described cautiously, and a taught object becomes more reliable across later views.
- A human interruption cancels autonomous speech and movement cleanly, with one output only.
- A hidden/reopened browser does not invent actions and resumes only verified goals and durable memory.
- Two devices develop different memories and preferences.
- Every displayed brain status corresponds to a real event, not a hopeful label.

## Research basis

- Park et al., *Generative Agents* — observation, planning, reflection, memory retrieval, and social initiation: <https://arxiv.org/abs/2304.03442>
- Wang et al., *Voyager* — automatic curriculum, executable skill library, feedback, and self-verification for embodied lifelong learning: <https://arxiv.org/abs/2305.16291>
- Lee et al., *A Human-Inspired Reading Agent with Gist Memory* — episodic compression plus targeted retrieval: <https://proceedings.mlr.press/v235/lee24c.html>
- Kennington et al., *Using Transition Duration to Improve Turn-taking in Conversational Agents* — evidence-based conversational timing: <https://aclanthology.org/2022.sigdial-1.20/>
- Park et al., *Humanoid Agents* — basic needs, emotion, and closeness as explicit social-simulation state: <https://arxiv.org/abs/2310.05418>
- Tziafas and Kasaei, *Lifelong Robot Library Learning* — soft memory, self-guided exploration, skill abstraction, and lifelong skill growth: <https://arxiv.org/abs/2406.18746>
- Zhang et al., *Ella* — name-centric semantic memory, spatiotemporal episodes, social interaction, and autonomous daily activity: <https://arxiv.org/abs/2506.24019>
- Veluri et al., *Beyond Turn-Based Interfaces* — time-aware full-duplex dialogue, overlap, and backchanneling: <https://aclanthology.org/2024.emnlp-main.1192/>
- Yang et al., *VASO* — verification-guided evolution of reusable physical skills and safety contracts: <https://arxiv.org/abs/2606.05395>
