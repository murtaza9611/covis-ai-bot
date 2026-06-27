import json
import logging
import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from src.agent.state import AgentState
from src.agent.prompts import (
    CREATE_TASK_EXTRACT_PROMPT,
    CREATE_TASK_CONFIRMATION_PROMPT,
    TASK_SIMILARITY_PROMPT,
    EXISTING_TASK_REPLY_PROMPT,
    PENDING_CONFIRMATION_FOLLOWUP_PROMPT,
)
from src.agent.task_confirmation import (
    is_affirmative,
    is_edit_request,
    is_negative,
    is_single_token_affirmative,
)
from src.agent.task_labels import workflow_status_phrase
from src.agent.response_actions import (
    clarify_actions,
    confirmation_actions,
    post_create_actions,
)
from src.agent.triage_memory import (
    ensure_triage_state,
    get_active_incident,
    create_incident,
    update_active_incident,
    should_start_new_incident,
)
from src.pms_client import client as pms_client
from src.pms_client.schemas import BoardColumn, TaskPayload
from src.settings import settings

logger = logging.getLogger(__name__)

_RELATION_VALUES = frozenset({"same_item", "new_item", "off_topic"})

SEVERITY_LABELS = {1: "Critical", 2: "Important", 3: "Normal", 4: "Minor", 5: "Low"}
TASK_TYPE_LABELS = {35: "Task", 36: "Bug", 37: "Story"}

_IDLE_CHAT_GREETING_RE = re.compile(
    r"^(hi|hey|hello|heelo|helo|hiya|yo|gm)\b",
    re.IGNORECASE,
)


def _looks_like_idle_chat_while_pending(user_query: str) -> bool:
    """
    Short social / filler messages while a task is awaiting yes/no.
    These must not run the pending-followup classifier (which labels them off_topic
    and repeats the confirmation prompt — feels broken in chat).
    """
    q = (user_query or "").strip().lower()
    q = re.sub(r"[!.…!?]+$", "", q).strip()
    if len(q) > 140:
        return False

    exact = {
        "hi",
        "hey",
        "hello",
        "heelo",
        "helo",
        "hiya",
        "yo",
        "gm",
        "thanks",
        "thank you",
        "thx",
        "ty",
        "cheers",
        "nice",
        "sup",
    }
    if q in exact:
        return True

    if _IDLE_CHAT_GREETING_RE.match(q) and len(q) < 55:
        m = _IDLE_CHAT_GREETING_RE.match(q)
        if m and m.end() < len(q):
            tail = q[m.end() :].lstrip(" ,—-")
            # "hey thanks" / "hi thanks" should use classifier (off_topic), not idle shortcut
            if tail and any(
                t in tail
                for t in ("thank", "thx", "appreciate", "grateful", "ty", "cheers")
            ):
                return False
        return True

    if any(
        phrase in q
        for phrase in (
            "how are you",
            "how's it going",
            "how are things",
            "how you doing",
            "what's up",
            "whats up",
            "wassup",
            "good morning",
            "good afternoon",
            "good evening",
            "morning",
            "afternoon",
            "evening",
        )
    ):
        return True

    if q in {"you?", "and you?", "what about you", "hbu", "u?"}:
        return True

    return False


def _idle_chat_reply_while_pending() -> str:
    """Warm reply without repeating the draft title (user already saw it)."""
    return (
        "Doing well — thanks for asking. "
        "Whenever you’re ready, say **yes** to log that pending task or **no** to skip it. No rush."
    )


_STOPWORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "on", "for", "to", "in", "of", "and", "or", "with", "as", "at", "by",
    "this", "that", "it", "its", "we", "you", "they", "i", "there", "here",
    "from", "into", "about", "any", "some", "our", "your", "their",
})


def _workflow_status_phrase(board_id: int) -> str:
    return workflow_status_phrase(board_id)


def _tokenize_for_search(text: str, max_tokens: int) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9]+", (text or "").lower())
    picked: list[str] = []
    seen: set[str] = set()
    for w in words:
        if len(w) < 2 or w in _STOPWORDS:
            continue
        if w not in seen:
            seen.add(w)
            picked.append(w)
        if len(picked) >= max_tokens:
            break
    return picked


