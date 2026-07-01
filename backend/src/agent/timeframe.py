"""Shared calendar / relative-time detection and range extraction for task queries."""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_TIMEFRAME_WORDS = frozenset(
    {
        "today",
        "yesterday",
        "tomorrow",
        "week",
        "weeks",
        "month",
        "months",
        "year",
        "years",
        "quarter",
        "quarters",
        "day",
        "days",
        "last",
        "this",
        "next",
        "past",
        "due",
        "overdue",
        "within",
        "during",
        "between",
        "from",
        "since",
        "ago",
    }
)

_TIMEFRAME_PATTERNS = (
    r"\btoday\b",
    r"\byesterday\b",
    r"\btomorrow\b",
    r"\b(this|last|next|past)\s+(week|month|year|quarter)\b",
    r"\b(due|overdue)\s+(today|tomorrow|this\s+week|next\s+week|this\s+month)\b",
    r"\blast\s+\d+\s+(days?|weeks?|months?|years?)\b",
    r"\bpast\s+\d+\s+(days?|weeks?|months?|years?)\b",
    r"\b(in|within|during)\s+(the\s+)?(last|past)\s+\d+\s+(days?|weeks?|months?)\b",
    r"\b(in|within|during)\s+(the\s+)?(last|past)\s+(week|month|year|quarter)\b",
    r"\bwhat\s+(?:happened|went\s+on|changed)\b.*\b(today|yesterday|week|month)\b",
    r"\b(tasks?|anything|something)\s+(due|overdue)\b",
)

_QUERY_STOP_WORDS = frozenset(
    {
        "what",
        "about",
        "how",
        "tell",
        "me",
        "status",
        "of",
        "is",
        "there",
        "any",
        "a",
        "an",
        "this",
        "that",
        "please",
        "just",
        "been",
        "has",
        "have",
        "which",
        "where",
        "the",
        "show",
        "list",
        "give",
        "get",
        "see",
        "check",
        "my",
        "all",
        "open",
        "tasks",
        "task",
        "for",
        "in",
        "on",
        "with",
        "were",
        "was",
        "are",
        "did",
        "do",
        "does",
        "happened",
        "going",
        "update",
        "summary",
        "details",
    }
)


def has_timeframe_in_query(user_query: str) -> bool:
    q = (user_query or "").lower().strip()
    if not q:
        return False
    return any(re.search(pattern, q) for pattern in _TIMEFRAME_PATTERNS)


def task_name_search_terms(user_query: str) -> list[str]:
    """Words that might identify a named task (excludes timeframe vocabulary)."""
    q = re.sub(r"[^\w\s]", " ", (user_query or "").lower())
    return [
        w
        for w in q.split()
        if w not in _QUERY_STOP_WORDS
        and w not in _TIMEFRAME_WORDS
        and not w.isdigit()
        and len(w) >= 3
    ]


def is_timeframe_only_query(user_query: str) -> bool:
    """True when the user is asking about a period, not a named task."""
    if not has_timeframe_in_query(user_query):
        return False
    return len(task_name_search_terms(user_query)) == 0


def describe_timeframe(user_query: str) -> str:
    q = (user_query or "").lower()
    if re.search(r"\blast\s+month\b", q):
        return "last month"
    if re.search(r"\bthis\s+month\b", q):
        return "this month"
    if re.search(r"\bnext\s+month\b", q):
        return "next month"
    if re.search(r"\blast\s+week\b", q):
        return "last week"
    if re.search(r"\bthis\s+week\b", q):
        return "this week"
    if re.search(r"\bnext\s+week\b", q):
        return "next week"
    if re.search(r"\byesterday\b", q):
        return "yesterday"
    if re.search(r"\btomorrow\b", q):
        return "tomorrow"
    if re.search(r"\btoday\b", q):
        return "today"
    last_days = re.search(r"\b(?:last|past)\s+(\d+)\s+days?\b", q)
    if last_days:
        return f"the last {last_days.group(1)} days"
    last_weeks = re.search(r"\b(?:last|past)\s+(\d+)\s+weeks?\b", q)
    if last_weeks:
        return f"the last {last_weeks.group(1)} weeks"
    return "that timeframe"


