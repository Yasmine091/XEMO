// Stable, language-neutral action IDs backed by a small set of bounded motor
// keyframes. Natural-language understanding belongs to the brain; this module
// only resolves IDs, composes trusted actions, and enforces physical limits.
const movement = (label, surface, steps, navigation = false) => ({
  label,
  surface,
  navigation,
  steps
});

export const MOVEMENTS = {
  stop: movement("stop", "any", [{ left: 0, right: 0, ms: 120 }]),
  forward_short: movement("brief forward roll", "floor", [{ left: .24, right: .24, ms: 600, arm: 135, armBoth: true }], true),
  forward_medium: movement("steady forward roll", "floor", [{ left: .25, right: .25, ms: 1050, arm: 135, armBoth: true }], true),
  backward_short: movement("brief reverse roll", "floor", [{ left: -.24, right: -.24, ms: 600, arm: 135, armBoth: true }], true),
  pivot_left: movement("pivot left", "floor", [{ left: -.34, right: .34, ms: 500, arm: 135, armBoth: true }], true),
  pivot_right: movement("pivot right", "floor", [{ left: .34, right: -.34, ms: 500, arm: 135, armBoth: true }], true),
  arc_left: movement("curved roll left", "floor", [{ left: .14, right: .30, ms: 700, arm: 135, armBoth: true }], true),
  arc_right: movement("curved roll right", "floor", [{ left: .30, right: .14, ms: 700, arm: 135, armBoth: true }], true),
  scan_left: movement("short left scan", "floor", [{ left: -.25, right: .25, ms: 420, arm: 135, armBoth: true }], true),
  scan_right: movement("short right scan", "floor", [{ left: .25, right: -.25, ms: 420, arm: 135, armBoth: true }], true),
  cautious_scan: movement("scan left, then right", "floor", [
    { left: -.22, right: .22, ms: 420, arm: 135, armBoth: true },
    { left: 0, right: 0, ms: 180 },
    { left: .22, right: -.22, ms: 840, arm: 135, armBoth: true }
  ], true),

  arms_down: movement("both arms down / neutral", "any", [{ left: 0, right: 0, arm: 135, armBoth: true, ms: 420 }]),
  arms_up: movement("both arms raised", "any", [{ left: 0, right: 0, arm: 270, armBoth: true, ms: 520 }]),
  arms_back: movement("both arms back", "any", [{ left: 0, right: 0, arm: 0, armBoth: true, ms: 480 }]),
  arms_open: movement("both arms in an open pose", "any", [{ left: 0, right: 0, arm: 20, armRight: 250, ms: 520 }]),
  raise_left: movement("raise only the left arm", "any", [{ left: 0, right: 0, arm: 270, armBoth: false, ms: 500 }]),
  raise_right: movement("raise only the right arm", "any", [{ left: 0, right: 0, armRight: 270, ms: 500 }]),
  lower_left: movement("lower only the left arm", "any", [{ left: 0, right: 0, arm: 135, armBoth: false, ms: 420 }]),
  lower_right: movement("lower only the right arm", "any", [{ left: 0, right: 0, armRight: 135, ms: 420 }]),
  wave_left: movement("wave with the left arm only", "any", [
    { left: 0, right: 0, arm: 270, armBoth: false, ms: 360 },
    { left: 0, right: 0, arm: 235, armBoth: false, ms: 260 },
    { left: 0, right: 0, arm: 270, armBoth: false, ms: 360 },
    { left: 0, right: 0, arm: 135, armBoth: false, ms: 360 }
  ]),
  wave_right: movement("wave with the right arm only", "any", [
    { left: 0, right: 0, armRight: 270, ms: 360 },
    { left: 0, right: 0, armRight: 235, ms: 260 },
    { left: 0, right: 0, armRight: 270, ms: 360 },
    { left: 0, right: 0, armRight: 135, ms: 360 }
  ]),
  wave_both: movement("wave with both arms", "any", [
    { left: 0, right: 0, arm: 270, armRight: 270, ms: 360 },
    { left: 0, right: 0, arm: 235, armRight: 235, ms: 260 },
    { left: 0, right: 0, arm: 270, armRight: 270, ms: 360 },
    { left: 0, right: 0, arm: 135, armRight: 135, ms: 360 }
  ]),
  signal_left: movement("signal left with the left arm", "any", [{ left: 0, right: 0, arm: 270, armBoth: false, ms: 520 }]),
  signal_right: movement("signal right with the right arm", "any", [{ left: 0, right: 0, armRight: 270, ms: 520 }]),
  salute_left: movement("brief left-arm salute", "any", [
    { left: 0, right: 0, arm: 270, armBoth: false, ms: 300 },
    { left: 0, right: 0, arm: 135, armBoth: false, ms: 360 }
  ]),
  salute_right: movement("brief right-arm salute", "any", [
    { left: 0, right: 0, armRight: 270, ms: 300 },
    { left: 0, right: 0, armRight: 135, ms: 360 }
  ]),
  shrug: movement("small two-arm shrug", "any", [
    { left: 0, right: 0, arm: 95, armRight: 95, ms: 300 },
    { left: 0, right: 0, arm: 135, armRight: 135, ms: 360 }
  ]),
  sweep_left: movement("sweep only the left arm through its range", "any", [
    { left: 0, right: 0, arm: 0, armBoth: false, ms: 360 },
    { left: 0, right: 0, arm: 135, armBoth: false, ms: 360 },
    { left: 0, right: 0, arm: 270, armBoth: false, ms: 480 },
    { left: 0, right: 0, arm: 135, armBoth: false, ms: 360 }
  ]),
  sweep_right: movement("sweep only the right arm through its range", "any", [
    { left: 0, right: 0, armRight: 0, ms: 360 },
    { left: 0, right: 0, armRight: 135, ms: 360 },
    { left: 0, right: 0, armRight: 270, ms: 480 },
    { left: 0, right: 0, armRight: 135, ms: 360 }
  ]),
  alternate_raise: movement("raise one arm, then the other", "any", [
    { left: 0, right: 0, arm: 270, armRight: 135, ms: 420 },
    { left: 0, right: 0, arm: 135, armRight: 270, ms: 420 },
    { left: 0, right: 0, arm: 135, armRight: 135, ms: 360 }
  ]),
  different_pose: movement("hold both arms at different angles", "any", [
    { left: 0, right: 0, arm: 90, armRight: 210, ms: 560 }
  ]),
  celebrate: movement("raise both arms in celebration", "any", [
    { left: 0, right: 0, arm: 270, armRight: 270, ms: 500 },
    { left: 0, right: 0, arm: 135, armRight: 135, ms: 280 },
    { left: 0, right: 0, arm: 270, armRight: 270, ms: 500 }
  ]),
  sway: movement("small alternating wheel sway", "floor", [
    { left: .20, right: -.20, arm: 115, armRight: 155, ms: 360 },
    { left: -.20, right: .20, arm: 155, armRight: 115, ms: 360 },
    { left: 0, right: 0, arm: 135, armRight: 135, ms: 260 }
  ], true),
  dance: movement("short, gentle two-turn dance", "floor", [
    { left: .30, right: -.30, arm: 270, armRight: 135, ms: 360 },
    { left: -.30, right: .30, arm: 135, armRight: 270, ms: 360 },
    { left: .30, right: -.30, arm: 270, armRight: 135, ms: 360 },
    { left: 0, right: 0, arm: 135, armRight: 135, ms: 280 }
  ], true),

  // Kept for the official Growbot wheel-kit vocabulary. XEMO full-body mode
  // translates these to bounded arcs before execution.
  left_wheel_once: movement("short left-wheel pulse", "floor", [
    { left: .38, right: 0, arm: 135, armBoth: true, ms: 420 },
    { left: 0, right: 0, ms: 220 }
  ], true),
  right_wheel_once: movement("short right-wheel pulse", "floor", [
    { left: 0, right: .38, arm: 135, armBoth: true, ms: 420 },
    { left: 0, right: 0, ms: 220 }
  ], true)
};

