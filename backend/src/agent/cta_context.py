"""Workflow and relevance context for reply-first CTA generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from src.agent.cta_product_areas import DEFAULT_PRODUCT_AREAS
from src.agent.triage_memory import ensure_triage_state, get_active_incident

WorkflowStage = Literal[
    "collecting",
    "confirming",
    "post_create",
    "post_answer",
    "idle",
]

ClarificationTarget = Literal["what", "where", "when", "who", "severity", "repro", "other"]

_ASSIGNEE_QUESTION_PHRASES = (
    "who's working",
    "who is working",
    "who working on",
    "who is assigned",
    "who's assigned",
    "assigned to who",
)

_DUE_QUESTION_PHRASES = (
    "when is it due",
    "when's it due",
    "what's the due date",
    "what is the due date",
    "due date",
)

_STATUS_QUESTION_PHRASES = (
    "what's the status",
    "what is the status",
    "current status",
    "how far along",
)

_PIVOT_PAYLOAD_FRAGMENTS = (
    "list my open tasks",
    "list all open",
    "i want to report a bug",
    "i want to report a new issue",
    "check project status",
    "i want to request a feature",
    "what's due this week",
    "what can you help me with",
)

_ASSIGNEE_ANSWER_MARKERS = (
    " is assigned",
    "assigned to ",
    "working on it",
    "tackling it",
    "will be the one",
)


@dataclass(frozen=True)
class CtaContext:
    workflow_stage: WorkflowStage
    clarification_target: ClarificationTarget
    suppress_pivots: bool
    answered_topics: frozenset[str]
    incident_draft: str
    assistant_question: str
    allowed_areas: tuple[str, ...]
    banned_phrases: frozenset[str]


def _reply_text(state: dict[str, Any]) -> str:
    return (state.get("final_response") or "").strip()


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
        for marker in (
            "want me to log",
            "ready to log",
            "should i log",
            "log it?",
            "log this",
            "confirm",
        )
    )


def is_active_issue_logging(state: dict[str, Any]) -> bool:
    """True while the user is mid-flow logging an issue (before confirmation)."""
    if _has_pending_confirmation(state):
        return False
    triage = ensure_triage_state(state.get("triage_state"))
    active = get_active_incident(triage)
    if active and active.get("status") == "collecting":
        return True
    intent = str(state.get("intent") or "").lower()
    response_kind = str(state.get("response_kind") or "").lower()
    if response_kind == "clarify" and intent in {"create_task", "clarify"}:
        return True
    if intent == "create_task" and response_kind in {"clarify", "text"}:
        return True
    return False


def infer_clarification_target(reply: str) -> ClarificationTarget:
    text = (reply or "").lower()
    if "?" in reply or any(w in text for w in ("share", "tell me", "can you")):
        if any(w in text for w in ("where", "which screen", "which page", "which module", "which part", "which area")):
            return "where"
        if any(
            w in text
            for w in (
                "what issue",
                "what exactly",
                "what is going",
                "what's going",
                "what went",
                "what happened",
                "what problem",
                "what did you notice",
                "what are you seeing",
            )
        ):
            return "what"
        if any(w in text for w in ("when", "how long", "how often", "since when")):
            return "when"
        if any(w in text for w in ("who", "assign")):
            return "who"
        if any(w in text for w in ("severity", "priority", "how bad", "how critical")):
            return "severity"
        if any(w in text for w in ("repro", "steps to", "how do i reproduce", "how can i reproduce")):
            return "repro"
    return "other"


def _extract_assistant_question(reply: str) -> str:
    text = (reply or "").strip()
    if not text:
        return ""
    parts = re.split(r"(?<=[?.!])\s+", text)
    for segment in reversed(parts):
        if "?" in segment:
            return segment.strip()
    if text.endswith("?"):
        return text
    return text


def detect_answered_topics(reply: str, user_query: str) -> frozenset[str]:
    topics: set[str] = set()
    r = (reply or "").lower()
    u = (user_query or "").lower()

    if any(p in u for p in _ASSIGNEE_QUESTION_PHRASES):
        if any(m in r for m in _ASSIGNEE_ANSWER_MARKERS) or re.search(r"\b[a-z][a-z']+\s+is assigned\b", r):
            topics.add("assignee")

    if any(p in u for p in _DUE_QUESTION_PHRASES):
        if any(w in r for w in ("due", "deadline", "by friday", "by monday", "next week")):
            topics.add("due_date")

    if any(p in u for p in _STATUS_QUESTION_PHRASES):
        if any(w in r for w in ("status", "progress", "in progress", "open", "closed", "blocked")):
            topics.add("status")

    if not topics and any(m in r for m in _ASSIGNEE_ANSWER_MARKERS):
        if any(p in u for p in _ASSIGNEE_QUESTION_PHRASES):
            topics.add("assignee")

    return frozenset(topics)


def _incident_draft_summary(state: dict[str, Any]) -> str:
    triage = ensure_triage_state(state.get("triage_state"))
    active = get_active_incident(triage)
    if not active:
        return ""
    parts = [
        str(active.get("title_draft") or "").strip(),
        str(active.get("draft_text") or "").strip(),
        str(active.get("scope") or "").strip(),
    ]
    return " ".join(p for p in parts if p).strip()


def resolve_allowed_areas(state: dict[str, Any], reply: str) -> tuple[str, ...]:
    """Hybrid: conversation/draft mentions first, then configured defaults for 'where' questions."""
    combined = " ".join(
        filter(
            None,
            [
                state.get("conversation_history") or "",
                state.get("user_query") or "",
                _incident_draft_summary(state),
            ],
        )
    ).lower()

    matched = [area for area in DEFAULT_PRODUCT_AREAS if area.lower() in combined]
    if matched:
        return tuple(dict.fromkeys(matched))

    if infer_clarification_target(reply) == "where":
        return DEFAULT_PRODUCT_AREAS[:4]
    return ()


def _build_banned_phrases(user_query: str, answered_topics: frozenset[str]) -> frozenset[str]:
    banned: set[str] = set()
    if "assignee" in answered_topics:
        banned.update(_ASSIGNEE_QUESTION_PHRASES)
    if "due_date" in answered_topics:
        banned.update(_DUE_QUESTION_PHRASES)
    if "status" in answered_topics:
        banned.update(_STATUS_QUESTION_PHRASES)
    return frozenset(banned)


def derive_workflow_stage(state: dict[str, Any]) -> WorkflowStage:
    response_kind = str(state.get("response_kind") or "text").lower()
    reply = _reply_text(state)

    if (
        _has_pending_confirmation(state)
        and response_kind == "pending_confirmation"
        and _is_confirmation_reply(reply)
    ):
        return "confirming"

    if response_kind == "task_created":
        return "post_create"

    if is_active_issue_logging(state):
        return "collecting"

    if response_kind in {"task_summary", "task_list"} and str(state.get("intent") or "").lower() == "get_task_info":
        return "post_answer"

    if response_kind == "task_summary":
        return "post_answer"

    return "idle"


def build_cta_context(state: dict[str, Any]) -> CtaContext:
    reply = _reply_text(state)
    user_query = str(state.get("user_query") or "")
    workflow_stage = derive_workflow_stage(state)
    clarification_target = infer_clarification_target(reply)
    answered_topics = detect_answered_topics(reply, user_query)
    suppress_pivots = workflow_stage == "collecting" or is_active_issue_logging(state)

    return CtaContext(
        workflow_stage=workflow_stage,
        clarification_target=clarification_target,
        suppress_pivots=suppress_pivots,
        answered_topics=answered_topics,
        incident_draft=_incident_draft_summary(state),
        assistant_question=_extract_assistant_question(reply),
        allowed_areas=resolve_allowed_areas(state, reply),
        banned_phrases=_build_banned_phrases(user_query, answered_topics),
    )


def is_pivot_action(action: dict[str, str]) -> bool:
    payload = (action.get("payload") or "").lower()
    label = (action.get("label") or "").lower()
    combined = f"{payload} {label}"
    return any(fragment in combined for fragment in _PIVOT_PAYLOAD_FRAGMENTS)


def _is_assignee_question(text: str) -> bool:
    lower = (text or "").lower()
    return any(p in lower for p in _ASSIGNEE_QUESTION_PHRASES)


def _repeats_user_question(action: dict[str, str], user_query: str) -> bool:
    if not user_query.strip():
        return False
    payload = (action.get("payload") or "").lower()
    label = (action.get("label") or "").lower()
    u = user_query.lower().strip()

    if u in payload or u in label:
        return True

    if _is_assignee_question(u) and _is_assignee_question(payload + " " + label):
        return True
    if any(p in u for p in _DUE_QUESTION_PHRASES) and any(
        p in payload or p in label for p in _DUE_QUESTION_PHRASES
    ):
        return True
    if any(p in u for p in _STATUS_QUESTION_PHRASES) and any(
        p in payload or p in label for p in _STATUS_QUESTION_PHRASES
    ):
        return True
    return False


def filter_irrelevant_actions(
    actions: list[dict[str, str]],
    state: dict[str, Any],
    ctx: CtaContext,
) -> list[dict[str, str]]:
    user_query = str(state.get("user_query") or "")
    filtered: list[dict[str, str]] = []

    for action in actions:
        if ctx.suppress_pivots and is_pivot_action(action):
            continue
        if _repeats_user_question(action, user_query):
            continue
        if "assignee" in ctx.answered_topics and _is_assignee_question(
            f"{action.get('payload', '')} {action.get('label', '')}"
        ):
            continue
        if "due_date" in ctx.answered_topics and any(
            p in (action.get("payload") or "").lower() or p in (action.get("label") or "").lower()
            for p in _DUE_QUESTION_PHRASES
        ):
            continue
        if "status" in ctx.answered_topics and any(
            p in (action.get("payload") or "").lower() or p in (action.get("label") or "").lower()
            for p in _STATUS_QUESTION_PHRASES
        ):
            continue

        filtered.append(action)

    return filtered
