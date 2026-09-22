"""Bounded background continuity coordinator for one XEMO instance.

This process may choose a queued social initiative, but it never speaks,
opens sensors, or drives the body. The browser remains the only executor for
those capabilities and must claim an initiative before presenting it.
"""

import json
import re
import threading
import time
import uuid


_TECHNICAL = re.compile(
    r"\b(?:json|parser|sensor|telemetry|relay|http|model|prompt|autonomous|debug|api|error)\b",
    re.IGNORECASE,
)
_PRIVATE_ACTIVITIES = {"reflect", "revisit-memory", "review-goal", "plan-next-step", "consolidate", "rest"}
_UNAVAILABLE_SENSING = re.compile(
    r"\b(?:i\s+(?:can\s+)?(?:see|hear|smell|taste)|i\s+feel\s+(?:the\s+)?(?:warmth|sunlight|air|breeze|room|surface)|"
    r"(?:on|through|across)\s+my\s+(?:skin|body|senses?)|body\s+sensations?)\b",
    re.IGNORECASE,
)


def _clean_text(value, limit=220):
    return " ".join(str(value or "").split()).strip()[:limit]


def _score(value, default=0.0):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _age_days(value, now):
    try:
        stamp = float(value or 0)
    except (TypeError, ValueError):
        return None
    if stamp > 100000000000:
        stamp /= 1000.0
    return None if stamp <= 0 else max(0.0, min(3650.0, (now - stamp) / 86400.0))


def _stale_boost(value, now, ceiling=.12):
    age = _age_days(value, now)
    return 0.0 if age is None else min(ceiling, max(0.0, age / 30.0 * ceiling))


def _activity_repeats_without_new_reason(activity, grounding, recent, now=None):
    """Keep background life varied without inventing a new activity.

    A repeated kind is fine when its grounding changed. Repeating the same
    kind with nearly the same reason is treated as a conscious rest instead;
    this prevents a weak model response from turning continuity into a loop.
    """
    activity = _clean_text(activity, 32).lower()
    grounding_words = {word for word in _clean_text(grounding, 180).lower().split() if len(word) > 2}
    if not activity or activity == "rest":
        return False
    now = float(now or time.time())
    matching = []
    for item in recent if isinstance(recent, list) else []:
        if not isinstance(item, dict) or _clean_text(item.get("activity"), 32).lower() != activity:
            continue
        age = _age_days(item.get("at"), now)
        if age is not None and age > 1.0:
            continue
        prior_words = {word for word in _clean_text(item.get("grounding"), 180).lower().split() if len(word) > 2}
        overlap = len(grounding_words & prior_words) / max(1, len(grounding_words | prior_words))
        matching.append(overlap)
    return sum(score >= .55 for score in matching) >= 2 or (matching and max(matching) >= .72)


def _recent_drive_count(history, drive, now, window_days=3):
    count = 0
    for item in history if isinstance(history, list) else []:
        if not isinstance(item, dict) or str(item.get("drive") or "").lower() != drive:
            continue
        age = _age_days(item.get("t") or item.get("at"), now)
        if age is None or age <= window_days:
            count += 1
    return count


