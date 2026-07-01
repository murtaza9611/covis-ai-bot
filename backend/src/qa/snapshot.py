from __future__ import annotations

import asyncio

from src.agent.workflow_registry import WorkflowRegistry
from src.pms_client import client as pms_client
from src.pms_client.schemas import BoardColumn
from src.qa.schemas import PMSTaskSnapshot


def flatten_boards_to_snapshot(boards: list[BoardColumn]) -> list[dict]:
    """Flatten PMS board columns into a compact QA task index."""
    registry = WorkflowRegistry.from_board_columns(boards)
    tasks: list[dict] = []
    seen: set[int] = set()

    for board in boards or []:
        for card in board.cards or []:
            if card.taskId in seen:
                continue
            seen.add(card.taskId)
            status = registry.label_for(card.currentTaskBoardId)
            tasks.append(
                PMSTaskSnapshot(
                    taskId=card.taskId,
                    title=card.title or "",
                    status=status,
                    assignee=card.assignee,
                    dueDate=card.dueDate,
                    description=(card.description or "")[:500] or None,
                ).to_dict()
            )

    return tasks


async def fetch_pms_snapshot(timezone: str) -> tuple[list[dict], int]:
    """Fetch live PMS data and return flattened task list + count."""

    def _fetch() -> list[BoardColumn]:
        token = pms_client.login()
        return pms_client.get_tasks(token, timezone)

    boards = await asyncio.to_thread(_fetch)
    tasks = flatten_boards_to_snapshot(boards)
    return tasks, len(tasks)