def _search_query_from_extracted(extracted: dict) -> str:
    title = (extracted.get("title") or "").strip()
    desc = (extracted.get("description") or "").strip()
    text = f"{title} {desc[:320]}"
    picked = _tokenize_for_search(text, 10)
    if picked:
        return " ".join(picked)
    return title[:120].strip()


def _duplicate_search_query_variants(extracted: dict, user_latest_message: str = "") -> list[str]:
    """Multiple PMS generalSearch phrases—API match quality varies by query length."""
    title = (extracted.get("title") or "").strip()
    variants: list[str] = []
    seen_q: set[str] = set()

    def _add(q: str) -> None:
        q = (q or "").strip()
        if len(q) < 1:
            return
        key = q.casefold()
        if key not in seen_q:
            seen_q.add(key)
            variants.append(q)

    _add(_search_query_from_extracted(extracted))

    title_tokens = _tokenize_for_search(title, 6)
    if title_tokens:
        _add(" ".join(title_tokens[:6]))
    short = _tokenize_for_search(title, 3)
    if short:
        _add(" ".join(short[:3]))

    tail = (user_latest_message or "").strip()
    if tail:
        tail = tail.split("\n")[-1].strip()[:240]
        raw_toks = _tokenize_for_search(tail, 6)
        if raw_toks:
            _add(" ".join(raw_toks[:6]))
        if len(raw_toks) >= 2:
            _add(" ".join(raw_toks[:2]))

    if title and not variants:
        _add(title[:120].strip())

    return variants


def _duplicate_search_range_pms(tz_name: str, days: int = 90) -> tuple[str, str]:
    try:
        zi = ZoneInfo(tz_name)
    except Exception:
        zi = ZoneInfo("UTC")
    local_end = datetime.now(zi)
    local_start = local_end - timedelta(days=days)
    start_dt = datetime.combine(local_start.date(), time.min, tzinfo=zi)
    end_dt = datetime.combine(local_end.date(), time(23, 59, 59), tzinfo=zi)
    start_utc = start_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.999Z")
    end_utc = end_dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.999Z")
    return start_utc, end_utc


# Cap merged candidates passed to the similarity LLM (PMS-only; session-agnostic).
DUPLICATE_CANDIDATE_LIMIT = 30


def _singleton_boards_with_cards(cards: list) -> list:
    if not cards:
        return []
    return [
        BoardColumn(
            id=0,
            title="Merged",
            taskBoardStatusName="DuplicateSearch",
            totalTask=len(cards),
            cards=cards,
        )
    ]


def _fetch_merged_duplicate_boards(
    token: str,
    timezone_name: str,
    query_variants: list[str],
    start_date: str | None,
    end_date: str | None,
) -> list:
    """
    Run generalSearch for each query variant; merge unique TaskCards by taskId (order preserved).
    """
    merged_cards: list = []
    seen_ids: set[int] = set()
    for q in query_variants:
        try:
            boards = pms_client.get_tasks(
                token,
                timezone_name,
                start_date=start_date,
                end_date=end_date,
                general_search=q,
            )
        except Exception as ex:
            logger.warning(
                "PMS duplicate search get_tasks failed (query=%r start=%s end=%s): %s",
                (q or "")[:100],
                start_date,
                end_date,
                ex,
            )
            continue
        for col in boards:
            for card in col.cards or []:
                tid = card.taskId
                if tid not in seen_ids:
                    seen_ids.add(tid)
                    merged_cards.append(card)
    return _singleton_boards_with_cards(merged_cards)


def _flatten_candidate_cards(boards: list, limit: int = DUPLICATE_CANDIDATE_LIMIT) -> list[dict]:
    out: list[dict] = []
    for col in boards:
        for card in col.cards or []:
            out.append(
                {
                    "task_id": card.taskId,
                    "title": (card.title or "").strip(),
                    "description": ((card.description or "").strip())[:400],
                    "currentTaskBoardId": card.currentTaskBoardId,
                }
            )
            if len(out) >= limit:
                return out
    return out


def _find_card_by_task_id(boards: list, task_id: int):
    for col in boards:
        for card in col.cards or []:
            if card.taskId == task_id:
                return card
    return None


def _parse_similarity_output(raw: str) -> dict:
    try:
        data = json.loads((raw or "").strip())
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    return {"same_issue": False, "task_id": None, "confidence": "low"}


