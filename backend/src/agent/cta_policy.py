"""Intent + sub-stage CTA policy registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from src.agent.cta_context import (
    CtaContext,
    build_cta_context,
    detect_answered_topics,
    is_active_issue_logging,
)
from src.agent.triage_memory import ensure_triage_state, get_active_incident

CtaType = Literal["starters", "answer", "confirmation", "drill_down", "next_step", "soft_pivot"]

TASK_TYPE_BUG = 36
TASK_TYPE_STORY = 37

_TIME_SNAPSHOT_PHRASES = (
    "today",
    "this week",
    "last week",
    "what happened",
    "yesterday",
    "what went on",
)

_BROAD_STATUS_PHRASES = (
    "project status",
    "what's going on",
    "whats going on",
    "open bugs",
    "open tasks",
    "overview",
    "give me an update",
    "status update",
)

_NO_RESULTS_MARKERS = (
    "nothing matching",
    "didn't find",
    "did not find",
    "no tasks",
    "couldn't find",
    "could not find",
    "nothing due",
    "nothing in progress",
    "don't see any",
    "do not see any",
    "there's nothing",
    "there is nothing",
    "nothing open",
    "no open bugs",
    "no matching",
    "don't have any",
    "do not have any",
    "no tasks due",
    "don't have any tasks",
    "we don't have any tasks",
    "we do not have any tasks",
    "none due",
    "no tasks due this week",
    "no tasks were due",
)

_DUPLICATE_REPLY_MARKERS = (
    "already something we're tracking",
    "already tracking",
    "might overlap",
    "existing task",
)


@dataclass(frozen=True)
class CtaPolicy:
    cta_type: CtaType
    scenario: str
    intent: str
    sub_stage: str
    min_actions: int
    max_actions: int
    use_llm: bool
    suppress_pivots: bool
    merge_templates: bool


def _reply_text(state: dict[str, Any]) -> str:
    return (state.get("final_response") or "").strip()


def _is_new_conversation(state: dict[str, Any]) -> bool:
    return not (state.get("conversation_history") or "").strip()


def _has_pending_confirmation(state: dict[str, Any]) -> bool:
    triage = state.get("triage_state") or {}
    pending = triage.get("pending_confirmation") or state.get("pending_task_payload") or {}
    if not isinstance(pending, dict):
        return False
    return bool(pending.get("task_payload"))


def _is_confirmation_reply(reply: str) -> bool:
    text = (reply or "").lower()
    return any(
        marker in text
        for marker in ("want me to log", "ready to log", "should i log", "log it?", "log this", "confirm")
    )


def _intent(state: dict[str, Any]) -> str:
    return str(state.get("intent") or "general_chat").lower()


def _response_kind(state: dict[str, Any]) -> str:
    return str(state.get("response_kind") or "text").lower()


def _cta_scenario(state: dict[str, Any]) -> str:
    return str(state.get("cta_scenario") or "").strip().lower()


def _structured_tasks(state: dict[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("structured_tasks") or []
    if not isinstance(raw, list):
        return []
    return [t for t in raw if isinstance(t, dict)]


def _task_type_id(state: dict[str, Any]) -> int | None:
    explicit = _cta_scenario(state)
    if explicit.startswith("post_create_"):
        pass
    pms = state.get("pms_response")
    if isinstance(pms, dict):
        raw = pms.get("taskTypeId")
        try:
            return int(raw) if raw is not None else None
        except (TypeError, ValueError):
            pass
    triage = ensure_triage_state(state.get("triage_state"))
    pending = triage.get("pending_confirmation") or {}
    if isinstance(pending, dict):
        payload = pending.get("task_payload") or {}
        if isinstance(payload, dict):
            try:
                return int(payload.get("taskTypeId")) if payload.get("taskTypeId") is not None else None
            except (TypeError, ValueError):
                pass
    return None


def _is_time_snapshot_query(user_query: str) -> bool:
    q = (user_query or "").lower()
    return any(p in q for p in _TIME_SNAPSHOT_PHRASES)


def _is_broad_status_query(user_query: str) -> bool:
    q = (user_query or "").lower()
    return any(p in q for p in _BROAD_STATUS_PHRASES)


def is_no_results_reply(reply: str) -> bool:
    lower = (reply or "").lower()
    return any(m in lower for m in _NO_RESULTS_MARKERS)


def _is_empty_task_list(state: dict[str, Any]) -> bool:
    if str(state.get("response_kind") or "").lower() != "task_list":
        return False
    return not _structured_tasks(state)


def _is_empty_task_summary(state: dict[str, Any], reply: str) -> bool:
    if str(state.get("response_kind") or "").lower() != "task_summary":
        return False
    if _structured_tasks(state):
        return False
    return is_no_results_reply(reply)


def is_time_range_context(state: dict[str, Any], user_query: str = "") -> bool:
    """True when the user is asking about a calendar window (week, today, etc.)."""
    q = str(state.get("resolved_query") or user_query or state.get("user_query") or "").lower()
    if _is_time_snapshot_query(q):
        return True
    if any(p in q for p in ("due this week", "due next week", "this month", "last week")):
        return True
    scenario = _cta_scenario(state)
    if scenario in {"time_snapshot", "no_results_range"}:
        return True
    triage = state.get("triage_state") or {}
    last = triage.get("last_task_query") if isinstance(triage, dict) else None
    if isinstance(last, dict):
        last_q = str(last.get("query") or "").lower()
        if _is_time_snapshot_query(last_q) or "due this week" in last_q:
            return True
    return False


def _looks_like_duplicate_reply(reply: str) -> bool:
    lower = (reply or "").lower()
    return any(m in lower for m in _DUPLICATE_REPLY_MARKERS)


def _policy(
    cta_type: CtaType,
    scenario: str,
    intent: str,
    sub_stage: str,
    *,
    min_actions: int = 2,
    max_actions: int = 3,
    use_llm: bool = True,
    suppress_pivots: bool = False,
    merge_templates: bool = False,
) -> CtaPolicy:
    return CtaPolicy(
        cta_type=cta_type,
        scenario=scenario,
        intent=intent,
        sub_stage=sub_stage,
        min_actions=min_actions,
        max_actions=max_actions,
        use_llm=use_llm,
        suppress_pivots=suppress_pivots,
        merge_templates=merge_templates,
    )


def resolve_sub_stage(state: dict[str, Any], ctx: CtaContext) -> tuple[str, str]:
    """Return (intent, sub_stage) for policy lookup."""
    intent = _intent(state)
    scenario_hint = _cta_scenario(state)
    response_kind = _response_kind(state)
    reply = _reply_text(state)
    user_query = str(state.get("user_query") or "")

    if intent == "get_task_info" and (
        scenario_hint in {"no_results", "no_results_range"}
        or is_no_results_reply(reply)
        or _is_empty_task_list(state)
        or _is_empty_task_summary(state, reply)
    ):
        if scenario_hint == "no_results_range" or is_time_range_context(state, user_query):
            return ("get_task_info", "no_results_time")
        return ("get_task_info", "no_results")

    if scenario_hint:
        scenario_to_sub = {
            "starters": ("greet", "new_session"),
            "new_session": ("greet", "new_session"),
            "returning_social": ("greet", "returning_social"),
            "duplicate_detected": ("create_task", "duplicate_detected"),
            "post_create_bug": ("create_task", "post_create_bug"),
            "post_create_feature": ("create_task", "post_create_feature"),
            "post_create_task": ("create_task", "post_create_task"),
            "broad_status": ("get_task_info", "broad_status"),
            "time_snapshot": ("get_task_info", "time_snapshot"),
            "assignee_answered": ("get_task_info", "assignee_answered"),
            "due_date_answered": ("get_task_info", "due_date_answered"),
            "specific_task": ("get_task_info", "specific_task"),
            "no_results": ("get_task_info", "no_results"),
            "no_results_range": ("get_task_info", "no_results_time"),
            "out_of_scope": ("clarify", "out_of_scope"),
        }
        if scenario_hint in scenario_to_sub:
            return scenario_to_sub[scenario_hint]

    if intent == "greet":
        return ("greet", "new_session" if _is_new_conversation(state) else "returning_social")

    if intent == "general_chat":
        return ("general_chat", "active")

    if intent == "create_task":
        if scenario_hint == "duplicate_detected" or (
            response_kind == "text" and _looks_like_duplicate_reply(reply)
        ):
            return ("create_task", "duplicate_detected")
        if (
            _has_pending_confirmation(state)
            and response_kind == "pending_confirmation"
            and _is_confirmation_reply(reply)
        ):
            return ("create_task", "confirming")
        if response_kind == "task_created":
            tt = _task_type_id(state)
            if tt == TASK_TYPE_BUG:
                return ("create_task", "post_create_bug")
            if tt == TASK_TYPE_STORY:
                return ("create_task", "post_create_feature")
            return ("create_task", "post_create_task")
        if is_active_issue_logging(state):
            return ("create_task", "collecting")
        triage = ensure_triage_state(state.get("triage_state"))
        if get_active_incident(triage) and get_active_incident(triage).get("status") == "collecting":
            return ("create_task", "collecting")
        return ("create_task", "collecting")

    if intent == "get_task_info":
        if _is_time_snapshot_query(user_query) or scenario_hint == "time_snapshot":
            return ("get_task_info", "time_snapshot")
        answered = detect_answered_topics(reply, user_query)
        if response_kind == "task_summary":
            if "assignee" in answered:
                return ("get_task_info", "assignee_answered")
            if "due_date" in answered:
                return ("get_task_info", "due_date_answered")
            tasks = _structured_tasks(state)
            if len(tasks) == 1:
                return ("get_task_info", "specific_task")
            return ("get_task_info", "specific_task")
        if response_kind == "task_list":
            if _is_broad_status_query(user_query) or len(_structured_tasks(state)) >= 3:
                return ("get_task_info", "broad_status")
            return ("get_task_info", "task_list")
        if _is_broad_status_query(user_query):
            return ("get_task_info", "broad_status")
        return ("get_task_info", "task_list")

    if intent == "clarify":
        if _is_new_conversation(state):
            return ("clarify", "new_session")
        if is_active_issue_logging(state):
            return ("clarify", "collecting")
        return ("clarify", "out_of_scope")

    return ("general_chat", "active")


_POLICY_MATRIX: dict[tuple[str, str], CtaPolicy] = {
    ("greet", "new_session"): _policy("starters", "new_session", "greet", "new_session", min_actions=3, max_actions=4, use_llm=False),
    ("greet", "returning_social"): _policy("starters", "new_session", "greet", "returning_social", min_actions=3, max_actions=4, use_llm=False),
    ("general_chat", "active"): _policy("soft_pivot", "general_chat", "general_chat", "active", min_actions=0, max_actions=2),
    ("create_task", "collecting"): _policy("answer", "collecting", "create_task", "collecting", min_actions=2, max_actions=3, suppress_pivots=True),
    ("create_task", "confirming"): _policy("confirmation", "confirming", "create_task", "confirming", min_actions=3, max_actions=3, use_llm=False),
    ("create_task", "duplicate_detected"): _policy("next_step", "duplicate_detected", "create_task", "duplicate_detected", min_actions=2, max_actions=2, use_llm=False),
    ("create_task", "post_create_bug"): _policy("next_step", "post_create_bug", "create_task", "post_create_bug", min_actions=3, max_actions=3, use_llm=False),
    ("create_task", "post_create_feature"): _policy("next_step", "post_create_feature", "create_task", "post_create_feature", min_actions=2, max_actions=2, use_llm=False),
    ("create_task", "post_create_task"): _policy("next_step", "post_create_task", "create_task", "post_create_task", min_actions=2, max_actions=3, use_llm=False),
    ("get_task_info", "task_list"): _policy("drill_down", "broad_status", "get_task_info", "task_list", min_actions=3, max_actions=3, use_llm=False),
    ("get_task_info", "broad_status"): _policy("drill_down", "broad_status", "get_task_info", "broad_status", min_actions=3, max_actions=3, use_llm=False),
    ("get_task_info", "specific_task"): _policy("next_step", "specific_task", "get_task_info", "specific_task", min_actions=3, max_actions=3, use_llm=False),
    ("get_task_info", "assignee_answered"): _policy("next_step", "assignee_answered", "get_task_info", "assignee_answered", min_actions=3, max_actions=3, suppress_pivots=True, use_llm=False),
    ("get_task_info", "due_date_answered"): _policy("next_step", "due_date_answered", "get_task_info", "due_date_answered", min_actions=2, max_actions=2, suppress_pivots=True, use_llm=False),
    ("get_task_info", "time_snapshot"): _policy("drill_down", "time_snapshot", "get_task_info", "time_snapshot", min_actions=2, max_actions=2, use_llm=False),
    ("get_task_info", "no_results"): _policy("starters", "out_of_scope", "get_task_info", "no_results", min_actions=3, max_actions=3, use_llm=False),
    ("get_task_info", "no_results_time"): _policy("starters", "no_results_range", "get_task_info", "no_results_time", min_actions=3, max_actions=3, use_llm=False),
    ("clarify", "new_session"): _policy("starters", "new_session", "clarify", "new_session", min_actions=3, max_actions=4, use_llm=False),
    ("clarify", "out_of_scope"): _policy("starters", "out_of_scope", "clarify", "out_of_scope", min_actions=3, max_actions=3, use_llm=False),
    ("clarify", "collecting"): _policy("answer", "collecting", "clarify", "collecting", min_actions=2, max_actions=3, suppress_pivots=True),
}


def resolve_policy(state: dict[str, Any], ctx: CtaContext | None = None) -> CtaPolicy:
    context = ctx or build_cta_context(state)
    intent, sub_stage = resolve_sub_stage(state, context)
    key = (intent, sub_stage)
    if key in _POLICY_MATRIX:
        policy = _POLICY_MATRIX[key]
        if policy.suppress_pivots or context.suppress_pivots:
            return CtaPolicy(
                cta_type=policy.cta_type,
                scenario=policy.scenario,
                intent=policy.intent,
                sub_stage=policy.sub_stage,
                min_actions=policy.min_actions,
                max_actions=policy.max_actions,
                use_llm=policy.use_llm,
                suppress_pivots=True,
                merge_templates=policy.merge_templates,
            )
        return policy
    return _policy("soft_pivot", "fallback", intent, sub_stage, min_actions=0, max_actions=2)
