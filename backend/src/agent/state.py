from typing import TypedDict, NotRequired, Any


class AgentState(TypedDict):
    user_query: str
    session_id: str
    timezone: str             # passed from API request
    conversation_history: str # formatted prior turns for this session
    intent: str               # create_task | get_task_info | greet | clarify | general_chat
    extracted_fields: dict    # parsed fields for task creation
    pms_token: str            # bearer token after login
    pms_response: dict        # raw API response data
    final_response: str       # natural language reply to user
    triage_state: NotRequired[dict[str, Any]]
    resolved_query: NotRequired[str]
    pending_task_payload: NotRequired[dict[str, Any] | None]
    clear_pending_task: NotRequired[bool]
    clear_session_state: NotRequired[bool]
    response_actions: NotRequired[list[dict[str, Any]]]
    response_kind: NotRequired[str]
    structured_tasks: NotRequired[list[dict[str, Any]]]
