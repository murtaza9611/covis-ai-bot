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


def post_create_actions() -> list[dict]:
    return [
        _action("view_tasks", "View open tasks", "List my open tasks"),
        _action("log_another", "Log another issue", "I want to report a new issue"),
    ]


def task_list_filter_actions() -> list[dict]:
    return [
        _action("filter_all_open", "List all open tasks", "List my open tasks"),
        _action("filter_in_progress", "Show in progress", "Show tasks in progress"),
        _action("filter_due_week", "Show due this week", "Show tasks due this week"),
        _action("log_new", "Log new issue", "I want to report a new issue"),
    ]


def greeting_actions() -> list[dict]:
    return [
        _action("list_tasks", "List open tasks", "List my open tasks"),
        _action("report_issue", "Report an issue", "I want to report a new issue"),
        _action("help", "What can you do?", "What can you help me with?"),
    ]


def clarify_actions() -> list[dict]:
    return [
        _action("free_text", "Type your reply", "", "free_text_hint"),
    ]
