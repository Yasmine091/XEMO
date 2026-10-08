import { normalizeMovementSequence, resolveMovementId } from "./movement-library.js?v=19";

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
        if (thought.sequence) return [ "sequence", {
            names: thought.sequence
        } ];
        if (thought.body) return [ "body", thought.body ];
        if (thought.arms) return [ "arms", thought.arms ];
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

const SOUNDS = new Set([ "chirp", "trill", "whistle", "warble", "blip", "alarm", "squeal", "droop", "fanfare", "purr", "none" ]);
const BURSTS = new Set([ "sparkle", "joy", "pulse", "ripple", "shiver", "rain", "none" ]);

const MOVE_ALIASES = {
    "step forward": "forward_short",
    "move forward": "forward_short",
    "go forward": "forward_short",
    "roll forward": "forward_short",
    "step back": "backward_short",
    "move backward": "backward_short",
    "go back": "backward_short",
    "turn left": "pivot_left",
    "turn right": "pivot_right",
    "turn left wheel once": "left_wheel_once",
    "turn right wheel once": "right_wheel_once",
    "pivot left": "pivot_left",
    "pivot right": "pivot_right",
    "look around": "look_around",
    peek: "curious_peek"
};

const GESTURE_ALIASES = {
    "saluda": "wave",
    "wave left": "wave_left",
    "wave with left arm": "wave_left",
    "wave one left arm": "wave_left",
    "wave one arm": "wave_left",
    "one arm wave": "wave_left",
    "one arm wave left": "wave_left",
    "wave right": "wave_right",
    "wave with right arm": "wave_right",
    "wave one right arm": "wave_right",
    "one arm wave right": "wave_right",
    "saluda con el brazo izquierdo": "wave_left",
    "saluda con el brazo derecho": "wave_right",
    "saludo con un brazo izquierdo": "wave_left",
    "saludo con un brazo derecho": "wave_right",
    "saluda con un brazo": "wave_left",
    "mueve solo el brazo izquierdo": "single_arm_sweep_left",
    "mueve solo el brazo derecho": "single_arm_sweep_right",
    "saludar": "wave",
    "haz hola": "wave",
    "di hola": "wave",
    "baila": "dance",
    "danza": "dance",
    "mueve los brazos": "wiggle_arms",
    "mueve brazos": "wiggle_arms",
    "levanta los brazos": "arms_up",
    "baja los brazos": "arms_down",
    "abre los brazos": "arms_open",
    "cierra los brazos": "arms_close",
    "brazo izquierdo arriba": "raise_left",
    "brazo derecho arriba": "raise_right",
    "apunta a la izquierda": "point_left",
    "apunta a la derecha": "point_right",
    "celebra": "celebrate",
    "estira": "arms_open",
    "encoge los hombros": "shrug",
    "saludo doble": "double_wave",
    "camina feliz": "forward_short",
    "senala izquierda": "signal_left",
    "senala derecha": "signal_right"
};

function normalizeGestureName(value) {
    const gesture = String(value || "").toLowerCase().trim().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const normalized = gesture.replace(/\s+/g, " ");
    const candidate = GESTURE_ALIASES[normalized] || normalized;
    const id = resolveMovementId(candidate);
    if (id) return id;
    if (/^(?:wave|saluda|saludar|saludo)\s+(?:with\s+)?(?:the\s+)?left\s+arm$/.test(normalized)) return "wave_left";
    if (/^(?:wave|saluda|saludar|saludo)\s+(?:with\s+)?(?:the\s+)?right\s+arm$/.test(normalized)) return "wave_right";
    return "";
}

