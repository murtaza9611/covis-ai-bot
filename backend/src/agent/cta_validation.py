"""Validate and classify chat CTA actions."""

from __future__ import annotations

import re
from typing import Any, Literal

CtaActionType = Literal["quick_reply", "prefill"]

_MAX_ACTIONS = 3
_MAX_LABEL_LEN = 40
_MAX_PAYLOAD_LEN = 120

VALID_ACTION_TYPES = frozenset({"quick_reply", "prefill"})

# Legacy/non-action types — never surface as CTAs.
_DISCARDED_TYPES = frozenset({"hint", "free_text_hint"})

_KNOWN_COMMAND_PREFIXES = (
    "list my ",
    "list all ",
    "show ",
    "what is the status",
    "what's the status",
    "what about ",
    "how many ",
    "give me ",
    "check ",
    "any task",
    "any tasks",
    "i want to ",
    "i'm seeing ",
    "im seeing ",
    "i am seeing ",
    "i'm seeing it on ",
    "the ",
)

_KNOWN_EXACT_COMMANDS = frozenset({
    "yes",
    "yes, log it",
    "no",
    "no, skip",
    "i want to change the details",
    "i want to report a new issue",
    "i want to report a bug",
    "what can you help me with?",
    "list my open tasks",
    "show tasks in progress",
    "show tasks due this week",
    "what's due next week?",
    "what's due this week?",
    "check project status",
    "i want to request a feature",
    "the login button doesn't respond when i tap it on mobile.",
    "checkout shows a 500 error after i submit the form.",
    "what is the status of the issue i just logged?",
    "what's the current status?",
    "when is it due?",
    "the patient data on the dashboard looks inconsistent.",
    "what is the status of the bug i just logged?",
    "show me all open bugs",
    "what is the status of the feature i just requested?",
    "show me all pending feature requests",
    "what is the status of the existing task?",
    "this is a separate issue — log it as new",
    "show me all open bugs",
    "who's working on what right now?",
    "what other tasks are they working on?",
    "i want to report an issue with this task",
    "what else is due soon?",
    "show me this week's progress",
    "show me completed tasks",
    "what is the status of the issue i reported last?",
    "i need to mark this task as urgent",
    "who is assigned to this task?",
    "when is this task due?",
})

_META_HINT_PATTERNS = (
    r"^(describe|explain|share|tell me|type your|enter your|provide|clarify)\b",
    r"^(can you|could you|please)\b",
    r"^(answer|reply|respond)\b",
    r"^(pick a task|ask about|try another|select a)\b",
    r"^(more details?|your issue here)\b",
    r"^(continue chatting|tell me more)\b",
)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return slug[:48] or "action"


def ensure_unique_action_id(action_id: str, seen_ids: set[str]) -> str:
    base = (action_id or "action").strip() or "action"
    if base not in seen_ids:
        seen_ids.add(base)
        return base
    n = 2
    while f"{base}_{n}" in seen_ids:
        n += 1
    unique = f"{base}_{n}"
    seen_ids.add(unique)
    return unique


def is_meta_hint_label(label: str) -> bool:
    """Reject chip labels that read like input hints rather than tappable actions."""
    return is_meta_hint_text(label)


def is_meta_hint_text(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return True
    if normalized in _KNOWN_EXACT_COMMANDS:
        return False
    for pattern in _META_HINT_PATTERNS:
        if re.search(pattern, normalized):
            return True
    return False


def is_sendable_user_message(payload: str) -> bool:
    """True when payload is a message the user could send as-is."""
    text = (payload or "").strip()
    if len(text) < 2:
        return False
    lower = text.lower()
    if lower in _KNOWN_EXACT_COMMANDS:
        return True
    if is_meta_hint_text(text):
        return False
    if any(lower.startswith(prefix) for prefix in _KNOWN_COMMAND_PREFIXES):
        return True
    if lower.startswith(("i ", "i'", "what ", "how ", "any ", "are there")):
        return True
    # Questions directed at the assistant about project work.
    if "?" in text and any(w in lower for w in ("task", "status", "issue", "bug", "due", "open")):
        return True
    return False


def is_prefill_example(payload: str) -> bool:
    """Example utterance suitable for input prefill (first-person, concrete)."""
    text = (payload or "").strip()
    if len(text) < 12:
        return False
    if is_meta_hint_text(text):
        return False
    lower = text.lower()
    return lower.startswith(("i ", "i'", "the ", "when ", "on ", "after "))


def normalize_action_type(raw_type: str | None) -> CtaActionType | None:
    value = (raw_type or "quick_reply").strip().lower()
    if value in _DISCARDED_TYPES:
        return None
    if value in VALID_ACTION_TYPES:
        return value  # type: ignore[return-value]
    return "quick_reply"


def normalize_and_validate_action(
    raw: dict[str, Any],
    index: int = 0,
) -> dict[str, str] | None:
    label = str(raw.get("label") or "").strip()
    payload = str(raw.get("payload") or "").strip()
    action_type = normalize_action_type(str(raw.get("type") or ""))
    if action_type is None:
        return None

    if not label or is_meta_hint_label(label):
        return None

    label = label[:_MAX_LABEL_LEN]
    payload = payload[:_MAX_PAYLOAD_LEN]
    action_id = str(raw.get("id") or "").strip() or _slugify(label)

    if action_type == "prefill":
        if not payload or not is_prefill_example(payload):
            return None
        return {
            "id": action_id,
            "label": label,
            "type": "prefill",
            "payload": payload,
        }

    # quick_reply
    if not payload or not is_sendable_user_message(payload):
        return None
    return {
        "id": action_id,
        "label": label,
        "type": "quick_reply",
        "payload": payload,
    }


def validate_actions(
    raw_actions: list[Any],
    max_actions: int = _MAX_ACTIONS,
    *,
    quick_reply_only: bool = False,
) -> list[dict[str, str]]:
    cap = max(1, min(max_actions, 4))
    seen_keys: set[str] = set()
    seen_ids: set[str] = set()
    validated: list[dict[str, str]] = []
    for index, item in enumerate(raw_actions):
        if not isinstance(item, dict):
            continue
        action = normalize_and_validate_action(item, index)
        if not action:
            continue
        if quick_reply_only and action["type"] != "quick_reply":
            continue
        key = f"{action['type']}:{(action.get('payload') or action['label']).lower()}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        action["id"] = ensure_unique_action_id(action["id"], seen_ids)
        validated.append(action)
        if len(validated) >= cap:
            break
    return validated
