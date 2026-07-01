from typing import Any

from src.agent.cta_generator import generate_response_actions
from src.chat.schemas import ChatAction, ChatReplyData


def build_chat_reply(result: dict[str, Any]) -> ChatReplyData:
    reply_text = (result.get("final_response") or "").strip()
    raw_actions = generate_response_actions(result)
    actions: list[ChatAction] = []
    for item in raw_actions:
        if isinstance(item, dict) and item.get("id") and item.get("label") is not None:
            actions.append(
                ChatAction(
                    id=str(item["id"]),
                    label=str(item["label"]),
                    type=str(item.get("type") or "quick_reply"),
                    payload=str(item.get("payload") or ""),
                )
            )

    response_kind = str(result.get("response_kind") or "text")
    raw_tasks = result.get("structured_tasks") or []
    tasks = [t for t in raw_tasks if isinstance(t, dict)]

    return ChatReplyData(
        reply=reply_text,
        actions=actions,
        response_kind=response_kind,
        tasks=tasks,
    )
