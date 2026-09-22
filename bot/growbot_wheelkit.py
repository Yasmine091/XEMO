"""Official GrowBot wheel-kit motor backend for XEMO's L298N wiring."""
import machine
import time
from machine import Pin, PWM
try:
    import wheels_config as cfg
except ImportError:
    class cfg:
        MOTOR_PINS = {1: (26, 19, 18), 3: (27, 17, 16)}
        INVERT = {1: False, 3: False}
        WIRE_FORWARD_SIGN = {1: -1, 3: 1}
        PWM_FREQ = 1500
        MAX_DUTY = 0.45
        MIN_DUTY = 0.20
        DEADBAND_DEG = 4
        SLEW_PER_S = 3.0
        DEADMAN_MS = 500

MOTOR_PINS = cfg.MOTOR_PINS
WIRE_FORWARD_SIGN = cfg.WIRE_FORWARD_SIGN
PWM_FREQ = cfg.PWM_FREQ
MAX_DUTY = cfg.MAX_DUTY
MIN_DUTY = cfg.MIN_DUTY
DEADBAND_DEG = cfg.DEADBAND_DEG
SLEW_PER_S = cfg.SLEW_PER_S
DEADMAN_MS = cfg.DEADMAN_MS
FULL = 65535


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


class Motor:
    def __init__(self, pins):
        en, a, b = pins
        self.enable = Pin(en, Pin.OUT, value=0)
        self.a = Pin(a, Pin.OUT, value=0)
        self.b = Pin(b, Pin.OUT, value=0)
        self.pwm = PWM(self.enable, freq=PWM_FREQ, duty_u16=0)
        self.cur = 0.0
        self.target = 0.0
        self.moving = False
        self.last_cmd = time.ticks_ms()
        self.last_step = self.last_cmd

    def stop(self):
        self.pwm.duty_u16(0)
        self.a.value(0)
        self.b.value(0)
        self.cur = 0.0
        self.target = 0.0
        self.moving = False
        self.last_step = time.ticks_ms()

    def drive(self, target):
        self.target = clamp(target, -1.0, 1.0)
        self.last_cmd = time.ticks_ms()
        self._step()

    def _step(self):
        now = time.ticks_ms()
        dt = clamp(time.ticks_diff(now, self.last_step) / 1000.0, 0.02, 0.05)
        self.last_step = now
        target = self.target
        deadband = DEADBAND_DEG / 90.0
        if abs(target) < deadband:
            self.stop()
            return
        before = self.cur
        step = SLEW_PER_S * dt
        self.cur += clamp(target - self.cur, -step, step)
        if before * self.cur < 0:
            self.cur = 0.0
        if abs(self.cur) < 0.000001:
            self.stop()
            return
        magnitude = abs(self.cur)
        duty = min(MAX_DUTY, (MIN_DUTY + (MAX_DUTY - MIN_DUTY) * magnitude) *
                   min(1.0, magnitude / deadband))
        self.pwm.duty_u16(0)
        forward = self.cur > 0
        self.a.value(1 if forward else 0)
        self.b.value(0 if forward else 1)
        self.pwm.duty_u16(int(FULL * duty))
        self.moving = True


class GrowbotWheelkit:
    def __init__(self):
        self.motors = {port: Motor(pins) for port, pins in MOTOR_PINS.items()}

    def servoWrite(self, port, degrees):
        motor = self.motors.get(int(port))
        if motor is None:
            return
        try:
            angle = float(degrees)
            if angle != angle or abs(angle) == float("inf"):
                raise ValueError
            speed = (clamp(angle, 0, 180) - 90.0) / 90.0
            motor.drive(speed * WIRE_FORWARD_SIGN[int(port)])
        except (ValueError, TypeError, OverflowError):
            motor.stop()

    def set_power(self, left, right):
        self.servoWrite(1, 90 + 90 * float(left) / WIRE_FORWARD_SIGN[1])
        self.servoWrite(3, 90 + 90 * float(right) / WIRE_FORWARD_SIGN[3])

    def release(self, port=None):
        if port is None:
            for motor in self.motors.values():
                motor.stop()
        elif int(port) in self.motors:
            self.motors[int(port)].stop()

    def tick(self):
        now = time.ticks_ms()
        for motor in self.motors.values():
            if motor.moving and time.ticks_diff(now, motor.last_cmd) >= DEADMAN_MS:
                motor.stop()
            elif motor.moving:
                motor._step()

    def snapshot(self):
        return {
            "target": [round(self.motors[1].target, 3),
                       round(self.motors[3].target, 3)],
            "output": [round(self.motors[1].cur, 3),
                       round(self.motors[3].cur, 3)],
        }
