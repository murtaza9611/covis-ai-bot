from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.qa.orchestrator import process_manual_message, run_qa_session, stop_qa_session
from src.qa.schemas import (
    QAManualMessageRequest,
    QASessionStartData,
    QASessionStartRequest,
    QASessionStatusData,
)
from src.qa.session_store import qa_session_store
from src.qa.snapshot import fetch_pms_snapshot
from src.response import BuildJSONResponses

router = APIRouter()


def _session_to_status(session) -> QASessionStatusData:
    return QASessionStatusData(
        qa_session_id=session.id,
        mode=session.mode,
        drive_mode=session.drive_mode,
        max_turns=session.max_turns,
        current_turn=len(session.turns),
        status=session.status,
        turns=session.turns,
        report=session.report,
        error=session.error,
        banner=session.banner,
        task_count=session.task_count,
    )


@router.post("/sessions", summary="Start a COVIS QA session")
async def start_session(
    request: QASessionStartRequest,
    db: AsyncSession = Depends(get_async_session),
):
    del db
    try:
        tasks, task_count = await fetch_pms_snapshot(request.timezone)
        session = await qa_session_store.create(
            mode=request.mode,
            drive_mode=request.drive_mode,
            max_turns=request.max_turns,
            timezone=request.timezone,
            pms_snapshot=tasks,
            task_count=task_count,
        )

        if session.drive_mode == "AUTO":
            asyncio.create_task(run_qa_session(session))

        data = QASessionStartData(
            qa_session_id=session.id,
            banner=session.banner,
            task_count=task_count,
            mode=session.mode,
            drive_mode=session.drive_mode,
            max_turns=session.max_turns,
        )
        return BuildJSONResponses.success_response(
            data=data.model_dump(),
            message="QA session started",
        )
    except Exception as e:
        return BuildJSONResponses.raise_exception(
            message=f"Failed to start QA session: {e}",
            status_code=500,
        )


@router.get("/sessions/{qa_session_id}", summary="Get QA session status")
async def get_session(qa_session_id: str):
    session = await qa_session_store.get(qa_session_id)
    if session is None:
        return BuildJSONResponses.raise_exception(
            message="QA session not found",
            status_code=404,
        )
    return BuildJSONResponses.success_response(
        data=_session_to_status(session).model_dump(),
        message="QA session status",
    )


@router.post("/sessions/{qa_session_id}/message", summary="Send manual client message")
async def send_manual_message(qa_session_id: str, request: QAManualMessageRequest):
    try:
        session = await process_manual_message(
            qa_session_id,
            request.message,
            source=request.source,
            cta_label=request.cta_label,
        )
        return BuildJSONResponses.success_response(
            data=_session_to_status(session).model_dump(),
            message="Turn processed",
        )
    except ValueError as e:
        return BuildJSONResponses.raise_exception(message=str(e), status_code=400)
    except Exception as e:
        return BuildJSONResponses.raise_exception(
            message=f"Failed to process message: {e}",
            status_code=500,
        )


@router.post("/sessions/{qa_session_id}/stop", summary="Stop QA session and get report")
async def stop_session(qa_session_id: str):
    session = await qa_session_store.get(qa_session_id)
    if session is None:
        return BuildJSONResponses.raise_exception(
            message="QA session not found",
            status_code=404,
        )

    if session.status == "running":
        await stop_qa_session(qa_session_id)

    session = await qa_session_store.get(qa_session_id)
    return BuildJSONResponses.success_response(
        data=_session_to_status(session).model_dump(),
        message="QA session stopped",
    )
