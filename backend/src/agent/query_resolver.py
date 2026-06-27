"""Resolve ambiguous user follow-ups using conversation history."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agent.prompts import QUERY_RESOLVE_PROMPT
from src.settings import settings

_AMBIGUOUS_FOLLOWUP_PAT = re.compile(
    r"^\s*("
    r"go for it|go ahead|do it|do that|sure|please|ok(?:ay)?|"
    r"yes please|yeah|yep|tell me more|continue|proceed|"
    r"that(?:'s fine| works| sounds good)?|sounds good|"
    r"what about that|how about that|same thing|"
    r"those details|more details|the details"
    r")[\s!.?…]*$",
    re.IGNORECASE,
)

_PRONOUN_FOLLOWUP_PAT = re.compile(
    r"^\s*(that|it|this|those|same)\b",
    re.IGNORECASE,
)

_TASK_CONTEXT_MARKERS = (
    "task",
    "bug",
    "issue",
    "summary",
    "update",
    "status",
    "progress",
    "list",
    "week",
    "month",
    "today",
    "yesterday",
    "due",
    "open",
    "report",
    "log",
    "create",
    "show",
    "details",
)

_UI_FEEDBACK_MARKERS = (
    "proper format",
    "not showing",
    "no space",
    "not enough space",
    "spacing",
    "hard to read",
    "display format",
    "looks wrong",
    "looks off",
    "messy",
    "cramped",
    "your message",
    "your reply",
    "your response",
    "the list",
    "task list",
    "how you showed",
    "how it shows",
    "formatting issue",
    "not in a proper format",
)

_UI_FEEDBACK_CONTEXT = (
    "format",
    "space",
    "spacing",
    "display",
    "showing",
    "render",
    "layout",
    "read",
    "message",
    "reply",
    "response",
    "list",
)


def looks_like_ui_display_feedback(text: str) -> bool:
    """Feedback about chat/list presentation — not a new product bug."""
    t = (text or "").lower().strip()
    if not t:
        return False
    if not any(m in t for m in _UI_FEEDBACK_MARKERS):
        return False
    if not any(w in t for w in _UI_FEEDBACK_CONTEXT):
        return False
    product_bug_hints = (
        "login",
        "checkout",
        "timeout",
        "crash",
        "500",
        "api error",
        "payment",
        "signup",
        "sign-up",
    )
    if any(h in t for h in product_bug_hints):
        return False
    return True


def is_ambiguous_followup(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if _AMBIGUOUS_FOLLOWUP_PAT.match(t):
        return True
    if len(t) <= 40 and _PRONOUN_FOLLOWUP_PAT.match(t):
        return True
    tl = t.lower()
    if len(t) <= 24 and not any(m in tl for m in _TASK_CONTEXT_MARKERS):
        if tl in {"yes", "yeah", "yep", "sure", "please", "ok", "okay", "go", "continue"}:
            return True
    return False


def _parse_history_turns(conversation_history: str) -> list[tuple[str, str]]:
    turns: list[tuple[str, str]] = []
    for line in (conversation_history or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("user:"):
            turns.append(("user", line[5:].strip()))
        elif line.lower().startswith("assistant:"):
            turns.append(("assistant", line[10:].strip()))
    return turns


def _last_substantive_user_message(turns: list[tuple[str, str]]) -> str | None:
    for role, text in reversed(turns):
        if role != "user":
            continue
        if text and not is_ambiguous_followup(text):
            return text
    return None


def _heuristic_resolve(user_query: str, conversation_history: str) -> str | None:
    turns = _parse_history_turns(conversation_history)
    prior = _last_substantive_user_message(turns)
    if not prior:
        return None
    q = (user_query or "").strip().lower()
    if _AMBIGUOUS_FOLLOWUP_PAT.match(user_query or ""):
        return prior
    if q in {"yes", "yeah", "yep", "sure", "please", "ok", "okay", "go", "continue"}:
        return prior
    if _PRONOUN_FOLLOWUP_PAT.match(user_query or ""):
        return prior
    return None


def _llm_resolve(user_query: str, conversation_history: str) -> str | None:
    if not (conversation_history or "").strip():
        return None
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    prompt = QUERY_RESOLVE_PROMPT.format(
        conversation_history=conversation_history.strip(),
        user_query=(user_query or "").strip(),
    )
    try:
        response = llm.invoke([
            SystemMessage(content="Return only valid JSON."),
            HumanMessage(content=prompt),
        ])
        raw = (response.content or "").strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None
        resolved = parsed.get("resolved_query")
        if isinstance(resolved, str) and resolved.strip():
            return resolved.strip()
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None
    return None


def resolve_query_with_history(
    user_query: str,
    conversation_history: str,
    triage_state: dict[str, Any] | None = None,
) -> str:
    """Return a standalone query; rephrase ambiguous follow-ups using history."""
    raw = (user_query or "").strip()
    if not raw:
        return raw
    if not is_ambiguous_followup(raw):
        return raw

    resolved = _heuristic_resolve(raw, conversation_history)
    if not resolved:
        resolved = _llm_resolve(raw, conversation_history)

    if not resolved and triage_state:
        last = triage_state.get("last_task_query") or {}
        if isinstance(last, dict):
            prior_query = last.get("query")
            if isinstance(prior_query, str) and prior_query.strip():
                resolved = prior_query.strip()

    return resolved or raw


def looks_like_task_followup(user_query: str, conversation_history: str) -> bool:
    """Short follow-up while recent history was a task/status ask."""
    if not is_ambiguous_followup(user_query):
        return False
    turns = _parse_history_turns(conversation_history)
    for role, text in reversed(turns[-6:]):
        if role != "user":
            continue
        tl = text.lower()
        if any(
            p in tl
            for p in (
                "summary",
                "update",
                "status",
                "task",
                "week",
                "month",
                "list",
                "progress",
                "what's going on",
                "whats going on",
                "details for",
                "show me",
                "give me",
            )
        ):
            return True
    return False