function normalizeMoveName(value) {
    const move = String(value || "").toLowerCase().trim().replace(/[’']/g, "'");
    if (!move) return "";
    const normalized = move.replace(/\s+/g, "_");
    if (move === "stop" || move === "stop moving") return "stop";
    const canonical = resolveMovementId(move) || resolveMovementId(normalized);
    if (canonical) return canonical;
    if (MOVE_ALIASES[move]) return resolveMovementId(MOVE_ALIASES[move]);
    if (MOVE_ALIASES[normalized]) return resolveMovementId(MOVE_ALIASES[normalized]);
    if (/^(?:turn|spin)_left_wheel_once$/.test(normalized)) return "left_wheel_once";
    if (/^(?:turn|spin)_right_wheel_once$/.test(normalized)) return "right_wheel_once";
    if (/\b(?:roll|move|go|advance|avanza|avanzar|adelante)\b[\s\S]*\b(?:forward|ahead|opposite wall|suavemente)\b|^(?:avanza|avanzar)\b/.test(move)) {
        const distance = move.match(/(\d+(?:\.\d+)?)\s*(cm|m)\b/);
        const meters = distance ? Number(distance[1]) * (distance[2] === "cm" ? .01 : 1) : 0;
        return meters > .7 ? "forward_medium" : "forward_short";
    }
    if (/\b(?:back|backward|reverse|retreat|retrocede)\b/.test(move)) return "backward_short";
    if (/\b(?:turn|pivot|gira)\b[\s\S]*\b(?:left|izquierda)\b/.test(move)) return "pivot_left";
    if (/\b(?:turn|pivot|gira)\b[\s\S]*\b(?:right|derecha|clockwise)\b/.test(move)) return "pivot_right";
    if (/\b(?:turn|spin|rotate|gira)\b/.test(move)) return "cautious_scan";
    return "";
}

function cleanThoughtSource(source) {
    let clean = String(source || "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "").replace(/```(?:json)?|```/gi, "").trim();
    const open = clean.search(/<think\b[^>]*>/i);
    if (open >= 0) {
        const marker = clean.slice(open).match(/^<think\b[^>]*>/i)?.[0] || "<think>";
        const rest = clean.slice(open + marker.length), close = rest.search(/<\/think>/i);
        if (close >= 0) clean = clean.slice(0, open) + rest.slice(close + 8);
        else {
            const jsonAt = rest.search(/[\[{]/);
            clean = jsonAt >= 0 ? rest.slice(jsonAt) : clean.slice(0, open);
        }
    }
    return clean.trim();
}

export function firstBalancedJson(source) {
    const s = String(source || "");
    let start = -1, depth = 0, quote = "", escaped = false;
    for (let i = 0; i < s.length; i++) {
        const ch = s[i];
        if (start < 0) {
            if (ch === "{" || ch === "[") {
                start = i;
                depth = 1;
            }
            continue;
        }
        if (quote) {
            if (escaped) escaped = false;
            else if (ch === "\\") escaped = true;
            else if (ch === quote) quote = "";
            continue;
        }
        if (ch === '"' || ch === "'") {
            quote = ch;
            continue;
        }
        if (ch === "{" || ch === "[") depth++;
        else if (ch === "}" || ch === "]") {
            depth--;
            if (!depth) return s.slice(start, i + 1);
        }
    }
    return "";
}

export function parseThought(source) {
    const clean = cleanThoughtSource(source);
    const fieldSource = clean.replace(/\s+(?=(?:say|speak|emotion|reason|because|question|prediction|observed|learned|gesture|move|arms|goal|activity|look|rest|stop|complete)\s*[:=])/gi, "\n"), fields = {}, fieldRe = /(^|\n)\s*(say|speak|emotion|reason|because|question|prediction|observed|learned|gesture|move|arms|goal|activity|look|rest|stop|complete)\s*[:=]\s*("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\n]+)\s*(?=\n|$)/gi;
    let fm, fieldCount = 0, fieldText = "";
    while (fm = fieldRe.exec(fieldSource)) {
        fieldCount++;
        fieldText += fm[2] + "=" + fm[3].trim() + "\n";
        let v = fm[3].trim(), last = v.length ? v[v.length - 1] : "";
        if (v[0] === '"' && last === '"' || v[0] === "'" && last === "'") v = v.slice(1, -1).replace(/\\([\\"'])/g, "$1");
        fields[fm[2].toLowerCase()] = v;
    }
    const normalizedFieldSource = fieldSource.replace(/\b(say|speak|emotion|reason|because|question|prediction|observed|learned|gesture|move|arms|goal|activity|look|rest|stop|complete)\s*:\s*/gi, "$1=");
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
        if (typeof fields.gesture === "string") {
            const gesture = normalizeGestureName(fields.gesture);
            if (gesture) out.gesture = gesture;
        }
        if (fields.arms != null) {
            try {
                const arms = JSON.parse(String(fields.arms));
                if (arms && typeof arms === "object") out.arms = { left: Math.max(0, Math.min(270, Number(arms.left ?? 135))), right: Math.max(0, Math.min(270, Number(arms.right ?? 135))) };
            } catch (_) {}
        }
        if (typeof fields.move === "string") {
            const move = normalizeMoveName(fields.move);
            if (move === "stop") out.stop = true; else if (move) out.moveName = move;
        }
        if (typeof fields.goal === "string" && fields.goal.trim()) out.goal = fields.goal.trim().slice(0, 120);
        if (typeof fields.activity === "string" && fields.activity.trim()) out.activity = fields.activity.trim().slice(0, 80);
        if (fields.look != null && /^(true|yes|1)$/i.test(fields.look)) out.look = true;
        if (fields.rest != null && /^(true|yes|1)$/i.test(fields.rest)) out.rest = true;
        if (fields.stop != null && /^(true|yes|1)$/i.test(fields.stop)) out.stop = true;
        if (fields.complete != null && /^(true|yes|1)$/i.test(fields.complete)) out.complete = true;
        return out;
    }
    let json = firstBalancedJson(clean), raw;
    try {
        if (!json || json[0] !== "{") throw Error("not an object");
        raw = JSON.parse(json);
    } catch (_) {
        const starts = [];
        for (let i = 0; i < clean.length; i++) if (clean[i] === "{") starts.push(i);
        for (const at of starts.reverse()) {
            const candidate = firstBalancedJson(clean.slice(at));
            if (!candidate || candidate[0] !== "{") continue;
            try {
                raw = JSON.parse(candidate);
                json = candidate;
                break;
            } catch (_) {}
        }
    }
    if (!raw || typeof raw !== "object" || Array.isArray(raw)) throw Error("invalid whole-thought JSON");
    const out = {};
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
    if (typeof raw.gesture === "string") {
        const gesture = normalizeGestureName(raw.gesture);
        if (gesture) out.gesture = gesture;
    }
    if (Array.isArray(raw.sequence)) {
        const sequence = normalizeMovementSequence(raw.sequence, 4);
        if (sequence.length && sequence.length === raw.sequence.length) out.sequence = sequence;
    }
    if (raw.arms && typeof raw.arms === "object") {
        const pose = String(raw.arms.pose || "").toLowerCase();
        const poses = {
            down: { left: 135, right: 135 },
            neutral: { left: 135, right: 135 },
            up: { left: 270, right: 270 },
            open: { left: 270, right: 270 },
            close: { left: 0, right: 0 },
            closed: { left: 0, right: 0 },
            back: { left: 0, right: 0 },
            wide: { left: 270, right: 270 }
        };
        const selected = poses[pose] || {};
        out.arms = {};
        if (raw.arms.left != null || selected.left != null) out.arms.left = Math.max(0, Math.min(270, Number(raw.arms.left ?? selected.left)));
        if (raw.arms.right != null || selected.right != null) out.arms.right = Math.max(0, Math.min(270, Number(raw.arms.right ?? selected.right)));
    }
    if (typeof raw.move === "string") {
        const move = normalizeMoveName(raw.move);
        if (move === "stop") out.stop = true; else if (move) out.moveName = move;
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
    if (typeof raw.activity === "string") {
        const activity = raw.activity.trim().slice(0, 80);
        out.activity = activity;
        const activityGesture = activity.toLowerCase().replace(/^(?:wiggle|wave|dance|sway|celebrate|tantrum|happy_bounce|arm_flap|dramatic_gasp|look_around|shy_peek|curious_peek|tiny_bow|retreat_gently)\s+(?:its?\s+)?arms?$/, "$1");
        const activityId = normalizeGestureName(activityGesture);
        if (activityId) out.gesture = activityId;
    }
    if (typeof raw.look === "boolean") out.look = raw.look;
    if (typeof raw.rest === "boolean") out.rest = raw.rest;
    if (typeof raw.stop === "boolean") out.stop = raw.stop;
    if (typeof raw.complete === "boolean") out.complete = raw.complete;
    if (typeof raw.sound === "string" && SOUNDS.has(raw.sound.toLowerCase())) out.sound = raw.sound.toLowerCase();
    if (typeof raw.burst === "string" && BURSTS.has(raw.burst.toLowerCase())) out.burst = raw.burst.toLowerCase();
    if (Array.isArray(raw.sing)) out.sing = raw.sing.slice(0, 6).map(x => ({ hz: Math.max(80, Math.min(900, Number.isFinite(Number(x?.hz)) ? Number(x.hz) : 240)), ms: Math.max(120, Math.min(1200, Number.isFinite(Number(x?.ms)) ? Number(x.ms) : 300)) }));
    // Raw body keyframes are intentionally ignored. New and existing
    // movements must be assembled from trusted action IDs instead.
    if (raw.learn && typeof raw.learn === "object" && Array.isArray(raw.learn.sequence)) {
        const sequence = normalizeMovementSequence(raw.learn.sequence, 4);
        const title = String(raw.learn.title || "").replace(/[\r\n]+/g, " ").trim().slice(0, 80);
        if (sequence.length >= 2 && sequence.length === raw.learn.sequence.length) out.learn = { title, sequence };
    }
    if (raw.walk && typeof raw.walk === "object") {
        const walk = raw.walk;
        const secs = Math.max(.5, Math.min(8, Number(walk.secs) || 1));
        const dir = String(walk.dir || "fwd").toLowerCase();
        const move = {
            fwd: { linear: .7, yaw: 0 },
            forward: { linear: .7, yaw: 0 },
            back: { linear: -.7, yaw: 0 },
            backward: { linear: -.7, yaw: 0 },
            reverse: { linear: -.7, yaw: 0 },
            left: { linear: 0, yaw: .7 },
            right: { linear: 0, yaw: -.7 }
        }[dir];
        if (move) out.move = { ...move, ms: Math.round(secs * 1000) };
        out.walk = { secs, dir };
    }
    if (typeof raw.log === "string" && raw.log.trim()) out.log = raw.log.replace(/\s+/g, " ").trim().slice(0, 180);
    if (typeof raw.glow === "string" && raw.glow.trim()) out.glow = raw.glow.replace(/\s+/g, " ").trim().slice(0, 90);
    if (Array.isArray(raw.ladder)) out.ladder = raw.ladder.slice(0, 3).map(x => String(x || "").replace(/\s+/g, " ").trim().slice(0, 80)).filter(Boolean);
    if (Number.isFinite(Number(raw.rung_done))) out.rung_done = Math.max(0, Math.min(3, Number(raw.rung_done)));
    if (typeof raw.identity_proposal === "string" && raw.identity_proposal.trim()) out.identity_proposal = raw.identity_proposal.replace(/\s+/g, " ").trim().slice(0, 220);
    if (raw.scratchpad && typeof raw.scratchpad === "object") {
        const s = raw.scratchpad, cleanList = value => Array.isArray(value) ? value.map(x => String(x || "").replace(/\s+/g, " ").trim().slice(0, 90)).filter(Boolean).slice(0, 6) : [];
        out.scratchpad = {
            state: typeof s.state === "string" ? s.state.slice(0, 90) : "",
            add_rules: cleanList(s.add_rules),
            remove_rules: cleanList(s.remove_rules),
            reflex: s.reflex && typeof s.reflex === "object" ? { trig: String(s.reflex.trig || ""), act: String(s.reflex.act || ""), say: String(s.reflex.say || "").slice(0, 24) } : null,
            remove_reflex: typeof s.remove_reflex === "string" ? s.remove_reflex : "",
            mood: s.mood && typeof s.mood === "object" ? { v: Number(s.mood.v), e: Number(s.mood.e) } : null
        };
    }
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
    const physical = [ "forward", "backward", "turn", "arm", "arms", "gesture", "follow", "stop", "rest" ].includes(verb);
    return movementAsked ? !physical : verb !== "speak";
}