def timeframe_list_intro(user_query: str) -> str:
    label = describe_timeframe(user_query)
    return f"Tasks due or completed {label}:"


def _resolve_timezone(tz_name: str):
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return timezone.utc


def _local_day_range(day: date, tz_info) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=tz_info)
    end = datetime.combine(day, time(23, 59, 59), tzinfo=tz_info)
    return start, end


def _to_pms_utc_string(dt_local: datetime) -> str:
    dt_utc = dt_local.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%S.999Z")


def extract_time_range(
    user_query: str,
    tz_name: str,
) -> tuple[str | None, str | None]:
    query = (user_query or "").lower().strip()
    if not query:
        return None, None

    tz_info = _resolve_timezone(tz_name)
    local_today = datetime.now(tz_info).date()

    if re.search(r"\btoday\b", query):
        start_dt, end_dt = _local_day_range(local_today, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\byesterday\b", query):
        day = local_today - timedelta(days=1)
        start_dt, end_dt = _local_day_range(day, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\btomorrow\b", query):
        day = local_today + timedelta(days=1)
        start_dt, end_dt = _local_day_range(day, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    last_days_match = re.search(r"\b(?:last|past|in|within)\s+(\d+)\s+days?\b", query)
    if last_days_match:
        day_count = int(last_days_match.group(1))
        if day_count > 0:
            start_day = local_today - timedelta(days=day_count - 1)
            start_dt, _ = _local_day_range(start_day, tz_info)
            _, end_dt = _local_day_range(local_today, tz_info)
            return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\bthis\s+week\b", query):
        week_start = local_today - timedelta(days=local_today.weekday())
        week_end = week_start + timedelta(days=6)
        start_dt, _ = _local_day_range(week_start, tz_info)
        _, end_dt = _local_day_range(week_end, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\blast\s+week\b", query):
        this_week_start = local_today - timedelta(days=local_today.weekday())
        week_start = this_week_start - timedelta(days=7)
        week_end = this_week_start - timedelta(days=1)
        start_dt, _ = _local_day_range(week_start, tz_info)
        _, end_dt = _local_day_range(week_end, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\bnext\s+week\b", query):
        this_week_start = local_today - timedelta(days=local_today.weekday())
        week_start = this_week_start + timedelta(days=7)
        week_end = week_start + timedelta(days=6)
        start_dt, _ = _local_day_range(week_start, tz_info)
        _, end_dt = _local_day_range(week_end, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\bthis\s+month\b", query):
        month_start = local_today.replace(day=1)
        if local_today.month == 12:
            month_end = local_today.replace(day=31)
        else:
            month_end = (local_today.replace(day=1, month=local_today.month + 1) - timedelta(days=1))
        start_dt, _ = _local_day_range(month_start, tz_info)
        _, end_dt = _local_day_range(month_end, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\blast\s+month\b", query):
        first_this_month = local_today.replace(day=1)
        last_day_prev = first_this_month - timedelta(days=1)
        month_start = last_day_prev.replace(day=1)
        start_dt, _ = _local_day_range(month_start, tz_info)
        _, end_dt = _local_day_range(last_day_prev, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    if re.search(r"\bnext\s+month\b", query):
        if local_today.month == 12:
            month_start = date(local_today.year + 1, 1, 1)
            month_end = date(local_today.year + 1, 1, 31)
        else:
            month_start = date(local_today.year, local_today.month + 1, 1)
            if month_start.month == 12:
                month_end = date(month_start.year, 12, 31)
            else:
                month_end = date(month_start.year, month_start.month + 1, 1) - timedelta(days=1)
        start_dt, _ = _local_day_range(month_start, tz_info)
        _, end_dt = _local_day_range(month_end, tz_info)
        return _to_pms_utc_string(start_dt), _to_pms_utc_string(end_dt)

    return None, None
