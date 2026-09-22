// Browser-side adapter for the current GrowBot wheel-kit contract.
// The official wheels build does not use XEMO's private `wheels` lane: walk
// traffic is a latest-wins `pose` stream at roughly 30 Hz, with port 1 and 3
// represented by a comma-separated pair of 0..180 degree values.

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, Number(v) || 0));

function angle270ToKitAngle(degrees) {
    // XEMO's physical arms are 0..270°, while the official wheel kit's
    // servo-shaped input is 0..180°. Preserve the neutral midpoint.
    return clamp((clamp(degrees, 0, 270) / 270) * 180, 0, 180);
}

// This is the direction table from the current wheel-kit driver. A logical
// XEMO wheel speed of +1 means "forward"; the driver expects left port 1
// inverted and right port 3 non-inverted.
const KIT_SIGN = { left: -1, right: 1 };

function speedToKitAngle(speed, side) {
    const value = clamp(speed, -1, 1);
    return Math.round(clamp(90 + (90 * value) / KIT_SIGN[side], 0, 180));
}

function wheelSpeedsToPose(left, right, message = {}) {
    return {
        t: "pose",
        lr: `${speedToKitAngle(left, "left")},${speedToKitAngle(right, "right")}`,
        rid: message.rid,
        seq: message.seq,
        ts: message.ts
    };
}

export function translateGrowbotWheelkitCommand(message) {
    if (!message || typeof message !== "object") return message;
    if (message.t === "arms") {
        return {
            t: "pose",
            lr: `${angle270ToKitAngle(message.left == null ? 135 : message.left)},${angle270ToKitAngle(message.right == null ? 135 : message.right)}`,
            rid: message.rid
        };
    }
    if (message.t === "arms_release") return { t: "pose", lr: "90,90", rid: message.rid };
    if (message.t === "wheels") return wheelSpeedsToPose(message.left, message.right, message);
    if (message.t === "drive") {
        const linear = clamp(message.linear, -1, 1);
        const yaw = clamp(message.yaw, -1, 1);
        const scale = Math.max(1, Math.abs(linear - yaw), Math.abs(linear + yaw));
        return wheelSpeedsToPose((linear - yaw) / scale, (linear + yaw) / scale, message);
    }
    return message;
}
