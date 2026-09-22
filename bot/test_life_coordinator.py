#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

try:
    from life_coordinator import LifeCoordinator, _activity_repeats_without_new_reason, _background_timing_gate, _decision_frame, _parse_initiative
    from life_state import LifeStateStore
except ImportError:
    from bot.life_coordinator import LifeCoordinator, _activity_repeats_without_new_reason, _background_timing_gate, _decision_frame, _parse_initiative
    from bot.life_state import LifeStateStore


class LifeCoordinatorTests(unittest.TestCase):
    def test_background_timing_gate_defers_after_recent_human_turn(self):
        import time
        reason_delay = _background_timing_gate({"socialState": {"lastHumanAt": time.time() - 2}})
        self.assertIsNotNone(reason_delay)
        self.assertIn("recently present", reason_delay[0])
        self.assertGreaterEqual(reason_delay[1], 12)

    def test_background_timing_gate_defers_unanswered_question(self):
        reason_delay = _background_timing_gate({"socialState": {"lastHumanAt": 200, "lastXemoAt": 100, "intent": "asking"}}, 220)
        self.assertIsNotNone(reason_delay)
        self.assertIn("owns", reason_delay[0])

    def test_background_timing_gate_allows_a_real_quiet_stretch(self):
        reason_delay = _background_timing_gate({"socialState": {"lastHumanAt": 100, "lastXemoAt": 120}}, 200)
        self.assertIsNone(reason_delay)

    def test_specific_grounding_becomes_private_reflection(self):
        item = _parse_initiative('{"reflection":"","say":"","grounding":"the quiet corner still matters because we explored it together"}')
        self.assertEqual(item["reflection"], "the quiet corner still matters because we explored it together")

    def test_generic_grounding_does_not_create_fake_inner_life(self):
        item = _parse_initiative('{"reflection":"","say":"","grounding":"no current priority or evidence to shift tone or action"}')
        self.assertIsNone(item)

    def test_background_parser_rejects_unavailable_present_sensations(self):
        item = _parse_initiative('{"reflection":"I can feel the warmth of sunlight on my skin","say":"I can hear the room breathing","activity":"rest","grounding":"sunlight on my skin"}')
        self.assertEqual(item["say"], "")
        self.assertEqual(item["reflection"], "")
        self.assertEqual(item["grounding"], "")
        self.assertEqual(item["activity"], "rest")

    def test_private_activity_is_a_bounded_nontechnical_outcome(self):
        item = _parse_initiative('{"reflection":"","activity":"revisit-memory","say":"","grounding":"the unfinished question still has a concrete thread"}')
        self.assertEqual(item["activity"], "revisit-memory")

    def test_unknown_private_activity_is_rejected(self):
        item = _parse_initiative('{"reflection":"","activity":"dance","say":"","grounding":"no current priority or evidence to shift tone or action"}')
        self.assertIsNone(item)

    def test_repeated_private_activity_requires_a_new_reason(self):
        import time
        now = time.time()
        recent = [
            {"activity": "review-goal", "grounding": "the cup question remains open", "at": now - 2},
            {"activity": "review-goal", "grounding": "the cup question remains open", "at": now - 1},
        ]
        self.assertTrue(_activity_repeats_without_new_reason("review-goal", "the cup question remains open", recent, now))
        self.assertFalse(_activity_repeats_without_new_reason("review-goal", "a new body result changes the next method", recent, now))

    def test_decision_frame_penalizes_recently_repeated_drive(self):
        import time
        frame = _decision_frame({
            "innerState": {"drives": {"curiosity": .99}, "attention": "the same question"},
            "autonomyHistory": [
                {"drive": "curiosity", "t": time.time() - 60},
                {"drive": "curiosity", "t": time.time() - 120},
            ],
        })
        self.assertEqual(frame["choice"], "hold a curious question")
        self.assertGreater(frame["repetition_penalty"], 0)

    def test_decision_frame_surfaces_stale_goal_as_freshness_not_urgency(self):
        import time
        frame = _decision_frame({
            "activeGoal": {"target": "understand the cup", "status": "active", "updatedAt": time.time() - 86400 * 30},
            "taskPlan": {"status": "open", "updatedAt": time.time() - 86400 * 30},
        })
        self.assertEqual(frame["choice"], "continue embodied intention")
        self.assertGreater(frame["freshness"], 0)
        self.assertLessEqual(frame["confidence"], .9)

    def test_decision_frame_surfaces_durable_wants_as_independent_priorities(self):
        frame = _decision_frame({
            "memoryContext": {"wants": ["learn whether the soft tapping has a pattern"]},
            "innerState": {"drives": {"curiosity": .8}},
        })
        self.assertEqual(frame["choice"], "return to a personal want")
        self.assertIn("soft tapping", frame["evidence"])

    def test_disabled_coordinator_only_heartbeats(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            calls = []
            coordinator = LifeCoordinator(store, lambda *_: calls.append(1), "model", enabled=False)
            coordinator.tick()
            self.assertFalse(calls)
            self.assertFalse(store.snapshot()["coordinator"]["enabled"])

    def test_coordinator_queues_specific_nontechnical_initiative(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            coordinator = LifeCoordinator(
                store,
                lambda *_: '{"say":"I wonder what the quietest thing in this room is?","emotion":"wonder","kind":"reflection","grounding":"a question I kept turning over"}',
                "model",
                enabled=True,
            )
            coordinator.tick()
            item = store.snapshot()["pendingInitiative"]
            self.assertEqual(item["status"], "pending")
            self.assertIn("quietest", item["text"])
            self.assertEqual(item["kind"], "reflection")
            self.assertTrue(item["grounding"])

    def test_coordinator_builds_a_grounded_decision_frame(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({
                "activeGoal": {"id": "goal-1", "target": "understand the cup", "status": "active"},
                "taskPlan": {"status": "revising", "lastResult": "the first view gave no verified change"},
            })
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I will change the view.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("decision_frame", prompts[0])
            decision = store.snapshot()["coordinator"]["lastDecision"]
            self.assertEqual(decision["choice"], "continue embodied intention")
            self.assertEqual(decision["outcome"], "reflected")

    def test_coordinator_selects_an_unfinished_project_by_salience(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"lifeProjects": [
                {"title": "finished corner", "status": "open", "progress": .8},
                {"title": "paused bottle question", "status": "paused", "progress": .1},
            ]})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I will return to the bottle question.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("paused bottle question", prompts[0])

    def test_coordinator_rejects_generic_or_technical_lines(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            coordinator = LifeCoordinator(store, lambda *_: '{"say":"I am here with you"}', "model", enabled=True)
            coordinator.tick()
            self.assertIsNone(store.snapshot()["pendingInitiative"])

    def test_coordinator_can_keep_a_private_reflection_without_speaking(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            coordinator = LifeCoordinator(
                store,
                lambda *_: '{"reflection":"I should revisit the unfinished question later.","say":"","kind":"goal-review","grounding":"the goal remains open"}',
                "model",
                enabled=True,
            )
            coordinator.tick()
            self.assertIsNone(store.snapshot()["pendingInitiative"])
            self.assertIn("unfinished question", store.snapshot()["reflections"][-1]["text"])

    def test_coordinator_records_private_activity_without_fabricating_body_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            coordinator = LifeCoordinator(
                store,
                lambda *_: '{"reflection":"","activity":"consolidate","say":"","kind":"reflection","grounding":"two remembered episodes support keeping this thread"}',
                "model",
                enabled=True,
            )
            coordinator.tick()
            activities = store.snapshot()["privateActivities"]
            self.assertEqual(activities[-1]["activity"], "consolidate")
            self.assertIn("remembered episodes", activities[-1]["grounding"])
            self.assertEqual(store.snapshot()["coordinator"]["lastDecision"]["outcome"], "reflected")

    def test_coordinator_varies_repeated_private_activity_into_rest(self):
        import time
        now = time.time()
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"privateActivities": [
                {"activity": "review-goal", "grounding": "the same open question", "at": now - 2},
                {"activity": "review-goal", "grounding": "the same open question", "at": now - 1},
            ]})
            coordinator = LifeCoordinator(
                store,
                lambda *_: '{"reflection":"","activity":"review-goal","say":"","grounding":"the same open question"}',
                "model",
                enabled=True,
            )
            coordinator.tick()
            self.assertEqual(store.snapshot()["privateActivities"][-1]["activity"], "rest")

    def test_coordinator_receives_durable_memory_context(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"memoryContext": {"preferences": ["likes quiet mornings"], "episodes": ["We discovered the quiet corner together."]}})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I remembered a preference.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("likes quiet mornings", prompts[0])
            self.assertIn("quiet corner together", prompts[0])

    def test_coordinator_receives_autobiographical_life_chapters(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"lifeChapters": ["I learned to vary the approach after the first attempt failed"]})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I remember how my approach changed.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("vary the approach after the first attempt", prompts[0])

    def test_coordinator_receives_bounded_inner_state(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"innerState": {"drives": {"curiosity": .91}, "attention": {"summary": "a quiet unfinished question"}}})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I noticed the quiet question.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("quiet unfinished question", prompts[0])
            self.assertIn("0.91", prompts[0])

    def test_coordinator_receives_task_plan_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"taskPlan": {"status": "revising", "target": "the cup", "lastResult": "no verified change", "evidence": ["the first view was blocked"]}})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I will keep the observation open.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("no verified change", prompts[0])
            self.assertIn("first view was blocked", prompts[0])

    def test_coordinator_receives_body_prediction_history(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"bodyPredictionLedger": [{
                "action": "turn left", "contextKey": "near table", "prediction": "clearance opens",
                "observed": "clearance narrowed", "verdict": "disconfirmed", "predictionMatched": False,
                "consistency": .2, "evidenceConfidence": .8
            }]})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I should change the approach.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("clearance narrowed", prompts[0])
            self.assertIn("body_prediction_history", prompts[0])

    def test_coordinator_receives_sanitized_world_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"memoryContext": {"worldObjects": [{"label": "walnut bottle", "confidence": .8, "sightings": 4}], "familiarScene": {"objects": ["table"], "visits": 3}}})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"The bottle remains a possible thread.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("walnut bottle", prompts[0])
            self.assertIn("\"visits\": 3", prompts[0])

    def test_coordinator_receives_current_autonomy_priority(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"autonomyState": {"priority": "curiosity", "need": "a new observation"}})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I am still curious about the remembered world.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("curiosity", prompts[0])
            self.assertIn("new observation", prompts[0])

    def test_coordinator_receives_recent_independent_choices(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"autonomyHistory": [{"choice": "curiosity: inspect the quiet corner", "drive": "curiosity", "outcome": "no verified change"}]})
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I will choose a different thread.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("inspect the quiet corner", prompts[0])

    def test_coordinator_receives_confirmed_memory_records_and_revisions(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({
                "memoryRecords": [{
                    "id": "memory-cup",
                    "text": "The cup is usually beside the walnut bottle.",
                    "type": "semantic",
                    "status": "confirmed",
                    "confidence": .9,
                    "observations": 3,
                }],
                "memoryHistory": [{
                    "id": "memory-old",
                    "text": "The cup was once near the window.",
                    "status": "outdated",
                    "supersededBy": "memory-cup",
                    "replacementReason": "later repeated observations changed the location",
                }],
            })
            prompts = []
            coordinator = LifeCoordinator(store, lambda _, prompt: prompts.append(prompt) or '{"reflection":"I remember the changed arrangement.","say":""}', "model", enabled=True)
            coordinator.tick()
            self.assertIn("The cup is usually beside the walnut bottle.", prompts[0])
            self.assertIn("later repeated observations changed the location", prompts[0])

    def test_coordinator_records_goal_review_without_claiming_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.update({"activeGoal": {"id": "goal-8", "target": "understand the cup", "status": "active"}})
            coordinator = LifeCoordinator(store, lambda *_: '{"reflection":"I should change the approach.","say":"","goalReview":{"status":"revise","reason":"the last attempt gave no verified change","nextFocus":"inspect the cup from another angle"}}', "model", enabled=True)
            coordinator.tick()
            review = store.snapshot()["goalReview"]
            self.assertEqual(review["goalId"], "goal-8")
            self.assertEqual(review["status"], "revise")

    def test_coordinator_can_queue_one_grounded_goal_proposal(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            coordinator = LifeCoordinator(store, lambda *_: '{"reflection":"I want to revisit a real unfinished question.","say":"","goalProposal":{"kind":"adaptive","target":"revisit the unfinished question about the cup","reason":"the question remains in my durable memory"}}', "model", enabled=True)
            coordinator.tick()
            proposal = store.snapshot()["pendingGoal"]
            self.assertEqual(proposal["status"], "pending")
            self.assertIn("unfinished question", proposal["target"])
            self.assertTrue(proposal["decisionId"])

    def test_coordinator_only_records_evidence_backed_memory_candidates(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            coordinator = LifeCoordinator(store, lambda *_: '{"reflection":"I noticed a repeatable body lesson.","say":"","memoryUpdate":{"kind":"procedural","text":"turning left works better near the table","evidence":["verified change on attempt one","verified change on attempt two"]}}', "model", enabled=True)
            coordinator.tick()
            candidate = store.snapshot()["memoryCandidates"][0]
            self.assertEqual(candidate["kind"], "procedural")
            self.assertEqual(candidate["status"], "pending")

    def test_coordinator_rejects_unsupported_memory_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            coordinator = LifeCoordinator(store, lambda *_: '{"memoryUpdate":{"kind":"semantic","text":"I know everything now","evidence":["one vague thought"]}}', "model", enabled=True)
            coordinator.tick()
            self.assertFalse(store.snapshot()["memoryCandidates"])


if __name__ == "__main__":
    unittest.main()
