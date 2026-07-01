from __future__ import annotations

import random
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.qa.prompts import (
    COVIS_QA_CLIENT_TURN_PROMPT,
    COVIS_QA_SYSTEM_PROMPT,
    NEGATIVE_ADVERSARIAL_EXAMPLES,
    NEGATIVE_ADVERSARIAL_TYPES,
    NEGATIVE_TURN_HINT,
    POSITIVE_CAPABILITIES,
    POSITIVE_CAPABILITY_EXAMPLES,
    POSITIVE_TURN_HINT,
)
from src.qa.schemas import QAChatAction
from src.qa.session_store import QASession
from src.settings import settings

MAX_MESSAGE_WORDS = 15
MAX_MESSAGE_CHARS = 120
CTA_PICK_PROBABILITY = 0.55


def _quick_reply_actions(actions: list[QAChatAction]) -> list[QAChatAction]:
    return [
        action
        for action in actions
        if action.type == "quick_reply" and action.payload.strip()
    ]


def _pick_cta_reply(session: QASession) -> tuple[str, str, str] | None:
    """Return (payload, source, label) when using a prior-turn CTA."""
    if not session.turns:
        return None
    last_turn = session.turns[-1]
    ctas = _quick_reply_actions(last_turn.bot_actions)
    if not ctas or random.random() > CTA_PICK_PROBABILITY:
        return None
    action = random.choice(ctas)
    return action.payload.strip(), "cta", action.label


async def resolve_client_message(session: QASession) -> tuple[str, str, str | None]:
    """Generate or pick the next client message (text or CTA tap)."""
    cta_pick = _pick_cta_reply(session)
    if cta_pick:
        payload, source, label = cta_pick
        return payload, source, label
    message = await generate_client_message(session)
    return message, "text", None


def _format_conversation(session: QASession) -> str:
    if not session.turns:
        return "(No messages yet — opening message.)"
    lines: list[str] = []
    for turn in session.turns:
        lines.append(f"Client: {turn.client_message}")
        lines.append(f"COVIS Assist: {turn.bot_reply}")
        if turn.bot_actions:
            chip_labels = ", ".join(a.label for a in turn.bot_actions[:4])
            lines.append(f"  CTAs offered: {chip_labels}")
    return "\n".join(lines) if lines else "(First turn)"


def _snapshot_summary(session: QASession, limit: int = 12) -> str:
    """Compact task list for context — avoids dumping full JSON into the prompt."""
    tasks = session.pms_snapshot[:limit]
    if not tasks:
        return "(No tasks in snapshot.)"
    lines = [
        f"- [{t.get('taskId')}] {t.get('title')} | {t.get('status')} | {t.get('assignee') or 'unassigned'}"
        for t in tasks
    ]
    extra = len(session.pms_snapshot) - limit
    if extra > 0:
        lines.append(f"... +{extra} more tasks")
    return "\n".join(lines)


def _sample_task_title(session: QASession) -> str:
    if not session.pms_snapshot:
        return "the dashboard task"
    task = random.choice(session.pms_snapshot)
    title = (task.get("title") or "that task").strip()
    # Keep task reference short in examples
    return title[:40] + ("..." if len(title) > 40 else "")


def _recent_adversarial_tags(session: QASession) -> list[str]:
    return [
        t.grade.adversarial_tag
        for t in session.turns[-3:]
        if t.grade.adversarial_tag
    ]


def _pick_adversarial_type(session: QASession) -> str:
    """Random adversarial type, avoiding 3 consecutive repeats."""
    recent = _recent_adversarial_tags(session)
    pool = list(NEGATIVE_ADVERSARIAL_TYPES)
    if len(recent) >= 2 and recent[-1] == recent[-2]:
        blocked = recent[-1]
        pool = [t for t in pool if t != blocked]
    return random.choice(pool or NEGATIVE_ADVERSARIAL_TYPES)


def _pick_positive_capability(session: QASession) -> str:
    covered = {
        t.grade.capability_tag
        for t in session.turns
        if t.grade.capability_tag
    }
    remaining = [c for c in POSITIVE_CAPABILITIES if c not in covered]
    pool = remaining if remaining else POSITIVE_CAPABILITIES
    return random.choice(pool)


def _example_for_capability(capability: str, session: QASession) -> str:
    examples = POSITIVE_CAPABILITY_EXAMPLES.get(capability, ["hey whats up"])
    raw = random.choice(examples)
    task = _sample_task_title(session)
    return raw.replace("{task}", task)


def _negative_mode_hint(session: QASession) -> tuple[str, str]:
    adv_type = _pick_adversarial_type(session)
    examples = NEGATIVE_ADVERSARIAL_EXAMPLES.get(adv_type, ["???"])
    sampled = random.sample(examples, k=min(3, len(examples)))
    hint = NEGATIVE_TURN_HINT.format(
        adversarial_type=adv_type,
        examples=" | ".join(f'"{e}"' for e in sampled),
        recent_adversarial=", ".join(_recent_adversarial_tags(session)) or "none",
    )
    directive = f"This turn's adversarial directive: {adv_type}"
    return directive, hint


def _positive_mode_hint(session: QASession) -> tuple[str, str]:
    capability = _pick_positive_capability(session)
    example = _example_for_capability(capability, session)
    hint = POSITIVE_TURN_HINT.format(capability=capability, example=example)
    directive = f"This turn's capability: {capability}"
    return directive, hint


def _enforce_short_message(text: str) -> str:
    """Trim overly long LLM output to WhatsApp-style length."""
    text = (text or "").strip()
    text = re.sub(r"\s+", " ", text)
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1].strip()

    words = text.split()
    if len(words) > MAX_MESSAGE_WORDS:
        text = " ".join(words[:MAX_MESSAGE_WORDS])

    if len(text) > MAX_MESSAGE_CHARS:
        text = text[:MAX_MESSAGE_CHARS].rsplit(" ", 1)[0] or text[:MAX_MESSAGE_CHARS]

    return text.strip()


def _fallback_message(session: QASession) -> str:
    if session.mode == "NEGATIVE":
        adv = _pick_adversarial_type(session)
        examples = NEGATIVE_ADVERSARIAL_EXAMPLES.get(adv, ["???"])
        return random.choice(examples)
    return random.choice(["hey", "any updates?", "quick q about the project"])


async def generate_client_message(session: QASession) -> str:
    """Generate the next simulated client message for the QA session."""
    current_turn = len(session.turns) + 1

    if session.mode == "NEGATIVE":
        turn_directive, mode_hint = _negative_mode_hint(session)
    else:
        turn_directive, mode_hint = _positive_mode_hint(session)

    system = COVIS_QA_SYSTEM_PROMPT.format(
        mode=session.mode,
        max_turns=session.max_turns,
        current_turn=current_turn,
    )

    human = COVIS_QA_CLIENT_TURN_PROMPT.format(
        mode=session.mode,
        current_turn=current_turn,
        max_turns=session.max_turns,
        turn_directive=turn_directive,
        conversation_so_far=_format_conversation(session),
        pms_snapshot_summary=_snapshot_summary(session),
        mode_specific_hint=mode_hint,
    )

    temperature = 1.0 if session.mode == "NEGATIVE" else 0.85

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )

    response = await llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=human),
    ])
    text = _enforce_short_message(response.content or "")
    return text or _fallback_message(session)
