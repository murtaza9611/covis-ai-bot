def _action(action_id: str, label: str, payload: str, action_type: str = "quick_reply") -> dict:
    return {
        "id": action_id,
        "label": label,
        "type": action_type,
        "payload": payload,
    }


def confirmation_actions() -> list[dict]:
    return [
        _action("confirm_yes", "Yes, log it", "yes"),
        _action("confirm_no", "No, skip", "no"),
        _action("confirm_edit", "Edit details", "I want to change the details"),
    ]


def starter_actions() -> list[dict]:
    """Greeting / new session / out-of-scope entry points."""
    return [
        _action("report_bug", "Report a bug", "I want to report a bug"),
        _action("check_status", "Check project status", "Check project status"),
        _action("request_feature", "Request a feature", "I want to request a feature"),
        _action("due_week", "What's due this week?", "What's due this week?"),
    ]


def out_of_scope_actions() -> list[dict]:
    return starter_actions()[:3]


def greeting_actions() -> list[dict]:
    return starter_actions()


def post_create_bug_actions() -> list[dict]:
    return [
        _action("track_bug", "Track this bug", "What is the status of the bug I just logged?"),
        _action("log_another", "Report another issue", "I want to report a new issue"),
        _action("open_bugs", "See all open bugs", "Show me all open bugs"),
    ]


def post_create_feature_actions() -> list[dict]:
    return [
        _action("check_request", "Check request status", "What is the status of the feature I just requested?"),
        _action("pending_features", "See all pending features", "Show me all pending feature requests"),
    ]


def post_create_actions() -> list[dict]:
    return [
        _action("check_logged_status", "Check its status", "What is the status of the issue I just logged?"),
        _action("log_another", "Report another issue", "I want to report a new issue"),
        _action("view_tasks", "View open tasks", "List my open tasks"),
    ]


def duplicate_detected_actions() -> list[dict]:
    return [
        _action("view_existing", "View existing task", "What is the status of the existing task?"),
        _action("log_separate", "Log as separate issue", "This is a separate issue — log it as new"),
    ]


def broad_status_actions() -> list[dict]:
    return [
        _action("due_week", "What's due this week?", "What's due this week?"),
        _action("open_bugs", "Show open bugs", "Show me all open bugs"),
        _action("who_working", "Who's working on what?", "Who's working on what right now?"),
    ]


def no_results_range_actions() -> list[dict]:
    """Pivot to other time ranges / broader views when a window had no tasks."""
    return [
        _action("open_bugs", "Show open bugs", "Show me all open bugs"),
        _action("who_working", "Who's working on what?", "Who's working on what right now?"),
        _action("due_next_week", "What's due next week?", "What's due next week?"),
    ]


def specific_task_actions() -> list[dict]:
    return [
        _action("ask_assignee", "Who's assigned to this?", "Who is assigned to this task?"),
        _action("ask_due", "When is it due?", "When is this task due?"),
        _action("mark_urgent", "Mark as urgent", "I need to mark this task as urgent"),
    ]


def assignee_answered_actions() -> list[dict]:
    return [
        _action("their_tasks", "See their other tasks", "What other tasks are they working on?"),
        _action("check_status", "Check task status", "What's the current status of this task?"),
        _action("report_issue", "Report an issue with this task", "I want to report an issue with this task"),
    ]


def due_date_answered_actions() -> list[dict]:
    return [
        _action("due_soon", "What else is due soon?", "What else is due soon?"),
        _action("check_status", "Check task status", "What's the current status of this task?"),
    ]


def time_snapshot_actions() -> list[dict]:
    return [
        _action("week_progress", "Show this week's progress", "Show me this week's progress"),
        _action("completed", "See completed tasks", "Show me completed tasks"),
    ]


def soft_pivot_actions() -> list[dict]:
    return [
        _action("check_status", "Check project status", "Check project status"),
        _action("last_issue", "Check on my last issue", "What is the status of the issue I reported last?"),
    ]


def task_list_filter_actions() -> list[dict]:
    return [
        _action("filter_all_open", "List all open tasks", "List my open tasks"),
        _action("filter_in_progress", "Show in progress", "Show tasks in progress"),
        _action("filter_due_week", "Show due this week", "Show tasks due this week"),
        _action("log_new", "Log new issue", "I want to report a new issue"),
    ]


def task_list_pivot_actions() -> list[dict]:
    return [
        _action("filter_in_progress", "Show in progress", "Show tasks in progress"),
        _action("filter_due_week", "Due this week", "Show tasks due this week"),
        _action("filter_completed", "Show completed", "any task completed till now"),
        _action("log_new", "Log new issue", "I want to report a new issue"),
    ]


def clarify_actions() -> list[dict]:
    return [
        _action("list_open", "List open tasks", "List my open tasks"),
        _action("report_issue", "Report an issue", "I want to report a new issue"),
    ]
