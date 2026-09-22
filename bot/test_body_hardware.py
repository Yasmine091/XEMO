import importlib
import sys
import types
import unittest


class FakeTime(types.ModuleType):
    def __init__(self):
        super().__init__("time")
        self.now = 0

    def ticks_ms(self):
        return self.now

    def ticks_diff(self, a, b):
        return a - b

    def sleep_ms(self, value):
        self.now += value

    def sleep_us(self, value):
        self.now += value / 1000


class FakePin:
    OUT = 1
    IN = 0

    def __init__(self, pin, mode=None, value=0):
        self.pin = pin
        self.mode = mode
        self.state = value

    def value(self, value=None):
        if value is not None:
            self.state = value
        return self.state


class FakePwm:
    def __init__(self, pin, freq, duty_u16=0):
        self.pin = pin
        self.freq = freq
        self.duty = duty_u16

    def duty_u16(self, value):
        self.duty = value


class FakeArms:
    def __init__(self):
        self.writes = []
        self.released = []

    def servoWrite(self, port, degrees):
        self.writes.append((port, degrees))

    def release(self, port):
        self.released.append(port)


class BodyHardwareContractTest(unittest.TestCase):
    def setUp(self):
        self.old_modules = {name: sys.modules.get(name) for name in ("time", "machine", "pico_robotics", "PicoRobotics", "lidar", "growbot_wheelkit", "bot.growbot_wheelkit")}
        self.clock = FakeTime()
        self.echo_pulse = 580

        machine = types.ModuleType("machine")
        machine.Pin = FakePin
        machine.PWM = FakePwm
        machine.time_pulse_us = lambda pin, level, timeout: self.echo_pulse
        robotics = types.ModuleType("pico_robotics")
        arms = FakeArms()
        robotics.KitronikPicoRobotics = lambda: arms
        lidar = types.ModuleType("lidar")
        lidar.open_scanner = lambda: None
        sys.modules.update({
            "time": self.clock,
            "machine": machine,
            "pico_robotics": robotics,
            "PicoRobotics": robotics,
            "lidar": lidar,
        })
        sys.modules.pop("bot.body", None)
        sys.modules.pop("growbot_wheelkit", None)
        sys.modules.pop("bot.growbot_wheelkit", None)
        self.body_module = importlib.import_module("bot.body")
        self.body = self.body_module.XemoBody()
        self.arms = arms

    def tearDown(self):
        sys.modules.pop("bot.body", None)
        for name, module in self.old_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module

    def test_wheels_are_clamped_and_ramped_to_motor_output(self):
        self.body.wheels(2, -2)
        self.assertEqual(self.body.motion_snapshot()["target"], [1.0, -1.0])
        self.clock.now += 100
        self.body.motion_tick()
        snapshot = self.body.motion_snapshot()
        self.assertGreater(snapshot["output"][0], 0)
        self.assertLess(snapshot["output"][1], 0)

    def test_stop_all_clears_wheels_and_releases_both_arms(self):
        self.body.wheels(1, 1)
        self.body.write_arms(-10, 320)
        self.body.stop_all()
        self.assertEqual(self.body.motion_snapshot(), {"target": [0.0, 0.0], "output": [0.0, 0.0]})
        self.assertEqual(self.arms.writes[-2:], [(1, 0), (3, 270)])
        self.assertEqual(self.arms.released, [1, 3])

    def test_range_uses_hcsr04_conversion_and_handles_timeout(self):
        self.assertEqual(self.body.distance_cm(), 10.0)
        self.echo_pulse = -1
        self.assertIsNone(self.body.distance_cm())

    def test_growbot_wheelkit_angles_center_and_cap_each_side(self):
        self.body.wheelkit_write(1, 90)
        self.body.wheelkit_write(3, 90)
        self.assertEqual(self.body.motion_snapshot()["target"], [0.0, 0.0])
        self.body.wheelkit_write(1, 0)
        self.body.wheelkit_write(3, 180)
        self.assertEqual(self.body.motion_snapshot()["target"], [0.45, 0.45])
        self.body.wheelkit_release(1)
        self.assertEqual(self.body.motion_snapshot()["target"], [0.0, 0.45])

    def test_growbot_wheelkit_applies_starting_duty(self):
        self.body.wheelkit_write(1, 180)
        self.clock.now += 100
        self.body.motion_tick()
        self.assertGreater(self.body._left_pwm.duty, 0)

    def test_growbot_wheelkit_lifts_small_pose_above_stiction_floor(self):
        self.body.wheelkit_write(1, 95)
        self.clock.now += 100
        self.body.motion_tick()
        self.assertGreaterEqual(self.body._left_pwm.duty, int(.20 * 65535))
        self.assertLessEqual(self.body._left_pwm.duty, int(.45 * 65535))

    def test_legacy_growbot_gait_rolls_forward_on_both_wheels(self):
        self.body.wheelkit_gait_pose(65, 115)
        first = self.body.motion_snapshot()["target"]
        self.body.wheelkit_gait_pose(115, 65)
        second = self.body.motion_snapshot()["target"]
        self.assertGreater(first[0], 0)
        self.assertGreater(first[1], 0)
        self.assertGreater(second[0], 0)
        self.assertGreater(second[1], 0)

    def test_growbot_wheelkit_sweeps_sparse_command_until_deadman(self):
        self.body.wheelkit_write(1, 180)
        first = self.body.motion_snapshot()["output"][0]
        self.clock.now += 100
        self.body.motion_tick()
        self.assertGreater(abs(self.body.motion_snapshot()["output"][0]), abs(first))


if __name__ == "__main__":
    unittest.main()
