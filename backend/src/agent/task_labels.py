WORKFLOW_USER_PHRASE = {
    2011: "not started yet",
    2012: "in progress",
    2013: "heading toward integration",
    2014: "in testing",
    2015: "done",
}

# Fallback labels when PMS column metadata is unavailable (e.g. unknown board id).
# Prefer WorkflowRegistry.label_for() built from BoardColumn title/status names.
WORKFLOW_SORT_ORDER = {
    2011: 0,
    2012: 1,
    2013: 2,
    2014: 3,
    2015: 4,
}


def workflow_status_phrase(board_id: int) -> str:
    return WORKFLOW_USER_PHRASE.get(board_id, "in the backlog")
