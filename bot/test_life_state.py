#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

try:
    from life_state import LifeStateStore
except ImportError:
    from bot.life_state import LifeStateStore


class LifeStateStoreTests(unittest.TestCase):
    def test_checkpoint_survives_restart_and_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            first = LifeStateStore(path)
            first.update({
                "lifeCycle": {
                    "sequence": 4,
                    "phase": "choosing",
                    "mode": "autonomous",
                    "reason": "curiosity",
                    "detail": "inspect the bottle",
                },
                "activeGoal": {
                    "id": "goal-4",
                    "kind": "inspect",
                    "target": "the bottle",
                    "status": "observing",
                    "steps": 1,
                    "maxSteps": 4,
                },
            })
            second = LifeStateStore(path)
            snapshot = second.snapshot()
            self.assertEqual(snapshot["lifeCycle"]["sequence"], 4)
            self.assertEqual(snapshot["lifeCycle"]["phase"], "choosing")
            self.assertEqual(snapshot["activeGoal"]["target"], "the bottle")

    def test_stale_checkpoint_cannot_replace_newer_life_phase(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"lifeCycle": {"sequence": 8, "phase": "acting"}})
            result = store.update({"lifeCycle": {"sequence": 2, "phase": "resting"}})
            self.assertEqual(result["lifeCycle"]["sequence"], 8)
            self.assertEqual(result["lifeCycle"]["phase"], "acting")

    def test_only_small_safe_state_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            store = LifeStateStore(path)
            store.update({
                "lifeCycle": {"sequence": 1, "phase": "resting", "detail": "x" * 1000},
                "activeGoal": {"target": "y" * 1000},
                "privateMemory": "must not be persisted by this journal",
            })
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("privateMemory", raw)
            self.assertLessEqual(len(raw["lifeCycle"]["detail"]), 220)
            self.assertLessEqual(len(raw["activeGoal"]["target"]), 180)


if __name__ == "__main__":
    unittest.main()
