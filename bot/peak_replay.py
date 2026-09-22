"""Deterministic longitudinal replay for XEMO's aliveness checks."""

try:
    from .aliveness_eval import evaluate_replay
except ImportError:
    from aliveness_eval import evaluate_replay


def peak_replay():
    return [
        {
            "sessionHistory": [{"id": "wake-1", "phase": "choosing", "mode": "autonomous", "reason": "waking"}],
            "emotionState": {"name": "curious", "intensity": 0.45},
            "privateActivities": [{"id": "activity-1", "activity": "review-goal", "grounding": "the quiet corner question remains open"}],
            "taskPlan": {"status": "active", "target": "inspect the quiet corner", "resumeCount": 0},
            "autonomyHistory": [{"choice": "inspect the quiet corner", "drive": "curiosity"}],
            "lifeEvents": [{"kind": "autonomy-decision", "detail": "chose to inspect the quiet corner", "at": 1}],
        },
        {
            "sessionHistory": [{"id": "wake-1", "phase": "verifying", "mode": "autonomous", "reason": "body result"}],
            "emotionState": {"name": "frustrated", "intensity": 0.72},
            "privateActivities": [
                {"id": "activity-1", "activity": "review-goal", "grounding": "the quiet corner question remains open"},
                {"id": "activity-2", "activity": "rest", "grounding": "the first method gave no verified change"},
            ],
            "taskPlan": {"status": "revising", "target": "inspect the quiet corner", "resumeCount": 0},
            "goalReview": {"status": "revise", "reason": "the first view gave no verified change"},
            "bodyEvidence": [{"action": "turn left", "verdict": "disconfirmed", "observed": "no verified change"}],
            "autonomyHistory": [{"choice": "inspect the quiet corner from another angle", "drive": "competence"}],
            "causalTimeline": [{"kind": "verification", "text": "turn left produced no verified change", "t": 2}],
        },
        {
            "sessionHistory": [{"id": "wake-1", "phase": "learning", "mode": "autonomous", "reason": "verified result"}],
            "emotionState": {"name": "proud", "intensity": 0.66},
            "privateActivities": [
                {"id": "activity-2", "activity": "rest", "grounding": "the first method gave no verified change"},
                {"id": "activity-3", "activity": "consolidate", "grounding": "the changed view produced a repeatable result"},
            ],
            "taskPlan": {"status": "resuming remembered plan", "target": "compare the quiet corner from another angle", "resumeCount": 1},
            "bodyEvidence": [{"action": "turn right", "verdict": "confirmed", "observed": "the corner changed in view"}],
            "autonomyHistory": [{"choice": "keep the changed angle as a body lesson", "drive": "competence"}],
            "causalTimeline": [{"kind": "learning", "text": "the changed view produced a repeatable result", "t": 3}],
        },
        {
            "sessionHistory": [{"id": "wake-1", "phase": "resting", "mode": "human", "reason": "person interrupted"}],
            "emotionState": {"name": "warm", "intensity": 0.52},
            "privateActivities": [{"id": "activity-4", "activity": "plan-next-step", "grounding": "the person returned and the shared thread is open"}],
            "taskPlan": {"status": "paused · resumable intention", "target": "compare the quiet corner from another angle", "resumeCount": 1},
            "lifeEvents": [{"kind": "interruption", "detail": "the person took the conversational floor", "at": 4}],
            "autonomyHistory": [{"choice": "answer the person before resuming the corner question", "drive": "social"}],
        },
        {
            "sessionHistory": [{"id": "wake-1", "phase": "choosing", "mode": "autonomous", "reason": "returned"}],
            "emotionState": {"name": "determined", "intensity": 0.58},
            "privateActivities": [{"id": "activity-5", "activity": "revisit-memory", "grounding": "the verified change is worth comparing once more"}],
            "taskPlan": {"status": "revising", "target": "compare the corner with the verified angle", "resumeCount": 2},
            "goalReview": {"status": "revise", "reason": "the earlier result needs one comparable repeat"},
            "autonomyHistory": [{"choice": "compare the corner with the verified angle", "drive": "persistence"}],
            "causalTimeline": [{"kind": "decision", "text": "returned with a changed comparison", "t": 5}],
        },
    ]


def evaluate_peak_replay():
    return evaluate_replay(peak_replay())


if __name__ == "__main__":
    import json

    print(json.dumps(evaluate_peak_replay(), indent=2, sort_keys=True))
