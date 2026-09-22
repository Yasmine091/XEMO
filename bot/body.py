"""XEMO body driver: original direct L298N wheels plus GrowBot pose adapter."""
from machine import Pin, PWM
try:
    import pico_robotics as PicoRobotics
except ImportError:
    import PicoRobotics
import machine
import time
try:
    from lidar import open_scanner
except Exception:
    open_scanner = lambda: None

try:
    from . import wheels_config as _wheel_cfg
except ImportError:
    try:
        import wheels_config as _wheel_cfg
    except ImportError:
        _wheel_cfg = None

_motor_pins = getattr(_wheel_cfg, "MOTOR_PINS", {}) if _wheel_cfg else {}
_left_pins = tuple(_motor_pins.get(1, (26, 19, 18)))
_right_pins = tuple(_motor_pins.get(3, (27, 17, 16)))
ENA, IN1, IN2 = _left_pins
ENB, IN3, IN4 = _right_pins
LEFT_ARM_PORT, RIGHT_ARM_PORT = 1, 3
ARM_MAX_DEGREES = 270
TRIG_PIN, ECHO_PIN = 5, 15
PWM_HZ = 1000
MAX_POWER = 1.00
REVERSE_DEADTIME_MS = 60
MOTION_ACCEL = 2.40
MOTION_DECEL = 4.20
WHEELKIT_MAX_POWER = float(getattr(_wheel_cfg, "MAX_DUTY", 0.45))
WHEELKIT_MIN_DUTY = float(getattr(_wheel_cfg, "MIN_DUTY", 0.20))
WHEELKIT_DEADBAND_DEG = float(getattr(_wheel_cfg, "DEADBAND_DEG", 4))
WHEELKIT_SLEW_PER_S = float(getattr(_wheel_cfg, "SLEW_PER_S", 3.0))
WHEELKIT_GAIT_YAW_DAMP = float(getattr(_wheel_cfg, "GAIT_YAW_DAMP", 0.20))
WHEELKIT_FORWARD_SIGN = dict(getattr(_wheel_cfg, "WIRE_FORWARD_SIGN", {1: -1, 3: 1}))
_wheelkit_invert = dict(getattr(_wheel_cfg, "INVERT", {}))
for _port, _inverted in _wheelkit_invert.items():
    if _inverted:
        WHEELKIT_FORWARD_SIGN[int(_port)] = -WHEELKIT_FORWARD_SIGN.get(int(_port), 1)