def _similarity_decision(
    llm: ChatOpenAI,
    draft_text: str,
    extracted: dict,
    candidates: list[dict],
) -> dict:
    if not candidates:
        return {"same_issue": False, "task_id": None}
    payload_items = []
    for c in candidates:
        bid = c.get("currentTaskBoardId")
        payload_items.append({
            "taskId": c["task_id"],
            "title": c.get("title") or "",
            "descriptionSnippet": (c.get("description") or "")[:280],
            "workflowStageHint": _workflow_status_phrase(int(bid) if bid is not None else 2011),
        })
    prompt = TASK_SIMILARITY_PROMPT.format(
        candidates_json=json.dumps(payload_items, indent=2),
        proposed_title=(extracted.get("title") or "").strip(),
        proposed_description_excerpt=((extracted.get("description") or "").strip())[:400],
        draft_text=draft_text.strip(),
    )
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        return _parse_similarity_output(resp.content)
    except Exception:
        return {"same_issue": False, "task_id": None}


def _reply_for_existing_task(
    llm: ChatOpenAI,
    draft_text: str,
    card,
) -> str:
    task_json = json.dumps(
        {
            "taskId": card.taskId,
            "title": card.title,
            "description": (card.description or "")[:800],
            "assignee": card.assignee,
            "dueDate": card.dueDate,
            "workflowStatus": _workflow_status_phrase(card.currentTaskBoardId),
        },
        indent=2,
    )
    prompt = EXISTING_TASK_REPLY_PROMPT.format(task_json=task_json, draft_text=draft_text.strip())
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        msg = (resp.content or "").strip()
        if msg:
            return msg
    except Exception:
        pass
    return (
        f"We already have this one tracked: \"{card.title}\" (task {card.taskId}). "
        f"It’s {_workflow_status_phrase(card.currentTaskBoardId)} right now."
    )


def _unrelated_candidates_prefix(candidates: list[dict]) -> str:
    titles = [(c.get("title") or "").strip() for c in candidates if (c.get("title") or "").strip()]
    if not titles:
        return ""
    shown = titles[:2]
    quoted = ", ".join(f'"{t}"' for t in shown)
    return (
        f"There’s already something we’re tracking that might overlap ({quoted}). "
        "If what you’re seeing is different, say the word and we’ll still log a new item."
    )


def _resolve_duplicate_flow(
    llm: ChatOpenAI,
    triage_state: dict,
    incident: dict,
    extracted: dict,
    draft_text: str,
    timezone_name: str,
    user_latest_message: str = "",
) -> tuple[str | None, str | None, str | None]:
    """
    Returns (early_reply_if_existing_match, prefix_when_unrelated_candidates, token_or_none).
    All matching uses PMS ``generalSearch`` only (works across devices/sessions).
    """
    variants = _duplicate_search_query_variants(extracted, user_latest_message)
    if not variants:
        return None, None, None

    try:
        token = pms_client.login()
    except Exception as ex:
        logger.warning("PMS login failed for duplicate search: %s", ex)
        return None, None, None

    boards_for_lookup: list = []
    for days in (90, 365):
        start_d, end_d = _duplicate_search_range_pms(timezone_name, days)
        boards_for_lookup = _fetch_merged_duplicate_boards(
            token, timezone_name, variants, start_d, end_d
        )
        if boards_for_lookup and boards_for_lookup[0].cards:
            break

    if not boards_for_lookup or not boards_for_lookup[0].cards:
        boards_for_lookup = _fetch_merged_duplicate_boards(
            token, timezone_name, variants, None, None
        )

    if not boards_for_lookup or not boards_for_lookup[0].cards:
        return None, None, None

    candidates = _flatten_candidate_cards(boards_for_lookup)
    if not candidates:
        return None, None, None

    sim = _similarity_decision(llm, draft_text, extracted, candidates)
    valid_ids = {c["task_id"] for c in candidates}
    raw_id = sim.get("task_id")
    try:
        tid = int(raw_id) if raw_id is not None else None
    except (TypeError, ValueError):
        tid = None

    if sim.get("same_issue") and tid is not None and tid in valid_ids:
        card = _find_card_by_task_id(boards_for_lookup, tid)
        if card is not None:
            msg = _reply_for_existing_task(llm, draft_text, card)
            update_active_incident(
                triage_state,
                {
                    "linked_task_id": tid,
                    "title_draft": (card.title or "").strip(),
                    "status": "parked",
                },
            )
            return msg, None, token

    prefix = _unrelated_candidates_prefix(candidates)
    return None, (prefix or None), None


