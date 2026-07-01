"""Deterministic CTA templates for stable conversation modes."""

from __future__ import annotations

import re
from typing import Any

from src.agent.cta_validation import validate_actions
from src.agent.response_actions import (
    assignee_answered_actions,
    broad_status_actions,
    confirmation_actions,
    due_date_answered_actions,
    duplicate_detected_actions,
    no_results_range_actions,
    out_of_scope_actions,
    post_create_actions,
    post_create_bug_actions,
    post_create_feature_actions,
    soft_pivot_actions,
    specific_task_actions,
    starter_actions,
    task_list_pivot_actions,
    time_snapshot_actions,
)

_CLARIFY_SYMPTOM_EXAMPLES = (
    {
        "id": "example_login",
        "label": "Login button issue",
        "type": "quick_reply",
        "payload": "The login button doesn't respond when I tap it on mobile.",
    },
    {
        "id": "example_checkout",
        "label": "Checkout error",
        "type": "quick_reply",
        "payload": "Checkout shows a 500 error after I submit the form.",
    },
    {
        "id": "example_data",
        "label": "Wrong data showing",
        "type": "quick_reply",
        "payload": "The patient data on the dashboard looks inconsistent.",
    },
)

_CLARIFY_QUICK_REPLIES = _CLARIFY_SYMPTOM_EXAMPLES

_CLARIFY_PIVOTS = (
    {
        "id": "list_open",
        "label": "List open tasks",
        "type": "quick_reply",
        "payload": "List my open tasks",
    },
)

_GENERAL_PIVOTS = (
    {
        "id": "report_bug",
        "label": "Report a bug",
        "type": "quick_reply",
        "payload": "I want to report a bug",
    },
    {
        "id": "check_status",
        "label": "Check project status",
        "type": "quick_reply",
        "payload": "Check project status",
    },
    {
        "id": "request_feature",
        "label": "Request a feature",
        "type": "quick_reply",
        "payload": "I want to request a feature",
    },
    {
        "id": "due_week",
        "label": "What's due this week?",
        "type": "quick_reply",
        "payload": "What's due this week?",
    },
)

_FULL_LIST_THRESHOLD = 3
_LABEL_MAX = 32


def _structured_tasks(state: dict[str, Any]) -> list[dict[str, Any]]:
    raw = state.get("structured_tasks") or []
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _task_count(state: dict[str, Any]) -> int:
    structured = _structured_tasks(state)
    if structured:
        return len(structured)
    reply = state.get("final_response") or ""
    return len(re.findall(r"^\d+\.\s+", reply, re.MULTILINE))


def _is_full_task_list(state: dict[str, Any]) -> bool:
    return _task_count(state) >= _FULL_LIST_THRESHOLD


def _short_label(title: str) -> str:
    text = (title or "Untitled").strip()
    if len(text) <= _LABEL_MAX:
        return text
    return text[: _LABEL_MAX - 1].rstrip() + "…"