export const MOVEMENT_IDS = Object.freeze(Object.keys(MOVEMENTS));
const CORE_IDS = new Set(MOVEMENT_IDS);

// Compatibility names are protocol aliases only; they are never offered as
// separate skills to the model and never create duplicate movement records.
const LEGACY_IDS = Object.freeze({
  forward: "forward_short",
  backward: "backward_short",
  wave: "wave_right",
  double_wave: "wave_both",
  hello_big: "wave_right",
  arm_flap: "wave_both",
  wiggle: "sway",
  wiggle_arms: "alternate_raise",
  arm_sweep_left: "sweep_left",
  arm_sweep_right: "sweep_right",
  raise_both: "arms_up",
  lower_both: "arms_down",
  arms_close: "arms_back",
  arms_cross: "arms_open",
  point_left: "signal_left",
  point_right: "signal_right",
  greeting_sequence: "wave_right",
  celebration_sequence: "celebrate",
  victory: "celebrate",
  happy_bounce: "celebrate",
  tiny_bow: "arms_down",
  curious_peek: "cautious_scan",
  look_around: "cautious_scan",
  scan: "cautious_scan",
  scan_left: "scan_left",
  scan_right: "scan_right",
  arc_left_long: "arc_left",
  arc_right_long: "arc_right",
  retreat_gently: "backward_short",
  inch_forward: "forward_short",
  inch_backward: "backward_short",
  quick_turn_left: "pivot_left",
  quick_turn_right: "pivot_right",
  left_wheel_twice: "left_wheel_once",
  right_wheel_twice: "right_wheel_once",
  alternating_raise: "alternate_raise",
  different_angles: "different_pose",
  single_arm_sweep_left: "sweep_left",
  single_arm_sweep_right: "sweep_right",
  signal_left: "signal_left",
  signal_right: "signal_right"
});