def _base_state(state: AgentState) -> dict:
    return {
        k: v
        for k, v in dict(state).items()
        if k not in {"pending_task_payload", "triage_state"}
    }


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _format_confirmation_request(payload: TaskPayload) -> str:
    tt = TASK_TYPE_LABELS.get(payload.taskTypeId, str(payload.taskTypeId)).lower()
    return (
        f"I've got this down as a {tt}: \"{payload.title}\". "
        "Want me to log it?"
    )


def _build_payload_from_extracted(extracted: dict) -> TaskPayload:
    title = (extracted.get("title") or "").strip()
    description = (extracted.get("description") or "").strip()
    if not title:
        title = "Task requires clarification"
    if not description:
        description = "Please review the user-reported item and add detailed implementation notes."

    board_id = int(extracted.get("currentTaskBoardId") or settings.PMS_DEFAULT_BOARD_ID)

    return TaskPayload(
        taskId=0,
        title=title,
        description=description,
        dueDate=extracted.get("dueDate") or date.today().isoformat(),
        severityId=int(extracted.get("severityId") or settings.PMS_DEFAULT_SEVERITY_ID),
        taskTypeId=int(extracted.get("taskTypeId") or settings.PMS_DEFAULT_TASK_TYPE_ID),
        projectId=settings.PMS_PROJECT_ID,
        currentMileStoneId=settings.PMS_MILESTONE_ID,
        currentTaskBoardId=board_id,
        currentTaskBoardTypeId=settings.PMS_DEFAULT_BOARD_TYPE_ID,
        currentReportedById=settings.PMS_USER_ID,
        currentAssigneeId=settings.PMS_USER_ID,
        currentEstimatedTime=0,
        taskDocuments=[],
        userId=settings.PMS_USER_ID,
    )


