from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from src.agent.state import AgentState
from src.agent.prompts import GENERAL_CHAT_PROMPT, INCIDENT_TRIAGE_PROMPT
from src.settings import settings


def general_chat_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
    )
    history = state.get("conversation_history", "")
    user_block = state["user_query"]
    if history:
        user_block = (
            "Conversation history:\n"
            f"{history}\n\n"
            "Current user message:\n"
            f"{state['user_query']}"
        )

    response = llm.invoke([
        SystemMessage(content=f"{GENERAL_CHAT_PROMPT}\n\n{INCIDENT_TRIAGE_PROMPT}"),
        HumanMessage(content=user_block),
    ])
    reply = (response.content or "").strip()
    if not reply:
        reply = "Hey — I’m here. What’s on your mind?"
    return {**state, "final_response": reply, "response_kind": "general_chat"}
