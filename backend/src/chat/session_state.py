import json
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.chat.models import ChatSessionState


class SessionStateHelper:
    _CACHE_TTL_SECONDS = 30
    _CACHE: dict[str, tuple[float, dict[str, Any]]] = {}

    @staticmethod
    def _cache_get(session_id: str) -> dict[str, Any] | None:
        record = SessionStateHelper._CACHE.get(session_id)
        if not record:
            return None
        expires_at, data = record
        if expires_at <= time.time():
            SessionStateHelper._CACHE.pop(session_id, None)
            return None
        return dict(data)

    @staticmethod
    def _cache_set(session_id: str, payload: dict[str, Any]) -> None:
        SessionStateHelper._CACHE[session_id] = (
            time.time() + SessionStateHelper._CACHE_TTL_SECONDS,
            dict(payload),
        )

    @staticmethod
    def _cache_clear(session_id: str) -> None:
        SessionStateHelper._CACHE.pop(session_id, None)

    @staticmethod
    async def get_session_state(db: AsyncSession, session_id: str) -> dict[str, Any]:
        if not session_id:
            return {}

        cached = SessionStateHelper._cache_get(session_id)
        if cached is not None:
            return cached

        stmt = select(ChatSessionState).where(ChatSessionState.session_id == session_id)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if not row or not row.pending_task_json:
            return {}
        try:
            data = json.loads(row.pending_task_json)
            if isinstance(data, dict):
                SessionStateHelper._cache_set(session_id, data)
                return data
            return {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    async def set_session_state(db: AsyncSession, session_id: str, payload: dict[str, Any]) -> None:
        if not session_id or not payload:
            return
        stmt = select(ChatSessionState).where(ChatSessionState.session_id == session_id)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        raw = json.dumps(payload)
        if row:
            row.pending_task_json = raw
        else:
            db.add(ChatSessionState(session_id=session_id, pending_task_json=raw))
        await db.commit()
        SessionStateHelper._cache_set(session_id, payload)

    @staticmethod
    async def clear_session_state(db: AsyncSession, session_id: str) -> None:
        if not session_id:
            return
        stmt = select(ChatSessionState).where(ChatSessionState.session_id == session_id)
        result = await db.execute(stmt)
        row = result.scalar_one_or_none()
        if row:
            row.pending_task_json = None
            await db.commit()
        SessionStateHelper._cache_clear(session_id)
