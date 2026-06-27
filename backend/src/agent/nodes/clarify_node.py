from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import AgentState
from src.agent.prompts import CLARIFY_PROMPT, INCIDENT_TRIAGE_PROMPT
from src.agent.response_actions import clarify_actions
from src.settings import settings


def clarify_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.3,
    )
    prompt = CLARIFY_PROMPT.format(
        conversation_history=state.get("conversation_history", ""),
        user_query=state.get("user_query", ""),
    )
    response = llm.invoke([
        SystemMessage(content=f"{INCIDENT_TRIAGE_PROMPT}\nReturn only the final user-facing message."),
        HumanMessage(content=prompt),
    ])
    reply = (response.content or "").strip()
    if not reply:
        reply = "Can you share one more detail so I can help with this properly?"
    return {
        **state,
        "final_response": reply,
        "response_kind": "clarify",
        "response_actions": clarify_actions(),
    }
