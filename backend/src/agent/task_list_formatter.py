import re
from datetime import date, datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from src.agent.timeframe import (
    has_timeframe_in_query,
    is_timeframe_only_query,
    task_name_search_terms,
)
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
    COMPLETED = "completed"


_LIST_FILTER_WORDS = frozenset(
    {
        "completed",
        "complete",
        "finished",
        "done",
        "open",
        "progress",
        "overdue",
        "pending",
        "blocked",
        "closed",
        "resolved",
        "todo",
    }
)


def _specific_task_name_terms(user_query: str) -> list[str]:
    """Task-name tokens for lookup — excludes status/filter vocabulary."""
    return [t for t in task_name_search_terms(user_query) if t not in _LIST_FILTER_WORDS]


def is_list_filter_only_query(user_query: str) -> bool:
    """True when the user wants a filtered task view, not a named task lookup."""
    q = (user_query or "").lower().strip()
    if not q:
        return False
    if parse_list_filter(user_query) != TaskListFilter.ALL_OPEN:
        return len(_specific_task_name_terms(user_query)) == 0
    if re.search(r"\b(completed|finished|done|open|progress|overdue)\b", q) and re.search(
        r"\btasks?\b",
        q,
    ):
        return len(_specific_task_name_terms(user_query)) == 0
    return False

def user_wants_list_format(user_query: str) -> bool:
    q = (user_query or "").lower().strip()
    if not q:
        return False
    if has_timeframe_in_query(user_query):
        return True
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
    if re.search(r"\b(what|anything).*(happened|going on)\b|\b(happened|going on)\b", q):
        return True
    if re.search(
        r"\b(completed|finished|done)\b",
        q,
    ) and re.search(r"\btasks?\b", q):
        return True
    if re.search(r"\b(any|are there).*(tasks?).*(completed|done|finished)\b", q):
        return True
    if user_asks_about_specific_task(user_query):
        return True
    return False


def user_asks_about_specific_task(user_query: str) -> bool:
    q = (user_query or "").lower().strip()
    if not q:
        return False
    if is_timeframe_only_query(user_query):
        return False
    if is_list_filter_only_query(user_query):
        return False
    patterns = (
        r"\bwhat about\b",
        r"\bhow about\b",
        r"\btell me about\b",
        r"\bstatus of (the )?\w",
        r"\bwhat(?:'s| is) the status\b",
        r"\bwhere(?:'s| is) .*(task|issue|bug)\b",
    )
    if not any(re.search(p, q) for p in patterns):
        return False
    return bool(_specific_task_name_terms(user_query))


def _query_search_terms(user_query: str) -> list[str]:
    return task_name_search_terms(user_query)


def find_tasks_matching_query(
    cards: list[TaskCard],
    user_query: str,
    search_terms: list[str] | None = None,
) -> list[TaskCard]:
    terms = [t.strip().lower() for t in (search_terms or []) if (t or "").strip()]
    if not terms:
        terms = _query_search_terms(user_query)
    if not terms:
        return []

    scored: list[tuple[int, TaskCard]] = []
    for card in cards:
        title = (card.title or "").lower()
        desc = (card.description or "").lower()
        hits = sum(1 for term in terms if term in title or term in desc)
        if hits <= 0:
            continue
        scored.append((hits, card))

    if not scored:
        return []

    scored.sort(key=lambda item: (-item[0], item[1].taskId))
    best_hits = scored[0][0]
    min_hits = 2 if len(terms) >= 2 else 1
    if best_hits < min_hits and not any(len(t) >= 5 for t in terms):
        return []

    return [card for hits, card in scored if hits >= best_hits]


def format_matched_tasks(
    cards: list[TaskCard],
    *,
    registry: WorkflowRegistry,
    intro: str | None = None,
) -> tuple[str, list[dict]]:
    if not cards:
        return "I couldn't find a matching task in what we're tracking.", []

    lines = [intro or "Here's what I found:", ""]
    structured: list[dict] = []
    for idx, card in enumerate(cards[:5], start=1):
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
    if any(
        phrase in q
        for phrase in (
            "completed",
            "been completed",
            "have been completed",
            "has been completed",
            "finished tasks",
            "done tasks",
            "tasks done",
            "tasks completed",
        )
    ) or (
        re.search(r"\b(completed|finished|done)\b", q)
        and re.search(r"\btasks?\b", q)
    ):
        return TaskListFilter.COMPLETED
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
    if filt == TaskListFilter.COMPLETED:
        return "Completed tasks:"
    return "Here's what we're tracking:"


def filter_empty_message(filt: TaskListFilter) -> str:
    if filt == TaskListFilter.IN_PROGRESS:
        return "Nothing in progress right now."
    if filt == TaskListFilter.DUE_THIS_WEEK:
        return "Nothing due this week."
    if filt == TaskListFilter.COMPLETED:
        return "I don't see any completed tasks in what we're tracking right now."
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

    if filt == TaskListFilter.COMPLETED:
        return [c for c in cards if _is_done_card(c, registry)]

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


flatten_cards = _flatten_cards


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
