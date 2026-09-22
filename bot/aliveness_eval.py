"""Small, deterministic checks for XEMO's persistent-life journal.

These metrics do not prove consciousness. They catch continuity failures that
make a character feel scripted: ungrounded initiative, repeated choices,
unverified body claims, missing lifecycle traces, and identical instances.
"""

import json
import sys
from collections import Counter
from pathlib import Path


def _text(value):
    return " ".join(str(value or "").split()).strip().lower()


def _bounded_rate(numerator, denominator):
    return round(max(0.0, min(1.0, numerator / denominator)), 3) if denominator else None


def _timestamp_seconds(value):
    try:
        stamp = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return stamp / 1000.0 if stamp > 100000000000 else stamp


def evaluate_snapshot(snapshot):
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    life_events = [x for x in snapshot.get("lifeEvents", []) if isinstance(x, dict)]
    choices = [x for x in snapshot.get("autonomyHistory", []) if isinstance(x, dict) and _text(x.get("choice"))]
    opportunities = [x.get("opportunity") for x in choices if isinstance(x.get("opportunity"), dict)]
    engaged_opportunities = [x for x in opportunities if _text(x.get("status")) == "engaged"]
    timed_engagements = [x for x in engaged_opportunities if 0 < _timestamp_seconds(x.get("resolvedAt")) - _timestamp_seconds(x.get("openedAt")) <= 120]
    choice_keys = [_text(x.get("choice")) for x in choices]
    counts = Counter(choice_keys)
    repeated = sum(max(0, count - 1) for count in counts.values())
    trait_drives = {
        "curiosity": {"curiosity", "competence", "unfinished"},
        "playfulness": {"play"},
        "persistence": {"competence", "unfinished"},
        "sociability": {"social", "expression"},
        "warmth": {"social", "expression"},
        "caution": {"rest", "comfort", "competence"},
    }
    personality_choices = []
    for item in choices:
        profile = item.get("personality") if isinstance(item.get("personality"), dict) else {}
        strongest = max(((key, float(profile.get(key) or 0)) for key in trait_drives), key=lambda pair: pair[1], default=("", 0.0))
        if strongest[1] >= .55:
            personality_choices.append(str(item.get("drive") or "").lower() in trait_drives[strongest[0]])
    initiatives = [x for x in life_events if x.get("kind") == "initiative-created"]
    initiative_outcomes = [x for x in life_events if str(x.get("kind") or "").startswith("initiative-") and x.get("kind") not in {"initiative-created", "initiative-claimed"}]
    grounded = sum(bool(_text(x.get("grounding"))) for x in initiatives)
    body = [x for x in snapshot.get("bodyEvidence", []) if isinstance(x, dict) and _text(x.get("verdict")) in {"confirmed", "disconfirmed", "unresolved"}]
    verified = sum(_text(x.get("verdict")) == "confirmed" for x in body)
    lifecycle = [x for x in snapshot.get("causalTimeline", []) if isinstance(x, dict) and _text(x.get("kind")) == "lifecycle"]
    causal_stages = {
        "observation", "appraisal", "motive", "decision", "plan", "action",
        "acknowledgement", "verification", "learning", "social-consequence",
        "memory-promotion",
    }
    seen_stages = {_text(x.get("kind")) for x in snapshot.get("causalTimeline", []) if isinstance(x, dict)}
    stage_coverage = len(causal_stages & seen_stages) / len(causal_stages)
    social_episodes = [x for x in snapshot.get("socialEpisodes", []) if isinstance(x, dict) and _text(x.get("text"))]
    projects = [x for x in snapshot.get("lifeProjects", []) if isinstance(x, dict) and _text(x.get("title"))]
    memories = [x for x in snapshot.get("memoryRecords", []) if isinstance(x, dict) and _text(x.get("text")) and _text(x.get("status")) in {"confirmed", "consolidated"}]
    memory_linked_choices = [x for x in choices if isinstance(x.get("memoryRefs"), list) and any(_text(ref) for ref in x.get("memoryRefs"))]
    strategy_linked_choices = [x for x in choices if isinstance(x.get("strategyRefs"), list) and any(_text(ref) for ref in x.get("strategyRefs"))]
    reflections = [x for x in snapshot.get("reflections", []) if isinstance(x, dict) and _text(x.get("text"))]
    private_activities = [x for x in snapshot.get("privateActivities", []) if isinstance(x, dict) and _text(x.get("activity"))]
    reflection_linked_choices = [x for x in choices if isinstance(x.get("reflectionRefs"), list) and any(_text(ref) for ref in x.get("reflectionRefs"))]
    activity_linked_choices = [x for x in choices if isinstance(x.get("privateActivityRefs"), list) and any(_text(ref) for ref in x.get("privateActivityRefs"))]
    action_linked_choices = [x for x in choices if isinstance(x.get("actionOutcome"), dict) and _text(x.get("actionOutcome", {}).get("action"))]
    memory_verified_choices = [x for x in action_linked_choices if x in memory_linked_choices and _text(x.get("actionOutcome", {}).get("status")) == "verified"]
    memory_history = [x for x in snapshot.get("memoryHistory", []) if isinstance(x, dict) and _text(x.get("text"))]
    recalls = [x for x in snapshot.get("memoryRecallHistory", []) if isinstance(x, dict) and _text(x.get("text"))]
    memory_context = snapshot.get("memoryContext") if isinstance(snapshot.get("memoryContext"), dict) else {}
    episode_source = snapshot.get("lifeEpisodes") if isinstance(snapshot.get("lifeEpisodes"), list) else memory_context.get("lifeEpisodes", [])
    episodes = [x for x in episode_source if isinstance(x, dict) and _text(x.get("trigger"))]
    episode_outcomes = [x for x in episodes if _text(x.get("action")) and _text(x.get("status")) in {"resolved", "unresolved"}]
    episode_verified = [x for x in episode_outcomes if x.get("verified") is True]
    resolved_recalls = [x for x in recalls if _text(x.get("outcome")) != "pending"]
    revisions = [x for x in memory_history if _text(x.get("status")) == "outdated" and (_text(x.get("supersededBy")) or _text(x.get("replacementReason")))]
    durable_memories = sum((float(x.get("durationDays") or 0) >= 1 or int(x.get("observations") or 0) >= 2) for x in memories)
    living_projects = [x for x in projects if _text(x.get("status")) not in {"completed", "dropped", "stopped"}]
    dormant_projects = sum(float(x.get("idleDays") or 0) >= 1 for x in living_projects)
    prospective_projects = [x for x in living_projects if _text(x.get("forecast")) or int(x.get("reviewCount") or 0) > 0]
    due_projects = sum(float(x.get("reviewAt") or 0) > 0 and float(x.get("reviewAt") or 0) <= 1e15 for x in prospective_projects)
    relationship = snapshot.get("relationshipState") if isinstance(snapshot.get("relationshipState"), dict) else {}
    social = snapshot.get("socialState") if isinstance(snapshot.get("socialState"), dict) else {}
    social_timing = social.get("timing") if isinstance(social.get("timing"), dict) else {}
    timing_samples = max(0, int(social_timing.get("samples") or 0))
    social_patterns = social_timing.get("byKind") if isinstance(social_timing.get("byKind"), dict) else {}
    observed_patterns = [item for item in social_patterns.values() if isinstance(item, dict) and int(item.get("samples") or 0) >= 2]
    social_strategies = [item for item in (social.get("strategies") or []) if isinstance(item, dict) and int(item.get("samples") or 0) >= 2 and _text(item.get("lesson"))]
    familiar_scene = memory_context.get("familiarScene") if isinstance(memory_context.get("familiarScene"), dict) else {}
    inner_state = snapshot.get("innerState") if isinstance(snapshot.get("innerState"), dict) else {}
    needs = inner_state.get("needs") if isinstance(inner_state.get("needs"), dict) else {}
    homeostasis = inner_state.get("homeostasis") if isinstance(inner_state.get("homeostasis"), dict) else {}
    need_pressure = max((max(0.0, min(1.0, float(needs.get(key) or 0))) for key in ("hunger", "thirst", "comfort", "connection", "sleep")), default=0.0)
    decision = snapshot.get("coordinator", {}).get("lastDecision", {}) if isinstance(snapshot.get("coordinator"), dict) else {}
    session_history = [x for x in snapshot.get("sessionHistory", []) if isinstance(x, dict) and _text(x.get("id"))]
    checkpoint_reasons = [_text(x.get("reason")) for x in session_history]
    checkpoint_quality = _bounded_rate(sum(bool(_text(x.get("phase")) and _text(x.get("mode"))) for x in session_history), len(session_history))
    recovery = snapshot.get("goalReview") if isinstance(snapshot.get("goalReview"), dict) else {}
    recovery_rate = 1.0 if _text(recovery.get("status")) in {"continue", "revise", "pause", "drop"} and _text(recovery.get("reason")) else None
    metrics = {
        "grounded_initiative_rate": _bounded_rate(grounded, len(initiatives)),
        "repetition_rate": _bounded_rate(repeated, len(choices)),
        "personality_alignment_rate": _bounded_rate(sum(personality_choices), len(personality_choices)),
        "body_verified_rate": _bounded_rate(verified, len(body)),
        "lifecycle_trace_rate": _bounded_rate(len(lifecycle), len(choices)),
        "causal_stage_coverage": round(stage_coverage, 3),
        "social_episode_count": len(social_episodes),
        "living_project_count": sum(_text(x.get("status")) not in {"completed", "dropped", "stopped"} for x in projects),
        "dormant_living_project_rate": _bounded_rate(dormant_projects, len(living_projects)),
        "prospective_project_rate": _bounded_rate(len(prospective_projects), len(living_projects)),
        "prospective_project_due_rate": _bounded_rate(due_projects, len(prospective_projects)),
        "durative_memory_rate": _bounded_rate(durable_memories, len(memories)),
        "relationship_age_days": round(max(0.0, (float(relationship.get("lastMeaningfulAt") or 0) - float(relationship.get("bondSince") or 0)) / 86400), 3) if relationship.get("bondSince") and relationship.get("lastMeaningfulAt") else None,
        "goal_recovery_rate": recovery_rate,
        "initiative_efficacy_rate": _bounded_rate(sum(x.get("kind") == "initiative-delivered" for x in initiative_outcomes), len(initiatives)),
        "initiative_outcome_rate": _bounded_rate(len(initiative_outcomes), len(initiatives)),
        "memory_revision_count": len(revisions),
        "memory_revision_link_rate": _bounded_rate(sum(bool(_text(x.get("supersededBy"))) for x in revisions), len(revisions)),
        "memory_recall_resolution_rate": _bounded_rate(len(resolved_recalls), len(recalls)),
        "memory_recall_use_rate": _bounded_rate(sum(_text(x.get("outcome")) in {"used", "confirmed"} for x in resolved_recalls), len(resolved_recalls)),
        "memory_recall_rejection_rate": _bounded_rate(sum(_text(x.get("outcome")) == "rejected" for x in resolved_recalls), len(resolved_recalls)),
        "memory_influenced_choice_rate": _bounded_rate(len(memory_linked_choices), len(choices)),
        "social_strategy_count": len(social_strategies),
        "social_strategy_reuse_rate": _bounded_rate(len(strategy_linked_choices), len(choices)),
        "private_reflection_count": len(reflections),
        "private_reflection_reuse_rate": _bounded_rate(len(reflection_linked_choices), len(choices)),
        "private_activity_count": len(private_activities),
        "private_activity_reuse_rate": _bounded_rate(len(activity_linked_choices), len(choices)),
        "private_activity_variety": _bounded_rate(len({_text(x.get("activity")) for x in private_activities}), len(private_activities)),
        "choice_action_outcome_link_rate": _bounded_rate(len(action_linked_choices), len(choices)),
        "memory_influenced_verified_outcome_rate": _bounded_rate(len(memory_verified_choices), len(memory_linked_choices)),
        "episode_action_outcome_link_rate": _bounded_rate(len(episode_outcomes), len(episodes)),
        "episode_verified_outcome_rate": _bounded_rate(len(episode_verified), len(episode_outcomes)),
        "session_checkpoint_count": len(session_history),
        "session_checkpoint_quality": checkpoint_quality,
        "session_lifecycle_coverage": _bounded_rate(len(set(checkpoint_reasons)), len(session_history)),
        "choice_count": len(choices),
        "initiative_count": len(initiatives),
        "body_evidence_count": len(body),
        "lifecycle_count": len(lifecycle),
        "autonomous_instruction_rejections": int((snapshot.get("alivenessMetrics") or {}).get("autonomousInstructionRejections") or 0),
        "intentional_rest_count": int((snapshot.get("alivenessMetrics") or {}).get("autonomousRestChoices") or 0),
        "autonomous_bids_engaged": int((snapshot.get("alivenessMetrics") or {}).get("autonomousBidsEngaged") or 0),
        "autonomous_bids_unanswered": int((snapshot.get("alivenessMetrics") or {}).get("autonomousBidsUnanswered") or 0),
        "correction_repair_count": int((snapshot.get("alivenessMetrics") or {}).get("correctionRepairs") or 0),
        "priority_freshness_bias": round(max(0.0, min(1.0, float(decision.get("freshness") or 0))), 3),
        "priority_repetition_penalty": round(max(0.0, min(1.0, float(decision.get("repetition_penalty") or 0))), 3),
        "autonomous_bid_count": len(opportunities),
        "opportunity_engagement_rate": _bounded_rate(len(engaged_opportunities), len(opportunities)),
        "opportunity_timing_quality": _bounded_rate(len(timed_engagements), len(engaged_opportunities)),
        "opportunity_unanswered_rate": _bounded_rate(sum(_text(x.get("status")) == "unanswered" for x in opportunities), len(opportunities)),
        "initiative_engagement_rate": _bounded_rate(int(social_timing.get("engaged") or 0), timing_samples),
        "initiative_unanswered_rate": _bounded_rate(int(social_timing.get("unanswered") or 0), timing_samples),
        "initiative_interruption_rate": _bounded_rate(int(social_timing.get("interrupted") or 0), timing_samples),
        "initiative_average_response_seconds": round(max(0.0, float(social_timing.get("averageResponseMs") or 0)) / 1000, 3),
        "social_response_pattern_count": len(observed_patterns),
        "scene_prediction_attempts": int(familiar_scene.get("predictionAttempts") or 0),
        "scene_prediction_stability": None if familiar_scene.get("stability") is None else round(max(0.0, min(1.0, float(familiar_scene.get("stability") or 0))), 3),
        "homeostatic_revision_count": max(0, int(homeostasis.get("revision") or 0)),
        "homeostatic_need_pressure": round(need_pressure, 3),
    }
    quality_parts = [metrics["grounded_initiative_rate"], None if metrics["repetition_rate"] is None else 1 - metrics["repetition_rate"], metrics["body_verified_rate"], metrics["lifecycle_trace_rate"], metrics["causal_stage_coverage"], recovery_rate, checkpoint_quality, metrics["initiative_efficacy_rate"], metrics["personality_alignment_rate"]]
    quality_parts = [x for x in quality_parts if x is not None]
    metrics["continuity_quality"] = round(sum(quality_parts) / len(quality_parts), 3) if quality_parts else None
    return metrics


