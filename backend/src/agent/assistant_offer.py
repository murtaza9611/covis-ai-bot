"""Assistant offer tracking and affirmation acceptance (e.g. broaden search)."""

from __future__ import annotations

import re
from typing import Any

BROADEN_SEARCH_TYPE = "broaden_search"
BROADEN_RESOLVED_ACTION = "Show all open tasks and give a broader project overview"
BROADEN_PROMPT_TEXT = "Want to try a broader look?"

_BROADEN_OFFER_MARKERS = (
    "broader look",
    "try a broader",
    "want to try a broader",
    "broader view",
    "broader search",
)

_AFFIRMATION_PAT = re.compile(
    r"^\s*("
    r"y|yes|yeah|yep|yup|sure|ok|okay|"
    r"go\b|go ahead|"
    r"do it|please|"
    r"sounds good|that works|"
    r"yeah sure|yes sure|sure thing"
    r")(?:\s+.*)?[\s!.?…]*$",
    re.IGNORECASE,
)


def is_short_affirmation(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) > 80:
        return False
    return bool(_AFFIRMATION_PAT.match(t))


def assistant_offered_broaden(text: str) -> bool:
    lower = (text or "").lower()
    return any(m in lower for m in _BROADEN_OFFER_MARKERS)


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


def last_assistant_message(conversation_history: str) -> str | None:
    for role, text in reversed(_parse_history_turns(conversation_history)):
        if role == "assistant" and text:
            return text
    return None


def get_broaden_offer(triage_state: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(triage_state, dict):
        return None
    offer = triage_state.get("last_assistant_offer")
    if not isinstance(offer, dict):
        return None
    if offer.get("type") != BROADEN_SEARCH_TYPE:
        return None
    return offer


def store_broaden_offer(
    triage_state: dict[str, Any],
    *,
    prior_query: str,
    prior_start_date: str | None,
    prior_end_date: str | None,
) -> None:
    triage_state["last_assistant_offer"] = {
        "type": BROADEN_SEARCH_TYPE,
        "prompt": BROADEN_PROMPT_TEXT,
        "prior_query": (prior_query or "").strip(),
        "prior_start_date": prior_start_date,
        "prior_end_date": prior_end_date,
        "resolved_action": BROADEN_RESOLVED_ACTION,
    }


def clear_assistant_offer(triage_state: dict[str, Any]) -> None:
    triage_state.pop("last_assistant_offer", None)


def broaden_offer_pending(
    conversation_history: str,
    triage_state: dict[str, Any] | None,
) -> bool:
    offer = get_broaden_offer(triage_state)
    if offer:
        return True
    last = last_assistant_message(conversation_history)
    return bool(last and assistant_offered_broaden(last))


def resolve_broaden_acceptance(
    user_query: str,
    conversation_history: str,
    triage_state: dict[str, Any] | None,
) -> str | None:
    """If user affirms a broaden offer, return the standalone broad query."""
    if not is_short_affirmation(user_query):
        return None
    if not broaden_offer_pending(conversation_history, triage_state):
        return None
    offer = get_broaden_offer(triage_state)
    if offer:
        action = (offer.get("resolved_action") or "").strip()
        if action:
            return action
    return BROADEN_RESOLVED_ACTION


def detect_broaden_acceptance(
    user_query: str,
    conversation_history: str,
    triage_state: dict[str, Any] | None,
) -> bool:
    return resolve_broaden_acceptance(user_query, conversation_history, triage_state) is not None
