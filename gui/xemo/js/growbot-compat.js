// Growbot-compatible browser surfaces for XEMO.
//
// This is deliberately an adapter, not a second brain: the XEMO state remains
// authoritative while the observable Growbot localStorage contract is kept in
// sync for inspection, migration, and episode tooling.

const clean = (value, max = 800) => String(value ?? "").replace(/\s+/g, " ").trim().slice(0, max);
const put = (key, value, scalar = false) => {
    try {
        localStorage.setItem(key, scalar ? String(value ?? "") : JSON.stringify(value));
    } catch (_) {}
};

export function createGrowbotCompat({ state, sessionId, bodyConnected = () => false } = {}) {
    const now = () => Date.now();
    let episode = 0;

    function readJson(key, fallback) {
        try {
            const value = JSON.parse(localStorage.getItem(key) || "null");
            return value == null ? fallback : value;
        } catch (_) { return fallback; }
    }

    function hydrate() {
        // Import only the official Growbot surfaces when XEMO is still at its
        // seed state. Existing XEMO memories always win over compatibility data.
        const identity = localStorage.getItem("pb2_identity");
        if (identity && state.soul && /newly awake|newly waking|curious little robot/i.test(String(state.memory || state.soul.identity || ""))) {
            state.soul.identity = clean(identity, 900);
            state.memory = state.soul.identity;
        }
        const scratch = readJson("pb2_scratch", null);
        if (scratch && typeof scratch === "object") {
            state.scratchpad = {
                state: clean(scratch.state || "just woken", 90),
                rules: Array.isArray(scratch.rules) ? scratch.rules.map(x => clean(x, 90)).filter(Boolean).slice(-6) : [],
                reflexes: Array.isArray(scratch.reflexes) ? scratch.reflexes.filter(x => x && typeof x === "object").slice(-6) : [],
                traces: Array.isArray(scratch.traces) ? scratch.traces.slice(-8) : [],
                glows: Array.isArray(scratch.glows) ? scratch.glows.slice(-10) : [],
                mood: scratch.mood && typeof scratch.mood === "object" ? scratch.mood : { v: 0, e: .4 }
            };
        }
    }

    function sync() {
        if (!state) return;
        const soul = state.soul || {}, scratch = state.scratchpad || {};
        const diary = Array.isArray(soul.diary) ? soul.diary : [];
        const rules = Array.isArray(soul.rules) ? soul.rules : [];
        const goals = state.activeGoal || state.intention || {};
        put("pb2_identity", clean(soul.identity || state.personality || "a curious little robot person", 900), true);
        put("pb2_scratch", {
            state: clean(state.lifeCycle?.phase || "resting", 32),
            rules: rules.slice(-6).map(x => clean(x, 180)),
            reflexes: Array.isArray(scratch.reflexes) ? scratch.reflexes.slice(-6) : [],
            traces: Array.isArray(state.moments) ? state.moments.slice(-6).map(x => ({
                u: clean(x?.text || x?.content, 220),
                a: clean(x?.kind || "moment", 32)
            })) : [],
            glows: [],
            mood: { v: +soul.mood?.v || 0, e: +soul.mood?.e || 0 },
            pending: null
        });
        const existing = readJson("pb2_log", []);
        // pb2_log is append-only in Growbot. Do not rewrite the whole XEMO
        // diary on every save or one thought would appear hundreds of times.
        if ((!Array.isArray(existing) || !existing.length) && diary.length) {
            put("pb2_log", diary.slice(-200).map(text => ({ t: now(), txt: clean(text, 400) })));
        }
        put("pb2_goals", {
            wants: Array.isArray(soul.wants) ? soul.wants.slice(-8).map(x => clean(x, 180)) : [],
            longing: clean(state.selfModel?.longing || "", 180),
            funLog: Array.isArray(state.funLog) ? state.funLog.slice(-8) : [],
            call: clean(state.activeGoal?.question || "", 180),
            song: "",
            nextTry: clean(state.activeGoal?.nextStep || "", 180),
            ladder: Array.isArray(state.activeGoal?.planSteps) ? state.activeGoal.planSteps.slice(-8) : [],
            lastLived: clean(state.lastActionResult?.observed || "", 180),
            pendingReached: false
        });
        put("pb2_beats", {
            face: !!state.birthSense?.passed?.includes("sight"),
            nap: !!state.lastSleepAt,
            dream: !!state.lastDream,
            pact: !!soul.owner,
            askedSupport: false,
            askedFeedback: false
        });
        const gateOrder = ["head", "updown", "face", "bright", "dark", "humlow", "speak"];
        const passed = Array.isArray(state.birthSense?.passed) ? state.birthSense.passed : [];
        const gate = state.birthSense?.complete ? gateOrder.length : Math.max(0, passed.length);
        put("pb2_gate", gate, true);
        put("pb2_gatesp", passed.slice(), false);
        put("pb2_n", episode, true);
        put("pb2_dreamn", Math.max(0, +state.lastDream || 0), true);
        put("pb2_body", clean(state.bodyEndpoint || state.endpoint || "", 300), true);
        put("pb2_bodyon", bodyConnected() ? "1" : "0", true);
        put("pb2_sid", sessionId || "", true);
        put("pb2_tab", { id: sessionId || "", t: now() });
    }

    function recordTurn({ observation = "", decision = "", human = "", provenance = "xemo" } = {}) {
        episode++;
        const text = clean(decision || human || observation, 400);
        const log = readJson("pb2_log", []);
        if (text && log[log.length - 1]?.txt !== text) log.push({ t: now(), txt: text });
        put("pb2_log", log.slice(-200));
        put("pb2_n", episode, true);
        put("pb2_last_turn", {
            t: now(),
            obs: clean(observation, 900),
            decision: clean(decision, 900),
            human: clean(human, 900),
            provenance: clean(provenance, 180)
        });
    }

    function recordMotor(sample) {
        const key = "pb2_motor";
        let rows = [];
        try { rows = JSON.parse(localStorage.getItem(key) || "[]"); } catch (_) {}
        rows.push({ t: now(), ...sample });
        put(key, rows.slice(-120));
    }

    function applyThought(thought) {
        const s = thought?.scratchpad;
        if (!s) return;
        state.scratchpad = state.scratchpad || { state: "just woken", rules: [], reflexes: [], traces: [], glows: [], mood: { v: 0, e: .4 } };
        const target = state.scratchpad;
        if (s.state) target.state = clean(s.state, 90);
        const remove = new Set((s.remove_rules || []).map(x => clean(x, 90).toLowerCase()));
        target.rules = (target.rules || []).filter(x => !remove.has(clean(x, 90).toLowerCase()));
        for (const rule of s.add_rules || []) {
            const value = clean(rule, 90);
            if (value && !target.rules.some(x => clean(x, 90).toLowerCase() === value.toLowerCase())) target.rules.push(value);
        }
        target.rules = target.rules.slice(-6);
        if (s.reflex?.trig && s.reflex?.act) {
            target.reflexes = (target.reflexes || []).filter(x => x.trig !== s.reflex.trig);
            target.reflexes.push({ trig: s.reflex.trig, act: s.reflex.act, ...(s.reflex.say ? { say: clean(s.reflex.say, 24) } : {}) });
            target.reflexes = target.reflexes.slice(-6);
        }
        if (s.remove_reflex === "all") target.reflexes = [];
        else if (s.remove_reflex) target.reflexes = (target.reflexes || []).filter(x => x.trig !== s.remove_reflex);
        if (s.mood && Number.isFinite(s.mood.v) && Number.isFinite(s.mood.e)) target.mood = { v: Math.max(-1, Math.min(1, s.mood.v)), e: Math.max(0, Math.min(1, s.mood.e)) };
        sync();
    }

    hydrate();
    return { sync, recordTurn, recordMotor, applyThought };
}