const normalizeId = value => String(value || "").toLowerCase().trim().replace(/[\s.-]+/g, "_").replace(/[^a-z0-9_]/g, "").replace(/^_+|_+$/g, "").slice(0, 48);

export function resolveMovementId(value) {
  const key = normalizeId(value);
  if (!key) return "";
  const id = LEGACY_IDS[key] || key;
  if (CORE_IDS.has(id)) return id;
  const stored = MOVEMENTS[id];
  return stored?.kind === "composition" && Array.isArray(stored.recipe) ? id : "";
}

export function movementIds(bodyProfile = "xemo-full") {
  return Object.keys(MOVEMENTS).filter(id => {
    const item = MOVEMENTS[id];
    return item && (CORE_IDS.has(id) || item.kind === "composition" && item.persisted === true && Array.isArray(item.recipe)) &&
      !(bodyProfile === "xemo-full" && ["left_wheel_once", "right_wheel_once"].includes(id));
  });
}

export function movementPrimitiveIds(bodyProfile = "xemo-full") {
  return MOVEMENT_IDS.filter(id => id !== "stop" && !(bodyProfile === "xemo-full" && ["left_wheel_once", "right_wheel_once"].includes(id)));
}

export function movementCatalog(bodyProfile = "xemo-full") {
  return movementIds(bodyProfile)
    .filter(id => id !== "stop")
    .map(id => `${id} = ${MOVEMENTS[id].label}`)
    .join("; ");
}

const clamp = (value, min, max, fallback) => {
  const n = Number(value);
  return Number.isFinite(n) ? Math.max(min, Math.min(max, n)) : fallback;
};

const copyStep = step => {
  const out = {
    left: clamp(step?.left, -1, 1, 0),
    right: clamp(step?.right, -1, 1, 0),
    ms: clamp(step?.ms, 120, 1600, 360)
  };
  if (step?.arm != null) out.arm = clamp(step.arm, 0, 270, 135);
  if (step?.armRight != null) out.armRight = clamp(step.armRight, 0, 270, 135);
  if (step?.armBoth === true) out.armBoth = true;
  return out;
};

export function normalizeMovementSequence(parts, maxParts = 4) {
  if (!Array.isArray(parts) || parts.length < 2 || parts.length > maxParts) return [];
  const ids = parts.map(resolveMovementId);
  if (ids.some(id => !id || id === "stop" || !CORE_IDS.has(id)) || new Set(ids).size < 2) return [];
  const counts = new Map();
  for (let i = 0; i < ids.length; i++) {
    const id = ids[i];
    if (id === ids[i - 1]) return [];
    const count = (counts.get(id) || 0) + 1;
    if (count > 2) return [];
    counts.set(id, count);
  }
  return ids;
}

export function movementSequenceId(parts, prefix = "combo") {
  const ids = normalizeMovementSequence(parts);
  if (!ids.length) return "";
  let hash = 2166136261;
  for (const ch of ids.join("|").toLowerCase()) {
    hash ^= ch.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  return `${normalizeId(prefix) || "combo"}_${(hash >>> 0).toString(36)}`;
}

export function composeMovement(name, parts, options = {}) {
  const key = normalizeId(name), ids = normalizeMovementSequence(parts, 4);
  if (!key || key === "stop" || !ids.length) throw Error("invalid movement composition");
  const steps = [], labels = [];
  for (const id of ids) {
    const item = MOVEMENTS[id];
    if (!item || !Array.isArray(item.steps) || !item.steps.length) throw Error(`invalid movement ingredient: ${id}`);
    labels.push(item.label);
    steps.push(...item.steps.map(copyStep));
    if (steps.length > 16) throw Error("movement composition is too long");
  }
  if (!steps.length) throw Error("empty movement composition");
  const navigation = ids.some(id => MOVEMENTS[id].navigation);
  const surface = ids.some(id => MOVEMENTS[id].surface === "floor") ? "floor" : "any";
  const last = steps[steps.length - 1];
  if (Math.abs(last.left) > .01 || Math.abs(last.right) > .01) steps.push({ left: 0, right: 0, ms: 220 });
  const total = steps.reduce((sum, step) => sum + step.ms, 0);
  if (total > 7000) throw Error("movement composition exceeds the time limit");
  const composed = {
    label: String(options.label || labels.join(" then ")).replace(/[\r\n]+/g, " ").slice(0, 100),
    surface,
    navigation,
    steps,
    kind: "composition",
    recipe: ids.slice(),
    learningCandidate: options.learningCandidate === true,
    persisted: options.persisted === true,
    createdAt: Date.now()
  };
  MOVEMENTS[key] = composed;
  const transient = Object.entries(MOVEMENTS)
    .filter(([id, item]) => item?.kind === "composition" && !item.persisted)
    .sort((a, b) => (+a[1].createdAt || 0) - (+b[1].createdAt || 0));
  while (transient.length > 12) {
    const [oldest] = transient.shift();
    if (oldest !== key) delete MOVEMENTS[oldest];
  }
  return composed;
}
