import unittest

try:
    from aliveness_eval import evaluate_replay, evaluate_snapshot, instance_divergence
except ImportError:
    from bot.aliveness_eval import evaluate_replay, evaluate_snapshot, instance_divergence


class AlivenessEvaluationTests(unittest.TestCase):
    def test_snapshot_counts_social_consequences_of_autonomous_bids(self):
        metrics = evaluate_snapshot({
            "alivenessMetrics": {
                "autonomousBidsEngaged": 2,
                "autonomousBidsUnanswered": 1,
            }
        })
        self.assertEqual(metrics["autonomous_bids_engaged"], 2)
        self.assertEqual(metrics["autonomous_bids_unanswered"], 1)

    def test_snapshot_exposes_learned_initiative_timing(self):
        metrics = evaluate_snapshot({"socialState": {"timing": {"samples": 4, "engaged": 3, "unanswered": 1, "averageResponseMs": 2500, "byKind": {"question": {"samples": 2, "engaged": 2}}}}})
        self.assertEqual(metrics["initiative_engagement_rate"], .75)
        self.assertEqual(metrics["initiative_unanswered_rate"], .25)
        self.assertEqual(metrics["initiative_average_response_seconds"], 2.5)
        self.assertEqual(metrics["social_response_pattern_count"], 1)

    def test_snapshot_exposes_reusable_social_strategy(self):
        metrics = evaluate_snapshot({
            "socialState": {"strategies": [{"channel": "question", "samples": 3, "successes": 2, "lesson": "keep questions brief"}]},
            "autonomyHistory": [{"choice": "ask a question", "strategyRefs": ["keep questions brief"]}],
        })
        self.assertEqual(metrics["social_strategy_count"], 1)
        self.assertEqual(metrics["social_strategy_reuse_rate"], 1.0)

    def test_snapshot_exposes_scene_prediction_learning(self):
        metrics = evaluate_snapshot({"memoryContext": {"familiarScene": {"predictionAttempts": 3, "stability": .67}}})
        self.assertEqual(metrics["scene_prediction_attempts"], 3)
        self.assertEqual(metrics["scene_prediction_stability"], .67)

    def test_snapshot_exposes_prospective_project_state(self):
        metrics = evaluate_snapshot({"lifeProjects": [{"title": "return to the corner", "status": "paused", "forecast": "a new angle", "reviewAt": 10, "reviewCount": 2}]})
        self.assertEqual(metrics["prospective_project_rate"], 1.0)
        self.assertEqual(metrics["prospective_project_due_rate"], 1.0)

    def test_snapshot_exposes_homeostatic_pressure_and_revision(self):
        metrics = evaluate_snapshot({"innerState": {
            "needs": {"connection": .74, "sleep": .2},
            "homeostasis": {"revision": 12},
        }})
        self.assertEqual(metrics["homeostatic_revision_count"], 12)
        self.assertEqual(metrics["homeostatic_need_pressure"], .74)

    def test_snapshot_measures_private_activity_ecology(self):
        metrics = evaluate_snapshot({
            "privateActivities": [
                {"activity": "review-goal"},
                {"activity": "rest"},
                {"activity": "consolidate"},
            ],
            "autonomyHistory": [{"choice": "rest", "privateActivityRefs": ["activity-1"]}],
        })
        self.assertEqual(metrics["private_activity_count"], 3)
        self.assertEqual(metrics["private_activity_variety"], 1.0)
        self.assertEqual(metrics["private_activity_reuse_rate"], 1.0)

    def test_replay_counts_homeostatic_change(self):
        metrics = evaluate_replay([
            {"innerState": {"homeostasis": {"revision": 2}}},
            {"innerState": {"homeostasis": {"revision": 3}}},
            {"innerState": {"homeostasis": {"revision": 3}}},
        ])
        self.assertEqual(metrics["homeostatic_change_count"], 1)

    def test_replay_measures_reflection_reuse_in_a_later_choice(self):
        metrics = evaluate_replay([
            {"reflections": [{"id": "reflection-1", "text": "the quiet corner still matters"}]},
            {"autonomyHistory": [{"choice": "inspect the quiet corner", "reflectionRefs": ["reflection-1"]}]},
        ])
        self.assertEqual(metrics["reflection_reuse_count"], 1)
        self.assertEqual(metrics["reflection_to_choice_rate"], 1.0)

    def test_replay_measures_intention_resume_revision_and_stale_expiry(self):
        metrics = evaluate_replay([
            {"taskPlan": {"status": "paused · resumable intention", "target": "inspect the quiet corner", "resumeCount": 0}},
            {"taskPlan": {"status": "resuming remembered plan", "target": "inspect the quiet corner", "resumeCount": 1}, "autonomyHistory": [{"choice": "look around the bright window"}]},
            {"taskPlan": {"status": "revising", "target": "compare the corner from another angle", "resumeCount": 1}, "goalReview": {"status": "revise", "reason": "the first view was not verified"}},
            {"taskPlan": {"status": "expired", "target": "an old thread", "blocked": "remembered plan was too old to resume", "resumeCount": 1}},
        ])
        self.assertEqual(metrics["intention_resumption_count"], 1)
        self.assertGreaterEqual(metrics["intention_revision_count"], 1)
        self.assertEqual(metrics["stale_intention_expiration_count"], 1)
        self.assertEqual(metrics["resumed_intention_adaptation_rate"], 1.0)

    def test_replay_measures_emotion_reactivity_and_private_activity_variety(self):
        metrics = evaluate_replay([
            {"emotionState": {"name": "curious", "intensity": .4}, "privateActivities": [{"activity": "review-goal"}]},
            {"emotionState": {"name": "frustrated", "intensity": .7}, "bodyEvidence": [{"action": "turn left", "verdict": "disconfirmed"}], "privateActivities": [{"activity": "review-goal"}, {"activity": "rest"}]},
        ])
        self.assertEqual(metrics["emotion_reactivity_rate"], 1.0)
        self.assertEqual(metrics["private_activity_variety_session_rate"], 1.0)

    def test_snapshot_exposes_completed_correction_repairs(self):
        metrics = evaluate_snapshot({"alivenessMetrics": {"correctionRepairs": 3}})
        self.assertEqual(metrics["correction_repair_count"], 3)

    def test_snapshot_exposes_priority_context(self):
        metrics = evaluate_snapshot({"coordinator": {"lastDecision": {"freshness": .14, "repetition_penalty": .08}}})
        self.assertEqual(metrics["priority_freshness_bias"], .14)
        self.assertEqual(metrics["priority_repetition_penalty"], .08)

    def test_snapshot_measures_opportunity_timing_without_treating_silence_as_failure(self):
        metrics = evaluate_snapshot({
            "autonomyHistory": [
                {"choice": "say: a thought", "opportunity": {"status": "engaged", "openedAt": 1000000000000, "resolvedAt": 1000000015000}},
                {"choice": "say: another thought", "opportunity": {"status": "unanswered", "openedAt": 1000000020000, "resolvedAt": 1000000165000}},
            ]
        })
        self.assertEqual(metrics["autonomous_bid_count"], 2)
        self.assertEqual(metrics["opportunity_engagement_rate"], .5)
        self.assertEqual(metrics["opportunity_timing_quality"], 1.0)
        self.assertEqual(metrics["opportunity_unanswered_rate"], .5)

    def test_snapshot_exposes_grounding_repetition_body_and_recovery(self):
        metrics = evaluate_snapshot({
            "autonomyHistory": [
                {"choice": "curiosity: inspect the quiet cup"},
                {"choice": "curiosity: inspect the quiet cup"},
                {"choice": "play: echo the tapping"},
            ],
            "lifeEvents": [
                {"kind": "initiative-created", "detail": "I kept a question about the cup", "grounding": "unfinished thread"},
                {"kind": "initiative-created", "detail": "generic line"},
                {"kind": "initiative-delivered"},
            ],
            "bodyEvidence": [
                {"verdict": "confirmed"},
                {"verdict": "unresolved"},
            ],
            "causalTimeline": [{"kind": "lifecycle", "text": "choosing"}] * 3,
            "socialEpisodes": [{"text": "we laughed at the walnut"}],
            "lifeProjects": [{"title": "learn the quiet corner", "status": "open", "idleDays": 2}],
            "memoryRecords": [{"text": "quiet mornings feel safe", "status": "confirmed", "durationDays": 4, "observations": 2}],
            "relationshipState": {"bondSince": 1000, "lastMeaningfulAt": 1000 + 3 * 86400},
            "goalReview": {"status": "revise", "reason": "the last attempt was unresolved"},
        })
        self.assertEqual(metrics["grounded_initiative_rate"], .5)
        self.assertEqual(metrics["repetition_rate"], round(1 / 3, 3))
        self.assertEqual(metrics["body_verified_rate"], .5)
        self.assertEqual(metrics["goal_recovery_rate"], 1.0)
        self.assertEqual(metrics["social_episode_count"], 1)
        self.assertEqual(metrics["living_project_count"], 1)
        self.assertEqual(metrics["durative_memory_rate"], 1.0)
        self.assertEqual(metrics["dormant_living_project_rate"], 1.0)
        self.assertEqual(metrics["relationship_age_days"], 3.0)
        self.assertEqual(metrics["causal_stage_coverage"], 0.0)
        self.assertEqual(metrics["initiative_efficacy_rate"], .5)
        self.assertEqual(metrics["initiative_outcome_rate"], .5)
        self.assertIsNotNone(metrics["continuity_quality"])

    def test_instance_divergence_is_zero_only_for_same_lived_identity(self):
        base = {"selfModel": {"traits": ["I am curious"], "chapters": ["I learned the quiet corner"]}}
        self.assertEqual(instance_divergence(base, base), 0.0)
        other = {"selfModel": {"traits": ["I am playful"], "chapters": ["I learned the bright corner"]}}
        self.assertGreater(instance_divergence(base, other), 0.5)

    def test_causal_stage_coverage_counts_typed_life_spine(self):
        stages = [
            "observation", "appraisal", "motive", "decision", "plan", "action",
            "acknowledgement", "verification", "learning", "social-consequence",
            "memory-promotion",
        ]
        metrics = evaluate_snapshot({"causalTimeline": [{"kind": stage} for stage in stages]})
        self.assertEqual(metrics["causal_stage_coverage"], 1.0)

    def test_session_history_reports_real_lifecycle_checkpoints(self):
        metrics = evaluate_snapshot({
            "sessionHistory": [
                {"id": "session-a", "reason": "opened", "phase": "resting", "mode": "idle"},
                {"id": "session-a", "reason": "backgrounded", "phase": "learning", "mode": "autonomous"},
            ]
        })
        self.assertEqual(metrics["session_checkpoint_count"], 2)
        self.assertEqual(metrics["session_checkpoint_quality"], 1.0)
        self.assertEqual(metrics["session_lifecycle_coverage"], 1.0)

    def test_memory_history_reports_linked_revisions(self):
        metrics = evaluate_snapshot({
            "memoryHistory": [
                {"text": "I like tea", "status": "outdated", "supersededBy": "mem-new"},
                {"text": "I prefer coffee", "status": "confirmed"},
            ]
        })
        self.assertEqual(metrics["memory_revision_count"], 1)
        self.assertEqual(metrics["memory_revision_link_rate"], 1.0)

    def test_memory_recall_reports_use_and_rejection(self):
        metrics = evaluate_snapshot({
            "memoryRecallHistory": [
                {"text": "I prefer quiet mornings", "outcome": "used"},
                {"text": "I dislike loud alarms", "outcome": "rejected"},
                {"text": "pending memory", "outcome": "pending"},
            ]
        })
        self.assertEqual(metrics["memory_recall_resolution_rate"], round(2 / 3, 3))
        self.assertEqual(metrics["memory_recall_use_rate"], .5)
        self.assertEqual(metrics["memory_recall_rejection_rate"], .5)

    def test_memory_links_to_autonomous_choices(self):
        metrics = evaluate_snapshot({
            "autonomyHistory": [
                {"choice": "inspect the cup", "memoryRefs": ["I learned the cup rolls toward the window"]},
                {"choice": "rest", "memoryRefs": []},
            ]
        })
        self.assertEqual(metrics["memory_influenced_choice_rate"], .5)

    def test_memory_choice_can_be_traced_to_verified_action(self):
        metrics = evaluate_snapshot({
            "autonomyHistory": [
                {"choice": "inspect the cup", "memoryRefs": ["cup rolls toward window"], "actionOutcome": {"action": "inspect", "status": "verified"}},
                {"choice": "rest", "memoryRefs": ["quiet is useful"], "actionOutcome": {"action": "rest", "status": "disconfirmed"}},
            ]
        })
        self.assertEqual(metrics["choice_action_outcome_link_rate"], 1.0)
        self.assertEqual(metrics["memory_influenced_verified_outcome_rate"], .5)

    def test_lived_episode_reports_action_and_verified_outcome(self):
        metrics = evaluate_snapshot({
            "memoryContext": {"lifeEpisodes": [
                {"trigger": "we tested the walnut", "action": "turn toward it", "status": "resolved", "verified": True},
                {"trigger": "we tried again", "action": "approach", "status": "unresolved", "verified": None},
            ]}
        })
        self.assertEqual(metrics["episode_action_outcome_link_rate"], 1.0)
        self.assertEqual(metrics["episode_verified_outcome_rate"], .5)

    def test_personality_alignment_measures_traits_affecting_choices(self):
        metrics = evaluate_snapshot({
            "autonomyHistory": [
                {"choice": "play: echo the tapping", "drive": "play", "personality": {"playfulness": .8}},
                {"choice": "inspect the quiet corner", "drive": "curiosity", "personality": {"playfulness": .8}},
            ]
        })
        self.assertEqual(metrics["personality_alignment_rate"], .5)

    def test_replay_reports_personality_change_followed_by_choice(self):
        first = {"sessionHistory": [{"id": "a", "personality": {"curiosity": .2}}]}
        second = {
            "sessionHistory": [{"id": "b", "personality": {"curiosity": .8}}],
            "autonomyHistory": [{"choice": "inspect the new object"}],
        }
        metrics = evaluate_replay([first, second])
        self.assertEqual(metrics["personality_change_count"], 1)
        self.assertEqual(metrics["personality_evolution_rate"], 1.0)

    def test_replay_carries_opportunity_timing_across_sessions(self):
        metrics = evaluate_replay([
            {"autonomyHistory": [{"choice": "say: one", "opportunity": {"status": "engaged", "openedAt": 1000000000000, "resolvedAt": 1000000010000}}]},
            {"autonomyHistory": [{"choice": "say: two", "opportunity": {"status": "unanswered", "openedAt": 1000000020000, "resolvedAt": 1000000160000}}]},
        ])
        self.assertEqual(metrics["opportunity_engagement_rate"], .5)
        self.assertEqual(metrics["opportunity_timing_quality"], 1.0)
        self.assertEqual(metrics["opportunity_unanswered_rate"], .5)

    def test_replay_measures_correction_failure_silence_and_memory_continuity(self):
        first = {
            "causalTimeline": [{"kind": "observation", "text": "the first angle gave no change", "t": 1}],
            "bodyEvidence": [{"verdict": "disconfirmed"}],
            "goalReview": {"status": "revise"},
            "lifeProjects": [{"title": "quiet corner", "status": "paused"}],
            "memoryRecords": [{"text": "quiet mornings", "status": "confirmed"}],
        }
        second = {
            "causalTimeline": [{"kind": "correction", "text": "the person corrected the angle", "t": 2}],
            "autonomyHistory": [{"choice": "inspect the corner"}, {"choice": "change the angle"}],
            "lifeEvents": [{"kind": "autonomy-decision", "detail": "returned to the question"}],
            "lifeProjects": [{"title": "quiet corner", "status": "reopened"}],
            "memoryRecords": [{"text": "quiet mornings", "status": "confirmed"}],
        }
        metrics = evaluate_replay([first, second])
        self.assertEqual(metrics["correction_adaptation_rate"], 1.0)
        self.assertEqual(metrics["failure_recovery_rate"], 1.0)
        self.assertEqual(metrics["silence_initiative_rate"], .5)
        self.assertEqual(metrics["project_resumption_count"], 1)
        self.assertEqual(metrics["memory_carryover_rate"], 1.0)

    def test_replay_detects_episode_closure_and_changed_choice(self):
        episode = {"id": "e1", "trigger": "the walnut was near the edge", "action": "approach", "status": "unresolved"}
        first = {"lifeEpisodes": [episode], "autonomyHistory": [{"choice": "approach the walnut"}]}
        second = {"lifeEpisodes": [{**episode, "status": "resolved", "verified": False, "outcome": "it did not move"}], "autonomyHistory": [{"choice": "inspect from another angle"}]}
        metrics = evaluate_replay([first, second])
        self.assertEqual(metrics["episode_outcome_progression_count"], 1)
        self.assertEqual(metrics["episode_adaptation_rate"], 1.0)

    def test_replay_measures_prospective_project_review_and_follow_through(self):
        metrics = evaluate_replay([
            {"lifeProjects": [{"title": "quiet corner", "status": "paused", "forecast": "a new angle may help", "reviewCount": 0}]},
            {"lifeProjects": [{"title": "quiet corner", "status": "paused", "forecast": "try the other side of the corner", "reviewCount": 1}], "autonomyHistory": [{"choice": "inspect the other side of the quiet corner"}]},
        ])
        self.assertEqual(metrics["prospective_review_count"], 1)
        self.assertEqual(metrics["prospective_forecast_change_count"], 1)
        self.assertEqual(metrics["prospective_review_choice_link_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
