import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import AgentState
from src.agent.prompts import INTENT_PROMPT
from src.agent.query_resolver import (
    looks_like_ui_display_feedback,
    resolve_query_with_history,
)
from src.agent.triage_memory import ensure_triage_state, format_triage_context
from src.settings import settings


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

    query = resolved_query.lower()
    incidents = triage_state.get("incidents", [])

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

    triage_block = format_triage_context(triage_state)
    system_prompt = INTENT_PROMPT.format(triage_context=triage_block)

    intent_parts: list[str] = []
    if history:
        intent_parts.append(f"Conversation history:\n{history}")
    intent_parts.append(f"Current user message (resolved for follow-ups):\n{resolved_query}")
    intent_input = "\n\n".join(intent_parts)

    response = llm.invoke([
        SystemMessage(content=system_prompt),
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
