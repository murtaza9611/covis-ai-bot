from __future__ import annotations

import asyncio
import traceback

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.chat.services import ChatService
from src.database import async_engine
from src.qa.client_agent import resolve_client_message
from src.qa.grader import grade_turn
from src.qa.report import build_report
from src.qa.schemas import QAChatAction, QATurnRecord
from src.qa.session_store import QASession, qa_session_store


async def _get_db_session() -> AsyncSession:
    factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autoflush=False,
        expire_on_commit=False,
    )
    return factory()


def finalize_session(session: QASession, *, status: str | None = None) -> None:
    """Build report and mark session done."""
    if not session.report:
        session.report = build_report(session)
    if status is None:
        status = "stopped" if session.stop_requested else "completed"
    session.mark_done(status)  # type: ignore[arg-type]


def _actions_from_chat_reply(chat_reply) -> list[QAChatAction]:
    actions: list[QAChatAction] = []
    for item in chat_reply.actions or []:
        actions.append(
            QAChatAction(
                id=item.id,
                label=item.label,
                type=item.type or "quick_reply",
                payload=item.payload or "",
            )
        )
    return actions


async def process_single_turn(
    session: QASession,
    client_message: str,
    db: AsyncSession,
    *,
    client_message_source: str = "text",
    client_cta_label: str | None = None,
) -> QATurnRecord:
    """Send one client message to Assist, grade the reply, append turn."""
    chat_reply = await ChatService.process_message(
        db=db,
        session_id=session.assist_session_id,
        user_message=client_message,
        timezone=session.timezone,
        channel="qa",
    )
    bot_reply = chat_reply.reply.strip()
    bot_actions = _actions_from_chat_reply(chat_reply)
    grade = await grade_turn(session, client_message, bot_reply, bot_actions)
    turn = QATurnRecord(
        turn_number=len(session.turns) + 1,
        client_message=client_message,
        client_message_source=client_message_source,  # type: ignore[arg-type]
        client_cta_label=client_cta_label,
        bot_reply=bot_reply,
        bot_actions=bot_actions,
        grade=grade,
    )
    session.turns.append(turn)
    return turn


async def run_qa_session(session: QASession) -> None:
    """Background loop for AUTO mode: generate client messages, call Assist, grade."""
    db: AsyncSession | None = None
    try:
        db = await _get_db_session()
        while len(session.turns) < session.max_turns:
            if session.stop_requested:
                break

            client_message, source, cta_label = await resolve_client_message(session)
            await process_single_turn(
                session,
                client_message,
                db,
                client_message_source=source,
                client_cta_label=cta_label,
            )

            if session.stop_requested:
                break

            await asyncio.sleep(0.5)

        finalize_session(session)

    except Exception as exc:
        session.error = str(exc)
        traceback.print_exc()
        if session.turns:
            finalize_session(session, status="failed")
        else:
            session.mark_done("failed")
    finally:
        if db is not None:
            await db.close()


async def process_manual_message(
    qa_session_id: str,
    message: str,
    *,
    source: str = "text",
    cta_label: str | None = None,
) -> QASession:
    """Process a user-typed client message in MANUAL mode."""
    session = await qa_session_store.get(qa_session_id)
    if session is None:
        raise ValueError("QA session not found")
    if session.drive_mode != "MANUAL":
        raise ValueError("Session is not in manual drive mode")
    if session.status != "running":
        raise ValueError("Session is not running")
    if len(session.turns) >= session.max_turns:
        raise ValueError("Turn budget exhausted")

    text = message.strip()
    if not text:
        raise ValueError("Message cannot be empty")

    async with session._turn_lock:
        if session.status != "running":
            raise ValueError("Session is not running")
        if len(session.turns) >= session.max_turns:
            raise ValueError("Turn budget exhausted")

        db = await _get_db_session()
        try:
            await process_single_turn(
                session,
                text,
                db,
                client_message_source=source,
                client_cta_label=cta_label,
            )
        finally:
            await db.close()

        if len(session.turns) >= session.max_turns:
            finalize_session(session)
        elif session.stop_requested:
            finalize_session(session)

    return session


async def stop_qa_session(qa_session_id: str) -> QASession | None:
    """Request stop and wait for session to finish (AUTO) or finalize immediately (MANUAL)."""
    session = await qa_session_store.request_stop(qa_session_id)
    if session is None:
        return None
    if session.status != "running":
        return session

    if session.drive_mode == "MANUAL":
        async with session._turn_lock:
            if session.status == "running":
                finalize_session(session, status="stopped")
        return session

    await session.wait_until_done(timeout=600.0)
    return session
