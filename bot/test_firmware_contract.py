from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent.parent


class FirmwareContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.firmware = (ROOT / "bot" / "firmware_main.py").read_text()
        cls.protocol = (ROOT / "gui" / "xemo" / "js" / "protocol.js").read_text()

    def test_firmware_keeps_body_commands_and_safety_fences(self):
        for command in ("drive", "wheels", "arms", "arms_release", "range", "lidar", "pose", "act", "routine", "stop"):
            self.assertIn('t == "' + command + '"', self.firmware)
        self.assertIn("DEADMAN_MS = 500", self.firmware)
        self.assertIn('"t": "hello"', self.firmware)
        self.assertIn('"t": "ack"', self.firmware)
        self.assertIn('"t": "body"', self.firmware)
        self.assertIn("body.stop_all()", self.firmware)

    def test_browser_protocol_keeps_bounded_movement_and_known_gestures(self):
        self.assertIn("Math.max(-.7, Math.min(.7", self.protocol)
        self.assertIn("Math.max(250, Math.min(2500", self.protocol)
        for gesture in ("wave", "look_around", "wiggle", "retreat_gently"):
            self.assertIn('"' + gesture + '"', self.protocol)


if __name__ == "__main__":
    unittest.main()
