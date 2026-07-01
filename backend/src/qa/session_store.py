from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.qa.schemas import QADriveMode, QAMode, QASessionStatus, QATurnRecord


def _build_banner(*, mode: QAMode, drive_mode: QADriveMode, max_turns: int, task_count: int) -> str:
    drive_label = "Auto" if drive_mode == "AUTO" else "Manual"
    lines = [
        "[COVIS QA SESSION STARTED]",
        f"Drive: {drive_label}",
        f"Test mode: {mode}",
        f"Turn budget: {max_turns}",
        f"PMS snapshot loaded: {task_count} tasks indexed",
    ]
    if drive_mode == "AUTO":
        lines.append("Initiating conversation with COVIS Assist...")
    else:
        lines.append("Type client messages below — grading and report are automatic.")
    return "\n".join(lines)


@dataclass
class QASession:
    id: str
    mode: QAMode
    drive_mode: QADriveMode
    max_turns: int
    timezone: str
    assist_session_id: str
    pms_snapshot: list[dict]
    task_count: int
    status: QASessionStatus = "running"
    turns: list[QATurnRecord] = field(default_factory=list)
    report: str | None = None
    stop_requested: bool = False
    error: str | None = None
    banner: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    _done_event: asyncio.Event = field(default_factory=asyncio.Event)
    _turn_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def mark_done(self, status: QASessionStatus) -> None:
        self.status = status
        self._done_event.set()

    async def wait_until_done(self, timeout: float = 300.0) -> None:
        try:
            await asyncio.wait_for(self._done_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass


class QASessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, QASession] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        mode: QAMode,
        drive_mode: QADriveMode,
        max_turns: int,
        timezone: str,
        pms_snapshot: list[dict],
        task_count: int,
    ) -> QASession:
        qa_id = str(uuid.uuid4())
        assist_id = str(uuid.uuid4())
        banner = _build_banner(
            mode=mode,
            drive_mode=drive_mode,
            max_turns=max_turns,
            task_count=task_count,
        )
        session = QASession(
            id=qa_id,
            mode=mode,
            drive_mode=drive_mode,
            max_turns=max_turns,
            timezone=timezone,
            assist_session_id=assist_id,
            pms_snapshot=pms_snapshot,
            task_count=task_count,
            banner=banner,
        )
        async with self._lock:
            self._sessions[qa_id] = session
        return session

    async def get(self, qa_session_id: str) -> QASession | None:
        async with self._lock:
            return self._sessions.get(qa_session_id)

    async def request_stop(self, qa_session_id: str) -> QASession | None:
        session = await self.get(qa_session_id)
        if session is None:
            return None
        session.stop_requested = True
        return session


qa_session_store = QASessionStore()
