"""Generate contextual CTAs from assistant reply and agent state."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agent.cta_context import build_cta_context, filter_irrelevant_actions
from src.agent.cta_policy import CtaPolicy, resolve_policy
from src.agent.cta_templates import template_confirmation, template_for_scenario
from src.agent.cta_validation import ensure_unique_action_id, validate_actions
from src.agent.prompts import CTA_SUGGEST_PROMPT
from src.settings import settings

_SCENARIO_PROMPT_HINTS: dict[str, str] = {
    "new_session": "Suggest starter chips aligned with the greeting: Report a bug, Check project status, Request a feature, What's due this week?",
    "out_of_scope": "Re-offer entry points: Report a bug, Check project status, Request a feature.",
    "post_create_bug": "Track this bug, Report another issue, See all open bugs.",
    "post_create_feature": "Check request status, See all pending features.",
    "duplicate_detected": "View existing task, Log as separate issue.",
    "broad_status": "What's due this week?, Show open bugs, Who's working on what?",
    "specific_task": "Who's assigned to this?, When is it due?, Mark as urgent.",
    "assignee_answered": "See their other tasks, Check task status, Report an issue with this task. NEVER Who's working on this?",
    "due_date_answered": "What else is due soon?, Check task status. NEVER repeat due-date question.",
    "time_snapshot": "Show this week's progress, See completed tasks.",
    "returning_social": "0-2 soft pivots only if greeting mentions project help.",
    "general_chat": "0-2 gentle pivots max, or return empty.",
}


def _tail_history(conversation_history: str, max_turns: int = 4) -> str:
    lines = [ln.strip() for ln in (conversation_history or "").splitlines() if ln.strip()]
    if not lines:
        return "(none)"
    return "\n".join(lines[-max_turns * 2 :])


def _format_structured_tasks(tasks: list[dict[str, Any]]) -> str:
    if not tasks:
        return "(none)"
    parts: list[str] = []
    for item in tasks[:8]:
        title = item.get("title") or "Untitled"
        status = item.get("status") or ""
        due = item.get("dueDate") or ""
        tid = item.get("taskId") or ""
        parts.append(f"- #{tid} {title} | {status} | due {due}")
    return "\n".join(parts)


def _format_allowed_areas(areas: tuple[str, ...]) -> str:
    if not areas:
        return "(none — do not invent module or screen names)"
    return "\n".join(f"- {area}" for area in areas)


def _reply_text(state: dict[str, Any]) -> str:
    return (state.get("final_response") or "").strip()


def _conversation_phase(policy: CtaPolicy, state: dict[str, Any]) -> str:
    if policy.sub_stage == "collecting":
        return "collecting"
    if not (state.get("conversation_history") or "").strip():
        return "new"
    return "mid"


def _llm_generate_actions(
    state: dict[str, Any],
    policy: CtaPolicy,
    ctx: Any,
    max_actions: int,
    min_actions: int,
) -> list[dict[str, str]] | None:
    triage = state.get("triage_state") or {}
    last_task = triage.get("last_task_query") if isinstance(triage, dict) else None
    if not isinstance(last_task, dict):
        last_task = {}

    structured = state.get("structured_tasks") or []
    if not isinstance(structured, list):
        structured = []

    scenario_hint = _SCENARIO_PROMPT_HINTS.get(policy.scenario, "")

    prompt = CTA_SUGGEST_PROMPT.format(
        intent=state.get("intent") or "",
        response_kind=state.get("response_kind") or "text",
        cta_type=policy.cta_type,
        cta_scenario=policy.scenario,
        sub_stage=policy.sub_stage,
        scenario_hint=scenario_hint or "(follow cta_type rules)",
        workflow_stage=ctx.workflow_stage,
        conversation_phase=_conversation_phase(policy, state),
        clarification_target=ctx.clarification_target,
        assistant_question=ctx.assistant_question or _reply_text(state),
        incident_draft=ctx.incident_draft or "(none)",
        allowed_areas=_format_allowed_areas(ctx.allowed_areas),
        answered_topics=", ".join(sorted(ctx.answered_topics)) or "(none)",
        suppress_pivots="yes" if policy.suppress_pivots else "no",
        max_actions=max_actions,
        min_actions=min_actions,
        user_query=state.get("user_query") or "",
        resolved_query=state.get("resolved_query") or state.get("user_query") or "",
        final_response=_reply_text(state),
        structured_tasks=_format_structured_tasks(structured),
        last_task_query=json.dumps(last_task, default=str) if last_task else "(none)",
        conversation_history=_tail_history(state.get("conversation_history") or ""),
    )

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    try:
        response = llm.invoke([
            SystemMessage(content="Return only valid JSON."),
            HumanMessage(content=prompt),
        ])
        raw = (response.content or "").strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return None
        actions = parsed.get("actions")
        if not isinstance(actions, list):
            return None
        validated = validate_actions(
            actions,
            max_actions=max_actions,
            quick_reply_only=True,
        )
        return validated or None
    except (json.JSONDecodeError, AttributeError, TypeError):
        return None


def _finalize_actions(
    actions: list[dict[str, str]],
    state: dict[str, Any],
    ctx: Any,
    policy: CtaPolicy,
) -> list[dict[str, str]]:
    filtered = filter_irrelevant_actions(actions, state, ctx)
    validated = validate_actions(
        filtered,
        max_actions=policy.max_actions,
        quick_reply_only=True,
    )
    return [a for a in validated if a.get("type") == "quick_reply"]


def generate_response_actions(state: dict[str, Any]) -> list[dict[str, str]]:
    """Build validated CTAs for the latest assistant message."""
    if not _reply_text(state):
        return []

    ctx = build_cta_context(state)
    policy = resolve_policy(state, ctx)

    if policy.cta_type == "confirmation":
        return template_confirmation()

    fallback = template_for_scenario(policy.scenario, state, ctx, policy.max_actions)

    if not policy.use_llm:
        return fallback

    if policy.min_actions == 0 and policy.cta_type == "soft_pivot":
        llm_actions = _llm_generate_actions(
            state, policy, ctx, policy.max_actions, policy.min_actions,
        )
        if not llm_actions:
            return fallback[:policy.max_actions] if fallback else []
        finalized = _finalize_actions(llm_actions, state, ctx, policy)
        return finalized if finalized else (fallback[:policy.max_actions] if fallback else [])

    llm_actions = _llm_generate_actions(
        state, policy, ctx, policy.max_actions, policy.min_actions,
    )

    llm_only_types = {"answer", "next_step"}
    if policy.cta_type in llm_only_types or not policy.merge_templates:
        source = llm_actions if llm_actions else fallback
        finalized = _finalize_actions(source, state, ctx, policy)
        return finalized if finalized else fallback

    if llm_actions:
        seen_keys: set[str] = set()
        seen_ids: set[str] = set()
        merged: list[dict[str, str]] = []
        for action in llm_actions:
            key = f"{action['type']}:{(action.get('payload') or action['label']).lower()}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            merged.append({
                **action,
                "id": ensure_unique_action_id(str(action.get("id") or ""), seen_ids),
            })
            if len(merged) >= policy.max_actions:
                break
        result = merged
    else:
        result = fallback

    finalized = _finalize_actions(result, state, ctx, policy)
    return finalized if finalized else fallback
