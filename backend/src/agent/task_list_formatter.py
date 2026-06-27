import re
from datetime import date, datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from src.agent.workflow_registry import WorkflowRegistry
from src.pms_client.schemas import BoardColumn, TaskCard

_LIST_INTENT_PHRASES = (
    "list",
    "show",
    "open tasks",
    "my tasks",
    "give me an update",
    "status update",
    "what's going on",
    "whats going on",
    "what else is open",
    "board update",
    "overall update",
    "anything else open",
    "what's on the board",
    "whats on the board",
    "where are we at",
    "where we at",
    "catch me up",
    "any tasks",
    "all tasks",
)


class TaskListFilter(str, Enum):
    ALL_OPEN = "all_open"
    IN_PROGRESS = "in_progress"
    DUE_THIS_WEEK = "due_this_week"


def user_wants_list_format(user_query: str) -> bool:
    q = (user_query or "").lower().strip()
    if not q:
        return False
    if user_wants_summary_format(user_query):
        return True
    if any(phrase in q for phrase in _LIST_INTENT_PHRASES):
        return True
    if re.search(r"\bwhat'?s going on\b", q):
        return True
    if re.search(r"\b(check|see|view|get)\s+(the\s+)?(task\s+)?status\b", q):
        return True
    if re.search(r"\btask\s+status\b", q):
        return True
    if re.search(r"\bstatus\s+of\s+(my\s+)?tasks\b", q):
        return True
    return False


def user_wants_summary_format(user_query: str) -> bool:
    q = (user_query or "").lower().strip()
    if not q:
        return False
    return any(
        phrase in q
        for phrase in (
            "summary",
            "overview",
            "recap",
            "run down",
            "rundown",
            "catch me up",
            "give me details",
            "show me details",
        )
    )


def parse_list_filter(user_query: str) -> TaskListFilter:
    q = (user_query or "").lower().strip()
    if "due this week" in q or "due within this week" in q:
        return TaskListFilter.DUE_THIS_WEEK
    if "in progress" in q or "in-progress" in q:
        return TaskListFilter.IN_PROGRESS
    return TaskListFilter.ALL_OPEN


def filter_intro(filt: TaskListFilter) -> str:
    if filt == TaskListFilter.IN_PROGRESS:
        return "Tasks in progress:"
    if filt == TaskListFilter.DUE_THIS_WEEK:
        return "Tasks due this week:"
    return "Here's what we're tracking:"


def filter_empty_message(filt: TaskListFilter) -> str:
    if filt == TaskListFilter.IN_PROGRESS:
        return "Nothing in progress right now."
    if filt == TaskListFilter.DUE_THIS_WEEK:
        return "Nothing due this week."
    return "I checked what we're tracking and there's nothing matching this view right now."


def _resolve_timezone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _week_range(reference: date) -> tuple[date, date]:
    week_start = reference - timedelta(days=reference.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _parse_due_date(due_date: str | None) -> date | None:
    if not due_date:
        return None
    raw = due_date.strip()
    if len(raw) < 10:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _is_done_card(card: TaskCard, registry: WorkflowRegistry) -> bool:
    if card.completedDate and str(card.completedDate).strip():
        return True
    return card.currentTaskBoardId in registry.done_board_ids


def apply_list_filter(
    cards: list[TaskCard],
    filt: TaskListFilter,
    registry: WorkflowRegistry,
    timezone_name: str = "UTC",
    reference_date: date | None = None,
) -> list[TaskCard]:
    if filt == TaskListFilter.ALL_OPEN:
        return [c for c in cards if not _is_done_card(c, registry)]

    if filt == TaskListFilter.IN_PROGRESS:
        if not registry.in_progress_board_ids:
            return []
        return [
            c
            for c in cards
            if c.currentTaskBoardId in registry.in_progress_board_ids
        ]

    if filt == TaskListFilter.DUE_THIS_WEEK:
        tz = _resolve_timezone(timezone_name)
        ref = reference_date or datetime.now(tz).date()
        week_start, week_end = _week_range(ref)
        filtered: list[TaskCard] = []
        for card in cards:
            due = _parse_due_date(card.dueDate)
            if due is not None and week_start <= due <= week_end:
                filtered.append(card)
        return filtered

    return list(cards)


def _flatten_cards(boards: list[BoardColumn]) -> list[TaskCard]:
    cards: list[TaskCard] = []
    seen: set[int] = set()
    for board in boards:
        for card in board.cards or []:
            if card.taskId not in seen:
                seen.add(card.taskId)
                cards.append(card)
    return cards


def _format_due(due_date: str | None) -> str:
    if not due_date:
        return "no due date"
    raw = due_date.strip()
    if len(raw) >= 10:
        try:
            parsed = datetime.fromisoformat(raw[:10])
            return parsed.strftime("%b %d")
        except ValueError:
            return raw[:10]
    return raw


def format_task_list(
    boards: list[BoardColumn],
    *,
    registry: WorkflowRegistry,
    filt: TaskListFilter = TaskListFilter.ALL_OPEN,
    timezone_name: str = "UTC",
    intro: str | None = None,
    reference_date: date | None = None,
) -> tuple[str, list[dict]]:
    cards = _flatten_cards(boards)
    cards = apply_list_filter(
        cards,
        filt,
        registry,
        timezone_name=timezone_name,
        reference_date=reference_date,
    )
    cards = sorted(
        cards,
        key=lambda c: registry.sort_key_for_card(
            c.currentTaskBoardId, c.dueDate, c.taskId
        ),
    )

    if not cards:
        return filter_empty_message(filt), []

    lines = [intro or filter_intro(filt), ""]
    structured: list[dict] = []

    for idx, card in enumerate(cards, start=1):
        status = registry.label_for(card.currentTaskBoardId)
        due = _format_due(card.dueDate)
        assignee = (card.assignee or "").strip()
        meta_parts = [status, f"due {due}", f"#{card.taskId}"]
        if assignee:
            meta_parts.insert(2, assignee)
        meta = " · ".join(meta_parts)
        title = (card.title or "Untitled").strip()
        lines.append(f"{idx}. **{title}** — {meta}")
        structured.append(
            {
                "taskId": card.taskId,
                "title": title,
                "status": status,
                "dueDate": card.dueDate,
                "assignee": assignee or None,
            }
        )

    return "\n".join(lines), structured