class XemoBody:
    def __init__(self):
        self._in = [Pin(p, Pin.OUT, value=0) for p in (IN1, IN2, IN3, IN4)]
        self._left_pwm = PWM(Pin(ENA), freq=PWM_HZ, duty_u16=0)
        self._right_pwm = PWM(Pin(ENB), freq=PWM_HZ, duty_u16=0)
        self._motor_sign = [0, 0]
        self._wheel_target = [0.0, 0.0]
        self._wheel_output = [0.0, 0.0]
        self._wheelkit_mode = [False, False]
        self._motion_at = time.ticks_ms()
        self.arms = PicoRobotics.KitronikPicoRobotics()
        self._trig = Pin(TRIG_PIN, Pin.OUT, value=0)
        self._echo = Pin(ECHO_PIN, Pin.IN)
        self.lidar = open_scanner()
        self.stop_wheels()

    @staticmethod
    def _clamp(value): return max(-1.0, min(1.0, float(value)))

    def _motor(self, index, pwm, a, b, value, forward_is_cw, wheelkit=False):
        value = self._clamp(value)
        deadband = (WHEELKIT_DEADBAND_DEG / 90.0) * WHEELKIT_MAX_POWER if wheelkit else 0.03
        if abs(value) < deadband:
            pwm.duty_u16(0); a.value(0); b.value(0); self._motor_sign[index] = 0; return
        sign = 1 if value > 0 else -1
        if self._motor_sign[index] and sign != self._motor_sign[index]:
            pwm.duty_u16(0); a.value(0); b.value(0); time.sleep_ms(REVERSE_DEADTIME_MS)
        cw = (value > 0) == forward_is_cw
        a.value(1 if cw else 0); b.value(0 if cw else 1)
        if wheelkit:
            # GrowBot's learned walk often asks for only a few degrees around
            # neutral.  Preserve the command's relative strength but lift any
            # nonzero command above the L298N/DC-motor stiction floor.
            raw = min(1.0, abs(value) / max(WHEELKIT_MAX_POWER, 0.001))
            ramp = min(1.0, raw / max(WHEELKIT_DEADBAND_DEG / 90.0, 0.001))
            duty = (WHEELKIT_MIN_DUTY +
                    (WHEELKIT_MAX_POWER - WHEELKIT_MIN_DUTY) * raw) * ramp
            duty = min(WHEELKIT_MAX_POWER, duty)
        else:
            duty = abs(value) * MAX_POWER
        pwm.duty_u16(int(duty * 65535)); self._motor_sign[index] = sign

    # Original XEMO wheel path used by the GUI.
    def drive(self, linear, yaw):
        left = self._clamp(linear - yaw); right = self._clamp(linear + yaw)
        scale = max(1.0, abs(left), abs(right)); self._set_wheel_targets(left / scale, right / scale)

    def wheels(self, left, right): self._set_wheel_targets(left, right)

    # GrowBot wheel-kit contract translated into the original XEMO wheel path.
    def wheelkit_write(self, port, degrees):
        try:
            port = int(port)
            angle = float(degrees)
            if angle != angle or abs(angle) == float("inf"): raise ValueError
            speed = (max(0.0, min(180.0, angle)) - 90.0) / 90.0
            speed *= WHEELKIT_FORWARD_SIGN.get(port, 1)
            if port == 1:
                self._wheel_target[0] = self._clamp(speed * WHEELKIT_MAX_POWER)
                self._wheelkit_mode[0] = True
            elif port == 3:
                self._wheel_target[1] = self._clamp(speed * WHEELKIT_MAX_POWER)
                self._wheelkit_mode[1] = True
        except (TypeError, ValueError, OverflowError): self.stop_wheels()

    def wheelkit_speed_write(self, left, right):
        """Apply logical wheel speeds (-1..1) using the wheel-kit power path."""
        try:
            self._wheel_target = [
                self._clamp(float(left) * WHEELKIT_MAX_POWER),
                self._clamp(float(right) * WHEELKIT_MAX_POWER),
            ]
            self._wheelkit_mode = [True, True]
        except (TypeError, ValueError, OverflowError):
            self.stop_wheels()

    def wheelkit_gait_pose(self, left_degrees, right_degrees):
        """Turn GrowBot's mirrored leg gait into safe forward wheel motion.

        The classic website has only a leg walk lane. Its streamed pair is an
        alternating mirrored gait, not left/right wheel throttle. A differential
        base would otherwise reverse one side every half-cycle. The magnitude of
        the mirrored component becomes forward throttle; the residual asymmetry
        is retained only as a damped turn request. Direction cannot be inferred
        from this legacy gait, so this compatibility path is forward-only.
        """
        try:
            left_phase = (max(0.0, min(180.0, float(left_degrees))) - 90.0) / 90.0
            right_phase = (max(0.0, min(180.0, float(right_degrees))) - 90.0) / 90.0
            throttle = abs((right_phase - left_phase) * 0.5)
            yaw = (left_phase + right_phase) * 0.5 * WHEELKIT_GAIT_YAW_DAMP
            self.wheelkit_speed_write(
                self._clamp(throttle - yaw),
                self._clamp(throttle + yaw),
            )
        except (TypeError, ValueError, OverflowError):
            self.stop_wheels()

    def wheelkit_release(self, port=None):
        if port is None: self.stop_wheels(); return
        port = int(port)
        if port == 1:
            self._wheel_target[0] = 0.0
            self._wheelkit_mode[0] = False
        if port == 3:
            self._wheel_target[1] = 0.0
            self._wheelkit_mode[1] = False

    def _set_wheel_targets(self, left, right):
        self._wheel_target = [self._clamp(left), self._clamp(right)]
        self._wheelkit_mode = [False, False]

    def motion_tick(self):
        now = time.ticks_ms(); dt = max(0.001, min(0.08, time.ticks_diff(now, self._motion_at) / 1000.0)); self._motion_at = now
        for i in (0, 1):
            current, target = self._wheel_output[i], self._wheel_target[i]
            changing = current and target and (current > 0) != (target > 0)
            rate = MOTION_DECEL if abs(target) < abs(current) or changing else MOTION_ACCEL
            step = rate * dt
            current = target if abs(target - current) <= step else current + (step if target > current else -step)
            stop_threshold = ((WHEELKIT_DEADBAND_DEG / 90.0) * WHEELKIT_MAX_POWER
                              if self._wheelkit_mode[i] else 0.025)
            if abs(current) < stop_threshold and abs(target) < stop_threshold: current = 0.0
            self._wheel_output[i] = current
        self._motor(0, self._left_pwm, self._in[0], self._in[1], self._wheel_output[0], False, self._wheelkit_mode[0])
        self._motor(1, self._right_pwm, self._in[2], self._in[3], self._wheel_output[1], True, self._wheelkit_mode[1])

    def motion_snapshot(self): return {"target": [round(x, 3) for x in self._wheel_target], "output": [round(x, 3) for x in self._wheel_output]}

    def stop_wheels(self):
        self._wheel_target = [0.0, 0.0]; self._wheel_output = [0.0, 0.0]; self._motion_at = time.ticks_ms()
        self._wheelkit_mode = [False, False]
        self._left_pwm.duty_u16(0); self._right_pwm.duty_u16(0)
        for pin in self._in: pin.value(0)
        self._motor_sign = [0, 0]

    def write_arms(self, left, right):
        self.arms.servoWrite(LEFT_ARM_PORT, int(max(0, min(ARM_MAX_DEGREES, left))))
        self.arms.servoWrite(RIGHT_ARM_PORT, int(max(0, min(ARM_MAX_DEGREES, right))))

    def release_arms(self): self.arms.release(LEFT_ARM_PORT); self.arms.release(RIGHT_ARM_PORT)

    def distance_cm(self):
        self._trig.value(0); time.sleep_us(2); self._trig.value(1); time.sleep_us(10); self._trig.value(0)
        pulse = machine.time_pulse_us(self._echo, 1, 30000)
        return None if pulse < 0 else round(pulse / 58.0, 1)

    def lidar_poll(self): return self.lidar.poll() if self.lidar else None
    def lidar_snapshot(self): return self.lidar.latest if self.lidar else None
    def stop_all(self): self.stop_wheels(); self.release_arms()
