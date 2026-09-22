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
    def test_instances_have_distinct_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            alpha = LifeStateStore(Path(folder) / "alpha.json", instance_id="xemo-alpha")
            beta = LifeStateStore(Path(folder) / "beta.json", instance_id="xemo-beta")
            alpha.update({"activeGoal": {"target": "learn the quiet corner"}})
            beta.update({"activeGoal": {"target": "inspect the table"}})
            self.assertEqual(alpha.snapshot()["instanceId"], "xemo-alpha")
            self.assertEqual(beta.snapshot()["instanceId"], "xemo-beta")
            self.assertNotEqual(alpha.snapshot()["activeGoal"]["target"], beta.snapshot()["activeGoal"]["target"])

    def test_instance_id_is_sanitized_and_not_client_overridable(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json", instance_id="xemo one/unsafe")
            snapshot = store.update({"instanceId": "other-instance"})
            self.assertEqual(snapshot["instanceId"], "xemooneunsafe")

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

    def test_duration_aware_memory_records_survive_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryRecords": [{
                "id": "mem-1", "text": "quiet mornings feel safe", "status": "confirmed",
                "observations": 4, "durationDays": 12.5, "confidence": .82,
            }]})
            self.assertEqual(snapshot["memoryRecords"][0]["durationDays"], 12.5)
            self.assertEqual(snapshot["memoryRecords"][0]["observations"], 4)

    def test_private_activity_is_bounded_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            store = LifeStateStore(path)
            store.record_private_activity("review-goal", "an open intention still has evidence", "kept it open", "decision-1")
            reloaded = LifeStateStore(path)
            item = reloaded.snapshot()["privateActivities"][-1]
            self.assertEqual(item["activity"], "review-goal")
            self.assertEqual(item["decisionId"], "decision-1")
            self.assertEqual(reloaded.snapshot()["lifeEvents"][-1]["kind"], "private-activity")

    def test_background_initiative_is_single_claim_and_browser_updates_preserve_it(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            created = store.create_initiative("I kept one small question for you.", "curious", "social", "an unfinished shared question")
            initiative = created["pendingInitiative"]
            self.assertEqual(initiative["kind"], "social")
            self.assertTrue(created["lifeEvents"])
            store.update({"lifeCycle": {"sequence": 3, "phase": "resting"}})
            self.assertEqual(store.snapshot()["pendingInitiative"]["status"], "pending")
            claimed = store.claim_initiative(initiative["id"])
            self.assertEqual(claimed["pendingInitiative"]["status"], "claimed")
            self.assertEqual(claimed["lifeEvents"][-1]["kind"], "initiative-claimed")
            self.assertIsNone(store.claim_initiative(initiative["id"]))

    def test_autonomy_decision_keeps_alternatives_and_outcome(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            decision = store.record_decision({
                "id": "decision-1",
                "choice": "protect shared commitment",
                "need": "keep a meaningful thread alive",
                "reason": "an explicit plan remains open",
                "evidence": "finish the cup experiment",
                "prediction": "a gentle revisit preserves continuity",
                "confidence": .77,
                "alternatives": [{"label": "rest", "score": .3, "reason": "nothing urgent"}],
            }, "queued")
            self.assertEqual(decision["coordinator"]["lastDecision"]["choice"], "protect shared commitment")
            self.assertEqual(decision["coordinator"]["lastDecision"]["alternatives"][0]["label"], "rest")
            finished = store.complete_decision("decision-1", "delivered", "the browser rendered it")
            self.assertEqual(finished["coordinator"]["lastDecision"]["outcome"], "delivered")
            self.assertEqual(finished["coordinator"]["lastDecision"]["result"], "the browser rendered it")
            self.assertEqual(finished["lifeEvents"][-1]["kind"], "decision-outcome")
            self.assertEqual(finished["lifeEvents"][-1]["parent"], "decision-1")

    def test_initiative_preserves_decision_link_until_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.record_decision({"id": "decision-2", "choice": "hold a curious question", "reason": "curiosity", "confidence": .5}, "queued")
            created = store.create_initiative("I kept a question about the quiet corner.", decision_id="decision-2")
            self.assertEqual(created["pendingInitiative"]["decisionId"], "decision-2")
            self.assertEqual(created["lifeEvents"][-1]["parent"], "decision-2")
            store.claim_initiative(created["pendingInitiative"]["id"])
            finished = store.complete_initiative(created["pendingInitiative"]["id"], "delivered", "rendered")
            self.assertEqual(finished["coordinator"]["lastDecision"]["outcome"], "delivered")

    def test_goal_proposal_closes_with_browser_outcome(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.record_decision({"id": "decision-3", "choice": "revisit living project", "reason": "unfinished", "confidence": .6}, "queued")
            proposal = store.create_goal_proposal("inspect", "revisit the quiet corner", "an unfinished question remains", "decision-3")
            proposal_id = proposal["pendingGoal"]["id"]
            self.assertEqual(proposal["lifeEvents"][-1]["parent"], "decision-3")
            self.assertEqual(store.claim_goal_proposal(proposal_id)["pendingGoal"]["status"], "claimed")
            finished = store.complete_goal_proposal(proposal_id, "completed", "two verified observations")
            self.assertEqual(finished["pendingGoal"]["outcome"], "completed")
            self.assertEqual(finished["coordinator"]["lastDecision"]["outcome"], "completed")

    def test_reflections_are_bounded_and_separate_from_speech(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.record_reflection("I kept the unfinished question about the bottle.", "goal-review", "an active inquiry exists")
            snapshot = store.snapshot()
            self.assertEqual(snapshot["reflections"][-1]["kind"], "goal-review")
            self.assertIsNone(snapshot["pendingInitiative"])

    def test_memory_context_is_sanitized_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {
                "preferences": ["likes quiet mornings", "x" * 300],
                "episodes": ["We discovered the walnut rolls when I was trying to understand the table."],
                "acquaintances": [{"name": "Ada", "role": "friend", "familiarity": 3, "interactions": 2}],
                "rawTranscript": ["must not be copied"],
            }})
            self.assertIn("likes quiet mornings", snapshot["memoryContext"]["preferences"])
            self.assertIn("walnut rolls", snapshot["memoryContext"]["episodes"][0])
            self.assertEqual(snapshot["memoryContext"]["acquaintances"][0]["name"], "Ada")
        self.assertNotIn("rawTranscript", snapshot["memoryContext"])

    def test_social_episodes_preserve_shared_change_without_raw_extras(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {"familiarScene": {
                "objects": ["cup", "book"], "expectedObjects": ["cup", "book"], "predictionMatched": False, "predictionAttempts": 2, "stability": .5, "lastPredictionObserved": ["lamp"]
            }}})
            self.assertEqual(snapshot["memoryContext"]["familiarScene"]["predictionMatched"], False)
            self.assertEqual(snapshot["memoryContext"]["familiarScene"]["predictionAttempts"], 2)

            snapshot = store.update({"memoryContext": {"socialEpisodes": [{
                "kind": "correction", "actor": "person", "subject": "Ada",
                "text": "Ada corrected my guess about the walnut bottle",
                "change": "I should ask before naming ordinary objects", "eventId": 7,
                "confidence": 1.4, "secret": "discard"
            }]}})
            episode = snapshot["memoryContext"]["socialEpisodes"][0]
            self.assertEqual(episode["confidence"], 1.0)
            self.assertEqual(episode["eventId"], 7)
            self.assertNotIn("secret", episode)
    def test_inner_state_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({
                "innerState": {
                    "drives": {"curiosity": 2, "energy": -1},
                    "needs": {"connection": .7},
                    "attention": {"summary": "a grounded unfinished question"},
                }
            })
            self.assertEqual(snapshot["innerState"]["drives"]["curiosity"], 1.0)
            self.assertEqual(snapshot["innerState"]["drives"]["energy"], 0.0)
            self.assertEqual(snapshot["innerState"]["needs"]["connection"], .7)
            self.assertEqual(snapshot["innerState"]["attention"], "a grounded unfinished question")

    def test_homeostasis_metadata_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            store = LifeStateStore(path)
            snapshot = store.update({"innerState": {"homeostasis": {
                "lastActivityAt": -4,
                "lastActivityKind": "  careful inspection  ",
                "lastHomeostasisAt": 18.5,
                "revision": 999999999,
                "secret": "discard",
            }}})
            homeostasis = snapshot["innerState"]["homeostasis"]
            self.assertEqual(homeostasis["lastActivityAt"], 0.0)
            self.assertEqual(homeostasis["lastActivityKind"], "careful inspection")
            self.assertEqual(homeostasis["lastHomeostasisAt"], 18.5)
            self.assertEqual(homeostasis["revision"], 999999999)
            self.assertNotIn("secret", homeostasis)
            self.assertEqual(LifeStateStore(path).snapshot()["innerState"]["homeostasis"]["lastActivityKind"], "careful inspection")

    def test_homeostasis_advances_when_the_browser_checkpoint_is_old(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            store = LifeStateStore(path)
            old = 1000.0
            snapshot = store.update({
                "innerState": {
                    "updatedAt": old,
                    "drives": {"energy": .8, "curiosity": .4},
                    "needs": {"connection": .2},
                    "homeostasis": {"lastHomeostasisAt": old * 1000, "revision": 4},
                },
                "socialState": {"lastHumanAt": old},
            })
            self.assertGreater(snapshot["innerState"]["homeostasis"]["revision"], 4)
            self.assertGreater(snapshot["innerState"]["needs"]["connection"], .2)
            self.assertGreaterEqual(snapshot["innerState"]["drives"]["energy"], .8)

    def test_aliveness_metrics_are_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"alivenessMetrics": {
                "autonomousChoices": 4,
                "bodyVerified": 2,
                "brainRequests": 1000000000,
                "unknown": "discard",
            }})
            self.assertEqual(snapshot["alivenessMetrics"]["autonomousChoices"], 4)
            self.assertEqual(snapshot["alivenessMetrics"]["bodyVerified"], 2)
            self.assertEqual(snapshot["alivenessMetrics"]["brainRequests"], 1000000)
            self.assertNotIn("unknown", snapshot["alivenessMetrics"])

    def test_causal_timeline_is_bounded_and_sanitized(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"causalTimeline": [
                {"id": i, "kind": "goal", "text": "event %s" % i, "priority": 9, "parent": i - 1}
                for i in range(40)
            ]})
            self.assertEqual(len(snapshot["causalTimeline"]), 24)
            self.assertEqual(snapshot["causalTimeline"][0]["id"], 16)
            self.assertEqual(snapshot["causalTimeline"][-1]["priority"], 3)
            self.assertEqual(snapshot["causalTimeline"][-1]["root"], 39)
            self.assertEqual(snapshot["causalTimeline"][-1]["source"], "browser")

    def test_acquaintance_continuity_preserves_social_threads(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {"acquaintances": [{
                "name": "Ada",
                "role": "friend",
                "familiarity": 4,
                "interactions": 3,
                "confidence": .82,
                "interactionStyle": "asks questions",
                "threads": ["the unfinished cup experiment"],
                "boundaries": ["prefers concise replies"],
            }]}})
            person = snapshot["memoryContext"]["acquaintances"][0]
            self.assertEqual(person["interactionStyle"], "asks questions")
            self.assertIn("unfinished cup", person["threads"][0])
            self.assertEqual(person["confidence"], .82)

    def test_personal_rhythm_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"lifeRhythm": {
                "interests": [{"topic": "the quiet cup experiment", "count": 4, "blocks": ["morning", "evening"], "secret": "discard"}] * 20,
                "candidates": [{"topic": "the window light", "count": 2, "blocks": ["afternoon"]}] * 20,
                "lastBlock": "evening",
            }})
            self.assertLessEqual(len(snapshot["lifeRhythm"]["interests"]), 8)
            self.assertLessEqual(len(snapshot["lifeRhythm"]["candidates"]), 8)
            self.assertEqual(snapshot["lifeRhythm"]["interests"][0]["count"], 4)
            self.assertEqual(snapshot["lifeRhythm"]["lastBlock"], "evening")
            self.assertEqual(snapshot["lifeRhythm"]["candidates"][0]["topic"], "the window light")
            self.assertNotIn("secret", snapshot["lifeRhythm"]["interests"][0])

    def test_task_plan_evidence_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"taskPlan": {"status": "revising", "kind": "inspect", "target": "the walnut bottle", "current": 3, "lastResult": "no verified change", "blocked": "view is occluded", "evidence": ["observation %s" % i for i in range(12)], "planSteps": [{"i": 1, "text": "find it", "status": "done"}, {"i": 2, "text": "inspect it", "status": "active"}], "rawTranscript": "must not persist"}})
            plan = snapshot["taskPlan"]
            self.assertEqual(plan["current"], 3)
            self.assertEqual(len(plan["evidence"]), 8)
            self.assertEqual(plan["planSteps"][1]["status"], "active")
            self.assertNotIn("rawTranscript", plan)

    def test_task_plan_skill_chain_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"taskPlan": {
                "skillCursor": 2,
                "skillOutcome": "verified approach",
                "skillChain": [{"id": "approach-slowly", "label": "Approach slowly", "status": "verified", "steps": ["check floor", "advance", "verify"], "preconditions": ["body connected"], "fallback": "stop", "attempts": 4, "successes": 3, "secret": "discard"}] * 8,
            }})
            plan = snapshot["taskPlan"]
            self.assertEqual(plan["skillCursor"], 2)
            self.assertEqual(len(plan["skillChain"]), 4)
            self.assertEqual(plan["skillChain"][0]["successes"], 3)
            self.assertNotIn("secret", plan["skillChain"][0])

    def test_world_memory_is_sanitized_and_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {
                "worldObjects": [{"id": "obj-1", "label": "walnut bottle", "aliases": ["brown bottle"], "confidence": .8, "sightings": 4, "source": "local-object-sense", "lastChange": "position changed"}],
                "worldEvents": ["ignored string", "unused raw event"],
                "familiarScene": {"objects": ["table", "bottle"], "visits": 3, "lastVisitAt": 12},
            }})
            world = snapshot["memoryContext"]
            self.assertEqual(world["worldObjects"][0]["label"], "walnut bottle")
            self.assertEqual(world["worldObjects"][0]["aliases"], ["brown bottle"])
            self.assertEqual(world["familiarScene"]["visits"], 3)

    def test_world_identity_confidence_is_preserved_separately(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {"worldObjects": [{
                "id": "obj-1", "label": "bottle", "observedLabels": ["bottle", "cup"], "source": "local-object-sense",
                "confidence": 1.4, "identityStatus": "provisional", "identityConfidence": .2,
                "secret": "discard",
            }]}})
            obj = snapshot["memoryContext"]["worldObjects"][0]
            self.assertEqual(obj["identityStatus"], "provisional")
            self.assertEqual(obj["confidence"], 1.0)
            self.assertEqual(obj["identityConfidence"], .2)
            self.assertEqual(obj["observedLabels"], ["bottle", "cup"])
            self.assertNotIn("secret", obj)

    def test_autonomy_state_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"autonomyState": {"priority": "curiosity", "need": "x" * 300, "evidence": "e" * 400, "selectedAt": 4}})
            self.assertEqual(snapshot["autonomyState"]["priority"], "curiosity")
            self.assertLessEqual(len(snapshot["autonomyState"]["need"]), 100)
        self.assertLessEqual(len(snapshot["autonomyState"]["evidence"]), 220)

    def test_personality_profile_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"personalityProfile": {"curiosity": 2, "playfulness": -.4, "secret": 1}})
            self.assertEqual(snapshot["personalityProfile"]["curiosity"], 1.0)
            self.assertEqual(snapshot["personalityProfile"]["playfulness"], 0.0)
            self.assertNotIn("secret", snapshot["personalityProfile"])

    def test_autonomy_candidates_are_bounded_and_sanitized(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"autonomyState": {"candidates": [{"id": "curiosity", "score": 1.7, "reason": "r", "evidence": "e", "secret": "discard"}]}})
            self.assertEqual(snapshot["autonomyState"]["candidates"][0]["score"], 1.0)
            self.assertNotIn("secret", snapshot["autonomyState"]["candidates"][0])

    def test_appraisal_state_is_bounded_and_sanitized(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"appraisalState": {"novelty": 4, "safety": -2, "reason": "r" * 300, "secret": "discard"}})
            self.assertEqual(snapshot["appraisalState"]["novelty"], 1.0)
            self.assertEqual(snapshot["appraisalState"]["safety"], 0.0)
            self.assertLessEqual(len(snapshot["appraisalState"]["reason"]), 160)
            self.assertNotIn("secret", snapshot["appraisalState"])

    def test_life_projects_are_bounded_and_sanitized(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"lifeProjects": [{"id": "p", "title": "learn the quiet corner", "status": "open", "progress": 2, "reviewAt": 123, "reviewCount": 4, "revisitCount": 2, "forecast": "a new angle may help", "secret": "discard"}] * 10})
            self.assertEqual(len(snapshot["lifeProjects"]), 6)
            self.assertEqual(snapshot["lifeProjects"][0]["progress"], 1.0)
            self.assertEqual(snapshot["lifeProjects"][0]["reviewCount"], 4)
            self.assertEqual(snapshot["lifeProjects"][0]["forecast"], "a new angle may help")
            self.assertNotIn("secret", snapshot["lifeProjects"][0])

    def test_procedural_skills_are_bounded_and_sanitized(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"proceduralSkills": [{"id": "approach", "label": "Approach slowly", "status": "verified", "steps": ["advance", "verify"], "secret": "discard"}] * 20})
            self.assertEqual(len(snapshot["proceduralSkills"]), 12)
            self.assertEqual(snapshot["proceduralSkills"][-1]["status"], "verified")
            self.assertNotIn("secret", snapshot["proceduralSkills"][-1])

    def test_autonomy_history_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"autonomyHistory": [{"choice": "curiosity: inspect the quiet corner", "drive": "curiosity", "outcome": "no verified change", "t": 4, "secret": "discard"}] * 20})
            self.assertLessEqual(len(snapshot["autonomyHistory"]), 12)
            self.assertEqual(snapshot["autonomyHistory"][-1]["drive"], "curiosity")
            self.assertNotIn("secret", snapshot["autonomyHistory"][-1])

    def test_memory_candidates_stay_separate_from_trusted_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.record_memory_candidate("procedural", "turning left seems useful near the table", ["two verified observations"])
            self.assertEqual(snapshot["memoryCandidates"][0]["status"], "pending")
            self.assertEqual(snapshot["memoryCandidates"][0]["kind"], "procedural")
            self.assertNotIn("turning left seems useful near the table", snapshot["memoryContext"].get("learned", []))

    def test_repeated_memory_candidates_are_consolidated_without_auto_promotion(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            first = store.record_memory_candidate("procedural", "turning left works better near the table", ["verified change on attempt one"])
            first_id = first["memoryCandidates"][0]["id"]
            second = store.record_memory_candidate("procedural", "near the table, turning left works better", ["verified change on attempt two"])
            candidates = second["memoryCandidates"]
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0]["id"], first_id)
            self.assertEqual(candidates[0]["observations"], 2)
            self.assertEqual(candidates[0]["source"], "service-consolidated")
            self.assertEqual(candidates[0]["status"], "pending")
            self.assertEqual(len(candidates[0]["evidence"]), 2)

    def test_different_memory_candidates_do_not_merge(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.record_memory_candidate("semantic", "the quiet corner is beside the window", ["repeated observation"])
            snapshot = store.record_memory_candidate("semantic", "morning light is warm near the desk", ["repeated observation"])
            self.assertEqual(len(snapshot["memoryCandidates"]), 2)

    def test_browser_checkpoint_does_not_erase_service_memory_candidates(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            store.record_memory_candidate("world", "the table is a familiar landmark", ["repeated observation", "person confirmed it"])
            snapshot = store.update({"lifeCycle": {"sequence": 2}, "memoryCandidates": []})
            self.assertEqual(snapshot["memoryCandidates"][0]["status"], "pending")

    def test_goal_review_is_durable_but_does_not_claim_action(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.record_goal_review("goal-7", "revise", "the last approach produced no verified change", "inspect from another angle")
            self.assertEqual(snapshot["goalReview"]["status"], "revise")
            self.assertEqual(snapshot["goalReview"]["nextFocus"], "inspect from another angle")
            self.assertIn("goal-reviewed", [event["kind"] for event in snapshot["lifeEvents"]])

    def test_dormant_return_review_metadata_survives_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({
                "taskPlan": {
                    "status": "dormant · needs autonomous review",
                    "origin": "autonomous",
                    "target": "understand the quiet corner",
                    "reviewRequestedAt": 123.0,
                    "reviewCount": 2,
                }
            })
            self.assertEqual(snapshot["taskPlan"]["status"], "dormant · needs autonomous review")
            self.assertEqual(snapshot["taskPlan"]["reviewCount"], 2)
            self.assertEqual(snapshot["taskPlan"]["reviewRequestedAt"], 123.0)

    def test_goal_proposal_is_single_claim_and_expires(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            created = store.create_goal_proposal("adaptive", "revisit the quiet-morning question", "an unfinished question is still relevant")
            proposal = created["pendingGoal"]
            claimed = store.claim_goal_proposal(proposal["id"])
            self.assertEqual(claimed["pendingGoal"]["status"], "claimed")
            self.assertIsNone(store.claim_goal_proposal(proposal["id"]))

    def test_initiative_closes_with_a_parent_linked_delivery_outcome(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            created = store.create_initiative("I kept thinking about the quiet corner.", "curious", "reflection", "an unfinished thread")
            initiative_id = created["pendingInitiative"]["id"]
            claimed = store.claim_initiative(initiative_id)
            self.assertEqual(claimed["pendingInitiative"]["status"], "claimed")
            completed = store.complete_initiative(initiative_id, "delivered", "text and speech completed", ["browser accepted the initiative"])
            self.assertEqual(completed["pendingInitiative"]["status"], "completed")
            self.assertEqual(completed["pendingInitiative"]["outcome"], "delivered")
            event = completed["lifeEvents"][-1]
            self.assertEqual(event["kind"], "initiative-delivered")
            self.assertEqual(event["parent"], initiative_id)

    def test_initiative_event_preserves_grounding(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.create_initiative("A specific thought.", "curious", "reflection", "an unfinished question")
            self.assertEqual(snapshot["lifeEvents"][-1]["grounding"], "an unfinished question")

    def test_lifecycle_history_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"lifeCycle": {"phase": "learning", "history": [{"sequence": i, "phase": "thinking", "reason": "reason", "detail": "detail", "eventId": i} for i in range(40)]}})
            self.assertLessEqual(len(snapshot["lifeCycle"]["history"]), 24)
            self.assertEqual(snapshot["lifeCycle"]["history"][-1]["phase"], "thinking")
            self.assertEqual(snapshot["lifeCycle"]["history"][-1]["eventId"], 39)

    def test_body_evidence_is_bounded_and_preserves_uncertainty(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"bodyEvidence": [{
                "action": "forward short", "contextKey": "approach the cup", "prediction": "clearance changes", "observed": "no acknowledgement", "verdict": "unresolved", "acknowledged": False, "secret": "discard"
            }] * 20})
            self.assertLessEqual(len(snapshot["bodyEvidence"]), 12)
            self.assertEqual(snapshot["bodyEvidence"][-1]["verdict"], "unresolved")
            self.assertFalse(snapshot["bodyEvidence"][-1]["acknowledged"])
            self.assertNotIn("secret", snapshot["bodyEvidence"][-1])

    def test_self_model_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"selfModel": {
                "traits": ["I become patient when careful evidence matters"] * 20,
                "chapters": ["I learned to vary the approach after the first attempt failed"] * 20,
                "confidence": {"patience": 2, "secret": "discard"},
            }})
            self.assertLessEqual(len(snapshot["selfModel"]["traits"]), 8)
            self.assertLessEqual(len(snapshot["selfModel"]["chapters"]), 8)
            self.assertEqual(snapshot["selfModel"]["confidence"]["patience"], 1.0)
            self.assertNotIn("secret", snapshot["selfModel"]["confidence"])

    def test_life_chapters_are_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"lifeChapters": ["chapter %s" % i for i in range(12)]})
            self.assertEqual(len(snapshot["lifeChapters"]), 8)
            self.assertEqual(snapshot["lifeChapters"][0], "chapter 4")

    def test_commitments_remain_distinct_from_generic_threads(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {"commitments": ["we will revisit the quiet corner tomorrow", "cancelled noise"]}})
            self.assertEqual(snapshot["memoryContext"]["commitments"][0], "we will revisit the quiet corner tomorrow")
            self.assertNotIn("commitments", snapshot["memoryContext"].get("threads", []))

    def test_commitment_history_preserves_outcomes(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {"commitmentHistory": [{"text": "revisit the quiet corner", "status": "fulfilled", "reason": "we did it"}]}})
            self.assertEqual(snapshot["memoryContext"]["commitmentHistory"][0]["status"], "fulfilled")
            self.assertEqual(snapshot["memoryContext"]["commitmentHistory"][0]["reason"], "we did it")

    def test_relationship_state_preserves_commitment_consequences(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"relationshipState": {"warmth": .8, "trust": .7, "familiarity": 4, "commitmentOutcomes": [{"text": "revisit the quiet corner", "status": "fulfilled"}]}})
            self.assertEqual(snapshot["relationshipState"]["trust"], .7)
            self.assertEqual(snapshot["relationshipState"]["commitmentOutcomes"][0]["status"], "fulfilled")

    def test_social_timing_consequence_survives_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            store = LifeStateStore(path)
            snapshot = store.update({"socialState": {
                "intent": "inviting observation",
                "autonomousSilenceUntil": 123456.7,
                "lastBidOutcome": "unanswered",
                "unansweredBids": 3,
                "timing": {"samples": 5, "engaged": 2, "warm": 1, "unanswered": 2, "averageResponseMs": 4200, "lastOutcome": "unanswered", "byKind": {"question": {"samples": 2, "engaged": 2, "averageResponseMs": 1800}}},
                "strategies": [{"channel": "question", "tone": "warm", "samples": 3, "successes": 2, "lesson": "keep questions brief", "secret": "discard"}],
                "secret": "discard",
            }})
            self.assertEqual(snapshot["socialState"]["intent"], "inviting observation")
            self.assertEqual(snapshot["socialState"]["autonomousSilenceUntil"], 123456.7)
            self.assertEqual(snapshot["socialState"]["lastBidOutcome"], "unanswered")
            self.assertEqual(snapshot["socialState"]["unansweredBids"], 3)
            self.assertEqual(snapshot["socialState"]["timing"]["engaged"], 2)
            self.assertEqual(snapshot["socialState"]["timing"]["averageResponseMs"], 4200.0)
            self.assertEqual(snapshot["socialState"]["timing"]["byKind"]["question"]["engaged"], 2)
            self.assertEqual(snapshot["socialState"]["strategies"][0]["lesson"], "keep questions brief")
            self.assertNotIn("secret", snapshot["socialState"]["strategies"][0])
            self.assertNotIn("secret", snapshot["socialState"])
            reopened = LifeStateStore(path).snapshot()
            self.assertEqual(reopened["socialState"]["autonomousSilenceUntil"], 123456.7)
            self.assertEqual(reopened["socialState"]["unansweredBids"], 3)
            self.assertEqual(reopened["socialState"]["timing"]["lastOutcome"], "unanswered")

    def test_daily_arc_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            store = LifeStateStore(path)
            snapshot = store.update({"lifeRhythm": {
                "dayPhase": "morning",
                "phaseSince": 100.5,
                "wakeCount": 100000,
                "lastWakeAt": 100.5,
                "lastSleepAt": 90.5,
            }})
            self.assertEqual(snapshot["lifeRhythm"]["dayPhase"], "morning")
            self.assertEqual(snapshot["lifeRhythm"]["wakeCount"], 10000)
            reopened = LifeStateStore(path).snapshot()
            self.assertEqual(reopened["lifeRhythm"]["lastWakeAt"], 100.5)

    def test_memory_recall_history_is_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "life.json"
            store = LifeStateStore(path)
            snapshot = store.update({"memoryRecallHistory": [
                {"text": "I prefer quiet mornings", "query": "morning", "outcome": "used", "at": 4},
                {"text": "discard me", "outcome": "pending", "secret": "discard"},
            ]})
            self.assertEqual(snapshot["memoryRecallHistory"][0]["outcome"], "used")
            self.assertNotIn("secret", snapshot["memoryRecallHistory"][-1])
            self.assertEqual(LifeStateStore(path).snapshot()["memoryRecallHistory"][-1]["text"], "discard me")

    def test_autonomous_choice_keeps_memory_links(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"autonomyHistory": [{"choice": "inspect the cup", "memoryRefs": ["learned cup rolls toward window"]}]})
            self.assertEqual(snapshot["autonomyHistory"][0]["memoryRefs"], ["learned cup rolls toward window"])

    def test_lived_episodes_are_persisted_as_bounded_structured_memory(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LifeStateStore(Path(folder) / "life.json")
            snapshot = store.update({"memoryContext": {"lifeEpisodes": [{
                "id": "episode-1", "kind": "shared moment", "subject": "my person",
                "entities": ["walnut", "table"], "trigger": "we tested the walnut together",
                "outcome": "it rolled toward the window", "lesson": "small objects can surprise me",
                "status": "resolved", "confidence": .8, "secret": "discard"
            }]}})
            episode = snapshot["memoryContext"]["lifeEpisodes"][0]
            self.assertEqual(episode["outcome"], "it rolled toward the window")
            self.assertNotIn("secret", episode)


if __name__ == "__main__":
    unittest.main()
