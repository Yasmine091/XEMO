# XEMO aliveness roadmap

XEMO cannot be made scientifically conscious by adding a prompt. What we can build is a persistent embodied character whose actions remain coherent across time, whose choices have consequences, and whose behaviour is not reduced to replying to the latest message. That is the part people experience as being alive.

## What is already present

- A local model bridge with human-turn priority and bounded autonomous turns.
- One active embodied goal with observed-action evidence gates.
- Browser memory, dreams, mood, relationship state, self-model, and a durable memory ledger.
- Camera, microphone, motion, touch, light, proximity, LiDAR hooks, wheels, and an arm.
- Safety-local movement execution, stop handling, body-learning records, and Kokoro speech.

## What is still missing

### 1. One life loop

The runtime has many timers for vitality, autonomy, felt events, dreams, recovery, and social repair. They protect one another, but they do not yet share one explicit lifecycle. XEMO needs one coordinator that moves through:

`notice → interpret → feel → remember → choose → act → verify → learn → rest`

Every autonomous turn should have a reason, a selected priority, a predicted outcome, an action or honest silence, and a result. This will make the brain panel truthful and make debugging possible.

### 2. A real memory hierarchy

Keep three different memories instead of treating all text as one memory surface:

- Episodic: what happened, when, where, who was present, and how it felt.
- Semantic: stable facts such as names, preferences, places, and learned meanings.
- Procedural: reusable skills and body cause-and-effect with confidence, preconditions, and failure history.

Retrieval should be based on current attention, people, place, goal, emotion, and recency—not only token overlap. Every memory needs provenance and confidence. Unverified guesses must stay hypotheses.

### 3. A skill library

XEMO currently remembers body lessons, but it does not yet have a first-class library of named, composable skills. Add skills such as `approach_slowly`, `inspect_new_object`, `greet_known_person`, or `return_to_charging_place`, each with preconditions, bounded steps, expected observations, success rate, and a safe fallback. Promote a new skill only after repeated verified success.

### 4. Needs that create behaviour, not fake pressure

The runtime already tracks private needs. They should influence priorities gradually, not force dramatic lines. Useful needs are curiosity, connection, play, comfort, rest, and competence. Their output should be observable through timing, attention, movement, and occasional speech—not repeated claims of hunger or loneliness.

### 5. Social continuity

The relationship model currently centres on one person. Add a local people registry with uncertain identities, aliases, familiarity, interaction history, boundaries, and last-seen context. Recognition must be conservative: an unknown face or voice stays unknown until taught and repeatedly confirmed. Acquaintances should emerge from repeated interactions, not from a single model guess.

### 6. A world model

Perception should produce stable entities and changes: `bottle-1 moved`, `chair is familiar`, `person is near`, `room is darker`, rather than isolated captions. XEMO should compare observations over time and ask for help when confidence is low. This directly addresses the walnut/bottle failure mode.

### 7. Presence and timing

Human conversation is sensitive to timing. XEMO needs a turn-taking layer with listening, endpoint detection, interruption, thinking latency, short backchannels, and speech ownership. It must never play two outputs, and it should not fill silence with generic “I’m here” lines. Autonomous initiatives need distinct cooldowns for urgent events, social bids, exploration, and rest.

### 8. Life between conversations

The browser cannot reliably run a full autonomous loop while hidden or suspended. For genuine continuity, move the durable life coordinator to the local Python service. The browser remains the face and sensor client; the service keeps time, memory, goals, dreams, and safe background planning alive even when the phone screen sleeps. It must never claim a physical action unless the body acknowledged it.

### 9. Multiple XEMO instances

Each instance should have a separate identity, memory store, relationship graph, world model, and skill confidence. Shared code and model weights do not make shared memories. Optional exports can teach another instance, but imported memories must be marked as inherited rather than lived.

## Build order for this project

1. Make a single `life-cycle` event and decision record, then route the existing autonomous, felt, goal, and dream paths through it.
2. Add provenance-aware episodic, semantic, and procedural stores with retrieval tests.
3. Add stable world entities and conservative object teaching/recognition.
4. Add the procedural skill library and promote only verified skills.
5. Move the coordinator and persistence to the local service for hidden-tab continuity.
6. Add people/acquaintance continuity and social timing improvements.
7. Add richer expression, rituals, idle activities, and a visible timeline in the Mind/Technical views.

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