def instance_divergence(left, right):
    """Return 0 for identical lived identity and 1 for no overlap."""
    def identity(snapshot):
        values = []
        model = snapshot.get("selfModel") if isinstance(snapshot, dict) else {}
        memory = snapshot.get("memoryContext") if isinstance(snapshot, dict) else {}
        for source in (model, memory):
            if not isinstance(source, dict):
                continue
            for key in ("traits", "chapters", "preferences", "threads", "unfinished"):
                values.extend(_text(x) for x in source.get(key, []) if _text(x))
        return set(values)
    a, b = identity(left), identity(right)
    if not a and not b:
        return 0.0
    return round(1 - len(a & b) / max(1, len(a | b)), 3)


def evaluate_replay(sessions):
    """Score a chronological set of snapshots, not a single frozen state."""
    snapshots = [item for item in sessions if isinstance(item, dict)]
    if not snapshots:
        return {"session_count": 0, "replay_quality": None}

    def events(snapshot):
        rows = []
        for item in (snapshot.get("causalTimeline") or []) + (snapshot.get("lifeEvents") or []):
            if isinstance(item, dict) and _text(item.get("kind") or item.get("detail")):
                rows.append({
                    "kind": _text(item.get("kind")),
                    "text": _text(item.get("text") or item.get("detail")),
                    "t": float(item.get("t") or item.get("at") or 0),
                })
        return sorted(rows, key=lambda item: item["t"])

    correction_sessions = 0
    correction_adapted = 0
    failure_sessions = 0
    failure_recovered = 0
    silence_sessions = 0
    silence_initiated = 0
    project_resumptions = 0
    previous_projects = {}
    previous_project_records = {}
    prospective_reviews = 0
    prospective_forecast_changes = 0
    prospective_review_choice_links = 0
    prior_memory = set()
    memory_carryovers = 0
    personality_changes = 0
    personality_changes_with_choices = 0
    prior_personality = None
    replay_opportunities = []
    previous_episodes = {}
    episode_progressions = 0
    episode_adaptations = 0
    episode_failure_count = 0
    homeostasis_changes = 0
    previous_homeostasis_revision = None
    previous_reflections = set()
    reflection_reuse_count = 0
    reflection_choice_opportunities = 0
    intention_resumptions = 0
    intention_revisions = 0
    stale_intention_expirations = 0
    resumed_intention_adaptations = 0
    previous_resume_count = 0
    previous_plan_target = ""
    resume_pending_adaptation = False
    prior_emotion = None
    emotion_reactions = 0
    emotion_opportunities = 0
    prior_private_activities = set()
    activity_variety_sessions = 0
    for snapshot in snapshots:
        rows = events(snapshot)
        kinds = {item["kind"] for item in rows}
        corrections = [item for item in rows if "correction" in item["text"] or "correct" in item["text"]]
        choices = [_text(item.get("choice")) for item in snapshot.get("autonomyHistory", []) if isinstance(item, dict) and _text(item.get("choice"))]
        choice_rows = [item for item in snapshot.get("autonomyHistory", []) if isinstance(item, dict) and _text(item.get("choice"))]
        current_reflections = {str(item.get("id") or item.get("text")) for item in snapshot.get("reflections", []) if isinstance(item, dict) and _text(item.get("text"))}
        if previous_reflections and choice_rows:
            reflection_choice_opportunities += len(choice_rows)
            reflection_reuse_count += sum(bool(previous_reflections.intersection({str(ref) for ref in item.get("reflectionRefs", [])})) for item in choice_rows)
        previous_reflections |= current_reflections
        task_plan = snapshot.get("taskPlan") if isinstance(snapshot.get("taskPlan"), dict) else {}
        task_status = _text(task_plan.get("status"))
        resume_count = max(0, int(task_plan.get("resumeCount") or 0))
        resumed = resume_count > previous_resume_count or "resuming" in task_status or "returned intention" in task_status
        if resumed:
            intention_resumptions += 1
            resume_pending_adaptation = True
        review = snapshot.get("goalReview") if isinstance(snapshot.get("goalReview"), dict) else {}
        target = _text(task_plan.get("target"))
        revised = _text(review.get("status")) == "revise" or "revis" in task_status or (target and previous_plan_target and target != previous_plan_target and resumed)
        if revised:
            intention_revisions += 1
        stale = task_status == "expired" and any(word in _text(task_plan.get("blocked")) for word in ("old", "stale", "too long", "freshness"))
        if stale:
            stale_intention_expirations += 1
        if resume_pending_adaptation and choices:
            latest = choices[-1]
            if target and latest and not any(token in latest for token in target.split() if len(token) > 4):
                resumed_intention_adaptations += 1
                resume_pending_adaptation = False
        previous_resume_count = max(previous_resume_count, resume_count)
        if target:
            previous_plan_target = target
        replay_opportunities.extend(item.get("opportunity") for item in snapshot.get("autonomyHistory", []) if isinstance(item, dict) and isinstance(item.get("opportunity"), dict))
        current_episode_source = snapshot.get("lifeEpisodes") if isinstance(snapshot.get("lifeEpisodes"), list) else (snapshot.get("memoryContext") or {}).get("lifeEpisodes", []) if isinstance(snapshot.get("memoryContext"), dict) else []
        inner_state = snapshot.get("innerState") if isinstance(snapshot.get("innerState"), dict) else {}
        homeostasis = inner_state.get("homeostasis") if isinstance(inner_state.get("homeostasis"), dict) else {}
        current_homeostasis_revision = int(homeostasis.get("revision") or 0)
        if previous_homeostasis_revision is not None and current_homeostasis_revision > previous_homeostasis_revision:
            homeostasis_changes += 1
        previous_homeostasis_revision = current_homeostasis_revision
        current_episodes = {str(item.get("id")): item for item in current_episode_source if isinstance(item, dict) and item.get("id")}
        for episode_id, episode in current_episodes.items():
            prior_episode = previous_episodes.get(episode_id)
            if prior_episode:
                prior_status = _text(prior_episode.get("status"))
                current_status = _text(episode.get("status"))
                if prior_status in {"open", "unresolved"} and current_status == "resolved" and _text(episode.get("action")):
                    episode_progressions += 1
            if _text(episode.get("status")) in {"unresolved", "disconfirmed"}:
                episode_failure_count += 1
        if previous_episodes:
            failed_actions = {_text(item.get("action")) for item in previous_episodes.values() if _text(item.get("status")) in {"unresolved", "disconfirmed"} and _text(item.get("action"))}
            current_choices = [_text(item.get("choice")) for item in snapshot.get("autonomyHistory", []) if isinstance(item, dict) and _text(item.get("choice"))]
            if failed_actions and current_choices and not any(any(action and action in choice for action in failed_actions) for choice in current_choices[-3:]):
                episode_adaptations += 1
        previous_episodes = current_episodes or previous_episodes
        if corrections:
            correction_sessions += 1
            if len(choices) >= 2 and choices[-1] != choices[-2]:
                correction_adapted += 1
        body = [item for item in snapshot.get("bodyEvidence", []) if isinstance(item, dict)]
        failures = [item for item in body if _text(item.get("verdict")) in {"disconfirmed", "unresolved"}]
        if failures:
            failure_sessions += 1
            review = snapshot.get("goalReview") if isinstance(snapshot.get("goalReview"), dict) else {}
            if _text(review.get("status")) in {"continue", "revise", "pause", "drop"}:
                failure_recovered += 1
        emotion = snapshot.get("emotionState") if isinstance(snapshot.get("emotionState"), dict) else {}
        emotion_name = _text(emotion.get("name"))
        emotion_intensity = max(0.0, min(1.0, float(emotion.get("intensity") or 0)))
        meaningful_event = bool(failures or corrections or any(item["kind"] in {"initiative-delivered", "social-consequence", "verification", "learning"} for item in rows))
        if prior_emotion is not None and meaningful_event:
            emotion_opportunities += 1
            if emotion_name != prior_emotion[0] or abs(emotion_intensity - prior_emotion[1]) >= .08:
                emotion_reactions += 1
        if emotion_name:
            prior_emotion = (emotion_name, emotion_intensity)
        current_private_activities = {_text(item.get("activity")) for item in snapshot.get("privateActivities", []) if isinstance(item, dict) and _text(item.get("activity"))}
        if current_private_activities and prior_private_activities and current_private_activities - prior_private_activities:
            activity_variety_sessions += 1
        prior_private_activities |= current_private_activities
        human_events = any(item["kind"] in {"you", "interruption"} for item in rows)
        initiatives = any(item["kind"] in {"initiative-created", "initiative-delivered", "autonomy-decision"} for item in rows)
        if not human_events:
            silence_sessions += 1
            if initiatives:
                silence_initiated += 1
        for project in snapshot.get("lifeProjects", []) if isinstance(snapshot.get("lifeProjects"), list) else []:
            if not isinstance(project, dict) or not _text(project.get("title")):
                continue
            key = _text(project.get("title"))
            status = _text(project.get("status"))
            if key in previous_projects and previous_projects[key] == "paused" and status in {"active", "reopened", "open", "resuming"}:
                project_resumptions += 1
            previous_projects[key] = status
            prior_project = previous_project_records.get(key)
            if prior_project:
                reviewed = int(project.get("reviewCount") or 0) > int(prior_project.get("reviewCount") or 0)
                forecast_changed = _text(project.get("forecast")) and _text(project.get("forecast")) != _text(prior_project.get("forecast"))
                if reviewed:
                    prospective_reviews += 1
                    choice_text = " ".join(choices[-4:]).lower()
                    anchors = " ".join((_text(project.get("title")), _text(project.get("nextStep")), _text(project.get("forecast")))).lower().split()
                    if choice_text and any(len(token) > 4 and token in choice_text for token in anchors):
                        prospective_review_choice_links += 1
                if forecast_changed:
                    prospective_forecast_changes += 1
            previous_project_records[key] = project
        current_memory = {_text(item.get("text")) for item in snapshot.get("memoryRecords", []) if isinstance(item, dict) and _text(item.get("text"))}
        if prior_memory and current_memory & prior_memory:
            memory_carryovers += 1
        prior_memory |= current_memory
        checkpoints = [item for item in snapshot.get("sessionHistory", []) if isinstance(item, dict) and isinstance(item.get("personality"), dict)]
        current_personality = checkpoints[-1].get("personality") if checkpoints else snapshot.get("personalityProfile")
        if isinstance(current_personality, dict):
            current_personality = {key: float(current_personality.get(key) or 0) for key in ("curiosity", "playfulness", "persistence", "sociability", "caution", "warmth")}
            if prior_personality is not None and max(abs(current_personality[key] - prior_personality[key]) for key in current_personality) >= .08:
                personality_changes += 1
                if choices:
                    personality_changes_with_choices += 1
            prior_personality = current_personality

    metrics = {
        "session_count": len(snapshots),
        "correction_adaptation_rate": _bounded_rate(correction_adapted, correction_sessions),
        "failure_recovery_rate": _bounded_rate(failure_recovered, failure_sessions),
        "silence_initiative_rate": _bounded_rate(silence_initiated, silence_sessions),
        "project_resumption_count": project_resumptions,
        "prospective_review_count": prospective_reviews,
        "prospective_forecast_change_count": prospective_forecast_changes,
        "prospective_review_choice_link_rate": _bounded_rate(prospective_review_choice_links, prospective_reviews),
        "memory_carryover_rate": _bounded_rate(memory_carryovers, max(0, len(snapshots) - 1)),
        "correction_session_count": correction_sessions,
        "failure_session_count": failure_sessions,
        "silence_session_count": silence_sessions,
        "personality_evolution_rate": _bounded_rate(personality_changes_with_choices, personality_changes),
        "personality_change_count": personality_changes,
        "opportunity_engagement_rate": _bounded_rate(sum(_text(item.get("status")) == "engaged" for item in replay_opportunities), len(replay_opportunities)),
        "opportunity_timing_quality": _bounded_rate(sum(_text(item.get("status")) == "engaged" and 0 < _timestamp_seconds(item.get("resolvedAt")) - _timestamp_seconds(item.get("openedAt")) <= 120 for item in replay_opportunities), sum(_text(item.get("status")) == "engaged" for item in replay_opportunities)),
        "opportunity_unanswered_rate": _bounded_rate(sum(_text(item.get("status")) == "unanswered" for item in replay_opportunities), len(replay_opportunities)),
        "episode_outcome_progression_count": episode_progressions,
        "episode_adaptation_rate": _bounded_rate(episode_adaptations, max(0, len(snapshots) - 1)),
        "episode_failure_count": episode_failure_count,
        "homeostatic_change_count": homeostasis_changes,
        "reflection_reuse_count": reflection_reuse_count,
        "reflection_to_choice_rate": _bounded_rate(reflection_reuse_count, reflection_choice_opportunities),
        "intention_resumption_count": intention_resumptions,
        "intention_revision_count": intention_revisions,
        "stale_intention_expiration_count": stale_intention_expirations,
        "resumed_intention_adaptation_rate": _bounded_rate(resumed_intention_adaptations, intention_resumptions),
        "emotion_reactivity_rate": _bounded_rate(emotion_reactions, emotion_opportunities),
        "emotion_reaction_count": emotion_reactions,
        "emotion_reaction_opportunities": emotion_opportunities,
        "private_activity_variety_session_rate": _bounded_rate(activity_variety_sessions, max(0, len(snapshots) - 1)),
    }
    parts = [metrics[key] for key in ("correction_adaptation_rate", "failure_recovery_rate", "silence_initiative_rate", "memory_carryover_rate", "opportunity_timing_quality", "resumed_intention_adaptation_rate") if metrics[key] is not None]
    metrics["replay_quality"] = round(sum(parts) / len(parts), 3) if parts else None
    return metrics


def _main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: python -m bot.aliveness_eval JOURNAL.json [OTHER_JOURNAL.json ...]")
    snapshots = [json.loads(Path(path).read_text(encoding="utf-8")) for path in argv[1:]]
    result = {"metrics": evaluate_snapshot(snapshots[0])}
    if len(snapshots) == 2:
        result["instance_divergence"] = instance_divergence(*snapshots)
    if len(snapshots) > 2:
        result["replay"] = evaluate_replay(snapshots)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    _main(sys.argv)