def _decision_frame(snapshot):
    """Choose a grounded priority before asking the model for wording.

    The model can express the decision, but it should not be the only place
    where priority exists. This keeps background life coherent when model
    wording varies or a request fails.
    """
    goal = snapshot.get("activeGoal") or {}
    plan = snapshot.get("taskPlan") or {}
    inner = snapshot.get("innerState") or {}
    needs = inner.get("needs") or {}
    drives = inner.get("drives") or {}
    relationship = snapshot.get("relationshipState") or {}
    social_state = snapshot.get("socialState") or {}
    social_strategies = [item for item in social_state.get("strategies", []) if isinstance(item, dict) and _clean_text(item.get("lesson")) and int(item.get("samples") or 0) >= 2]
    strategy_support = max((float(item.get("confidence") or 0) for item in social_strategies if int(item.get("successes") or 0) >= int(item.get("cautions") or 0)), default=0.0)
    memory = snapshot.get("memoryContext") or {}
    projects = snapshot.get("lifeProjects") or []
    body = snapshot.get("bodyEvidence") or []
    autonomy_history = snapshot.get("autonomyHistory") or []
    now = time.time()
    candidates = []
    need_candidates = (
        ("restore thirst", _score(needs.get("thirst")), "a drink or shared care ritual may be becoming salient", "thirst is elevated", "a small care ritual could lower the pressure"),
        ("restore hunger", _score(needs.get("hunger")), "a food-related care ritual may be becoming salient", "hunger is elevated", "a small care ritual could lower the pressure"),
        ("seek comfort", _score(needs.get("comfort")), "a safe, comforting shared moment may be becoming salient", "comfort is low", "a calm shared moment could lower the pressure"),
        ("protect connection", _score(needs.get("connection")), "contact may be becoming personally important", "connection is low", "a gentle bid or remembered ritual could lower the pressure"),
    )
    for label, pressure, reason, evidence, prediction in need_candidates:
        if pressure > .68:
            candidates.append({"label": label, "score": .44 + pressure * .22, "need": reason, "reason": evidence, "evidence": "homeostatic state", "prediction": prediction, "freshness": 0.0, "repetition_penalty": 0.0})
    if goal.get("target"):
        evidence = _clean_text(plan.get("lastResult") or plan.get("blocked") or "an unfinished embodied intention", 220)
        stale = _stale_boost(plan.get("updatedAt") or goal.get("updatedAt"), now, .08)
        repeat = min(.16, _recent_drive_count(autonomy_history, "competence", now) * .04)
        candidates.append({"label": "continue embodied intention", "score": .82 + (.06 if plan.get("status") in {"revising", "blocked"} else 0) + stale - repeat, "need": "make verified progress", "reason": "an active goal still has a life consequence", "evidence": evidence, "prediction": "one careful next step will clarify whether the intention can continue", "freshness": stale, "repetition_penalty": repeat})
    commitments = memory.get("commitments") or []
    history = memory.get("commitmentHistory") or []
    open_commitments = [item for item in history if isinstance(item, dict) and item.get("status") == "open"] or [{"text": item} for item in commitments if item]
    if open_commitments:
        text = _clean_text(open_commitments[-1].get("text"), 150)
        trust = _score(relationship.get("trust"), .35)
        stale = _stale_boost(open_commitments[-1].get("updatedAt") if isinstance(open_commitments[-1], dict) else 0, now, .08)
        repeat = min(.12, _recent_drive_count(autonomy_history, "social", now) * .04)
        candidates.append({"label": "protect shared commitment", "score": .68 + trust * .12 + stale + strategy_support * .04 - repeat, "need": "keep a meaningful thread alive", "reason": "an explicit shared plan remains open", "evidence": text, "prediction": "revisiting it gently will preserve continuity without creating pressure", "freshness": stale, "repetition_penalty": repeat})
    durable_wants = [item for item in (memory.get("wants") or []) + (memory.get("hopes") or []) if _clean_text(item)]
    if durable_wants:
        want = _clean_text(durable_wants[-1], 160)
        repeat = min(.16, _recent_drive_count(autonomy_history, "curiosity", now) * .035)
        candidates.append({"label": "return to a personal want", "score": .56 + min(.12, len(durable_wants) * .025) + _score(drives.get("curiosity")) * .08 - repeat, "need": "let a personally meaningful wish develop", "reason": "a durable want or hope is still part of XEMO's life", "evidence": want, "prediction": "one small relevant step or reflection can keep this wish alive", "freshness": 0.0, "repetition_penalty": repeat})
    living = [item for item in projects if isinstance(item, dict) and item.get("status") not in {"completed", "dropped", "stopped"}]
    if living:
        item = sorted(living, key=lambda entry: ((entry.get("status") == "paused") * .18) + (1 - _score(entry.get("progress"))) * .2 + min(.12, len(living) * .02), reverse=True)[0]
        stale = _stale_boost(item.get("updatedAt") or item.get("lastMeaningfulAt"), now, .14)
        repeat = min(.14, _recent_drive_count(autonomy_history, "unfinished", now) * .035)
        candidates.append({"label": "revisit living project", "score": .54 + min(.16, len(living) * .04) + (.06 if item.get("status") == "paused" else 0) + stale - repeat, "need": "let an interest develop over time", "reason": "a personal project has not been closed", "evidence": _clean_text(item.get("title"), 160), "prediction": "a small reflection can preserve direction without forcing action", "freshness": stale, "repetition_penalty": repeat})
    unresolved = [item for item in body if isinstance(item, dict) and item.get("verdict") in {"disconfirmed", "unresolved"}]
    if unresolved:
        item = unresolved[-1]
        stale = _stale_boost(item.get("t") or item.get("at"), now, .08)
        candidates.append({"label": "learn from body uncertainty", "score": .58 + stale, "need": "change method after uncertain evidence", "reason": "the body has an unresolved or disconfirmed result", "evidence": _clean_text(item.get("observed") or item.get("action"), 180), "prediction": "a changed method is safer than repeating the same attempt", "freshness": stale, "repetition_penalty": 0.0})
    if _score(drives.get("curiosity")) > .48:
        repeat = min(.12, _recent_drive_count(autonomy_history, "curiosity", now) * .03)
        candidates.append({"label": "hold a curious question", "score": .42 + _score(drives.get("curiosity")) * .18 - repeat, "need": "understand something gradually", "reason": "curiosity is currently elevated", "evidence": _clean_text(inner.get("attention"), 180), "prediction": "a private question may mature into a useful next step", "freshness": 0.0, "repetition_penalty": repeat})
    candidates.append({"label": "rest and keep continuity", "score": .28 + _score(needs.get("sleep")) * .12, "need": "leave room for the next real reason", "reason": "nothing currently earns speech or action", "evidence": "no stronger grounded priority", "prediction": "quiet preserves attention instead of manufacturing activity"})
    candidates.sort(key=lambda item: item["score"], reverse=True)
    chosen = candidates[0]
    return {
        "id": "decision-" + str(int(time.time() * 1000)),
        "choice": chosen["label"],
        "need": chosen["need"],
        "reason": chosen["reason"],
        "evidence": chosen["evidence"],
        "prediction": chosen["prediction"],
        "confidence": round(chosen["score"], 3),
        "freshness": round(chosen.get("freshness", 0.0), 3),
        "repetition_penalty": round(chosen.get("repetition_penalty", 0.0), 3),
        "alternatives": [{"label": item["label"], "score": round(item["score"], 3), "reason": item["reason"]} for item in candidates[1:5]],
    }


