from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from src.models import Base
from src.chat.settings import settings


class ChatHistory(Base):
    __tablename__ = settings.TABLE_NAME

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(32), default="api", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class ChatSessionState(Base):
    """Per-session data that must survive between HTTP/Webhook turns."""

    __tablename__ = "chat_session_state"

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    pending_task_json: Mapped[str | None] = mapped_column(Text, nullable=True)