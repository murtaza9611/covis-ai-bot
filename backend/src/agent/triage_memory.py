from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_triage_state() -> dict[str, Any]:
    return {
        "incidents": [],
        "active_incident_id": None,
        "pending_confirmation": None,
        "last_logged_task_id": None,
        "last_logged_title": None,
        "last_tool_verified_at": None,
        "verification_status": "unknown",
        "last_task_query": None,
    }


# After a successful PMS log or duplicate match, draft merge should start fresh.
_TERMINAL_INCIDENT_STATUSES = frozenset({"created", "closed", "parked"})

# Extra signals for starting a new incident while the active one is still collecting / ready_to_confirm.
_NEW_TOPIC_SIGNAL_PHRASES = (
    "another issue",
    "new issue",
    "different issue",
    "separate issue",
    "different problem",
    "another problem",
    "new problem",
    "i noticed an issue",
    "i noticed a bug",
    "i think there is an issue",
    "i think there's an issue",
    "i think there is another",
    "i think there's another",
    "found a bug",
    "something else is wrong",
)


def ensure_triage_state(state: dict[str, Any] | None) -> dict[str, Any]:
    base = default_triage_state()
    if not isinstance(state, dict):
        return base
    merged = {**base, **state}
    if not isinstance(merged.get("incidents"), list):
        merged["incidents"] = []
    return merged


def get_active_incident(state: dict[str, Any]) -> dict[str, Any] | None:
    active_id = state.get("active_incident_id")
    if not active_id:
        return None
    for incident in state.get("incidents", []):
        if incident.get("incident_id") == active_id:
            return incident
    return None


def create_incident(state: dict[str, Any], draft_text: str) -> dict[str, Any]:
    now = utc_now_iso()
    incident = {
        "incident_id": str(uuid4()),
        "title_draft": "",
        "symptoms": [],
        "scope": "",
        "impact": "",
        "repro_steps": "",
        "severity_hint": "",
        "status": "collecting",
        "linked_task_id": None,
        "draft_text": draft_text.strip(),
        "created_at": now,
        "updated_at": now,
    }
    state["incidents"] = [*state.get("incidents", []), incident]
    state["active_incident_id"] = incident["incident_id"]
    return incident


def update_active_incident(state: dict[str, Any], update: dict[str, Any]) -> None:
    active = get_active_incident(state)
    if not active:
        return
    active.update(update)
    active["updated_at"] = utc_now_iso()


def should_start_new_incident(user_query: str, active_incident: dict[str, Any] | None) -> bool:
    if not active_incident:
        return True
    q = (user_query or "").lower()
    if any(k in q for k in _NEW_TOPIC_SIGNAL_PHRASES):
        return True
    return active_incident.get("status") in _TERMINAL_INCIDENT_STATUSES
