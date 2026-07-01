from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.agent.state import AgentState
from src.agent.prompts import GREET_PROMPT
from src.settings import settings


def greet_node(state: AgentState) -> AgentState:
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
    )
    history = state.get("conversation_history", "")
    greet_input = state["user_query"]
    if history:
        greet_input = (
            "Conversation history:\n"
            f"{history}\n\n"
            "Current user message:\n"
            f"{state['user_query']}"
        )

    response = llm.invoke([
        SystemMessage(content=GREET_PROMPT),
        HumanMessage(content=greet_input),
    ])
    return {
        **state,
        "final_response": response.content.strip(),
        "response_kind": "greeting",
        "cta_scenario": "new_session",
    }
