import json
import re
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from langchain_openai import ChatOpenAI
from src.agent.state import AgentState
from src.agent.prompts import GET_TASK_ANSWER_PROMPT, TIME_RANGE_EXTRACT_PROMPT
from src.agent.timeframe import (
    describe_timeframe,
    extract_time_range,
    is_timeframe_only_query,
    timeframe_list_intro,
)
from src.agent.task_list_formatter import (
    find_tasks_matching_query,
    flatten_cards,
    format_matched_tasks,
    format_task_list,
    is_list_filter_only_query,
    parse_list_filter,
    user_asks_about_specific_task,
    user_wants_list_format,
    user_wants_summary_format,
)
from src.agent.assistant_offer import (
    clear_assistant_offer,
    store_broaden_offer,
)
from src.agent.task_query_plan import plan_task_query, resolve_plan_dates
from src.agent.triage_memory import ensure_triage_state, utc_now_iso
from src.agent.workflow_registry import WorkflowRegistry
from src.pms_client import client as pms_client
from src.pms_client.schemas import BoardColumn, TaskCard
from src.agent.cta_policy import is_no_results_reply, is_time_range_context
from src.settings import settings


def _cta_scenario_for_get_task_answer(user_query: str) -> str:
    q = (user_query or "").lower()
    if any(p in q for p in ("who is working", "who's working", "who working", "assigned to", "assigned to who")):
        return "assignee_answered"
    if any(p in q for p in ("when is it due", "when's it due", "due date", "what's the due")):
        return "due_date_answered"
    return "specific_task"


def _cta_scenario_for_get_task_response(
    state: dict,
    user_query: str,
    reply: str,
    *,
    is_time_query: bool = False,
) -> str:
    if is_no_results_reply(reply):
        ctx = {**state, "user_query": user_query}
        if is_time_query or is_time_range_context(ctx, user_query):
            return "no_results_range"
        return "no_results"
    return _cta_scenario_for_get_task_answer(user_query)
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
        return extract_time_range(user_query, tz_name)

    start_date = response.get("start_date", None)
    end_date = response.get("end_date", None)
    if isinstance(start_date, str) and isinstance(end_date, str):
        if _PMS_UTC_RE.match(start_date) and _PMS_UTC_RE.match(end_date):
            return start_date, end_date

    # Prompt often returns null dates + is_time_query=false for loose "today" asks — use heuristics.
    return extract_time_range(user_query, tz_name)


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


def _timeframe_empty_fallback(user_query: str) -> bool:
    """When a date window is empty, show open work for bare timeframe asks."""
    return is_timeframe_only_query(user_query)


def _parse_card_date(value: str | None) -> date | None:
    if not value:
        return None
    raw = value.strip()
    if len(raw) >= 10:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass
    normalized = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return None


def _local_range_from_pms_utc(
    start_date: str,
    end_date: str,
    tz_name: str,
) -> tuple[date, date]:
    tz = _resolve_timezone(tz_name)

    def to_local_day(raw: str) -> date:
        normalized = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(tz).date()

    return to_local_day(start_date), to_local_day(end_date)


def _card_in_local_date_range(
    card: TaskCard,
    range_start: date,
    range_end: date,
) -> bool:
    for field in (card.dueDate, card.completedDate):
        day = _parse_card_date(field)
        if day is not None and range_start <= day <= range_end:
            return True
    return False


def _filter_boards_by_local_date_range(
    boards: list[BoardColumn],
    range_start: date,
    range_end: date,
) -> list[BoardColumn]:
    cards: list[TaskCard] = []
    seen: set[int] = set()
    for col in boards:
        for card in col.cards or []:
            if card.taskId in seen:
                continue
            if _card_in_local_date_range(card, range_start, range_end):
                seen.add(card.taskId)
                cards.append(card)
    if not cards:
        return []
    return [
        BoardColumn(
            id=0,
            title="Board",
            taskBoardStatusName="DateFilteredView",
            totalTask=len(cards),
            cards=cards,
        )
    ]


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
        "timeframe_label": describe_timeframe(query),
    }