def _task_specific_actions(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in tasks[:2]:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        actions.append({
            "id": f"task_{item.get('taskId', _short_label(title))}",
            "label": _short_label(title),
            "type": "quick_reply",
            "payload": f"What is the status of {title}?",
        })
    return actions


def template_confirmation() -> list[dict[str, str]]:
    return validate_actions(confirmation_actions())


def template_starters(max_actions: int = 4) -> list[dict[str, str]]:
    return validate_actions(starter_actions(), max_actions=max_actions, quick_reply_only=True)


def template_greeting(max_actions: int = 4) -> list[dict[str, str]]:
    return template_starters(max_actions=max_actions)


def template_out_of_scope(max_actions: int = 3) -> list[dict[str, str]]:
    return validate_actions(out_of_scope_actions(), max_actions=max_actions, quick_reply_only=True)


def template_no_results_range(max_actions: int = 3) -> list[dict[str, str]]:
    return validate_actions(no_results_range_actions(), max_actions=max_actions, quick_reply_only=True)


def template_soft_pivot(max_actions: int = 2) -> list[dict[str, str]]:
    return validate_actions(soft_pivot_actions(), max_actions=max_actions, quick_reply_only=True)


def template_post_create_bug() -> list[dict[str, str]]:
    return validate_actions(post_create_bug_actions(), quick_reply_only=True)


def template_post_create_feature() -> list[dict[str, str]]:
    return validate_actions(post_create_feature_actions(), quick_reply_only=True)


def template_duplicate_detected() -> list[dict[str, str]]:
    return validate_actions(duplicate_detected_actions(), quick_reply_only=True)


def template_broad_status() -> list[dict[str, str]]:
    return validate_actions(broad_status_actions(), quick_reply_only=True)


def template_time_snapshot() -> list[dict[str, str]]:
    return validate_actions(time_snapshot_actions(), quick_reply_only=True)


def template_assignee_answered() -> list[dict[str, str]]:
    return validate_actions(assignee_answered_actions(), quick_reply_only=True)


def template_due_date_answered() -> list[dict[str, str]]:
    return validate_actions(due_date_answered_actions(), quick_reply_only=True)


def template_specific_task(_state: dict[str, Any] | None = None) -> list[dict[str, str]]:
    return validate_actions(specific_task_actions(), quick_reply_only=True)


def template_for_scenario(scenario: str, state: dict[str, Any], ctx: Any, max_actions: int) -> list[dict[str, str]]:
    """Return fallback chips for a resolved CTA scenario."""
    if scenario in {"new_session", "returning_social"}:
        return template_starters(max_actions=max_actions)
    if scenario == "out_of_scope":
        return template_out_of_scope(max_actions=max_actions)
    if scenario == "no_results_range":
        return template_no_results_range(max_actions=max_actions)
    if scenario in {"general_chat", "no_results"}:
        return template_out_of_scope(max_actions=max_actions)
    if scenario == "collecting":
        return template_clarify_collecting(
            getattr(ctx, "clarification_target", "other"),
            getattr(ctx, "allowed_areas", ()),
            max_actions=max_actions,
        )
    if scenario == "confirming":
        return template_confirmation()
    if scenario == "duplicate_detected":
        return template_duplicate_detected()
    if scenario == "post_create_bug":
        return template_post_create_bug()
    if scenario == "post_create_feature":
        return template_post_create_feature()
    if scenario in {"post_create_task", "post_create"}:
        return template_task_created()
    if scenario == "broad_status":
        return template_broad_status()
    if scenario == "time_snapshot":
        return template_time_snapshot()
    if scenario == "assignee_answered":
        return template_assignee_answered()
    if scenario == "due_date_answered":
        return template_due_date_answered()
    if scenario == "specific_task":
        return template_specific_task()
    if scenario == "task_list":
        return template_broad_status()
    return template_soft_pivot(max_actions=min(max_actions, 2))


def template_task_created() -> list[dict[str, str]]:
    return validate_actions(post_create_actions())


def template_task_list(state: dict[str, Any]) -> list[dict[str, str]]:
    reply_lower = (state.get("final_response") or "").lower()
    structured = _structured_tasks(state)
    count = _task_count(state)

    if "nothing matching" in reply_lower or "didn't find" in reply_lower:
        return validate_actions([
            {
                "id": "list_open",
                "label": "List all open tasks",
                "type": "quick_reply",
                "payload": "List my open tasks",
            },
            {
                "id": "last_month",
                "label": "Try last month",
                "type": "quick_reply",
                "payload": "What about last month?",
            },
            {
                "id": "this_week",
                "label": "Due this week",
                "type": "quick_reply",
                "payload": "Show tasks due this week",
            },
        ])

    if "completed" in reply_lower:
        if count <= 2:
            actions = _task_specific_actions(structured)
            actions.extend([
                {
                    "id": "show_open",
                    "label": "Show open tasks",
                    "type": "quick_reply",
                    "payload": "List my open tasks",
                },
                {
                    "id": "show_in_progress",
                    "label": "Show in progress",
                    "type": "quick_reply",
                    "payload": "Show tasks in progress",
                },
            ])
            return validate_actions(actions)
        return validate_actions(task_list_pivot_actions())

    if _is_full_task_list(state):
        return validate_actions(task_list_pivot_actions()[:3])

    actions = _task_specific_actions(structured)
    if actions:
        actions.append({
            "id": "log_new",
            "label": "Log new issue",
            "type": "quick_reply",
            "payload": "I want to report a new issue",
        })
        return validate_actions(actions)

    return validate_actions(task_list_pivot_actions()[:3])


def _where_area_actions(areas: tuple[str, ...] | list[str], max_actions: int = 3) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for area in list(areas)[:max_actions]:
        name = str(area).strip()
        if not name:
            continue
        slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "area"
        actions.append({
            "id": f"area_{slug}",
            "label": name,
            "type": "quick_reply",
            "payload": f"I'm seeing it on the {name}.",
        })
    return actions


def template_clarify_collecting(
    clarification_target: str,
    allowed_areas: tuple[str, ...] | list[str] = (),
    max_actions: int = 3,
) -> list[dict[str, str]]:
    """Fallback CTAs during issue logging — answers only, no pivots."""
    if clarification_target == "where" and allowed_areas:
        return validate_actions(
            _where_area_actions(allowed_areas, max_actions=max_actions),
            max_actions=max_actions,
            quick_reply_only=True,
        )
    return validate_actions(
        _CLARIFY_SYMPTOM_EXAMPLES,
        max_actions=max_actions,
        quick_reply_only=True,
    )


def template_post_answer(
    answered_topics: frozenset[str] | set[str],
    max_actions: int = 3,
) -> list[dict[str, str]]:
    """Legacy alias — delegates to scenario-specific templates."""
    topics = set(answered_topics)
    if "assignee" in topics:
        return template_assignee_answered()
    if "due_date" in topics:
        return template_due_date_answered()
    return template_assignee_answered()


def template_clarify(max_actions: int = 4) -> list[dict[str, str]]:
    return validate_actions(
        [*_CLARIFY_SYMPTOM_EXAMPLES],
        max_actions=max_actions,
        quick_reply_only=True,
    )


def template_general(state: dict[str, Any]) -> list[dict[str, str]]:
    if state.get("structured_tasks"):
        return template_task_list(state)
    return validate_actions(_GENERAL_PIVOTS)


def template_soft_pending() -> list[dict[str, str]]:
    return validate_actions([
        *_GENERAL_PIVOTS,
        {
            "id": "confirm_yes",
            "label": "Yes, log it",
            "type": "quick_reply",
            "payload": "yes",
        },
    ])
