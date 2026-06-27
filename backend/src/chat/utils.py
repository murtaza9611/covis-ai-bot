from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.chat.models import ChatHistory


MAX_HISTORY_TURNS = 20

class ChatHistoryHelper:

    @staticmethod
    async def get_formatted_history(
        db: AsyncSession,
        session_id: str,
        max_turns: int = MAX_HISTORY_TURNS,
    ) -> str:
        stmt = (
            select(ChatHistory)
            .where(ChatHistory.session_id == session_id)
            .order_by(ChatHistory.created_at.desc())
            .limit(max_turns)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        rows.reverse()
        return "\n".join(f"{row.role}: {row.message}" for row in rows)

    @staticmethod
    async def append_turn(
        db: AsyncSession,
        session_id: str,
        role: str,
        message: str,
        channel: str,
    ) -> None:
        normalized_message = (message or "").strip()
        if not session_id or not normalized_message:
            return

        row = ChatHistory(
            session_id=session_id,
            role=role,
            message=normalized_message,
            channel=channel,
        )
        db.add(row)
        await db.commit()
