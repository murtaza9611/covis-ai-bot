"""LLM-driven task fetch and presentation plan."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.agent.assistant_offer import (
    BROADEN_RESOLVED_ACTION,
    detect_broaden_acceptance,
    get_broaden_offer,
)
from src.agent.prompts import TASK_QUERY_PLAN_PROMPT
from src.agent.task_list_formatter import (
    TaskListFilter,
    is_list_filter_only_query,
    parse_list_filter,
    user_asks_about_specific_task,
    user_wants_list_format,
    user_wants_summary_format,
)
from src.agent.timeframe import extract_time_range, has_timeframe_in_query
from src.agent.triage_memory import format_triage_context
from src.settings import settings

logger = logging.getLogger(__name__)

_PMS_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.999Z$")

TaskQueryMode = Literal[
    "full_snapshot",
    "timeframe",
    "specific_task",
    "list_filter",
    "freeform_qa",
]

_FILTER_MAP = {
    "all_open": TaskListFilter.ALL_OPEN,
    "in_progress": TaskListFilter.IN_PROGRESS,
    "due_this_week": TaskListFilter.DUE_THIS_WEEK,
    "completed": TaskListFilter.COMPLETED,
}


class TaskQueryPlan(BaseModel):
    mode: TaskQueryMode = "freeform_qa"
    start_date: str | None = None
    end_date: str | None = None
    search_terms: list[str] = Field(default_factory=list)
    list_filter: TaskListFilter | None = None
    merge_today_with_full: bool = False
    reuse_last_timeframe: bool = False


def _today_for_timezone(tz_name: str) -> str:
    try:
        return datetime.now(ZoneInfo(tz_name)).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def _valid_pms_dates(start: str | None, end: str | None) -> bool:
    return (
        isinstance(start, str)
        and isinstance(end, str)
        and _PMS_UTC_RE.match(start)
        and _PMS_UTC_RE.match(end)
    )


def _normalize_mode(raw: str | None) -> TaskQueryMode:
    value = (raw or "").strip().lower()
    allowed: set[str] = {
        "full_snapshot",
        "timeframe",
        "specific_task",
        "list_filter",
        "freeform_qa",
    }
    if value in allowed:
        return value  # type: ignore[return-value]
    return "freeform_qa"


def _normalize_filter(raw: str | None) -> TaskListFilter | None:
    if not raw:
        return None
    return _FILTER_MAP.get(str(raw).strip().lower())


def _needs_full_project_snapshot(user_query: str) -> bool:
    q = (user_query or "").lower()
    if re.search(r"\bwhat'?s going on\b", q):
        return True
    if re.search(r"\bwhere do we stand\b", q) or "where are we at" in q:
        return True
    for phrase in (
        "give me an update",
        "status update",
        "board update",
        "overall update",
        "anything on the board",
        "what's on the board",
        "whats on the board",
        "anything else open",
        "what else is open",
        "how are things overall",
        "any movement",
        "catch me up",
    ):
        if phrase in q:
            return True
    return False


def _broad_today_merge_query(user_query: str) -> bool:
    q = (user_query or "").lower()
    if "today" not in q:
        return False
    keys = (
        "update",
        "going on",
        "what about",
        "any task",
        "any tasks",
        "anything",
        "catch me up",
        "on the board",
        "scheduled",
    )
    return any(k in q for k in keys)


def _fallback_plan(user_query: str, tz_name: str) -> TaskQueryPlan:
    """Regex fallback when LLM plan JSON fails."""
    start, end = extract_time_range(user_query, tz_name)
    if _broad_today_merge_query(user_query):
        return TaskQueryPlan(
            mode="timeframe",
            start_date=start,
            end_date=end,
            merge_today_with_full=True,
        )
    if _needs_full_project_snapshot(user_query):
        return TaskQueryPlan(mode="full_snapshot")
    if user_asks_about_specific_task(user_query):
        return TaskQueryPlan(mode="specific_task")
    if (
        has_timeframe_in_query(user_query)
        or user_wants_list_format(user_query)
        or user_wants_summary_format(user_query)
        or is_list_filter_only_query(user_query)
    ):
        filt = parse_list_filter(user_query)
        mode: TaskQueryMode = "list_filter" if filt != TaskListFilter.ALL_OPEN else "timeframe"
        if not start and not end and has_timeframe_in_query(user_query):
            mode = "timeframe"
        elif user_wants_list_format(user_query) and not has_timeframe_in_query(user_query):
            mode = "list_filter"
        return TaskQueryPlan(
            mode=mode,
            start_date=start,
            end_date=end,
            list_filter=filt if mode == "list_filter" else None,
        )
    return TaskQueryPlan(mode="freeform_qa", start_date=start, end_date=end)


def _parse_plan_payload(data: dict[str, Any]) -> TaskQueryPlan:
    terms = data.get("search_terms")
    if not isinstance(terms, list):
        terms = []
    search_terms = [str(t).strip() for t in terms if str(t).strip()]

    start = data.get("start_date")
    end = data.get("end_date")
    start_s = start if isinstance(start, str) and start.strip() else None
    end_s = end if isinstance(end, str) and end.strip() else None
    if start_s and end_s and not _valid_pms_dates(start_s, end_s):
        start_s, end_s = None, None

    return TaskQueryPlan(
        mode=_normalize_mode(data.get("mode")),
        start_date=start_s,
        end_date=end_s,
        search_terms=search_terms,
        list_filter=_normalize_filter(data.get("list_filter")),
        merge_today_with_full=bool(data.get("merge_today_with_full")),
        reuse_last_timeframe=bool(data.get("reuse_last_timeframe")),
    )


def _llm_plan(
    user_query: str,
    conversation_history: str,
    triage_state: dict[str, Any] | None,
    tz_name: str,
) -> TaskQueryPlan | None:
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    prompt = TASK_QUERY_PLAN_PROMPT.format(
        current_date=_today_for_timezone(tz_name),
        timezone=tz_name,
        triage_context=format_triage_context(triage_state),
        conversation_history=(conversation_history or "").strip() or "(none)",
        user_query=(user_query or "").strip(),
    )
    try:
        response = llm.invoke([
            SystemMessage(content="Return only valid JSON."),
            HumanMessage(content=prompt),
        ])
        raw = (response.content or "").strip()
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return _parse_plan_payload(parsed)
    except (json.JSONDecodeError, AttributeError, TypeError) as ex:
        logger.warning("task query plan LLM failed: %s", ex)
    return None


def resolve_plan_dates(
    plan: TaskQueryPlan,
    user_query: str,
    tz_name: str,
    triage_state: dict[str, Any] | None,
    llm_extract_fn,
) -> tuple[str | None, str | None]:
    """Fill start/end dates from plan, regex, LLM extract, or last_task_query."""
    start, end = plan.start_date, plan.end_date
    if not _valid_pms_dates(start, end):
        start, end = extract_time_range(user_query, tz_name)
    if not _valid_pms_dates(start, end):
        start, end = llm_extract_fn(user_query, tz_name)

    if plan.reuse_last_timeframe and triage_state and plan.mode != "full_snapshot":
        last = triage_state.get("last_task_query") or {}
        if isinstance(last, dict):
            if not _valid_pms_dates(start, end):
                start = start or last.get("start_date")
                end = end or last.get("end_date")

    if _valid_pms_dates(start, end):
        return start, end
    return (
        start if isinstance(start, str) and start else None,
        end if isinstance(end, str) and end else None,
    )


def _is_broaden_resolved_query(
    user_query: str,
    triage_state: dict[str, Any] | None,
) -> bool:
    q = (user_query or "").strip().casefold()
    if not q:
        return False
    if q == BROADEN_RESOLVED_ACTION.casefold():
        return True
    offer = get_broaden_offer(triage_state)
    if offer:
        action = (offer.get("resolved_action") or "").strip().casefold()
        if action and q == action:
            return True
    markers = ("all open tasks", "broader project overview", "broader overview")
    return any(m in q for m in markers)


def _broaden_acceptance_plan() -> TaskQueryPlan:
    return TaskQueryPlan(
        mode="full_snapshot",
        start_date=None,
        end_date=None,
        reuse_last_timeframe=False,
    )


def plan_task_query(
    user_query: str,
    conversation_history: str,
    triage_state: dict[str, Any] | None,
    tz_name: str,
) -> TaskQueryPlan:
    if detect_broaden_acceptance(user_query, conversation_history, triage_state):
        return _broaden_acceptance_plan()
    if _is_broaden_resolved_query(user_query, triage_state):
        return _broaden_acceptance_plan()

    plan = _llm_plan(user_query, conversation_history, triage_state, tz_name)
    if plan is None:
        logger.info("Using regex fallback task query plan for: %r", user_query[:80])
        plan = _fallback_plan(user_query, tz_name)
    return plan