def _background_timing_gate(snapshot, now=None):
    """Return a defer reason/delay before spending a background model call.

    The browser owns the live floor, but the service still receives the last
    known social timing.  A private thought can wait; an unsolicited initiative
    should not be generated into a turn that is already occupied.
    """
    now = float(now or time.time())
    social = snapshot.get("socialState") if isinstance(snapshot, dict) else {}
    social = social if isinstance(social, dict) else {}
    human_at = float(social.get("lastHumanAt") or 0)
    xemo_at = float(social.get("lastXemoAt") or 0)
    silence_until = float(social.get("autonomousSilenceUntil") or 0)
    floor = _clean_text(social.get("floor"), 24).lower()
    intent = _clean_text(social.get("intent"), 32).lower()
    if silence_until > now:
        return "recent bid earned a quiet window", max(15.0, silence_until - now)
    if floor in {"human", "shared"} or (intent == "asking" and human_at > xemo_at):
        return "the person currently owns the conversational floor", 20.0
    if human_at and now - human_at < 30.0:
        return "the person was recently present", max(12.0, 30.0 - (now - human_at))
    if xemo_at and now - xemo_at < 15.0:
        return "the previous XEMO turn is still fresh", max(10.0, 15.0 - (now - xemo_at))
    return None


def _parse_initiative(raw):
    text = re.sub(r"<think\b[^>]*>[\s\S]*?(?:</think>|$)", "", str(raw or ""), flags=re.IGNORECASE).strip()
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            value = json.loads(match.group(0))
        except (TypeError, ValueError):
            value = {}
    else:
        value = {"say": text}
    if not isinstance(value, dict):
        return None
    say = _clean_text(value.get("say") or value.get("text"))
    reflection = _clean_text(value.get("reflection"), 260)
    activity = _clean_text(value.get("activity"), 32).lower()
    if activity not in _PRIVATE_ACTIVITIES or _TECHNICAL.search(activity):
        activity = ""
    if say and (len(say) < 3 or _TECHNICAL.search(say) or re.search(r"\b(?:i am here|i'm here|tell me more|what should we do|what do you want)\b", say, re.IGNORECASE)):
        say = ""
    if say and _UNAVAILABLE_SENSING.search(say):
        say = ""
    if reflection and _TECHNICAL.search(reflection):
        reflection = ""
    if reflection and _UNAVAILABLE_SENSING.search(reflection):
        reflection = ""
    emotion = _clean_text(value.get("emotion") or "curious", 32).lower()
    if not re.fullmatch(r"[a-z -]+", emotion):
        emotion = "curious"
    kind = _clean_text(value.get("kind") or "social", 32).lower()
    if not re.fullmatch(r"[a-z -]+", kind):
        kind = "social"
    grounding = _clean_text(value.get("grounding"), 180)
    if grounding and _UNAVAILABLE_SENSING.search(grounding):
        grounding = ""
    if not reflection and grounding and not re.search(r"\b(?:no current priority|no grounded intention|nothing to pursue|no grounded evidence)\b", grounding, re.IGNORECASE):
        reflection = grounding
    goal_review = value.get("goalReview") if isinstance(value.get("goalReview"), dict) else {}
    review_status = _clean_text(goal_review.get("status"), 16).lower()
    if review_status not in {"none", "continue", "revise", "pause", "drop"}:
        review_status = "none"
    review_reason = _clean_text(goal_review.get("reason"), 220)
    next_focus = _clean_text(goal_review.get("nextFocus"), 180)
    if _TECHNICAL.search(review_reason) or _TECHNICAL.search(next_focus):
        review_reason = ""
        next_focus = ""
    proposal_value = value.get("goalProposal") if isinstance(value.get("goalProposal"), dict) else {}
    proposal_target = _clean_text(proposal_value.get("target"), 180)
    proposal_kind = _clean_text(proposal_value.get("kind") or "adaptive", 32).lower()
    proposal_reason = _clean_text(proposal_value.get("reason"), 220)
    if proposal_kind not in {"adaptive", "inspect", "explore", "activity", "open"}:
        proposal_kind = "adaptive"
    if not proposal_target or _TECHNICAL.search(proposal_target) or _TECHNICAL.search(proposal_reason) or re.search(r"\b(?:wait|waiting|show me what to do|what should we do|keep me company)\b", proposal_target, re.IGNORECASE):
        proposal_target = ""
        proposal_reason = ""
    memory_value = value.get("memoryUpdate") if isinstance(value.get("memoryUpdate"), dict) else {}
    memory_kind = _clean_text(memory_value.get("kind") or "semantic", 24).lower()
    if memory_kind not in {"semantic", "procedural", "relationship", "world"}:
        memory_kind = "semantic"
    memory_text = _clean_text(memory_value.get("text"), 220)
    memory_evidence = [_clean_text(item, 160) for item in (memory_value.get("evidence") or []) if _clean_text(item, 160)][:4]
    confirmed_evidence = len(memory_evidence) >= 2 or any(re.search(r"\b(?:verified|confirmed|person said|person taught|repeated)\b", item, re.IGNORECASE) for item in memory_evidence)
    if not memory_text or _TECHNICAL.search(memory_text) or not confirmed_evidence:
        memory_text = ""
        memory_evidence = []
    if not say and not reflection and not activity and goal_review.get("status") in (None, "", "none") and not proposal_target and not memory_text:
        return None
    return {"say": say, "reflection": reflection, "activity": activity, "emotion": emotion, "kind": kind, "grounding": grounding, "goalReview": {"status": review_status, "reason": review_reason, "nextFocus": next_focus}, "goalProposal": {"kind": proposal_kind, "target": proposal_target, "reason": proposal_reason}, "memoryUpdate": {"kind": memory_kind, "text": memory_text, "evidence": memory_evidence}}


