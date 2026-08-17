import unittest
from tempfile import TemporaryDirectory

from bot.agent import Xemo, clean_model_command, strategy_hint


class AgentParserTests(unittest.TestCase):
    def test_discards_closed_reasoning_and_fences(self):
        value = "<think>choose a cautious turn</think>\n```\nturn(degrees=30)\n```"
        self.assertEqual(clean_model_command(value), "turn(degrees=30)")

    def test_discards_unclosed_reasoning(self):
        self.assertEqual(clean_model_command("<think>forward(seconds=2)"), "")

    def test_extracts_one_allowed_command_from_prose(self):
        self.assertEqual(clean_model_command("I will move now. forward(seconds=1)"), "forward(seconds=1)")

    def test_learning_promotes_repeated_verified_effect(self):
        bot = Xemo("test")
        for _ in range(2):
            result = {"verified": True, "inconclusive": False, "observed": "distance changed"}
            bot.learn("forward", "distance should change", result)
        self.assertEqual(bot.body_learning["forward"]["successes"], 2)
        self.assertAlmostEqual(bot.body_learning["forward"]["prediction_confidence"], .53, places=2)
        self.assertIn("forward repeatedly produced an observable change", bot.memories)

    def test_learning_keeps_missing_evidence_unresolved(self):
        bot = Xemo("test")
        result = {"verified": False, "inconclusive": True, "observed": "no sensor result"}
        bot.learn("turn", "orientation should change", result)
        self.assertEqual(result["verdict"], "unresolved")
        self.assertEqual(bot.body_learning["turn"]["unresolved"], 1)

    def test_learning_survives_agent_restart(self):
        with TemporaryDirectory() as folder:
            path = f"{folder}/state.json"
            bot = Xemo("test", path)
            bot.learn("forward", "distance should change", {"verified": True, "observed": "changed"})
            restored = Xemo("test", path)
            self.assertEqual(restored.body_learning["forward"]["attempts"], 1)

    def test_learning_curve_tracks_decline(self):
        bot = Xemo("test")
        for verified in (True, True, False, False):
            bot.learn("turn", "orientation should change", {
                "verified": verified, "inconclusive": False, "observed": "changed" if verified else "unchanged"
            })
        model = bot.body_learning["turn"]
        self.assertEqual(model["learning_trend"], "declining")
        self.assertEqual(model["learning_delta"], -1.0)

    def test_prediction_consistency_measures_agreement(self):
        bot = Xemo("test")
        bot.learn("forward", "the action should produce observable progress", {
            "verified": False, "inconclusive": False, "observed": "unchanged"
        })
        self.assertFalse(bot.predictions[-1]["prediction_matched"])
        self.assertEqual(bot.body_learning["forward"]["prediction_consistency"], 0.0)
        self.assertLess(bot.body_learning["forward"]["prediction_confidence"], .2)

    def test_repeated_callback_replaces_one_attempt(self):
        bot = Xemo("test")
        bot.learn("forward", "distance should change", {
            "verified": False, "inconclusive": False, "observed": "unchanged"
        }, "hallway", "attempt-1")
        bot.learn("forward", "distance should change", {
            "verified": True, "inconclusive": False, "observed": "changed"
        }, "hallway", "attempt-1")
        self.assertEqual(len([x for x in bot.predictions if x["attempt_id"] == "attempt-1"]), 1)
        self.assertEqual(bot.body_learning["forward"]["attempts"], 1)
        self.assertEqual(bot.body_learning["forward"]["successes"], 1)

    def test_restart_rebuilds_learning_from_canonical_predictions(self):
        with TemporaryDirectory() as folder:
            path = f"{folder}/state.json"
            bot = Xemo("test", path)
            bot.learn("forward", "distance should change", {
                "verified": True, "observed": "changed"
            }, "hallway", "attempt-1")
            bot.learn("forward", "distance should change", {
                "verified": True, "observed": "changed again"
            }, "hallway", "attempt-1")
            restored = Xemo("test", path)
            self.assertEqual(len(restored.predictions), 1)
            self.assertEqual(restored.body_learning["forward"]["attempts"], 1)
            self.assertEqual(restored.body_learning["forward"]["successes"], 1)

    def test_learning_keeps_contexts_separate(self):
        bot = Xemo("test")
        bot.learn("forward", "the action should produce observable progress", {
            "verified": False, "observed": "unchanged"
        }, "inspect doorway")
        bot.learn("forward", "the action should produce observable progress", {
            "verified": True, "observed": "changed"
        }, "follow person")
        contexts = bot.body_learning["forward"]["contexts"]
        self.assertEqual(contexts["inspect doorway"]["successes"], 0)
        self.assertEqual(contexts["follow person"]["successes"], 1)
        self.assertEqual(bot.predictions[-1]["context"], "follow person")

    def test_strategy_hint_uses_context_learning(self):
        bot = Xemo("test")
        for verified in (True, True, False, False):
            bot.learn("turn", "orientation should change", {
                "verified": verified, "observed": "changed" if verified else "unchanged"
            }, "inspect doorway")
        self.assertEqual(strategy_hint(bot.body_learning, "turn", "inspect doorway"),
                         "vary the method and revise the prediction")

    def test_memory_consolidation_keeps_context_and_survives_restart(self):
        with TemporaryDirectory() as folder:
            path = f"{folder}/state.json"
            bot = Xemo("test", path)
            for _ in range(2):
                bot.learn("turn", "orientation should change", {
                    "verified": True, "observed": "orientation changed"
                }, "inspect doorway")
            key = "turn :: inspect doorway"
            self.assertEqual(bot.memory_meta[key]["state"], "stable lesson")
            self.assertIn("inspect doorway", bot.memory_meta[key]["lesson"])
            restored = Xemo("test", path)
            self.assertEqual(restored.memory_meta[key]["state"], "stable lesson")

    def test_strategy_avoids_repeated_context_failure(self):
        bot = Xemo("test")
        for _ in range(2):
            bot.learn("turn", "orientation should change", {
                "verified": False, "observed": "orientation unchanged"
            }, "blocked hallway")
        self.assertEqual(strategy_hint(bot.body_learning, "turn", "blocked hallway"),
                         "avoid this action in this context")


if __name__ == "__main__":
    unittest.main()