def get_task_node(state: AgentState) -> AgentState:
    triage_state = ensure_triage_state(state.get("triage_state"))
    timezone_name = state.get("timezone", "UTC")
    user_query = state.get("resolved_query") or state.get("user_query", "")
    history = state.get("conversation_history", "")

    plan = plan_task_query(user_query, history, triage_state, timezone_name)
    start_date, end_date = resolve_plan_dates(
        plan,
        user_query,
        timezone_name,
        triage_state,
        _extract_time_range_with_llm,
    )
    is_time_query = bool(start_date and end_date) or plan.mode == "timeframe"

    scope_note = ""
    boards_raw: list[BoardColumn] = []
    timeframe_fallback_intro: str | None = None
    plan_dump = plan.model_dump(mode="json")

    try:
        token = pms_client.login()
        if plan.merge_today_with_full or (
            plan.mode == "timeframe" and "today" in (user_query or "").lower()
            and any(k in (user_query or "").lower() for k in ("update", "going on", "catch me up"))
        ):
            win_s, win_e = start_date, end_date
            if not win_s or not win_e:
                win_s, win_e = extract_time_range("today", timezone_name)
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
        elif plan.mode == "full_snapshot":
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
        elif plan.mode == "timeframe" and start_date and end_date:
            boards_full = pms_client.get_tasks(
                token,
                timezone=timezone_name,
                start_date=None,
                end_date=None,
            )
            boards_raw = boards_full
            range_start, range_end = _local_range_from_pms_utc(
                start_date,
                end_date,
                timezone_name,
            )
            boards = _filter_boards_by_local_date_range(
                boards_full,
                range_start,
                range_end,
            )
            scope_note = (
                "Tasks filtered by due or completion date within the requested timeframe. "
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

    card_count = sum(len(board.cards) for board in boards)

    if (
        card_count == 0
        and start_date
        and end_date
        and boards_raw
        and _timeframe_empty_fallback(user_query)
    ):
        boards = boards_raw
        card_count = sum(len(board.cards) for board in boards)
        timeframe = describe_timeframe(user_query)
        timeframe_fallback_intro = (
            f"No tasks were due or completed {timeframe}. "
            "Here's everything we're still tracking:"
        )
        scope_note = (
            "User asked what happened in a timeframe; strict date match was empty so show open work. "
            "Do not say 'board' to the user."
        )

    registry = WorkflowRegistry.from_board_columns(boards_raw)

    board_data = json.dumps(
        [board.model_dump() for board in boards],
        indent=2,
    )
    triage_state["last_tool_verified_at"] = utc_now_iso()
    triage_state["verification_status"] = "verified"

    base_task_state = {
        **state,
        "triage_state": triage_state,
        "task_query_plan": plan_dump,
    }

    if card_count == 0:
        _store_last_task_query(
            triage_state,
            query=user_query,
            start_date=start_date,
            end_date=end_date,
        )
        timeframe = describe_timeframe(user_query)
        store_broaden_offer(
            triage_state,
            prior_query=user_query,
            prior_start_date=start_date,
            prior_end_date=end_date,
        )
        return {
            **base_task_state,
            "pms_token": token,
            "final_response": (
                f"I checked what we're tracking for {timeframe} and didn't find anything "
                "matching that view. Want to try a broader look?"
            ),
            "response_kind": "task_list",
            "structured_tasks": [],
            "cta_scenario": "no_results_range" if is_time_query else "no_results",
        }

    clear_assistant_offer(triage_state)

    _store_last_task_query(
        triage_state,
        query=user_query,
        start_date=start_date,
        end_date=end_date,
    )

    all_cards = flatten_cards(boards_raw)

    use_specific = plan.mode == "specific_task" or (
        plan.mode == "freeform_qa"
        and user_asks_about_specific_task(user_query)
        and not is_time_query
        and not is_list_filter_only_query(user_query)
    )
    if use_specific:
        matches = find_tasks_matching_query(
            all_cards,
            user_query,
            search_terms=plan.search_terms or None,
        )
        if matches:
            list_text, structured_tasks = format_matched_tasks(
                matches,
                registry=registry,
            )
            return {
                **base_task_state,
                "pms_token": token,
                "final_response": list_text,
                "response_kind": "task_list",
                "structured_tasks": structured_tasks,
            }
        return {
            **base_task_state,
            "pms_token": token,
            "final_response": (
                "I couldn't find a tracked task matching that in what we're tracking."
            ),
            "response_kind": "task_list",
            "structured_tasks": [],
            "cta_scenario": "no_results",
        }

    use_list = (
        plan.mode in {"timeframe", "list_filter", "full_snapshot"}
        or timeframe_fallback_intro
        or (
            plan.mode == "freeform_qa"
            and (
                is_time_query
                or user_wants_list_format(user_query)
                or user_wants_summary_format(user_query)
            )
        )
    )
    if use_list:
        filt = plan.list_filter or parse_list_filter(user_query)
        intro = timeframe_fallback_intro
        if is_time_query and not intro:
            intro = timeframe_list_intro(user_query)
        list_text, structured_tasks = format_task_list(
            boards,
            registry=registry,
            filt=filt,
            timezone_name=timezone_name,
            intro=intro,
        )
        if is_no_results_reply(list_text) or not structured_tasks:
            cta_scenario = "no_results_range" if is_time_query else "no_results"
        elif is_time_query:
            cta_scenario = "time_snapshot"
        else:
            cta_scenario = "broad_status"
        return {
            **base_task_state,
            "pms_token": token,
            "final_response": list_text,
            "response_kind": "task_list",
            "structured_tasks": structured_tasks,
            "cta_scenario": cta_scenario,
        }

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    prompt = ChatPromptTemplate.from_template(template=GET_TASK_ANSWER_PROMPT)
    chain = prompt | llm
    response = chain.invoke({
        "board_data": board_data,
        "conversation_history": history,
        "user_query": user_query,
        "scope_note": scope_note or "",
    })

    final_response = response.content.strip()
    return {
        **base_task_state,
        "pms_token": token,
        "final_response": final_response,
        "response_kind": "task_summary",
        "structured_tasks": [],
        "cta_scenario": _cta_scenario_for_get_task_response(
            state,
            user_query,
            final_response,
            is_time_query=is_time_query,
        ),
    }