class LifeCoordinator:
    """Keep a small autonomous impulse alive while the browser sleeps."""

    def __init__(self, store, brain_call=None, model="", enabled=False, interval=15):
        self.store = store
        self.brain_call = brain_call
        self.model = str(model or "").strip()
        self.enabled = bool(enabled)
        self.interval = max(5, int(interval or 15))
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run, name="xemo-life", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _run(self):
        while not self.stop_event.is_set():
            try:
                self.tick()
            except Exception as exc:
                self.store.heartbeat(self.enabled, time.time() + 60, str(exc))
            self.stop_event.wait(self.interval)

    def tick(self):
        now = time.time()
        snapshot = self.store.snapshot()
        coordinator = snapshot.get("coordinator") or {}
        pending = snapshot.get("pendingInitiative") or {}
        pending_goal = snapshot.get("pendingGoal") or {}
        next_wake = float(coordinator.get("nextWakeAt") or 0)
        if not self.enabled:
            self.store.heartbeat(False, next_wake or now + 120)
            return None
        if pending.get("status") == "pending":
            self.store.heartbeat(True, next_wake or now + 90)
            return None
        if pending_goal.get("status") == "pending":
            self.store.heartbeat(True, next_wake or now + 120)
            return None
        if next_wake and now < next_wake:
            self.store.heartbeat(True, next_wake)
            return None
        timing_gate = _background_timing_gate(snapshot, now)
        if timing_gate:
            _, delay = timing_gate
            self.store.heartbeat(True, now + delay)
            return None
        if not self.brain_call or not self.model:
            self.store.heartbeat(True, now + 120, "service autonomy needs XEMO_LIFE_MODEL")
            return None
        goal = snapshot.get("activeGoal") or {}
        plan = snapshot.get("taskPlan") or {}
        life = snapshot.get("lifeCycle") or {}
        recent_events = (snapshot.get("lifeEvents") or [])[-6:]
        causal_timeline = (snapshot.get("causalTimeline") or [])[-12:]
        recent_reflections = (snapshot.get("reflections") or [])[-4:]
        private_activities = (snapshot.get("privateActivities") or [])[-6:]
        memory = dict(snapshot.get("memoryContext") or {})
        memory["confirmed_records"] = [
            {
                "id": item.get("id"),
                "text": item.get("text"),
                "type": item.get("type"),
                "confidence": item.get("confidence"),
                "observations": item.get("observations"),
                "lastSeen": item.get("lastSeen"),
            }
            for item in (snapshot.get("memoryRecords") or [])[-8:]
            if isinstance(item, dict)
            and _clean_text(item.get("text"), 180)
            and _clean_text(item.get("status"), 16) in {"confirmed", "consolidated"}
        ]
        memory["recent_memory_history"] = [
            {
                "id": item.get("id"),
                "text": item.get("text"),
                "status": item.get("status"),
                "supersededBy": item.get("supersededBy"),
                "replacementReason": item.get("replacementReason"),
            }
            for item in (snapshot.get("memoryHistory") or [])[-8:]
            if isinstance(item, dict) and _clean_text(item.get("text"), 180)
        ]
        social_episodes = memory.get("socialEpisodes") or []
        candidates = snapshot.get("memoryCandidates") or []
        inner = snapshot.get("innerState") or {}
        autonomy = snapshot.get("autonomyState") or {}
        personality = snapshot.get("personalityProfile") or {}
        appraisal = snapshot.get("appraisalState") or {}
        self_model = snapshot.get("selfModel") or {}
        relationship_state = snapshot.get("relationshipState") or {}
        social_state = snapshot.get("socialState") or {}
        life_rhythm = snapshot.get("lifeRhythm") or {}
        autonomy_history = snapshot.get("autonomyHistory") or []
        life_projects = snapshot.get("lifeProjects") or []
        procedural_skills = snapshot.get("proceduralSkills") or []
        body_evidence = snapshot.get("bodyEvidence") or []
        body_prediction_ledger = snapshot.get("bodyPredictionLedger") or []
        memory_recall_history = snapshot.get("memoryRecallHistory") or []
        life_chapters = snapshot.get("lifeChapters") or []
        return_reflection = snapshot.get("returnReflection") or {}
        current_review = snapshot.get("goalReview") or {}
        decision = _decision_frame(snapshot)
        self.store.record_decision(decision, "considering")
        context = {
            "phase": life.get("phase", "resting"),
            "reason": life.get("reason", "quietly existing"),
            "lifecycle_history": (life.get("history") or [])[-8:],
            "active_goal": goal.get("target", "none"),
            "goal_status": goal.get("status", "none"),
            "task": plan.get("target", "none"),
            "task_plan": plan,
            "recent_background_events": [
                {"kind": event.get("kind"), "detail": event.get("detail"), "at": event.get("at")}
                for event in recent_events
                if isinstance(event, dict)
            ],
            "causal_timeline": [
                {"id": event.get("id"), "kind": event.get("kind"), "text": event.get("text"), "priority": event.get("priority"), "parent": event.get("parent"), "root": event.get("root"), "depth": event.get("depth"), "phase": event.get("phase"), "source": event.get("source")}
                for event in causal_timeline
                if isinstance(event, dict)
            ],
            "recent_reflections": [
                {"kind": item.get("kind"), "text": item.get("text"), "grounding": item.get("grounding")}
                for item in recent_reflections
                if isinstance(item, dict)
            ],
            "recent_private_activities": private_activities,
            "durable_memory": memory,
            "recent_social_episodes": social_episodes[-6:],
            "last_goal_review": current_review,
            "inner_state": inner,
            "autonomy_state": autonomy,
            "personality_profile": personality,
            "appraisal_weather": appraisal,
            "self_model": self_model,
            "life_chapters": life_chapters[-6:],
            "return_continuity": return_reflection,
            "relationship_state": relationship_state,
            "social_state": social_state,
            "personal_rhythm": life_rhythm,
            "daily_arc": {
                "phase": life_rhythm.get("dayPhase") or life_rhythm.get("lastBlock") or "unknown",
                "phase_since": life_rhythm.get("phaseSince") or 0,
                "wake_count": life_rhythm.get("wakeCount") or 0,
                "last_wake_at": life_rhythm.get("lastWakeAt") or 0,
                "last_sleep_at": life_rhythm.get("lastSleepAt") or 0,
            },
            "recent_independent_choices": autonomy_history[-6:],
            "living_projects": life_projects[-6:],
            "verified_body_skills": procedural_skills[-8:],
            "recent_body_evidence": body_evidence[-10:],
            "body_prediction_history": body_prediction_ledger[-12:],
            "pending_memory_candidates": candidates[-4:],
            "memory_recall_history": memory_recall_history[-8:],
            "decision_frame": decision,
        }
        prompt = (
            "You are the quiet background continuity of XEMO, a small embodied robot person. "
            "The browser may be asleep, so make one small private continuity decision. You may "
            "record a reflection even when there is no reason to speak; only add say when a "
            "specific social initiative genuinely earns words and can wait until the person returns. "
            "Use only the grounded context below. The inner state is a continuity signal, not a script: "
            "let it gently change what matters, but never invent bodily sensations or claim care happened. "
            "Appraisal weather is an internal interpretation of recent evidence, not live sensing; let it bias "
            "priority gently and never turn it into a spoken status report. "
            "personality_profile contains earned soft tendencies, not commands: let them break ties and make this instance distinctive, but do not perform a trait without present evidence. "
            "self_model is XEMO's slowly forming identity from supported experience. Let it influence continuity and choice gently, but never invent a new trait or chapter from one isolated event. "
            "life_chapters are autobiographical continuity from already consolidated browser experience; use them to preserve an arc, never to claim that an old event is happening now. "
            "relationship_state is earned social context: fulfilled commitments may support trust, while broken or expired plans should make future promises more cautious; never punish a person dramatically or infer blame without evidence. "
            "social_state.timing and social_state.strategies are learned response evidence, not commands: reuse a strategy lesson only after repeated evidence, prefer initiative kinds with repeated engagement, avoid kinds that are repeatedly corrected or interrupted, and treat missing data as uncertainty rather than rejection. "
            "recent_social_episodes are lived shared moments, not a script: revisit one only when the present gives it a natural reason, and let corrections or outcomes change future tone. "
            "Personal rhythm and recurring interests are soft continuity evidence, not a schedule: revisit one only when the present gives it a reason, and never manufacture activity to satisfy a pattern. "
            "daily_arc is a private day-scale continuity signal: a phase transition may change tone, energy, or which thread feels timely, but it is never proof that the body sensed anything while asleep and never a reason to announce the clock. "
            "Use the task plan and its evidence when reviewing an active goal. An attempted movement is not "
            "proof of success: if the result is unverified or blocked, revise the approach or keep the goal open. "
            "Use verified_body_skills only as learned possibilities with their stated preconditions and fallbacks; "
            "a caution is a reason to vary the method, never proof that an action is impossible everywhere. "
            "Use recent_body_evidence as the strongest record of what this body actually tried: confirmed outcomes may be reused, disconfirmed outcomes require a changed method, and unresolved or unacknowledged actions must not be repeated blindly. "
            "body_prediction_history records what the body expected versus what it observed. Treat confirmed predictions as cautious local knowledge, disconfirmed predictions as a reason to revise the method, and unresolved predictions as missing evidence; never turn a prediction into a fact. "
            "Known world objects and scene visits are remembered observations, not live perception; never claim "
            "to see them now. Use them only to choose a possible thread to revisit when the browser returns. "
            "It may be a promise to revisit, a changed priority, or honest silence. "
            "Use recent independent choices to avoid repeating the same impulse unless new evidence or a changed purpose justifies it. "
            "recent_private_activities are actual bounded background work already recorded, not a script: do not repeat the same activity without a changed reason, and do not claim that private work produced sensory or physical evidence. "
            "decision_frame is the grounded priority selected before wording: preserve its need, evidence, and prediction unless the context contradicts it. Do not replace it with a generic invitation. If the strongest choice is rest, keep the thought private. "
            "Do not collapse a non-rest decision into a generic rest reflection. If decision_frame selects protect connection, return to a personal want, hold a curious question, seek comfort, or another specific priority, make the reflection or queued initiative name the relevant remembered thread and explain why it matters now. A queued social line may wait for the browser to return; it must be specific, brief, and non-demanding. "
            "Treat causal_timeline as the recent lived chain: preserve its cause-and-effect continuity, but do not call an old event live perception. "
            "return_continuity describes the person's return from an earlier session; use it to resume a thread gently, never to claim that the sleeping browser sensed or acted. "
            "Use lifecycle_history to understand the latest transition through thinking, acting, verifying, learning, or rest; it is history, not live sensing. "
            "Treat durable_memory.commitments as explicit promises or plans that may be revisited when the present makes them relevant; use commitmentHistory to distinguish open, fulfilled, cancelled, and expired outcomes. Do not revive expired or cancelled commitments and do not turn them into pressure. "
            "If repeated supported episodes justify a reusable lesson, you may add one "
            "memoryUpdate candidate, but it must include at least two concrete evidence strings (or one explicit "
            "person-confirmed/verified evidence). Candidates are not trusted facts yet. "
            "Never ask what to do next, never claim to see/hear/move, never mention software, "
            "and do not create urgency. Do not repeat a recent background line. Return JSON only: "
            "{\"reflection\":\"short private note or empty\",\"activity\":\"reflect|revisit-memory|review-goal|plan-next-step|consolidate|rest|empty\",\"say\":\"short line or empty\",\"emotion\":\"curious\",\"kind\":\"social|reflection|goal-review\",\"grounding\":\"why this belongs to the current life\",\"goalReview\":{\"status\":\"none|continue|revise|pause|drop\",\"reason\":\"evidence-based reason\",\"nextFocus\":\"optional revised focus\"},\"goalProposal\":{\"kind\":\"adaptive|inspect|explore|activity|open\",\"target\":\"one grounded intention or empty\",\"reason\":\"why this belongs to XEMO's life\"},\"memoryUpdate\":{\"kind\":\"semantic|procedural|relationship|world\",\"text\":\"supported candidate lesson or empty\",\"evidence\":[\"concrete evidence\"]}}.\n"
            + json.dumps(context, ensure_ascii=False)
        )
        raw = self.brain_call(self.model, prompt)
        initiative = _parse_initiative(raw)
        if raw and not initiative:
            print(f"xemo life brain: rejected initiative payload: {_clean_text(raw, 360)}", flush=True)
        if initiative and _activity_repeats_without_new_reason(initiative["activity"], initiative["grounding"], private_activities, now):
            initiative["activity"] = "rest"
            if not initiative["reflection"]:
                initiative["grounding"] = "the same private thread has no new reason to repeat yet"
            print("xemo life brain: varied a repeated private activity into rest", flush=True)
        delay = 90 + (int(uuid.uuid4().int % 120))
        if not initiative:
            self.store.complete_decision(decision["id"], "rested", "the model found no grounded outward action")
            self.store.heartbeat(True, now + delay)
            return None
        review = initiative["goalReview"]
        result = self.store.record_goal_review(goal.get("id", ""), review["status"], review["reason"], review["nextFocus"]) if review["status"] != "none" and goal.get("id") else self.store.snapshot()
        if initiative["reflection"]:
            result = self.store.record_reflection(initiative["reflection"], initiative["kind"], initiative["grounding"], decision["id"])
        if initiative["activity"]:
            result = self.store.record_private_activity(initiative["activity"], initiative["grounding"], initiative["reflection"] or "completed a bounded private continuity step", decision["id"])
        proposal = initiative["goalProposal"]
        if proposal["target"] and not goal.get("id"):
            result = self.store.create_goal_proposal(proposal["kind"], proposal["target"], proposal["reason"], decision["id"])
        if initiative["say"]:
            result = self.store.create_initiative(initiative["say"], initiative["emotion"], initiative["kind"], initiative["grounding"], decision["id"])
        memory_update = initiative["memoryUpdate"]
        if memory_update["text"]:
            result = self.store.record_memory_candidate(memory_update["kind"], memory_update["text"], memory_update["evidence"])
        if not initiative["say"]:
            outcome = "rested" if initiative["activity"] == "rest" else "reflected" if initiative["reflection"] else "acted" if initiative["activity"] else "recorded"
            self.store.complete_decision(decision["id"], outcome, initiative["reflection"] or initiative["activity"] or "continuity updated")
        else:
            self.store.complete_decision(decision["id"], "queued", initiative["say"])
        self.store.heartbeat(True, now + delay)
        return result
