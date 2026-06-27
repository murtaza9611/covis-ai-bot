from pydantic import BaseModel
from typing import Optional


class TaskPayload(BaseModel):
    taskId: int = 0
    title: str
    description: str = ""
    projectId: int
    currentMileStoneId: str
    currentTaskBoardId: int
    currentTaskBoardTypeId: int
    currentReportedById: int
    currentAssigneeId: int
    taskTypeId: int
    severityId: int
    currentEstimatedTime: int = 0
    dueDate: Optional[str] = None
    taskDocuments: list = []
    userId: int


class TaskCard(BaseModel):
    taskId: int
    title: str
    description: Optional[str] = ""
    severityId: Optional[int] = None
    currentTaskBoardId: int
    taskTypeId: Optional[int] = None
    assignee: Optional[str] = None
    reportedBy: Optional[str] = None
    currentAssigneeId: Optional[int] = None
    dueDate: Optional[str] = None
    currentEstimatedTime: Optional[int] = None
    subTaskCount: Optional[int] = 0
    attachmentCount: Optional[int] = 0
    commentsCount: Optional[int] = 0
    completedDate: Optional[str] = None


class BoardColumn(BaseModel):
    id: int
    title: str
    taskBoardStatusName: str
    totalTask: int
    cards: list[TaskCard] = []
