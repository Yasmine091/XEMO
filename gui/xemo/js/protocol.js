export function parseVerb(source) {
    const clean = String(source || "").replace(/<think>[\s\S]*?<\/think>/gi, "").replace(/```(?:\w+)?|```/g, "").trim();
    const shorthand = /^(?:say|speak)\s*=\s*(["'])([\s\S]*?)\1\s*$/i.exec(clean);
    if (shorthand) return [ "speak", {
        text: shorthand[2].trim()
    } ];
    try {
        const thought = parseThought(clean);
        if (thought.say) return [ "speak", {
            text: thought.say
        } ];
        if (thought.gesture) return [ "gesture", {
            name: thought.gesture
        } ];
        if (thought.moveName) return [ "gesture", {
            name: thought.moveName
        } ];
        if (thought.move) return [ "forward", {
            seconds: Math.max(.2, Math.min(4, (thought.move.ms || 700) / 1e3))
        } ];
        if (thought.rest) return [ "rest", {} ];
        if (thought.stop) return [ "stop", {} ];
        if (thought.complete) return [ "complete", {} ];
        if (thought.goal) return [ "goal", {
            text: thought.goal
        } ];
        if (thought.activity) return [ "activity", {
            name: thought.activity
        } ];
        if (thought.look) return [ "look", {} ];
    } catch (_) {}
    const match = /\b([a-z_]+)\s*\(([\s\S]*?)\)/i.exec(clean);
    if (!match) throw Error("invalid one-verb reply");
    let verb = match[1].toLowerCase(), raw = match[2].trim(), params = {};
    if (verb === "say") verb = "speak";
    if (raw) {
        const keyed = /^([a-z_]+)\s*=\s*(?:"([\s\S]*)"|'([\s\S]*)'|(-?\d+(?:\.\d+)?))$/i.exec(raw);
        if (keyed) params[keyed[1].toLowerCase()] = keyed[2] ?? keyed[3] ?? Number(keyed[4]); else if (verb === "speak") params.text = raw.replace(/^["']|["']$/g, ""); else if (/^-?\d+(?:\.\d+)?$/.test(raw)) {
            const key = {
                arm: "degrees",
                turn: "degrees",
                forward: "seconds",
                backward: "seconds"
            }[verb];
            if (!key) throw Error("invalid parameters");
            params[key] = Number(raw);
        } else if (verb === "gesture" || verb === "emote") params.name = raw.replace(/^["']|["']$/g, ""); else throw Error("invalid parameters");
    }
    return [ verb, params ];
}

const EMOTIONS = new Set([ "happy", "excited", "sad", "suspicious", "proud", "love", "confused", "determined", "surprised", "giggly", "wink", "awe", "wonder", "annoyed", "angry", "worried", "focused", "cheeky", "bashful", "shy", "laughing", "dreaming", "scanning", "mischief", "embarrassed", "victorious", "curious", "resting", "calm", "cautious", "protective", "relieved", "lonely", "hopeful", "tender", "frustrated", "bored", "stubborn", "playful", "safe", "homesick", "warm", "attentive", "settled" ]);

const GESTURES = new Set([ "wave", "dance", "sway", "tantrum", "happy_bounce", "arm_flap", "dramatic_gasp", "look_around", "celebrate", "wiggle", "shy_peek", "left_wheel_twice", "right_wheel_twice", "curious_peek", "tiny_bow", "retreat_gently" ]);

const MOVE_ALIASES = {
    "step forward": "forward_short",
    "move forward": "forward_short",
    "go forward": "forward_short",
    "step back": "backward_short",
    "move backward": "backward_short",
    "go back": "backward_short",
    "turn left": "pivot_left",
    "turn right": "pivot_right",
    "look around": "look_around",
    peek: "curious_peek"
};

export function parseThought(source) {
    const clean = String(source || "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").replace(/<think>[\s\S]*?<\/think>/gi, "").replace(/```(?:json)?|```/gi, "").trim();
    const fieldSource = clean.replace(/\s+(?=(?:say|speak|emotion|reason|because|question|prediction|observed|learned|gesture|move|goal|activity|look|rest|stop|complete)\s*[:=])/gi, "\n"), fields = {}, fieldRe = /(^|\n)\s*(say|speak|emotion|reason|because|question|prediction|observed|learned|gesture|move|goal|activity|look|rest|stop|complete)\s*[:=]\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\n]+)\s*(?=\n|$)/gi;
    let fm, fieldCount = 0, fieldText = "";
    while (fm = fieldRe.exec(fieldSource)) {
        fieldCount++;
        fieldText += fm[2] + "=" + fm[3].trim() + "\n";
        let v = fm[3].trim(), last = v.length ? v[v.length - 1] : "";
        if (v[0] === '"' && last === '"' || v[0] === "'" && last === "'") v = v.slice(1, -1).replace(/\\([\\"'])/g, "$1");
        fields[fm[2].toLowerCase()] = v;
    }
    const normalizedFieldSource = fieldSource.replace(/\b(say|speak|emotion|reason|because|question|prediction|observed|learned|gesture|move|goal|activity|look|rest|stop|complete)\s*:\s*/gi, "$1=");
    if (fieldCount && fieldText.trim() === normalizedFieldSource.replace(/\r/g, "").trim()) {
        const out = {};
        if (fields.say != null || fields.speak != null) {
            const s = String(fields.say ?? fields.speak).trim().slice(0, 220);
            if (s) out.say = s;
        }
        if (fields.reason != null || fields.because != null) {
            const r = String(fields.reason ?? fields.because).trim().slice(0, 140);
            if (r) out.reason = r;
        }
        for (const k of [ "question", "prediction", "observed", "learned" ]) {
            if (fields[k] != null && String(fields[k]).trim()) out[k] = String(fields[k]).trim().slice(0, 180);
        }
        if (typeof fields.emotion === "string" && EMOTIONS.has(fields.emotion.toLowerCase())) out.emotion = fields.emotion.toLowerCase();
        if (typeof fields.gesture === "string" && GESTURES.has(fields.gesture.toLowerCase())) out.gesture = fields.gesture.toLowerCase();
        if (typeof fields.move === "string") {
            const move = fields.move.toLowerCase().trim();
            if (GESTURES.has(move)) out.moveName = move; else if (MOVE_ALIASES[move]) out.moveName = MOVE_ALIASES[move];
        }
        if (typeof fields.goal === "string" && fields.goal.trim()) out.goal = fields.goal.trim().slice(0, 120);
        if (typeof fields.activity === "string" && fields.activity.trim()) out.activity = fields.activity.trim().slice(0, 80);
        if (fields.look != null && /^(true|yes|1)$/i.test(fields.look)) out.look = true;
        if (fields.rest != null && /^(true|yes|1)$/i.test(fields.rest)) out.rest = true;
        if (fields.stop != null && /^(true|yes|1)$/i.test(fields.stop)) out.stop = true;
        if (fields.complete != null && /^(true|yes|1)$/i.test(fields.complete)) out.complete = true;
        return out;
    }
    const m = clean.match(/\{[\s\S]*\}/);
    if (!m) throw Error("invalid whole-thought JSON");
    const raw = JSON.parse(m[0]), out = {};
    if (raw.say != null) {
        const s = String(raw.say).replace(/[\r\n]+/g, " ").trim().slice(0, 220);
        if (s.length < 221) out.say = s;
    }
    if (typeof raw.emotion === "string" && EMOTIONS.has(raw.emotion.toLowerCase())) out.emotion = raw.emotion.toLowerCase();
    if (raw.reason != null || raw.because != null) {
        const r = String(raw.reason ?? raw.because).replace(/[\r\n]+/g, " ").trim().slice(0, 140);
        if (r) out.reason = r;
    }
    for (const k of [ "question", "prediction", "observed", "learned" ]) {
        if (raw[k] != null && String(raw[k]).trim()) out[k] = String(raw[k]).replace(/[\r\n]+/g, " ").trim().slice(0, 180);
    }
    if (typeof raw.gesture === "string" && GESTURES.has(raw.gesture.toLowerCase())) out.gesture = raw.gesture.toLowerCase();
    if (typeof raw.move === "string") {
        const move = raw.move.toLowerCase().trim();
        if (GESTURES.has(move)) out.moveName = move; else if (MOVE_ALIASES[move]) out.moveName = MOVE_ALIASES[move];
    }
    if (raw.move && typeof raw.move === "object") {
        const linear = Math.max(-.7, Math.min(.7, Number(raw.move.linear) || 0)), yaw = Math.max(-.7, Math.min(.7, Number(raw.move.yaw) || 0));
        if (Math.abs(linear) + Math.abs(yaw) > 0) out.move = {
            linear: linear,
            yaw: yaw,
            ms: Math.max(250, Math.min(2500, Number(raw.move.ms) || 700))
        };
    }
    if (typeof raw.goal === "string" && raw.goal.trim()) out.goal = raw.goal.trim().slice(0, 120);
    if (typeof raw.activity === "string") out.activity = raw.activity.trim().slice(0, 80);
    if (typeof raw.look === "boolean") out.look = raw.look;
    if (typeof raw.rest === "boolean") out.rest = raw.rest;
    if (typeof raw.stop === "boolean") out.stop = raw.stop;
    if (typeof raw.complete === "boolean") out.complete = raw.complete;
    return out;
}

export function responseNeedsCorrection(reply, {autonomous: autonomous = false, movementAsked: movementAsked = false} = {}) {
    try {
        const t = parseThought(reply);
        if (t && Object.keys(t).length) {
            if (!autonomous && !movementAsked && (!Object.prototype.hasOwnProperty.call(t, "say") || !String(t.say || "").trim())) return true;
            if (!autonomous && Object.prototype.hasOwnProperty.call(t, "say") && t.say === "") return true;
            return false;
        }
    } catch (_) {}
    let verb = "", params = {};
    try {
        [verb, params] = parseVerb(reply);
    } catch (_) {}
    if (verb === "speak") {
        const text = String(params.text || "").trim();
        if (!text || /^(?:[.…]+|undefined|null|(?:reply|response|answer|text)|(?:your )?(?:actual )?(?:natural )?(?:reply|response|answer))$/i.test(text)) return true;
    }
    const prose = String(reply || "").replace(/<think>[\s\S]*?<\/think>/gi, "").replace(/```[\s\S]*?```/g, "").trim();
    if (!autonomous && prose && !/^\s*(?:error|failed|invalid|undefined|null)\b/i.test(prose)) return false;
    if (autonomous) return !verb;
    const physical = [ "forward", "backward", "turn", "arm", "gesture", "follow", "stop", "rest" ].includes(verb);
    return movementAsked ? !physical : verb !== "speak";
}