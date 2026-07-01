from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


QAMode = Literal["POSITIVE", "NEGATIVE"]
QADriveMode = Literal["AUTO", "MANUAL"]
QASessionStatus = Literal["running", "stopped", "completed", "failed"]
TurnClassification = Literal["issue", "suggestion"]
QAMessageSource = Literal["text", "cta"]


class QAChatAction(BaseModel):
    id: str
    label: str
    type: str = "quick_reply"
    payload: str = ""


class QASessionStartRequest(BaseModel):
    mode: QAMode = "POSITIVE"
    drive_mode: QADriveMode = "AUTO"
    max_turns: int = Field(default=10, ge=1, le=30)
    timezone: str = "UTC"


class QAManualMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    source: QAMessageSource = "text"
    cta_label: str | None = None


class TurnGrade(BaseModel):
    relevance: int = Field(ge=0, le=100)
    accuracy: int = Field(ge=0, le=100)
    tone: int = Field(ge=0, le=100)
    completeness: int = Field(ge=0, le=100)
    cta_relevance: int | None = Field(default=None, ge=0, le=100)
    cta_quality: int | None = Field(default=None, ge=0, le=100)
    weighted_score: float = Field(ge=0, le=100)
    classification: TurnClassification
    what_went_wrong: str | None = None
    expected_reply: str | None = None
    prompt_fix: str | None = None
    what_could_be_better: str | None = None
    prompt_enhancement: str | None = None
    cta_feedback: str | None = None
    capability_tag: str | None = None
    adversarial_tag: str | None = None


class QATurnRecord(BaseModel):
    turn_number: int
    client_message: str
    client_message_source: QAMessageSource = "text"
    client_cta_label: str | None = None
    bot_reply: str
    bot_actions: list[QAChatAction] = Field(default_factory=list)
    grade: TurnGrade


class QASessionStartData(BaseModel):
    qa_session_id: str
    banner: str
    task_count: int
    mode: QAMode
    drive_mode: QADriveMode
    max_turns: int


class QASessionStatusData(BaseModel):
    qa_session_id: str
    mode: QAMode
    drive_mode: QADriveMode
    max_turns: int
    current_turn: int
    status: QASessionStatus
    turns: list[QATurnRecord] = Field(default_factory=list)
    report: str | None = None
    error: str | None = None
    banner: str | None = None
    task_count: int = 0


class PMSTaskSnapshot(BaseModel):
    taskId: int
    title: str
    status: str
    assignee: str | None = None
    dueDate: str | None = None
    description: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)
