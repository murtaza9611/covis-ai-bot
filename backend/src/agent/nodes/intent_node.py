import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import AgentState
from src.agent.prompts import INTENT_PROMPT
from src.agent.query_resolver import (
    looks_like_task_followup,
    looks_like_ui_display_feedback,
    resolve_query_with_history,
)
from src.agent.triage_memory import ensure_triage_state
from src.settings import settings


def _looks_like_progress_query(query_lower: str) -> bool:
    """Board/status asks — must win over stale triage shortcuts."""
    q = query_lower
    if any(
        s in q
        for s in (
            "any progress",
            "progress on",
            "progress with",
            "progress?",
            "give me an update",
            "status update",
            "any update",
            "what's the status",
            "what is the status",
            "any news",
            "what happened to",
            "what happened with",
            "how's it going",
            "how is it going",
            "been fixed",
            "been addressed",
            "still open",
            "where we at",
            "where are we",
            "summary",
            "overview",
            "last week",
            "last month",
            "details for",
        )
    ):
        return True
    if ("issue i reported" in q or "ticket i logged" in q or "bug i reported" in q) and any(
        w in q for w in ("progress", "update", "status", "news", "fixed", "happening", "going", "still")
    ):
        return True
    return False


def _looks_like_pure_social_opener(text: str) -> bool:
    """
    Short hello/thanks-only messages while a task awaits confirmation should hit greet,
    not create_task (avoids off_topic reminder: 'still have X ready to log').
    """
    t = (text or "").strip()
    if not t or len(t) > 100:
        return False
    tl = t.lower()
    for marker in (
        "log",
        "task",
        "bug",
        "issue",
        "story",
        "yes",
        "no",
        "confirm",
        "implement",
        "signup",
        "sign-up",
        "progress",
        "status",
        "update",
        "delete",
        "create",
    ):
        if marker in tl:
            return False
    patterns = (
        r"^(hi|hello|hey|hiya|yo|sup|howdy|heelo|h[e]+l+o+)(!|\?|\.|…)?\s*$",
        r"^(hi|hello|hey)\s+(there|you)(!|\?|\.|…)?\s*$",
        r"^good\s+(morning|afternoon|evening|night)(!|\?|\.|…)?\s*$",
        r"^what'?s\s+up(!|\?|\.|…)?\s*$",
        r"^how(\s+are)\s+you(!|\?|\.|…)?\s*$",
        r"^how'?re\s+you(!|\?|\.|…)?\s*$",
        r"^thanks?(!|\?|\.|…)?\s*$",
        r"^thank\s+you(!|\?|\.|…)?\s*$",
        r"^thx$|^ty$",
    )
    return any(re.match(p, tl, re.IGNORECASE) for p in patterns)


def intent_node(state: AgentState) -> AgentState:
    triage_state = ensure_triage_state(state.get("triage_state"))
    history = state.get("conversation_history", "")
    raw_query = (state.get("user_query") or "").strip()
    resolved_query = resolve_query_with_history(raw_query, history, triage_state)

    base_update = {
        **state,
        "resolved_query": resolved_query,
        "triage_state": triage_state,
    }

    if looks_like_ui_display_feedback(raw_query):
        return {**base_update, "intent": "clarify"}

    pending = triage_state.get("pending_confirmation") or {}
    if isinstance(pending, dict) and pending.get("task_payload"):
        uq = resolved_query
        if _looks_like_progress_query(uq.lower()):
            return {**base_update, "intent": "get_task_info"}
        if _looks_like_pure_social_opener(uq):
            return {**base_update, "intent": "greet"}
        return {**base_update, "intent": "create_task"}

    query = resolved_query.lower()
    incidents = triage_state.get("incidents", [])
    if _looks_like_progress_query(query):
        return {**base_update, "intent": "get_task_info"}

    if looks_like_task_followup(raw_query, history):
        return {**base_update, "intent": "get_task_info"}

    # Multiple past incidents + vague pointer → ask which thread (not create_task).
    _ambiguous = ("that issue", "the issue", "same issue", "this issue", "earlier issue", "which issue")
    _domain_hints = ("payment", "scan", "booking", "email")
    if len(incidents) > 1 and any(a in query for a in _ambiguous):
        if not any(h in query for h in _domain_hints):
            return {**base_update, "intent": "clarify"}

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    intent_input = resolved_query
    if history:
        intent_input = (
            "Conversation history:\n"
            f"{history}\n\n"
            "Current user message (resolved for follow-ups):\n"
            f"{resolved_query}"
        )

    response = llm.invoke([
        SystemMessage(content=INTENT_PROMPT),
        HumanMessage(content=intent_input),
    ])

    try:
        result = json.loads(response.content.strip())
        intent = result.get("intent", "general_chat")

    except (json.JSONDecodeError, AttributeError):
        intent = "general_chat"

    if intent == "out_of_scope":
        intent = "general_chat"

    valid_intents = {"create_task", "get_task_info", "greet", "clarify", "general_chat"}

    if intent not in valid_intents:
        intent = "general_chat"

    if intent == "create_task" and looks_like_ui_display_feedback(resolved_query):
        intent = "clarify"

    return {**base_update, "intent": intent}
