import json
import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from src.agent.state import AgentState
from src.agent.prompts import GET_TASK_ANSWER_PROMPT, TIME_RANGE_EXTRACT_PROMPT
from src.agent.response_actions import task_list_filter_actions
from src.agent.task_list_formatter import (
    format_task_list,
    parse_list_filter,
    user_wants_list_format,
    user_wants_summary_format,
)
from src.agent.workflow_registry import WorkflowRegistry
from src.agent.triage_memory import ensure_triage_state, utc_now_iso
from src.pms_client import client as pms_client
from src.pms_client.schemas import BoardColumn
from src.settings import settings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser


_PMS_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.999Z$")


def _today_for_timezone(tz_name: str) -> str:
    try:
        return datetime.now(ZoneInfo(tz_name)).date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def _resolve_timezone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return timezone.utc


def _to_pms_utc_string(dt_local: datetime) -> str:
    dt_utc = dt_local.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.999Z")


def _local_day_range(day, tz_info) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=tz_info)
    end = datetime.combine(day, time(23, 59, 59), tzinfo=tz_info)
    return start, end


def _extract_time_range(
    user_query: str,
    tz_name: str,
) -> tuple[str | None, str | None]:
    query = (user_query or "").lower().strip()
    if not query:
        return None, None

    tz_info = _resolve_timezone(tz_name)
    local_today = datetime.now(tz_info).date()

    if "today" in query:
        start_dt, end_dt = _local_day_range(local_today, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if "yesterday" in query:
        day = local_today - timedelta(days=1)
        start_dt, end_dt = _local_day_range(day, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    last_days_match = re.search(r"\blast\s+(\d+)\s+days?\b", query)
    if last_days_match:
        day_count = int(last_days_match.group(1))
        if day_count > 0:
            start_day = local_today - timedelta(days=day_count - 1)
            start_dt, _ = _local_day_range(start_day, tz_info)
            _, end_dt = _local_day_range(local_today, tz_info)
            return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if "this week" in query:
        week_start = local_today - timedelta(days=local_today.weekday())
        start_dt, _ = _local_day_range(week_start, tz_info)
        _, end_dt = _local_day_range(local_today, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if "last week" in query:
        this_week_start = local_today - timedelta(days=local_today.weekday())
        week_start = this_week_start - timedelta(days=7)
        week_end = this_week_start - timedelta(days=1)
        start_dt, _ = _local_day_range(week_start, tz_info)
        _, end_dt = _local_day_range(week_end, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if "this month" in query:
        month_start = local_today.replace(day=1)
        start_dt, _ = _local_day_range(month_start, tz_info)
        _, end_dt = _local_day_range(local_today, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if "last month" in query:
        first_this_month = local_today.replace(day=1)
        last_day_prev = first_this_month - timedelta(days=1)
        month_start = last_day_prev.replace(day=1)
        start_dt, _ = _local_day_range(month_start, tz_info)
        _, end_dt = _local_day_range(last_day_prev, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    return None, None


def _extract_time_range_with_llm(
    user_query: str,
    tz_name: str,
) -> tuple[str | None, str | None]:
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_template(template=TIME_RANGE_EXTRACT_PROMPT)
    parser = JsonOutputParser()
    chain = prompt | llm | parser
    try:
        response = chain.invoke({
            "current_date": _today_for_timezone(tz_name),
            "timezone": tz_name,
            "user_query": user_query,
        })
    except Exception:
        return _extract_time_range(user_query, tz_name)

    start_date = response.get("start_date", None)
    end_date = response.get("end_date", None)
    if isinstance(start_date, str) and isinstance(end_date, str):
        if _PMS_UTC_RE.match(start_date) and _PMS_UTC_RE.match(end_date):
            return start_date, end_date

    # Prompt often returns null dates + is_time_query=false for loose "today" asks — use heuristics.
    return _extract_time_range(user_query, tz_name)


def _needs_full_project_snapshot(user_query: str) -> bool:
    """Broad status asks: use full project fetch (PMS DateType window often filters by due date)."""
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
    ):
        if phrase in q:
            return True
    return False


def _broad_today_merge_query(user_query: str) -> bool:
    """Loose 'today' overview: merge date-window slice with full-project snapshot (see PMS DateType semantics)."""
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


def _merge_board_snapshots(boards_window: list, boards_full: list) -> list:
    """Dedupe TaskCards by taskId across two get_tasks responses."""
    seen: set[int] = set()
    ordered: list = []
    for boards in (boards_window, boards_full):
        for col in boards:
            for card in col.cards or []:
                tid = card.taskId
                if tid not in seen:
                    seen.add(tid)
                    ordered.append(card)
    if not ordered:
        return []
    return [
        BoardColumn(
            id=0,
            title="Board",
            taskBoardStatusName="MergedView",
            totalTask=len(ordered),
            cards=ordered,
        )
    ]


def _describe_timeframe(user_query: str) -> str:
    q = (user_query or "").lower()
    if "last month" in q:
        return "last month"
    if "this month" in q:
        return "this month"
    if "last week" in q:
        return "last week"
    if "this week" in q:
        return "this week"
    if "yesterday" in q:
        return "yesterday"
    if "today" in q:
        return "today"
    last_days_match = re.search(r"\blast\s+(\d+)\s+days?\b", q)
    if last_days_match:
        return f"the last {last_days_match.group(1)} days"
    return "that timeframe"


def _store_last_task_query(
    triage_state: dict,
    *,
    query: str,
    start_date: str | None,
    end_date: str | None,
) -> None:
    triage_state["last_task_query"] = {
        "query": query,
        "start_date": start_date,
        "end_date": end_date,
        "timeframe_label": _describe_timeframe(query),
    }


def get_task_node(state: AgentState) -> AgentState:
    triage_state = ensure_triage_state(state.get("triage_state"))
    timezone_name = state.get("timezone", "UTC")
    user_query = state.get("resolved_query") or state.get("user_query", "")
    raw_query = state.get("user_query", "")
    # Deterministic phrases (today, yesterday, last N days, …) — avoid LLM nulls and extra latency.
    start_date, end_date = _extract_time_range(user_query, timezone_name)
    if not start_date or not end_date:
        start_date, end_date = _extract_time_range_with_llm(user_query, timezone_name)
    if (not start_date or not end_date) and triage_state.get("last_task_query"):
        if user_query.strip().lower() != raw_query.strip().lower():
            last = triage_state.get("last_task_query") or {}
            if isinstance(last, dict):
                start_date = start_date or last.get("start_date")
                end_date = end_date or last.get("end_date")

    # Step 1: Login and fetch board data (broad "today" / overview uses merge or full snapshot — not chat-session scoped).
    scope_note = ""
    boards_raw: list[BoardColumn] = []
    try:
        token = pms_client.login()
        if _broad_today_merge_query(user_query):
            win_s, win_e = start_date, end_date
            if not win_s or not win_e:
                win_s, win_e = _extract_time_range("today", timezone_name)
            boards_window = pms_client.get_tasks(
                token,
                timezone=timezone_name,
                start_date=win_s,
                end_date=win_e,
            )
            try:
                boards_full = pms_client.get_tasks(
                    token,
                    timezone=timezone_name,
                    start_date=None,
                    end_date=None,
                )
            except Exception:
                boards_full = []
            boards_raw = boards_full or boards_window
            boards = _merge_board_snapshots(boards_window, boards_full)
            scope_note = (
                "Merged task snapshot: date-window slice plus full-project list. "
                "For loose 'today' questions, mention open items even if not due strictly today; say so in plain words. "
                "Do not say 'board' to the user."
            )
        elif _needs_full_project_snapshot(user_query):
            boards = pms_client.get_tasks(
                token,
                timezone=timezone_name,
                start_date=None,
                end_date=None,
            )
            boards_raw = boards
            scope_note = (
                "Full-project task list (no single-date filter). Summarize across items when the user asked broadly. "
                "Do not say 'board' to the user."
            )
        else:
            boards = pms_client.get_tasks(
                token,
                timezone=timezone_name,
                start_date=start_date,
                end_date=end_date,
            )
            boards_raw = boards

    except Exception as e:
        return {**state, "final_response": f"Failed to fetch task data: {str(e)}"}

    registry = WorkflowRegistry.from_board_columns(boards_raw)

    # Step 2: Serialize board data for LLM context
    board_data = json.dumps(
        [board.model_dump() for board in boards],
        indent=2,
    )
    card_count = sum(len(board.cards) for board in boards)
    triage_state["last_tool_verified_at"] = utc_now_iso()
    triage_state["verification_status"] = "verified"

    if card_count == 0:
        _store_last_task_query(
            triage_state,
            query=user_query,
            start_date=start_date,
            end_date=end_date,
        )
        timeframe = _describe_timeframe(user_query)
        return {
            **state,
            "triage_state": triage_state,
            "pms_token": token,
            "final_response": (
                f"I checked what we're tracking for {timeframe} and didn't find anything "
                "matching that view. Want to try a broader look?"
            ),
            "response_kind": "task_list",
            "response_actions": task_list_filter_actions(),
        }

    _store_last_task_query(
        triage_state,
        query=user_query,
        start_date=start_date,
        end_date=end_date,
    )

    if user_wants_list_format(user_query) or user_wants_summary_format(user_query):
        filt = parse_list_filter(user_query)
        list_text, structured_tasks = format_task_list(
            boards,
            registry=registry,
            filt=filt,
            timezone_name=timezone_name,
        )
        return {
            **state,
            "triage_state": triage_state,
            "pms_token": token,
            "final_response": list_text,
            "response_kind": "task_list",
            "response_actions": task_list_filter_actions(),
            "structured_tasks": structured_tasks,
        }

    # Step 3: Ask LLM to answer the user's question using board data as context
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_template(template=GET_TASK_ANSWER_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "board_data": board_data,
        "conversation_history": state.get("conversation_history", ""),
        "user_query": user_query,
        "scope_note": scope_note or "",
    })


    # prompt = GET_TASK_ANSWER_PROMPT.format(
    #     board_data=board_data,
    #     conversation_history=state.get("conversation_history", ""),
    #     current_date=_today_for_timezone(timezone_name),
    #     timezone=timezone_name,
    #     user_query=state["user_query"],
    # )
    # response = llm.invoke([HumanMessage(content=prompt)])

    return {
        **state,
        "triage_state": triage_state,
        "pms_token": token,
        "final_response": response.content.strip(),
    }
