"""Small durable journal for XEMO's browser life state.

This is deliberately not an autonomous brain. It preserves continuity when a
browser tab is suspended, while leaving perception, model calls, and physical
actions under their existing safety owners.
"""

import json
import hashlib
import os
import threading
import time
from pathlib import Path


class LifeStateStore:
    """Read/write a bounded, private checkpoint for one XEMO instance."""

    def __init__(self, path=None, instance_id=None):
        configured_id = str(instance_id or os.environ.get("XEMO_INSTANCE_ID", "")).strip()
        token = os.environ.get("XEMO_LIFE_TOKEN", "").strip()
        if not configured_id and token:
            configured_id = "token-" + hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]
        self.instance_id = self._safe_id(configured_id or "default")
        default = os.environ.get("XEMO_LIFE_STATE", str(Path.home() / ".xemo-life" / (self.instance_id + ".json")))
        self.path = Path(path or default).expanduser()
        self.lock = threading.RLock()
        self.state = self._read()

    @staticmethod
    def _safe_id(value):
        return "".join(ch for ch in str(value or "default") if ch.isalnum() or ch in "-_" )[:64] or "default"

    @staticmethod
    def _clean_text(value, limit):
        return " ".join(str(value or "").split())[:limit]

    @staticmethod
    def _memory_similarity(left, right):
        words = lambda value: {word for word in LifeStateStore._clean_text(value, 220).lower().split() if len(word) > 2}
        a, b = words(left), words(right)
        if not a or not b:
            return 0.0
        if a == b:
            return 1.0
        return len(a & b) / max(1, len(a | b))

    @staticmethod
    def _bounded_score(value):
        try:
            return max(0.0, min(1.0, float(value or 0)))
        except (TypeError, ValueError):
            return None

    def _normalise(self, value):
        value = value if isinstance(value, dict) else {}
        lifecycle = value.get("lifeCycle") if isinstance(value.get("lifeCycle"), dict) else {}
        goal = value.get("activeGoal") if isinstance(value.get("activeGoal"), dict) else None
        coordinator = value.get("coordinator") if isinstance(value.get("coordinator"), dict) else {}
        initiative = value.get("pendingInitiative") if isinstance(value.get("pendingInitiative"), dict) else None
        events = value.get("lifeEvents") if isinstance(value.get("lifeEvents"), list) else []
        causal_timeline = value.get("causalTimeline") if isinstance(value.get("causalTimeline"), list) else []
        memory_records = value.get("memoryRecords") if isinstance(value.get("memoryRecords"), list) else []
        memory_history = value.get("memoryHistory") if isinstance(value.get("memoryHistory"), list) else []
        memory_recall_history = value.get("memoryRecallHistory") if isinstance(value.get("memoryRecallHistory"), list) else []
        reflections = value.get("reflections") if isinstance(value.get("reflections"), list) else []
        private_activities = value.get("privateActivities") if isinstance(value.get("privateActivities"), list) else []
        memory = value.get("memoryContext") if isinstance(value.get("memoryContext"), dict) else {}
        inner = value.get("innerState") if isinstance(value.get("innerState"), dict) else {}
        review = value.get("goalReview") if isinstance(value.get("goalReview"), dict) else None
        pending_goal = value.get("pendingGoal") if isinstance(value.get("pendingGoal"), dict) else None
        memory_candidates = value.get("memoryCandidates") if isinstance(value.get("memoryCandidates"), list) else []
        task_plan = value.get("taskPlan") if isinstance(value.get("taskPlan"), dict) else {}
        autonomy = value.get("autonomyState") if isinstance(value.get("autonomyState"), dict) else {}
        appraisal = value.get("appraisalState") if isinstance(value.get("appraisalState"), dict) else {}
        homeostasis = inner.get("homeostasis") if isinstance(inner.get("homeostasis"), dict) else {}
        self_model = value.get("selfModel") if isinstance(value.get("selfModel"), dict) else {}
        relationship_state = value.get("relationshipState") if isinstance(value.get("relationshipState"), dict) else {}
        social_state = value.get("socialState") if isinstance(value.get("socialState"), dict) else {}
        rhythm = value.get("lifeRhythm") if isinstance(value.get("lifeRhythm"), dict) else {}
        aliveness = value.get("alivenessMetrics") if isinstance(value.get("alivenessMetrics"), dict) else {}
        autonomy_history = value.get("autonomyHistory") if isinstance(value.get("autonomyHistory"), list) else []
        session_history = value.get("sessionHistory") if isinstance(value.get("sessionHistory"), list) else []
        return_reflection = value.get("returnReflection") if isinstance(value.get("returnReflection"), dict) else None
        projects = value.get("lifeProjects") if isinstance(value.get("lifeProjects"), list) else []
        procedural_skills = value.get("proceduralSkills") if isinstance(value.get("proceduralSkills"), list) else []
        body_evidence = value.get("bodyEvidence") if isinstance(value.get("bodyEvidence"), list) else []
        body_prediction_ledger = value.get("bodyPredictionLedger") if isinstance(value.get("bodyPredictionLedger"), list) else []
        life_chapters = value.get("lifeChapters") if isinstance(value.get("lifeChapters"), list) else []
        personality = value.get("personalityProfile") if isinstance(value.get("personalityProfile"), dict) else {}
        attention = (inner.get("attention") or {}).get("summary") if isinstance(inner.get("attention"), dict) else inner.get("attention")
        list_fields = ("learned", "preferences", "people", "places", "wants", "rules", "hopes", "unfinished", "episodes", "threads", "commitments", "anchors", "skills", "worldEvents")
        return {
            "schema": 1,
            "instanceId": self.instance_id,
            "updatedAt": float(value.get("updatedAt") or time.time()),
            "clientSeenAt": float(value.get("clientSeenAt") or time.time()),
            "lifeCycle": {
                "sequence": max(0, int(lifecycle.get("sequence") or 0)),
                "phase": self._clean_text(lifecycle.get("phase") or "resting", 24),
                "mode": self._clean_text(lifecycle.get("mode") or "idle", 24),
                "reason": self._clean_text(lifecycle.get("reason"), 180),
                "detail": self._clean_text(lifecycle.get("detail"), 220),
                "updatedAt": float(lifecycle.get("updatedAt") or 0),
                "history": [
                    {
                        "sequence": max(0, int(item.get("sequence") or 0)),
                        "phase": self._clean_text(item.get("phase") or "resting", 24),
                        "mode": self._clean_text(item.get("mode") or "idle", 24),
                        "reason": self._clean_text(item.get("reason"), 180),
                        "detail": self._clean_text(item.get("detail"), 220),
                        "t": float(item.get("t") or 0),
                        "eventId": max(0, int(item.get("eventId") or 0)),
                    }
                    for item in (lifecycle.get("history") or [])[-24:]
                    if isinstance(item, dict)
                ],
            },
            "causalTimeline": [
                {
                    "id": max(0, int(item.get("id") or 0)),
                    "t": float(item.get("t") or 0),
                    "kind": self._clean_text(item.get("kind") or "event", 40),
                    "text": self._clean_text(item.get("text"), 220),
                    "priority": max(1, min(3, int(item.get("priority") or 1))),
                    "parent": max(0, int(item.get("parent") or 0)) or None,
                    "root": max(0, int(item.get("root") or item.get("id") or 0)),
                    "depth": max(0, min(24, int(item.get("depth") or 0))),
                    "phase": self._clean_text(item.get("phase") or "resting", 24),
                    "source": self._clean_text(item.get("source") or "browser", 24),
                }
                for item in causal_timeline[-24:]
                if isinstance(item, dict) and self._clean_text(item.get("text"), 220)
            ],
            "memoryRecords": [
                {
                    "id": self._clean_text(item.get("id"), 48),
                    "text": self._clean_text(item.get("text"), 180),
                    "type": self._clean_text(item.get("type") or "episodic", 24),
                    "status": self._clean_text(item.get("status") or "confirmed", 16),
                    "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0))),
                    "observations": max(1, int(item.get("observations") or 1)),
                    "firstSeen": float(item.get("firstSeen") or 0),
                    "lastSeen": float(item.get("lastSeen") or 0),
                    "durationDays": max(0.0, min(3650.0, float(item.get("durationDays") or 0))),
                    "validFrom": float(item.get("validFrom") or item.get("firstSeen") or 0),
                    "validUntil": float(item.get("validUntil") or 0),
                    "supersededBy": self._clean_text(item.get("supersededBy"), 48),
                    "supersedes": self._clean_text(item.get("supersedes"), 48),
                    "replacementReason": self._clean_text(item.get("replacementReason"), 160),
                }
                for item in memory_records[-32:]
                if isinstance(item, dict) and self._clean_text(item.get("text"), 180)
            ],
            "memoryHistory": [
                {
                    "id": self._clean_text(item.get("id"), 48),
                    "text": self._clean_text(item.get("text"), 180),
                    "type": self._clean_text(item.get("type") or "episodic", 24),
                    "status": self._clean_text(item.get("status") or "outdated", 16),
                    "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0))),
                    "observations": max(1, int(item.get("observations") or 1)),
                    "validFrom": float(item.get("validFrom") or 0),
                    "validUntil": float(item.get("validUntil") or 0),
                    "supersededBy": self._clean_text(item.get("supersededBy"), 48),
                    "supersedes": self._clean_text(item.get("supersedes"), 48),
                    "replacementReason": self._clean_text(item.get("replacementReason"), 160),
                }
                for item in memory_history[-48:]
                if isinstance(item, dict) and self._clean_text(item.get("text"), 180)
            ],
            "memoryRecallHistory": [
                {
                    "text": self._clean_text(item.get("text"), 180),
                    "query": self._clean_text(item.get("query"), 140),
                    "at": float(item.get("at") or 0),
                    "channel": self._clean_text(item.get("channel") or "conversation", 24),
                    "outcome": self._clean_text(item.get("outcome") or "pending", 16),
                }
                for item in memory_recall_history[-24:]
                if isinstance(item, dict) and self._clean_text(item.get("text"), 180)
            ],
            "activeGoal": None if not goal else {
                "id": self._clean_text(goal.get("id"), 48),
                "kind": self._clean_text(goal.get("kind"), 32),
                "target": self._clean_text(goal.get("target"), 180),
                "status": self._clean_text(goal.get("status"), 100),
                "steps": max(0, int(goal.get("steps") or 0)),
                "maxSteps": max(1, int(goal.get("maxSteps") or 1)),
                "started": float(goal.get("started") or 0),
                "updatedAt": float(goal.get("updatedAt") or 0),
            },
            "taskPlan": {
                "status": self._clean_text(task_plan.get("status") or "idle", 80),
                "kind": self._clean_text(task_plan.get("kind"), 32),
                "target": self._clean_text(task_plan.get("target"), 180),
                "origin": self._clean_text(task_plan.get("origin"), 24),
                "current": max(0, int(task_plan.get("current") or 0)),
                "phase": self._clean_text(task_plan.get("phase"), 32),
                "lastAction": self._clean_text(task_plan.get("lastAction"), 100),
                "lastResult": self._clean_text(task_plan.get("lastResult"), 180),
                "blocked": self._clean_text(task_plan.get("blocked"), 140),
                "evidence": [self._clean_text(item, 180) for item in (task_plan.get("evidence") or []) if self._clean_text(item, 180)][-8:],
                "skillCursor": max(0, int(task_plan.get("skillCursor") or 0)),
                "skillOutcome": self._clean_text(task_plan.get("skillOutcome"), 180),
                "reviewRequestedAt": float(task_plan.get("reviewRequestedAt") or 0),
                "reviewCount": max(0, int(task_plan.get("reviewCount") or 0)),
                "lastResumedAt": float(task_plan.get("lastResumedAt") or 0),
                "resumeCount": max(0, int(task_plan.get("resumeCount") or 0)),
                "planSteps": [
                    {"i": max(1, int(step.get("i") or index + 1)), "text": self._clean_text(step.get("text"), 160), "status": self._clean_text(step.get("status") or "queued", 16)}
                    for index, step in enumerate((task_plan.get("planSteps") or [])[:8])
                    if isinstance(step, dict) and self._clean_text(step.get("text"), 160)
                ],
                "skillChain": [
                    {
                        "id": self._clean_text(skill.get("id"), 72),
                        "label": self._clean_text(skill.get("label") or skill.get("id"), 100),
                        "status": self._clean_text(skill.get("status") or "template", 16),
                        "steps": [self._clean_text(step, 90) for step in (skill.get("steps") or []) if self._clean_text(step, 90)][-8:],
                        "preconditions": [self._clean_text(step, 110) for step in (skill.get("preconditions") or []) if self._clean_text(step, 110)][-8:],
                        "expected": self._clean_text(skill.get("expected"), 160),
                        "fallback": self._clean_text(skill.get("fallback") or "stop and adapt", 160),
                        "attempts": max(0, int(skill.get("attempts") or 0)),
                        "successes": max(0, int(skill.get("successes") or 0)),
                        "lastOutcome": self._clean_text(skill.get("lastOutcome"), 160),
                    }
                    for skill in (task_plan.get("skillChain") or [])[:4]
                    if isinstance(skill, dict) and self._clean_text(skill.get("id"), 72)
                ],
            },
            "autonomyState": {
                "priority": self._clean_text(autonomy.get("priority") or "rest", 32),
                "need": self._clean_text(autonomy.get("need") or "none", 100),
                "reason": self._clean_text(autonomy.get("reason") or "no autonomous beat yet", 180),
                "evidence": self._clean_text(autonomy.get("evidence"), 220),
                "selectedAt": float(autonomy.get("selectedAt") or 0),
                "candidates": [
                    {
                        "id": self._clean_text(item.get("id"), 32),
                        "score": max(0.0, min(1.0, float(item.get("score") or 0))),
                        "reason": self._clean_text(item.get("reason"), 140),
                        "evidence": self._clean_text(item.get("evidence"), 160),
                    }
                    for item in (autonomy.get("candidates") or [])[:8]
                    if isinstance(item, dict) and self._clean_text(item.get("id"), 32)
                ],
            },
            "personalityProfile": {
                key: self._bounded_score(personality.get(key)) or 0.0
                for key in ("curiosity", "playfulness", "persistence", "sociability", "caution", "warmth")
            },
            "appraisalState": {
                key: max(0.0, min(1.0, float(appraisal.get(key) or 0)))
                for key in ("novelty", "agency", "progress", "control", "safety", "connection", "uncertainty")
            } | {
                "source": self._clean_text(appraisal.get("source") or "waking", 32),
                "reason": self._clean_text(appraisal.get("reason") or "nothing specific", 160),
                "at": float(appraisal.get("at") or 0),
            },
            "selfModel": {
                key: [self._clean_text(item, limit) for item in (self_model.get(key) or []) if self._clean_text(item, limit)][-size:]
                for key, limit, size in (("traits", 120, 8), ("chapters", 150, 8), ("hopes", 120, 6), ("uncertainties", 120, 6), ("unfinished", 120, 6))
            } | {
                "confidence": {
                    self._clean_text(key, 48): self._bounded_score(score)
                    for key, score in list((self_model.get("confidence") or {}).items())[-12:]
                    if self._clean_text(key, 48) and self._bounded_score(score) is not None
                }
            },
            "lifeChapters": [
                self._clean_text(item, 220)
                for item in life_chapters[-8:]
                if self._clean_text(item, 220)
            ],
            "relationshipState": {
                "warmth": self._bounded_score(relationship_state.get("warmth")),
                "trust": self._bounded_score(relationship_state.get("trust")),
                "familiarity": max(0, min(100, int(relationship_state.get("familiarity") or 0))),
                "bondSince": float(relationship_state.get("bondSince") or 0),
                "lastMeaningfulAt": float(relationship_state.get("lastMeaningfulAt") or 0),
                "style": self._clean_text(relationship_state.get("style") or "unknown", 100),
                "commitmentOutcomes": [
                    {
                        "text": self._clean_text(item.get("text"), 160),
                        "status": self._clean_text(item.get("status"), 16),
                        "at": float(item.get("at") or 0),
                    }
                    for item in (relationship_state.get("commitmentOutcomes") or [])[-8:]
                    if isinstance(item, dict) and self._clean_text(item.get("text"), 160)
                ],
                "openCommitments": [
                    {
                        "text": self._clean_text(item.get("text"), 160),
                        "createdAt": float(item.get("createdAt") or 0),
                        "updatedAt": float(item.get("updatedAt") or 0),
                        "durationDays": max(0.0, min(3650.0, float(item.get("durationDays") or 0))),
                    }
                    for item in (relationship_state.get("openCommitments") or [])[-6:]
                    if isinstance(item, dict) and self._clean_text(item.get("text"), 160)
                ],
            },
            "socialState": {
                "floor": self._clean_text(social_state.get("floor") or "none", 24),
                "intent": self._clean_text(social_state.get("intent") or "unknown", 32),
                "tone": self._clean_text(social_state.get("tone") or "neutral", 24),
                "repairNeeded": bool(social_state.get("repairNeeded")),
                "lastHumanAt": float(social_state.get("lastHumanAt") or 0),
                "lastXemoAt": float(social_state.get("lastXemoAt") or 0),
                "interrupted": max(0, min(1000, int(social_state.get("interrupted") or 0))),
                "autonomousSilenceUntil": max(0.0, float(social_state.get("autonomousSilenceUntil") or 0)),
                "lastBidOutcome": self._clean_text(social_state.get("lastBidOutcome") or "none", 16),
                "unansweredBids": max(0, min(100, int(social_state.get("unansweredBids") or 0))),
                "timing": {
                    "samples": max(0, min(1000, int((social_state.get("timing") or {}).get("samples") or 0))),
                    "engaged": max(0, min(1000, int((social_state.get("timing") or {}).get("engaged") or 0))),
                    "warm": max(0, min(1000, int((social_state.get("timing") or {}).get("warm") or 0))),
                    "correcting": max(0, min(1000, int((social_state.get("timing") or {}).get("correcting") or 0))),
                    "unanswered": max(0, min(1000, int((social_state.get("timing") or {}).get("unanswered") or 0))),
                    "interrupted": max(0, min(1000, int((social_state.get("timing") or {}).get("interrupted") or 0))),
                    "averageResponseMs": max(0.0, min(86400000.0, float((social_state.get("timing") or {}).get("averageResponseMs") or 0))),
                    "lastResponseMs": max(0.0, min(86400000.0, float((social_state.get("timing") or {}).get("lastResponseMs") or 0))),
                    "lastOutcome": self._clean_text((social_state.get("timing") or {}).get("lastOutcome") or "none", 16),
                    "updatedAt": float((social_state.get("timing") or {}).get("updatedAt") or 0),
                    "byKind": {
                        kind: {
                            "samples": max(0, min(100, int((((social_state.get("timing") or {}).get("byKind") or {}).get(kind) or {}).get("samples") or 0))),
                            "engaged": max(0, min(100, int((((social_state.get("timing") or {}).get("byKind") or {}).get(kind) or {}).get("engaged") or 0))),
                            "warm": max(0, min(100, int((((social_state.get("timing") or {}).get("byKind") or {}).get(kind) or {}).get("warm") or 0))),
                            "correcting": max(0, min(100, int((((social_state.get("timing") or {}).get("byKind") or {}).get(kind) or {}).get("correcting") or 0))),
                            "unanswered": max(0, min(100, int((((social_state.get("timing") or {}).get("byKind") or {}).get(kind) or {}).get("unanswered") or 0))),
                            "interrupted": max(0, min(100, int((((social_state.get("timing") or {}).get("byKind") or {}).get(kind) or {}).get("interrupted") or 0))),
                            "averageResponseMs": max(0.0, min(86400000.0, float((((social_state.get("timing") or {}).get("byKind") or {}).get(kind) or {}).get("averageResponseMs") or 0))),
                        }
                        for kind in ("speech", "question", "observation", "play", "feeling", "movement")
                    },
                },
                "strategies": [
                    {
                        "channel": self._clean_text(item.get("channel") or "speech", 16),
                        "tone": self._clean_text(item.get("tone") or "neutral", 16),
                        "samples": max(0, min(100, int(item.get("samples") or 0))),
                        "successes": max(0, min(100, int(item.get("successes") or 0))),
                        "cautions": max(0, min(100, int(item.get("cautions") or 0))),
                        "confidence": self._bounded_score(item.get("confidence")),
                        "lesson": self._clean_text(item.get("lesson"), 180),
                        "lastAt": float(item.get("lastAt") or 0),
                    }
                    for item in (social_state.get("strategies") or [])[-8:]
                    if isinstance(item, dict) and self._clean_text(item.get("channel") or "speech", 16)
                ],
            },
            "lifeRhythm": {
                "interests": [
                    {
                        "topic": self._clean_text(item.get("topic"), 140),
                        "count": max(1, min(24, int(item.get("count") or 1))),
                        "firstAt": float(item.get("firstAt") or 0),
                        "lastAt": float(item.get("lastAt") or 0),
                        "blocks": [self._clean_text(block, 16) for block in (item.get("blocks") or []) if self._clean_text(block, 16)][-4:],
                        "evidence": [self._clean_text(entry, 120) for entry in (item.get("evidence") or []) if self._clean_text(entry, 120)][-4:],
                    }
                    for item in (rhythm.get("interests") or [])[-6:]
                    if isinstance(item, dict) and self._clean_text(item.get("topic"), 140)
                ],
                "candidates": [
                    {
                        "topic": self._clean_text(item.get("topic"), 140),
                        "count": max(1, min(24, int(item.get("count") or 1))),
                        "firstAt": float(item.get("firstAt") or 0),
                        "lastAt": float(item.get("lastAt") or 0),
                        "blocks": [self._clean_text(block, 16) for block in (item.get("blocks") or []) if self._clean_text(block, 16)][-4:],
                        "evidence": [self._clean_text(entry, 120) for entry in (item.get("evidence") or []) if self._clean_text(entry, 120)][-4:],
                    }
                    for item in (rhythm.get("candidates") or [])[-8:]
                    if isinstance(item, dict) and self._clean_text(item.get("topic"), 140)
                ],
                "lastBlock": self._clean_text(rhythm.get("lastBlock"), 16),
                "updatedAt": float(rhythm.get("updatedAt") or 0),
                "dayPhase": self._clean_text(rhythm.get("dayPhase"), 16),
                "phaseSince": float(rhythm.get("phaseSince") or 0),
                "wakeCount": max(0, min(10000, int(rhythm.get("wakeCount") or 0))),
                "lastWakeAt": float(rhythm.get("lastWakeAt") or 0),
                "lastSleepAt": float(rhythm.get("lastSleepAt") or 0),
            },
            "alivenessMetrics": {
                key: max(0, min(1000000, int(aliveness.get(key) or 0)))
                for key in (
                    "autonomousBeats", "autonomousChoices", "autonomousNoops", "autonomousRepeatsBlocked",
                    "autonomousInstructionRejections", "autonomousRestChoices",
                    "autonomousBidsEngaged", "autonomousBidsUnanswered",
                    "correctionRepairs",
                    "humanInterruptions", "goalStarted", "goalCompleted", "goalResumed", "goalRevised", "goalFailed",
                    "bodyAttempts", "bodyVerified", "bodyInconclusive", "clarificationsAsked",
                    "memoryCandidatesCreated", "memoryCandidatesPromoted", "speechDuplicatesSuppressed", "brainRequests",
                )
            },
            "autonomyHistory": [
                {
                    "decisionId": self._clean_text(item.get("decisionId"), 80),
                    "choice": self._clean_text(item.get("choice"), 180),
                    "drive": self._clean_text(item.get("drive"), 32),
                    "need": self._clean_text(item.get("need"), 100),
                    "outcome": self._clean_text(item.get("outcome"), 160),
                    "memoryRefs": [self._clean_text(x, 140) for x in (item.get("memoryRefs") or []) if self._clean_text(x, 140)][-4:],
                    "strategyRefs": [self._clean_text(x, 160) for x in (item.get("strategyRefs") or []) if self._clean_text(x, 160)][-3:],
                    "reflectionRefs": [self._clean_text(x, 120) for x in (item.get("reflectionRefs") or []) if self._clean_text(x, 120)][-3:],
                    "actionOutcome": {
                        "action": self._clean_text((item.get("actionOutcome") or {}).get("action"), 100),
                        "status": self._clean_text((item.get("actionOutcome") or {}).get("status"), 16),
                        "verified": bool((item.get("actionOutcome") or {}).get("verified")),
                        "observed": self._clean_text((item.get("actionOutcome") or {}).get("observed"), 180),
                        "attemptId": self._clean_text((item.get("actionOutcome") or {}).get("attemptId"), 80),
                        "learning": self._clean_text((item.get("actionOutcome") or {}).get("learning"), 180),
                        "at": float((item.get("actionOutcome") or {}).get("at") or 0),
                    } if isinstance(item.get("actionOutcome"), dict) else None,
                    "personality": {
                        key: self._bounded_score((item.get("personality") or {}).get(key))
                        for key in ("curiosity", "playfulness", "persistence", "sociability", "caution", "warmth")
                    },
                    "traits": [self._clean_text(x, 120) for x in (item.get("traits") or [])[-6:] if self._clean_text(x, 120)],
                    "opportunity": {
                        "kind": self._clean_text((item.get("opportunity") or {}).get("kind") or "speech", 20),
                        "status": self._clean_text((item.get("opportunity") or {}).get("status") or "pending", 16),
                        "openedAt": float((item.get("opportunity") or {}).get("openedAt") or 0),
                        "resolvedAt": float((item.get("opportunity") or {}).get("resolvedAt") or 0),
                        "response": self._clean_text((item.get("opportunity") or {}).get("response"), 140),
                    } if isinstance(item.get("opportunity"), dict) else None,
                    "t": float(item.get("t") or 0),
                }
                for item in autonomy_history[-12:]
                if isinstance(item, dict) and self._clean_text(item.get("choice"), 180)
            ],
            "sessionHistory": [
                {
                    "id": self._clean_text(item.get("id"), 80),
                    "t": float(item.get("t") or 0),
                    "reason": self._clean_text(item.get("reason") or "checkpoint", 32),
                    "phase": self._clean_text(item.get("phase") or "resting", 24),
                    "mode": self._clean_text(item.get("mode") or "idle", 24),
                    "activeGoal": self._clean_text(item.get("activeGoal"), 140),
                    "goalStatus": self._clean_text(item.get("goalStatus"), 24),
                    "autonomy": self._clean_text(item.get("autonomy"), 160),
                    "drives": {
                        key: self._bounded_score((item.get("drives") or {}).get(key))
                        for key in ("social", "curiosity", "play", "expression", "energy", "frustration")
                    },
                    "projects": item.get("projects")[-6:] if isinstance(item.get("projects"), list) else [],
                    "memories": item.get("memories")[-10:] if isinstance(item.get("memories"), list) else [],
                    "relationship": item.get("relationship") if isinstance(item.get("relationship"), dict) else {},
                    "self": item.get("self") if isinstance(item.get("self"), dict) else {},
                    "personality": {
                        key: self._bounded_score((item.get("personality") or {}).get(key))
                        for key in ("curiosity", "playfulness", "persistence", "sociability", "caution", "warmth")
                    },
                    "causalKinds": [self._clean_text(x, 32) for x in (item.get("causalKinds") or [])[-16:] if self._clean_text(x, 32)],
                    "lifecycleSequence": max(0, int(item.get("lifecycleSequence") or 0)),
                }
                for item in session_history[-24:]
                if isinstance(item, dict) and self._clean_text(item.get("id"), 80)
            ],
            "returnReflection": None if not return_reflection else {
                "at": float(return_reflection.get("at") or 0),
                "awayDays": max(0.0, min(3650.0, float(return_reflection.get("awayDays") or 0))),
                "previousPhase": self._clean_text(return_reflection.get("previousPhase") or "resting", 24),
                "previousGoal": self._clean_text(return_reflection.get("previousGoal"), 140),
                "unfinishedProject": self._clean_text(return_reflection.get("unfinishedProject"), 120),
                "rememberedCount": max(0, min(48, int(return_reflection.get("rememberedCount") or 0))),
            },
            "lifeProjects": [
                {
                    "id": self._clean_text(item.get("id"), 64),
                    "title": self._clean_text(item.get("title"), 100),
                    "kind": self._clean_text(item.get("kind") or "adaptive", 32),
                    "status": self._clean_text(item.get("status") or "open", 32),
                    "origin": self._clean_text(item.get("origin") or "autonomous", 24),
                    "why": self._clean_text(item.get("why"), 140),
                    "nextStep": self._clean_text(item.get("nextStep"), 140),
                    "forecast": self._clean_text(item.get("forecast"), 160),
                    "reviewAt": float(item.get("reviewAt") or 0),
                    "lastReviewAt": float(item.get("lastReviewAt") or 0),
                    "reviewCount": max(0, min(99, int(item.get("reviewCount") or 0))),
                    "revisitCount": max(0, min(99, int(item.get("revisitCount") or 0))),
                    "lastReview": self._clean_text(item.get("lastReview"), 160),
                    "progress": max(0.0, min(1.0, float(item.get("progress") or 0))),
                    "attempts": max(0, int(item.get("attempts") or 0)),
                    "successes": max(0, int(item.get("successes") or 0)),
                    "createdAt": float(item.get("createdAt") or 0),
                    "updatedAt": float(item.get("updatedAt") or 0),
                    "ageDays": max(0.0, min(3650.0, float(item.get("ageDays") or 0))),
                    "idleDays": max(0.0, min(3650.0, float(item.get("idleDays") or 0))),
                }
                for item in projects[-6:]
                if isinstance(item, dict) and self._clean_text(item.get("title"), 100)
            ],
            "proceduralSkills": [
                {
                    "id": self._clean_text(item.get("id"), 72),
                    "label": self._clean_text(item.get("label") or item.get("id"), 100),
                    "kind": self._clean_text(item.get("kind") or "body", 32),
                    "status": self._clean_text(item.get("status") or "forming", 16),
                    "steps": [self._clean_text(step, 90) for step in (item.get("steps") or []) if self._clean_text(step, 90)][-6:],
                    "preconditions": [self._clean_text(step, 100) for step in (item.get("preconditions") or []) if self._clean_text(step, 100)][-6:],
                    "expected": self._clean_text(item.get("expected"), 160),
                    "fallback": self._clean_text(item.get("fallback") or "stop and gather evidence", 160),
                    "attempts": max(0, int(item.get("attempts") or 0)),
                    "successes": max(0, int(item.get("successes") or 0)),
                    "unresolved": max(0, int(item.get("unresolved") or 0)),
                    "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0))),
                    "lastOutcome": self._clean_text(item.get("lastOutcome"), 160),
                }
                for item in procedural_skills[-12:]
                if isinstance(item, dict) and self._clean_text(item.get("label") or item.get("id"), 100)
            ],
            "bodyEvidence": [
                {
                    "t": float(item.get("t") or 0),
                    "attemptId": self._clean_text(item.get("attemptId"), 80),
                    "action": self._clean_text(item.get("action") or "unknown", 100),
                    "channel": self._clean_text(item.get("channel") or "navigation", 32),
                    "contextKey": self._clean_text(item.get("contextKey") or "unscoped", 120),
                    "prediction": self._clean_text(item.get("prediction"), 160),
                    "observed": self._clean_text(item.get("observed"), 180),
                    "verdict": self._clean_text(item.get("verdict") or "unresolved", 16),
                    "predictionMatched": None if item.get("predictionMatched") is None else bool(item.get("predictionMatched")),
                    "evidenceConfidence": max(0.0, min(1.0, float(item.get("evidenceConfidence") or 0))),
                    "acknowledged": None if item.get("acknowledged") is None else bool(item.get("acknowledged")),
                }
                for item in body_evidence[-12:]
                if isinstance(item, dict) and self._clean_text(item.get("action"), 100)
            ],
            "bodyPredictionLedger": [
                {
                    "action": self._clean_text(item.get("action") or "unknown", 100),
                    "contextKey": self._clean_text(item.get("contextKey") or "unscoped", 120),
                    "prediction": self._clean_text(item.get("prediction"), 160),
                    "observed": self._clean_text(item.get("observed"), 180),
                    "verdict": self._clean_text(item.get("verdict") or "unresolved", 16),
                    "predictionMatched": None if item.get("predictionMatched") is None else bool(item.get("predictionMatched")),
                    "consistency": None if item.get("consistency") is None else max(0.0, min(1.0, float(item.get("consistency") or 0))),
                    "evidenceConfidence": max(0.0, min(1.0, float(item.get("evidenceConfidence") or 0))),
                    "at": float(item.get("at") or 0),
                }
                for item in body_prediction_ledger[-16:]
                if isinstance(item, dict) and self._clean_text(item.get("action"), 100)
            ],
            "memoryCandidates": [
                {
                    "id": self._clean_text(item.get("id"), 64),
                    "kind": self._clean_text(item.get("kind") or "semantic", 24),
                    "text": self._clean_text(item.get("text"), 220),
                    "evidence": [self._clean_text(x, 160) for x in (item.get("evidence") or []) if self._clean_text(x, 160)][-8:],
                    "status": self._clean_text(item.get("status") or "pending", 16),
                    "createdAt": float(item.get("createdAt") or 0),
                    "firstSeen": float(item.get("firstSeen") or item.get("createdAt") or 0),
                    "lastSeen": float(item.get("lastSeen") or item.get("createdAt") or 0),
                    "observations": max(1, int(item.get("observations") or 1)),
                    "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0.35))),
                    "source": self._clean_text(item.get("source") or "service", 24),
                }
                for item in memory_candidates[-12:]
                if isinstance(item, dict) and self._clean_text(item.get("text"), 220)
            ],
            "lastDream": float(value.get("lastDream") or 0),
            "innerState": {
                "drives": {
                    key: max(0.0, min(1.0, float((inner.get("drives") or {}).get(key) or 0)))
                    for key in ("social", "curiosity", "play", "expression", "energy", "frustration")
                },
                "needs": {
                    key: max(0.0, min(1.0, float((inner.get("needs") or {}).get(key) or 0)))
                    for key in ("hunger", "thirst", "comfort", "connection", "sleep")
                },
                "homeostasis": {
                    "lastActivityAt": max(0.0, float(homeostasis.get("lastActivityAt") or 0)),
                    "lastActivityKind": self._clean_text(homeostasis.get("lastActivityKind"), 32),
                    "lastHomeostasisAt": max(0.0, float(homeostasis.get("lastHomeostasisAt") or 0)),
                    "revision": max(0, int(homeostasis.get("revision") or 0)),
                },
                "attention": self._clean_text(attention, 220),
                "updatedAt": float(inner.get("updatedAt") or 0),
            },
            "coordinator": {
                "enabled": bool(coordinator.get("enabled")),
                "tick": max(0, int(coordinator.get("tick") or 0)),
                "lastTickAt": float(coordinator.get("lastTickAt") or 0),
                "nextWakeAt": float(coordinator.get("nextWakeAt") or 0),
                "lastInitiativeAt": float(coordinator.get("lastInitiativeAt") or 0),
                "lastError": self._clean_text(coordinator.get("lastError"), 180),
                "lastDecision": self._normalise_decision(coordinator.get("lastDecision")),
                "decisionHistory": [
                    self._normalise_decision(item)
                    for item in (coordinator.get("decisionHistory") or [])[-12:]
                    if isinstance(item, dict) and self._normalise_decision(item).get("id")
                ],
            },
            "goalReview": None if not review else {
                "goalId": self._clean_text(review.get("goalId"), 48),
                "status": self._clean_text(review.get("status") or "none", 16).lower() if self._clean_text(review.get("status") or "none", 16).lower() in {"none", "continue", "revise", "pause", "drop"} else "none",
                "reason": self._clean_text(review.get("reason"), 220),
                "nextFocus": self._clean_text(review.get("nextFocus"), 180),
                "at": float(review.get("at") or 0),
                "source": self._clean_text(review.get("source") or "service", 24),
            },
            "pendingGoal": None if not pending_goal else {
                "id": self._clean_text(pending_goal.get("id"), 64),
                "kind": self._clean_text(pending_goal.get("kind") or "adaptive", 32),
                "target": self._clean_text(pending_goal.get("target"), 180),
                "reason": self._clean_text(pending_goal.get("reason"), 220),
                "decisionId": self._clean_text(pending_goal.get("decisionId"), 72),
                "createdAt": float(pending_goal.get("createdAt") or 0),
                "expiresAt": float(pending_goal.get("expiresAt") or 0),
                "claimedAt": float(pending_goal.get("claimedAt") or 0),
                "completedAt": float(pending_goal.get("completedAt") or 0),
                "status": self._clean_text(pending_goal.get("status") or "pending", 24),
                "outcome": self._clean_text(pending_goal.get("outcome"), 24),
                "result": self._clean_text(pending_goal.get("result"), 220),
            },
            "pendingInitiative": None if not initiative else {
                "id": self._clean_text(initiative.get("id"), 64),
                "text": self._clean_text(initiative.get("text"), 220),
                "emotion": self._clean_text(initiative.get("emotion") or "curious", 32),
                "kind": self._clean_text(initiative.get("kind") or "social", 32),
                "grounding": self._clean_text(initiative.get("grounding"), 180),
                "decisionId": self._clean_text(initiative.get("decisionId"), 72),
                "createdAt": float(initiative.get("createdAt") or 0),
                "expiresAt": float(initiative.get("expiresAt") or 0),
                "claimedAt": float(initiative.get("claimedAt") or 0),
                "completedAt": float(initiative.get("completedAt") or 0),
                "status": self._clean_text(initiative.get("status") or "pending", 24),
                "outcome": self._clean_text(initiative.get("outcome"), 32),
                "result": self._clean_text(initiative.get("result"), 220),
                "evidence": [self._clean_text(item, 160) for item in (initiative.get("evidence") or []) if self._clean_text(item, 160)][-4:],
            },
            "lifeEvents": [
                {
                    "id": self._clean_text(event.get("id"), 64),
                    "kind": self._clean_text(event.get("kind") or "continuity", 32),
                    "detail": self._clean_text(event.get("detail"), 220),
                    "grounding": self._clean_text(event.get("grounding"), 180),
                    "at": float(event.get("at") or 0),
                    "source": self._clean_text(event.get("source") or "service", 24),
                    "parent": self._clean_text(event.get("parent"), 64),
                    "root": self._clean_text(event.get("root") or event.get("id"), 64),
                    "depth": max(0, min(24, int(event.get("depth") or 0))),
                    "phase": self._clean_text(event.get("phase") or "resting", 24),
                }
                for event in events[-48:]
                if isinstance(event, dict) and self._clean_text(event.get("detail"), 220)
            ],
            "reflections": [
                {
                    "id": self._clean_text(reflection.get("id"), 64),
                    "text": self._clean_text(reflection.get("text"), 260),
                    "kind": self._clean_text(reflection.get("kind") or "reflection", 32),
                    "grounding": self._clean_text(reflection.get("grounding"), 180),
                    "at": float(reflection.get("at") or 0),
                    "source": self._clean_text(reflection.get("source") or "service", 24),
                }
                for reflection in reflections[-24:]
                if isinstance(reflection, dict) and self._clean_text(reflection.get("text"), 260)
            ],
            "privateActivities": [
                {
                    "id": self._clean_text(item.get("id"), 72),
                    "activity": self._clean_text(item.get("activity"), 32),
                    "grounding": self._clean_text(item.get("grounding"), 180),
                    "result": self._clean_text(item.get("result"), 180),
                    "decisionId": self._clean_text(item.get("decisionId"), 72),
                    "at": float(item.get("at") or 0),
                    "source": self._clean_text(item.get("source") or "service", 24),
                }
                for item in private_activities[-24:]
                if isinstance(item, dict) and self._clean_text(item.get("activity"), 32)
            ],
            "memoryContext": {
                **{
                    field: [self._clean_text(item, 160) for item in memory.get(field, []) if self._clean_text(item, 160)][-8:]
                    for field in list_fields
                    if isinstance(memory.get(field), list)
                },
                "acquaintances": [
                    {
                        "name": self._clean_text(item.get("name"), 48),
                        "role": self._clean_text(item.get("role") or "acquaintance", 60),
                        "familiarity": max(0, min(100, int(item.get("familiarity") or 0))),
                        "interactions": max(0, int(item.get("interactions") or 0)),
                        "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0))),
                        "interactionStyle": self._clean_text(item.get("interactionStyle") or "unknown", 100),
                        "lastInteraction": self._clean_text(item.get("lastInteraction"), 160),
                        "boundaries": [self._clean_text(value, 120) for value in (item.get("boundaries") or []) if self._clean_text(value, 120)][-6:],
                        "notes": [self._clean_text(value, 140) for value in (item.get("notes") or []) if self._clean_text(value, 140)][-8:],
                        "threads": [self._clean_text(value, 140) for value in (item.get("threads") or []) if self._clean_text(value, 140)][-6:],
                    }
                    for item in (memory.get("acquaintances") or [])[-8:]
                    if isinstance(item, dict) and self._clean_text(item.get("name"), 48)
                ],
                "worldObjects": [
                    {
                        "id": self._clean_text(item.get("id"), 48),
                        "label": self._clean_text(item.get("label"), 80),
                        "aliases": [self._clean_text(alias, 60) for alias in (item.get("aliases") or []) if self._clean_text(alias, 60)][-3:],
                        "observedLabels": [self._clean_text(label, 60) for label in (item.get("observedLabels") or []) if self._clean_text(label, 60)][-4:],
                        "source": self._clean_text(item.get("source") or "local-object-sense", 32),
                        "confidence": max(0.0, min(1.0, float(item.get("confidence") or 0))),
                        "identityStatus": self._clean_text(item.get("identityStatus") or "provisional", 16),
                        "identityConfidence": max(0.0, min(1.0, float(item.get("identityConfidence") or 0))),
                        "sightings": max(0, int(item.get("sightings") or 0)),
                        "lastChange": self._clean_text(item.get("lastChange"), 80),
                    }
                    for item in (memory.get("worldObjects") or [])[-12:]
                    if isinstance(item, dict) and self._clean_text(item.get("label"), 80)
                ],
                "familiarScene": {
                    "objects": [self._clean_text(item, 60) for item in (memory.get("familiarScene") or {}).get("objects", []) if self._clean_text(item, 60)][-8:],
                    "visits": max(0, int((memory.get("familiarScene") or {}).get("visits") or 0)),
                    "lastVisitAt": float((memory.get("familiarScene") or {}).get("lastVisitAt") or 0),
                    "expectedObjects": [self._clean_text(item, 60) for item in (memory.get("familiarScene") or {}).get("expectedObjects", []) if self._clean_text(item, 60)][-8:],
                    "predictionMatched": None if (memory.get("familiarScene") or {}).get("predictionMatched") is None else bool((memory.get("familiarScene") or {}).get("predictionMatched")),
                    "predictionAttempts": max(0, min(99, int((memory.get("familiarScene") or {}).get("predictionAttempts") or 0))),
                    "stability": None if (memory.get("familiarScene") or {}).get("stability") is None else max(0.0, min(1.0, float((memory.get("familiarScene") or {}).get("stability") or 0))),
                    "lastPredictionObserved": [self._clean_text(item, 60) for item in (memory.get("familiarScene") or {}).get("lastPredictionObserved", []) if self._clean_text(item, 60)][-8:],
                },
                "socialEpisodes": [
                    {
                        "t": float(item.get("t") or 0),
                        "kind": self._clean_text(item.get("kind") or "shared moment", 32),
                        "actor": self._clean_text(item.get("actor") or "shared", 16),
                        "subject": self._clean_text(item.get("subject") or "my person", 64),
                        "text": self._clean_text(item.get("text"), 180),
                        "change": self._clean_text(item.get("change"), 140),
                        "eventId": max(0, int(item.get("eventId") or 0)),
                        "confidence": max(0.0, min(1.0, float(item.get("confidence") or .5))),
                    }
                    for item in (memory.get("socialEpisodes") or [])[-12:]
                    if isinstance(item, dict) and self._clean_text(item.get("text"), 180)
                ],
                "lifeEpisodes": [
                    {
                        "id": self._clean_text(item.get("id"), 72),
                        "startedAt": float(item.get("startedAt") or 0),
                        "endedAt": float(item.get("endedAt") or 0),
                        "kind": self._clean_text(item.get("kind") or "shared moment", 32),
                        "subject": self._clean_text(item.get("subject") or "shared world", 80),
                        "entities": [self._clean_text(x, 60) for x in (item.get("entities") or []) if self._clean_text(x, 60)][-8:],
                        "trigger": self._clean_text(item.get("trigger"), 180),
                        "response": self._clean_text(item.get("response"), 180),
                        "action": self._clean_text(item.get("action"), 100),
                        "outcome": self._clean_text(item.get("outcome"), 180),
                        "verified": None if item.get("verified") is None else bool(item.get("verified")),
                        "attemptId": self._clean_text(item.get("attemptId"), 80),
                        "lesson": self._clean_text(item.get("lesson"), 160),
                        "emotion": self._clean_text(item.get("emotion"), 32),
                        "status": self._clean_text(item.get("status") or "shared", 16),
                        "confidence": max(0.0, min(1.0, float(item.get("confidence") or .5))),
                        "eventIds": [max(0, int(x or 0)) for x in (item.get("eventIds") or [])][-6:],
                    }
                    for item in (memory.get("lifeEpisodes") or [])[-12:]
                    if isinstance(item, dict) and self._clean_text(item.get("trigger"), 180)
                ],
                "commitmentHistory": [
                    {
                        "text": self._clean_text(item.get("text"), 180),
                        "status": self._clean_text(item.get("status") or "open", 16),
                        "reason": self._clean_text(item.get("reason"), 160),
                        "createdAt": float(item.get("createdAt") or 0),
                        "updatedAt": float(item.get("updatedAt") or 0),
                    }
                    for item in (memory.get("commitmentHistory") or [])[-12:]
                    if isinstance(item, dict) and self._clean_text(item.get("text"), 180)
                ],
                "updatedAt": float(memory.get("updatedAt") or 0),
            },
        }

    def _read(self):
        try:
            return self._normalise(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return self._normalise({})

    def _advance_homeostasis(self, value, now=None):
        """Advance private bounded state while the browser is away.

        This changes priorities, not the world model: no sensor observation,
        physical action, or human response is invented by the service.
        """
        value = value if isinstance(value, dict) else {}
        now = float(now or time.time())
        inner = value.get("innerState") if isinstance(value.get("innerState"), dict) else {}
        updated = float(inner.get("updatedAt") or now)
        elapsed = max(0.0, min(1440.0, (now - updated) / 60.0))
        if elapsed <= 0:
            return value
        drives = inner.get("drives") if isinstance(inner.get("drives"), dict) else {}
        needs = inner.get("needs") if isinstance(inner.get("needs"), dict) else {}
        homeostasis = inner.get("homeostasis") if isinstance(inner.get("homeostasis"), dict) else {}
        clamp = lambda x: max(0.0, min(1.0, float(x or 0)))
        for key in ("social", "curiosity", "play", "expression", "energy", "frustration"):
            drives[key] = clamp(drives.get(key))
        for key in ("hunger", "thirst", "comfort", "connection", "sleep"):
            needs[key] = clamp(needs.get(key))
        last_activity = float(homeostasis.get("lastActivityAt") or 0) / 1000.0
        active = last_activity > 0 and now - last_activity < 90.0
        active_goal = value.get("activeGoal") if isinstance(value.get("activeGoal"), dict) else {}
        resting = not active and active_goal.get("status") != "active"
        social_state = value.get("socialState") if isinstance(value.get("socialState"), dict) else {}
        human_age = now - float(social_state.get("lastHumanAt") or 0)
        quiet = max(0.0, min(1.0, (now - last_activity) / 900.0)) if last_activity else 1.0
        needs["hunger"] = clamp(needs["hunger"] + elapsed * .0032)
        needs["thirst"] = clamp(needs["thirst"] + elapsed * .0046)
        needs["comfort"] = clamp(needs["comfort"] + elapsed * (.0024 if human_age > 180 else .0007))
        needs["connection"] = clamp(needs["connection"] + elapsed * (.0032 if human_age > 120 else .0005))
        if active:
            drives["energy"] = clamp(drives["energy"] - elapsed * .0028)
            needs["sleep"] = clamp(needs["sleep"] + elapsed * .0007)
        elif resting:
            drives["energy"] = clamp(drives["energy"] + elapsed * .0011)
            needs["sleep"] = clamp(needs["sleep"] - elapsed * .0007)
        drives["social"] = clamp(drives["social"] + elapsed * (.00018 + needs["connection"] * .00042))
        drives["expression"] = clamp(drives["expression"] + elapsed * (.00012 + quiet * .00018))
        drives["curiosity"] = clamp(drives["curiosity"] + elapsed * (.0001 + quiet * .00016))
        drives["play"] = clamp(drives["play"] + elapsed * (.00006 + quiet * .0001))
        drives["frustration"] = clamp(drives["frustration"] - elapsed * .00055)
        homeostasis["lastHomeostasisAt"] = now * 1000
        homeostasis["revision"] = max(0, int(homeostasis.get("revision") or 0)) + 1
        inner.update({"drives": drives, "needs": needs, "homeostasis": homeostasis, "updatedAt": now})
        value["innerState"] = inner
        return value

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))

    def update(self, value):
        with self.lock:
            value = value if isinstance(value, dict) else {}
            merged = dict(self.state)
            merged.update(value)
            merged["instanceId"] = self.instance_id
            if "memoryCandidates" in value:
                existing = {item.get("id"): item for item in (self.state.get("memoryCandidates") or []) if isinstance(item, dict) and item.get("id")}
                incoming = {item.get("id"): item for item in (value.get("memoryCandidates") or []) if isinstance(item, dict) and item.get("id")}
                merged["memoryCandidates"] = list({**existing, **incoming}.values())[-12:]
            else:
                merged["memoryCandidates"] = self.state.get("memoryCandidates")
            for key in ("lifeCycle", "activeGoal", "taskPlan", "innerState", "autonomyState", "appraisalState", "selfModel", "lifeChapters", "relationshipState", "socialState", "lifeRhythm", "alivenessMetrics", "autonomyHistory", "sessionHistory", "returnReflection", "memoryHistory", "memoryRecallHistory", "lifeProjects", "proceduralSkills", "bodyEvidence", "bodyPredictionLedger", "coordinator", "goalReview", "pendingGoal", "pendingInitiative", "lifeEvents", "reflections", "privateActivities"):
                if key not in value:
                    merged[key] = self.state.get(key)
            incoming = self._advance_homeostasis(self._normalise(merged))
            current_sequence = int(self.state.get("lifeCycle", {}).get("sequence") or 0)
            incoming_sequence = int(incoming.get("lifeCycle", {}).get("sequence") or 0)
            if incoming_sequence < current_sequence:
                incoming["lifeCycle"] = self.state["lifeCycle"]
            self.state = incoming
            self._write()
            return self.snapshot()

    def heartbeat(self, enabled=False, next_wake_at=0, error=""):
        with self.lock:
            current = self.state.get("coordinator") or {}
            current.update({
                "enabled": bool(enabled),
                "tick": int(current.get("tick") or 0) + 1,
                "lastTickAt": time.time(),
                "nextWakeAt": float(next_wake_at or current.get("nextWakeAt") or 0),
                "lastInitiativeAt": float(current.get("lastInitiativeAt") or 0),
                "lastError": self._clean_text(error, 180),
            })
            merged = dict(self.state)
            merged["coordinator"] = current
            self.state = self._advance_homeostasis(self._normalise(merged))
            self._write()
            return self.snapshot()

    def _normalise_decision(self, value):
        value = value if isinstance(value, dict) else {}
        alternatives = []
        for item in (value.get("alternatives") or [])[:6]:
            if not isinstance(item, dict):
                continue
            label = self._clean_text(item.get("label"), 64)
            if label:
                alternatives.append({
                    "label": label,
                    "score": max(0.0, min(1.0, float(item.get("score") or 0))),
                    "reason": self._clean_text(item.get("reason"), 120),
                })
        return {
            "id": self._clean_text(value.get("id"), 72),
            "choice": self._clean_text(value.get("choice") or "rest", 64),
            "need": self._clean_text(value.get("need"), 140),
            "reason": self._clean_text(value.get("reason"), 220),
            "evidence": self._clean_text(value.get("evidence"), 220),
            "prediction": self._clean_text(value.get("prediction"), 180),
            "confidence": max(0.0, min(1.0, float(value.get("confidence") or 0))),
            "outcome": self._clean_text(value.get("outcome") or "pending", 24),
            "result": self._clean_text(value.get("result"), 180),
            "at": float(value.get("at") or 0),
            "alternatives": alternatives,
        }

    def record_decision(self, decision, outcome="pending"):
        with self.lock:
            now = time.time()
            item = dict(decision if isinstance(decision, dict) else {})
            item.setdefault("id", f"decision-{int(now * 1000)}")
            item["at"] = now
            item["outcome"] = outcome or item.get("outcome") or "pending"
            item = self._normalise_decision(item)
            current = self.state.get("coordinator") or {}
            history = [*(current.get("decisionHistory") or []), item][-12:]
            merged = dict(self.state)
            merged["coordinator"] = {**current, "lastDecision": item, "decisionHistory": history}
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": item["id"], "kind": "autonomy-decision", "detail": f"{item['choice']}: {item['reason']}", "at": now, "source": "service", "root": item["id"], "phase": "thinking"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def complete_decision(self, decision_id, outcome, result=""):
        with self.lock:
            current = self.state.get("coordinator") or {}
            target = current.get("lastDecision") or {}
            if not decision_id or target.get("id") != str(decision_id):
                return self.snapshot()
            target = {**target, "outcome": self._clean_text(outcome or "observed", 24), "result": self._clean_text(result, 180), "at": time.time()}
            history = [target if item.get("id") == target["id"] else item for item in (current.get("decisionHistory") or [])]
            merged = dict(self.state)
            merged["coordinator"] = {**current, "lastDecision": target, "decisionHistory": history}
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": f"{target['id']}-outcome", "kind": "decision-outcome", "detail": result or target.get("outcome"), "at": target["at"], "source": "service", "parent": target["id"], "root": target["id"], "depth": 1, "phase": "learning"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def create_initiative(self, text, emotion="curious", kind="social", grounding="", decision_id=""):
        with self.lock:
            now = time.time()
            current = self.state.get("coordinator") or {}
            merged = dict(self.state)
            initiative_id = f"initiative-{int(now * 1000)}"
            merged["pendingInitiative"] = {
                "id": initiative_id,
                "text": text,
                "emotion": emotion,
                "kind": kind,
                "grounding": grounding,
                "decisionId": self._clean_text(decision_id, 72),
                "createdAt": now,
                "expiresAt": now + 86400,
                "status": "pending",
            }
            merged["coordinator"] = {
                **current,
                "lastInitiativeAt": now,
                "lastError": "",
            }
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": initiative_id, "kind": "initiative-created", "detail": text, "grounding": grounding, "at": now, "source": "service", "parent": self._clean_text(decision_id, 72), "root": self._clean_text(decision_id or initiative_id, 72), "depth": 1 if decision_id else 0, "phase": "acting"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def record_reflection(self, text, kind="reflection", grounding="", decision_id=""):
        with self.lock:
            now = time.time()
            reflection_id = f"reflection-{int(now * 1000)}"
            merged = dict(self.state)
            merged["reflections"] = [
                *(self.state.get("reflections") or []),
                {"id": reflection_id, "text": text, "kind": kind, "grounding": grounding, "at": now, "source": "service"},
            ]
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": reflection_id, "kind": "reflection-recorded", "detail": text, "at": now, "source": "service", "parent": self._clean_text(decision_id, 72), "root": self._clean_text(decision_id or reflection_id, 72), "depth": 1 if decision_id else 0, "phase": "learning"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def record_private_activity(self, activity, grounding="", result="", decision_id=""):
        with self.lock:
            now = time.time()
            item = {
                "id": f"activity-{int(now * 1000)}",
                "activity": self._clean_text(activity, 32),
                "grounding": self._clean_text(grounding, 180),
                "result": self._clean_text(result, 180),
                "decisionId": self._clean_text(decision_id, 72),
                "at": now,
                "source": "service",
            }
            if not item["activity"]:
                return self.snapshot()
            merged = dict(self.state)
            merged["privateActivities"] = [*(self.state.get("privateActivities") or []), item]
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": item["id"], "kind": "private-activity", "detail": item["activity"], "grounding": item["grounding"], "at": now, "source": "service", "parent": item["decisionId"], "root": item["decisionId"] or item["id"], "depth": 1 if item["decisionId"] else 0, "phase": "learning"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def record_goal_review(self, goal_id, status, reason="", next_focus=""):
        with self.lock:
            now = time.time()
            review = {
                "goalId": goal_id,
                "status": status,
                "reason": reason,
                "nextFocus": next_focus,
                "at": now,
                "source": "service",
            }
            merged = dict(self.state)
            merged["goalReview"] = review
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": f"goal-review-{int(now * 1000)}", "kind": "goal-reviewed", "detail": f"{status}: {reason or 'no reason recorded'}", "at": now, "source": "service"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def record_memory_candidate(self, kind, text, evidence=None):
        with self.lock:
            now = time.time()
            kind = self._clean_text(kind or "semantic", 24).lower()
            text = self._clean_text(text, 220)
            evidence = [self._clean_text(item, 160) for item in (evidence or []) if self._clean_text(item, 160)]
            candidates = list(self.state.get("memoryCandidates") or [])
            match = next((item for item in reversed(candidates)
                          if item.get("status") == "pending" and item.get("kind") == kind
                          and self._memory_similarity(item.get("text"), text) >= .72), None)
            if match:
                prior_evidence = list(match.get("evidence") or [])
                merged_evidence = list(dict.fromkeys(prior_evidence + evidence))[-8:]
                observations = max(1, int(match.get("observations") or 1)) + 1
                match.update({
                    "evidence": merged_evidence,
                    "observations": min(12, observations),
                    "confidence": min(.95, max(float(match.get("confidence") or .35), .45 + observations * .045)),
                    "lastSeen": now,
                    "source": "service-consolidated",
                })
                candidate_id = match.get("id")
                event_kind = "memory-candidate-consolidated"
            else:
                candidate_id = f"memory-candidate-{int(now * 1000)}"
                candidates.append({
                    "id": candidate_id,
                    "kind": kind,
                    "text": text,
                    "evidence": evidence[-8:],
                    "observations": 1,
                    "confidence": .35,
                    "firstSeen": now,
                    "lastSeen": now,
                    "status": "pending",
                    "createdAt": now,
                    "source": "service",
                })
                event_kind = "memory-candidate"
            candidate = {
                "id": candidate_id,
                "kind": kind,
                "text": text,
                "evidence": evidence,
                "status": "pending",
                "createdAt": now,
                "source": "service",
            }
            merged = dict(self.state)
            if match is None:
                merged["memoryCandidates"] = candidates
            else:
                merged["memoryCandidates"] = candidates
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": f"{event_kind}-{int(now * 1000)}", "kind": event_kind, "detail": text, "at": now, "source": "service"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def create_goal_proposal(self, kind, target, reason="", decision_id=""):
        with self.lock:
            now = time.time()
            goal_id = f"proposal-{int(now * 1000)}"
            merged = dict(self.state)
            merged["pendingGoal"] = {
                "id": goal_id,
                "kind": kind,
                "target": target,
                "reason": reason,
                "decisionId": self._clean_text(decision_id, 72),
                "createdAt": now,
                "expiresAt": now + 86400,
                "status": "pending",
            }
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": goal_id, "kind": "goal-proposed", "detail": target, "at": now, "source": "service", "parent": self._clean_text(decision_id, 72), "root": self._clean_text(decision_id or goal_id, 72), "depth": 1 if decision_id else 0, "phase": "planning"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def claim_goal_proposal(self, proposal_id):
        with self.lock:
            proposal = self.state.get("pendingGoal")
            if not proposal or proposal.get("status") != "pending" or proposal.get("id") != str(proposal_id):
                return None
            if float(proposal.get("expiresAt") or 0) and float(proposal.get("expiresAt")) < time.time():
                return None
            merged = dict(self.state)
            merged["pendingGoal"] = {**proposal, "status": "claimed", "claimedAt": time.time()}
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": f"claim-{proposal.get('id')}", "kind": "goal-proposal-claimed", "detail": proposal.get("target"), "at": time.time(), "source": "browser"},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def complete_goal_proposal(self, proposal_id, outcome, result=""):
        with self.lock:
            proposal = self.state.get("pendingGoal")
            allowed = {"started", "completed", "paused", "stopped", "failed", "expired"}
            outcome = self._clean_text(outcome or "", 24).lower()
            if outcome not in allowed or not proposal or proposal.get("id") != str(proposal_id) or proposal.get("status") not in {"claimed", "active"}:
                return None
            now = time.time()
            result = self._clean_text(result, 220)
            merged = dict(self.state)
            merged["pendingGoal"] = {**proposal, "status": "active" if outcome == "started" else "completed", "outcome": outcome, "result": result, "completedAt": 0 if outcome == "started" else now}
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": f"goal-outcome-{proposal.get('id')}", "kind": f"goal-{outcome}", "detail": result or proposal.get("target"), "at": now, "source": "browser", "parent": proposal.get("id")},
            ]
            self.state = self._normalise(merged)
            self._write()
            if proposal.get("decisionId"):
                return self.complete_decision(proposal.get("decisionId"), outcome, result)
            return self.snapshot()

    def claim_initiative(self, initiative_id):
        with self.lock:
            initiative = self.state.get("pendingInitiative")
            if not initiative or initiative.get("status") != "pending" or initiative.get("id") != str(initiative_id):
                return None
            if float(initiative.get("expiresAt") or 0) and float(initiative.get("expiresAt")) < time.time():
                return None
            merged = dict(self.state)
            now = time.time()
            merged["pendingInitiative"] = {**initiative, "status": "claimed", "claimedAt": now}
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": f"claim-{initiative.get('id')}", "kind": "initiative-claimed", "detail": initiative.get("text"), "at": now, "source": "browser", "parent": initiative.get("id")},
            ]
            self.state = self._normalise(merged)
            self._write()
            return self.snapshot()

    def complete_initiative(self, initiative_id, outcome, result="", evidence=None):
        with self.lock:
            initiative = self.state.get("pendingInitiative")
            allowed = {"delivered", "failed", "skipped", "expired"}
            outcome = self._clean_text(outcome or "", 32).lower()
            if outcome not in allowed or not initiative or initiative.get("id") != str(initiative_id) or initiative.get("status") != "claimed":
                return None
            now = time.time()
            result = self._clean_text(result, 220)
            evidence = [self._clean_text(item, 160) for item in (evidence or []) if self._clean_text(item, 160)][-4:]
            merged = dict(self.state)
            merged["pendingInitiative"] = {**initiative, "status": "completed", "outcome": outcome, "result": result, "evidence": evidence, "completedAt": now}
            merged["lifeEvents"] = [
                *(self.state.get("lifeEvents") or []),
                {"id": f"outcome-{initiative.get('id')}", "kind": f"initiative-{outcome}", "detail": result or initiative.get("text"), "at": now, "source": "browser", "parent": initiative.get("id")},
            ]
            self.state = self._normalise(merged)
            self._write()
            if initiative.get("decisionId"):
                return self.complete_decision(initiative.get("decisionId"), outcome, result)
            return self.snapshot()

    def _write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        temporary.replace(self.path)
