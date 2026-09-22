"""GrowBot body driver for XEMO's ESP32 + L298N wiring."""
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

ENA, IN1, IN2 = 26, 19, 18
ENB, IN3, IN4 = 27, 17, 16
LEFT_ARM_PORT, RIGHT_ARM_PORT = 1, 3
ARM_MAX_DEGREES = 270
TRIG_PIN, ECHO_PIN = 5, 15

PWM_HZ = 1000
MAX_POWER = 1.00
REVERSE_DEADTIME_MS = 60
MOTION_ACCEL = 2.40
MOTION_DECEL = 4.20


class XemoBody:
    def __init__(self):
        self._in = [Pin(p, Pin.OUT, value=0) for p in (IN1, IN2, IN3, IN4)]
        self._left_pwm = PWM(Pin(ENA), freq=PWM_HZ, duty_u16=0)
        self._right_pwm = PWM(Pin(ENB), freq=PWM_HZ, duty_u16=0)
        self._motor_sign = [0, 0]
        self._wheel_target = [0.0, 0.0]
        self._wheel_output = [0.0, 0.0]
        self._motion_at = time.ticks_ms()
        self.arms = PicoRobotics.KitronikPicoRobotics()
        self._trig = Pin(TRIG_PIN, Pin.OUT, value=0)
        self._echo = Pin(ECHO_PIN, Pin.IN)
        self.lidar = open_scanner()
        self.stop_wheels()

    @staticmethod
    def _clamp(value):
        return max(-1.0, min(1.0, float(value)))

    def _motor(self, index, pwm, a, b, value, forward_is_cw):
        value = self._clamp(value)
        if abs(value) < 0.03:
            pwm.duty_u16(0)
            a.value(0)
            b.value(0)
            self._motor_sign[index] = 0
            return
        sign = 1 if value > 0 else -1
        if self._motor_sign[index] and sign != self._motor_sign[index]:
            pwm.duty_u16(0)
            a.value(0)
            b.value(0)
            time.sleep_ms(REVERSE_DEADTIME_MS)
        cw = (value > 0) == forward_is_cw
        a.value(1 if cw else 0)
        b.value(0 if cw else 1)
        pwm.duty_u16(int(abs(value) * MAX_POWER * 65535))
        self._motor_sign[index] = sign

    def drive(self, linear, yaw):
        left = self._clamp(linear - yaw)
        right = self._clamp(linear + yaw)
        scale = max(1.0, abs(left), abs(right))
        self._set_wheel_targets(left / scale, right / scale)

    def wheels(self, left, right):
        """Drive each L298N channel independently; useful for body diagnostics."""
        self._set_wheel_targets(left, right)

    def _set_wheel_targets(self, left, right):
        self._wheel_target[0] = self._clamp(left)
        self._wheel_target[1] = self._clamp(right)

    def motion_tick(self):
        """Move actual wheel power toward its target without step changes."""
        now = time.ticks_ms()
        dt = max(0.001, min(0.08, time.ticks_diff(now, self._motion_at) / 1000.0))
        self._motion_at = now
        for i in (0, 1):
            current = self._wheel_output[i]
            target = self._wheel_target[i]
            changing_direction = current and target and (current > 0) != (target > 0)
            rate = MOTION_DECEL if abs(target) < abs(current) or changing_direction else MOTION_ACCEL
            step = rate * dt
            if abs(target - current) <= step:
                current = target
            else:
                current += step if target > current else -step
            if abs(current) < 0.025 and abs(target) < 0.025:
                current = 0.0
            self._wheel_output[i] = current
        self._motor(0, self._left_pwm, self._in[0], self._in[1], self._wheel_output[0], False)
        self._motor(1, self._right_pwm, self._in[2], self._in[3], self._wheel_output[1], True)

    def motion_snapshot(self):
        """Return commanded and currently applied wheel power for diagnostics."""
        return {
            "target": [round(self._wheel_target[0], 3), round(self._wheel_target[1], 3)],
            "output": [round(self._wheel_output[0], 3), round(self._wheel_output[1], 3)],
        }

    def stop_wheels(self):
        self._wheel_target = [0.0, 0.0]
        self._wheel_output = [0.0, 0.0]
        self._motion_at = time.ticks_ms()
        self._left_pwm.duty_u16(0)
        self._right_pwm.duty_u16(0)
        for pin in self._in:
            pin.value(0)
        self._motor_sign = [0, 0]

    def write_arms(self, left, right):
        self.arms.servoWrite(LEFT_ARM_PORT, int(max(0, min(ARM_MAX_DEGREES, left))))
        self.arms.servoWrite(RIGHT_ARM_PORT, int(max(0, min(ARM_MAX_DEGREES, right))))

    def release_arms(self):
        self.arms.release(LEFT_ARM_PORT)
        self.arms.release(RIGHT_ARM_PORT)

    def distance_cm(self):
        """One HC-SR04 sample. ECHO must be reduced from 5 V to 3.3 V."""
        self._trig.value(0)
        time.sleep_us(2)
        self._trig.value(1)
        time.sleep_us(10)
        self._trig.value(0)
        pulse = machine.time_pulse_us(self._echo, 1, 30000)
        if pulse < 0:
            return None
        return round(pulse / 58.0, 1)

    def lidar_poll(self):
        return self.lidar.poll() if self.lidar else None

    def lidar_snapshot(self):
        return self.lidar.latest if self.lidar else None

    def stop_all(self):
        self.stop_wheels()
        self.release_arms()