def _extract_fields(
    llm: ChatOpenAI,
    user_query: str,
    conversation_history: str,
) -> dict:
    prompt = CREATE_TASK_EXTRACT_PROMPT.format(
        today=date.today().isoformat(),
        conversation_history=conversation_history,
        user_query=user_query,
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        parsed = json.loads(response.content.strip())
        return parsed if isinstance(parsed, dict) else {}
    except (json.JSONDecodeError, AttributeError):
        return {}


def _classify_pending_followup(
    llm: ChatOpenAI,
    pending: dict,
    user_query: str,
    conversation_history: str,
) -> str:
    """
    Returns same_item | new_item | off_topic.
    On LLM/JSON failure, default same_item (merge) to avoid dropping a valid pending draft.
    """
    payload = pending.get("task_payload") or {}
    if not isinstance(payload, dict):
        return "same_item"
    title = (payload.get("title") or "").strip()
    desc = (payload.get("description") or "").strip()
    excerpt = desc[:400] + ("…" if len(desc) > 400 else "")
    try:
        tt_id = int(payload.get("taskTypeId") or 35)
    except (TypeError, ValueError):
        tt_id = 35
    task_type_label = TASK_TYPE_LABELS.get(tt_id, str(tt_id))
    draft_text = (pending.get("draft_text") or "").strip()
    prompt = PENDING_CONFIRMATION_FOLLOWUP_PROMPT.format(
        proposed_title=title or "(untitled)",
        task_type_label=task_type_label,
        description_excerpt=excerpt or "(none)",
        draft_text=draft_text or "(none)",
        user_query=(user_query or "").strip(),
        conversation_history=(conversation_history or "").strip() or "(none)",
    )
    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw = (response.content or "").strip()
        parsed = json.loads(raw)
        rel = parsed.get("relation") if isinstance(parsed, dict) else None
        if rel in _RELATION_VALUES:
            return str(rel)
    except (json.JSONDecodeError, AttributeError, TypeError) as ex:
        logger.warning("pending followup classifier failed: %s", ex)
    return "same_item"


def _complete_from_pending(
    state: AgentState,
    triage_state: dict,
    pending: dict,
    llm: ChatOpenAI,
) -> AgentState:
    try:
        payload = TaskPayload.model_validate(pending.get("task_payload", {}))
    except Exception:
        return {
            **_base_state(state),
            "triage_state": {**triage_state, "pending_confirmation": None},
            "final_response": (
                "That draft task didn’t line up anymore — send the details again and we’ll set it up fresh."
            ),
        }

    try:
        token = pms_client.login()
        task = pms_client.create_task(token, payload)
    except Exception as e:
        return {**state, "final_response": f"Failed to create task: {str(e)}"}

    severity_label = SEVERITY_LABELS.get(payload.severityId, str(payload.severityId))
    task_type_label = TASK_TYPE_LABELS.get(payload.taskTypeId, str(payload.taskTypeId))
    workflow_status = _workflow_status_phrase(payload.currentTaskBoardId)
    assignee = task.get("assignee", "N/A")
    due_date = (task.get("dueDate") or "")[:10] or payload.dueDate or "N/A"
    confirmation_prompt = CREATE_TASK_CONFIRMATION_PROMPT.format(
        user_query=state.get("user_query", ""),
        task_id=task.get("taskId"),
        title=task.get("title"),
        task_type=f"{task_type_label} ({payload.taskTypeId})",
        workflow_status=workflow_status,
        severity=severity_label,
        assignee=assignee,
        due_date=due_date,
    )
    confirmation_response = llm.invoke([HumanMessage(content=confirmation_prompt)])
    message = (confirmation_response.content or "").strip()
    if not message:
        message = (
            f"Done — logged \"{task.get('title')}\" as a {task_type_label.lower()}. "
            f"It’s {workflow_status} for now. ID {task.get('taskId')}, with {assignee}, due {due_date}."
        )

    incident_id = pending.get("incident_id")
    if incident_id:
        for incident in triage_state.get("incidents", []):
            if incident.get("incident_id") == incident_id:
                incident["status"] = "created"
                incident["linked_task_id"] = task.get("taskId")
                break
    triage_state["pending_confirmation"] = None
    triage_state["active_incident_id"] = None
    tid = task.get("taskId")
    if tid is not None:
        triage_state["last_logged_task_id"] = tid
    triage_state["last_logged_title"] = (task.get("title") or "").strip()

    return {
        **_base_state(state),
        "pms_token": token,
        "pms_response": task,
        "triage_state": triage_state,
        # Clear graph-level stale pending_task_payload from the invoke input after create.
        "pending_task_payload": None,
        "final_response": message,
        "response_kind": "task_created",
        "response_actions": post_create_actions(),
    }


def _run_collecting_step(
    state: AgentState,
    triage_state: dict,
    incident: dict,
    llm: ChatOpenAI,
    draft_text: str,
) -> AgentState:
    extracted = _extract_fields(llm, draft_text, state.get("conversation_history", ""))
    requires_clarification = _to_bool(extracted.get("requiresClarification"))
    clarification_question = (extracted.get("clarificationQuestion") or "").strip()

    update_active_incident(
        triage_state,
        {
            "draft_text": draft_text,
            "title_draft": (extracted.get("title") or "").strip(),
            "status": "collecting",
        },
    )

    if requires_clarification:
        if not clarification_question:
            clarification_question = "Got it. What exactly is going wrong?"
        triage_state["pending_confirmation"] = None
        return {
            **_base_state(state),
            "triage_state": triage_state,
            "pending_task_payload": {},
            "final_response": clarification_question,
        }

    payload = _build_payload_from_extracted(extracted)
    tz_name = state.get("timezone") or "UTC"
    early, unrelated_prefix, dup_token = _resolve_duplicate_flow(
        llm,
        triage_state,
        incident,
        extracted,
        draft_text,
        tz_name,
        state.get("user_query") or "",
    )
    if early:
        out = {
            **_base_state(state),
            "triage_state": triage_state,
            "pending_task_payload": {},
            "final_response": early,
        }
        if dup_token:
            out["pms_token"] = dup_token
        return out

    pending_confirmation = {
        "incident_id": incident.get("incident_id"),
        "task_payload": payload.model_dump(mode="json"),
        "draft_text": draft_text,
        "asked_once": False,
    }
    triage_state["pending_confirmation"] = pending_confirmation
    update_active_incident(
        triage_state,
        {
            "status": "ready_to_confirm",
            "title_draft": payload.title,
        },
    )
    confirm_msg = _format_confirmation_request(payload)
    if unrelated_prefix:
        confirm_msg = f"{unrelated_prefix}\n\n{confirm_msg}"
    return {
        **_base_state(state),
        "triage_state": triage_state,
        "pending_task_payload": pending_confirmation,
        "final_response": confirm_msg,
        "response_kind": "pending_confirmation",
        "response_actions": confirmation_actions(),
    }


def _handle_pending_branch(
    state: AgentState,
    triage_state: dict,
    pending: dict,
    llm: ChatOpenAI,
) -> AgentState:
    draft_text = (pending.get("draft_text") or "").strip() or state.get("user_query", "")
    incident = get_active_incident(triage_state) or create_incident(triage_state, draft_text)

    q = (state.get("user_query") or "").strip()

    if pending.get("editing") and q:
        triage_state["pending_confirmation"] = None
        updated_draft = f"{draft_text}\n{q}".strip()
        return _run_collecting_step(state, triage_state, incident, llm, updated_draft)

    if is_affirmative(q):
        return _complete_from_pending(state, triage_state, pending, llm)

    if is_negative(q):
        triage_state["pending_confirmation"] = None
        if incident:
            incident["status"] = "parked"
        return {
            **_base_state(state),
            "triage_state": triage_state,
            "final_response": (
                "No problem — I didn't log anything. "
                "If you want to capture it differently later, just send the details."
            ),
        }

    if _looks_like_idle_chat_while_pending(q):
        return {
            **_base_state(state),
            "triage_state": triage_state,
            "pending_task_payload": pending,
            "final_response": _idle_chat_reply_while_pending(),
            "response_kind": "pending_confirmation",
            "response_actions": confirmation_actions(),
        }

    if is_single_token_affirmative(q):
        return _complete_from_pending(state, triage_state, pending, llm)

    if is_edit_request(q):
        pending = {**pending, "editing": True}
        triage_state["pending_confirmation"] = pending
        return {
            **_base_state(state),
            "triage_state": triage_state,
            "pending_task_payload": pending,
            "final_response": (
                "Sure — tell me what you'd like to change "
                "(title, description, priority, or anything else)."
            ),
            "response_kind": "clarify",
            "response_actions": clarify_actions(),
        }

    relation = _classify_pending_followup(
        llm,
        pending,
        q,
        state.get("conversation_history", "") or "",
    )

    if relation == "new_item":
        triage_state["pending_confirmation"] = None
        if incident:
            incident["status"] = "parked"
        new_incident = create_incident(triage_state, q)
        return _run_collecting_step(state, triage_state, new_incident, llm, q)

    if relation == "off_topic":
        return {
            **_base_state(state),
            "triage_state": triage_state,
            "pending_task_payload": pending,
            "final_response": (
                "Got it. Pick an option below when you're ready, or keep chatting — no pressure."
            ),
            "response_kind": "pending_confirmation",
            "response_actions": confirmation_actions(),
        }

    updated_draft = f"{draft_text}\n{q}".strip()
    triage_state["pending_confirmation"] = None
    return _run_collecting_step(state, triage_state, incident, llm, updated_draft)


def create_task_node(state: AgentState) -> AgentState:
    triage_state = ensure_triage_state(state.get("triage_state"))
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )

    pending = triage_state.get("pending_confirmation")
    if isinstance(pending, dict) and pending.get("task_payload"):
        return _handle_pending_branch(state, triage_state, pending, llm)

    active_incident = get_active_incident(triage_state)
    if should_start_new_incident(state.get("user_query", ""), active_incident):
        active_incident = create_incident(triage_state, state.get("user_query", ""))
    else:
        merged = f"{active_incident.get('draft_text', '')}\n{state.get('user_query', '')}".strip()
        active_incident["draft_text"] = merged

    initial_draft = (active_incident.get("draft_text") or state.get("user_query", "")).strip()
    return _run_collecting_step(state, triage_state, active_incident, llm, initial_draft)
