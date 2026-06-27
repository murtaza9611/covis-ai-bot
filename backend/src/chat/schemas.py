from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str
    timezone: str = "UTC"
    session_id: str


class ChatAction(BaseModel):
    id: str
    label: str
    type: str = "quick_reply"
    payload: str = ""


class ChatReplyData(BaseModel):
    reply: str
    actions: list[ChatAction] = Field(default_factory=list)
    response_kind: str = "text"
    tasks: list[dict[str, Any]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: ChatReplyData
