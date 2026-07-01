from langgraph.graph import StateGraph, END
from src.agent.state import AgentState
from src.agent.nodes.intent_node import intent_node
from src.agent.nodes.greet_node import greet_node
from src.agent.nodes.general_chat_node import general_chat_node
from src.agent.nodes.create_task_node import create_task_node
from src.agent.nodes.get_task_node import get_task_node
from src.agent.nodes.clarify_node import clarify_node


def route_by_intent(state: AgentState) -> str:
    return state.get("intent", "general_chat")


def build_agent():
    graph = StateGraph(AgentState)

    graph.add_node("intent", intent_node)
    graph.add_node("greet", greet_node)
    graph.add_node("general_chat", general_chat_node)
    graph.add_node("create_task", create_task_node)
    graph.add_node("get_task_info", get_task_node)
    graph.add_node("clarify", clarify_node)

    graph.set_entry_point("intent")

    graph.add_conditional_edges(
        "intent",
        route_by_intent,
        {
            "greet": "greet",
            "general_chat": "general_chat",
            "create_task": "create_task",
            "get_task_info": "get_task_info",
            "clarify": "clarify",               
        },
    )

    for node in ["greet", "general_chat", "create_task", "get_task_info", "clarify"]:
        graph.add_edge(node, END)

    return graph.compile()


agent = build_agent()
