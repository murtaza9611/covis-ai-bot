from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.qa.prompts import COVIS_QA_CTA_EVAL_RUBRIC, COVIS_QA_GRADER_PROMPT
from src.qa.schemas import QAChatAction, TurnClassification, TurnGrade
from src.qa.session_store import QASession
from src.settings import settings

WEIGHTS = {
    "relevance": 0.30,
    "accuracy": 0.30,
    "tone": 0.20,
    "completeness": 0.20,
}

WEIGHTS_WITH_CTA = {
    "relevance": 0.25,
    "accuracy": 0.25,
    "tone": 0.15,
    "completeness": 0.15,
    "cta": 0.20,
}


def compute_weighted_score(
    relevance: int,
    accuracy: int,
    tone: int,
    completeness: int,
    *,
    cta_relevance: int | None = None,
    cta_quality: int | None = None,
) -> float:
    if cta_relevance is not None and cta_quality is not None:
        cta_avg = (cta_relevance + cta_quality) / 2
        score = (
            relevance * WEIGHTS_WITH_CTA["relevance"]
            + accuracy * WEIGHTS_WITH_CTA["accuracy"]
            + tone * WEIGHTS_WITH_CTA["tone"]
            + completeness * WEIGHTS_WITH_CTA["completeness"]
            + cta_avg * WEIGHTS_WITH_CTA["cta"]
        )
    else:
        score = (
            relevance * WEIGHTS["relevance"]
            + accuracy * WEIGHTS["accuracy"]
            + tone * WEIGHTS["tone"]
            + completeness * WEIGHTS["completeness"]
        )
    return round(score, 1)


def classify_score(weighted_score: float) -> TurnClassification:
    return "issue" if weighted_score < 80 else "suggestion"


def _format_conversation(session: QASession, include_current: bool = False) -> str:
    lines: list[str] = []
    for turn in session.turns:
        source = ""
        if turn.client_message_source == "cta":
            label = turn.client_cta_label or "CTA"
            source = f" [via CTA: {label}]"
        lines.append(f"Client{source}: {turn.client_message}")
        lines.append(f"COVIS Assist: {turn.bot_reply}")
        if turn.bot_actions:
            chips = ", ".join(f'"{a.label}"' for a in turn.bot_actions)
            lines.append(f"  (CTAs offered: {chips})")
    return "\n".join(lines) if lines else "(First turn)"


def _infer_cta_moment(client_message: str, bot_reply: str, is_first_turn: bool) -> str:
    """Heuristic hint so the grader applies the right REPLY-FIRST rules."""
    client = client_message.strip().lower()
    reply = bot_reply.strip()
    lower = reply.lower()

    if any(
        marker in lower
        for marker in ("want me to log", "should i log", "ready to log", "log it?", "log this", "confirm")
    ):
        return "confirmation — chips should be yes/no/change-details only"

    if reply.rstrip().endswith("?"):
        return "assistant asked a question — chips must be direct ANSWERS, not topic pivots"

    if is_first_turn or client in {"hi", "hey", "hello", "yo", "morning", "hiya"}:
        return "greeting/new session — chips should be starter entry points aligned with the bot greeting"

    if any(
        phrase in lower
        for phrase in ("how can i help", "what can i help", "how's it going", "how are you")
    ):
        return "greeting/social — chips may be 0-2 soft project pivots or starter entry points"

    return "post-answer — chips must be logical NEXT steps, not repeats of the user's question"


def _format_actions(actions: list[QAChatAction]) -> str:
    if not actions:
        return "(No CTA chips offered on this reply)"
    lines: list[str] = []
    for action in actions:
        lines.append(
            f'- label="{action.label}" | payload="{action.payload}" | type={action.type}'
        )
    return "\n".join(lines)


_GENERIC_PIVOT_PHRASES = (
    "report a bug",
    "check project status",
    "request a feature",
    "what's due",
    "whats due",
    "list my",
    "show open",
)


def _is_social_greeting_question(bot_reply: str) -> bool:
    lower = bot_reply.lower()
    return any(
        phrase in lower
        for phrase in (
            "how's it going",
            "how are you",
            "how can i help",
            "what can i help",
            "what can you help",
        )
    )


def _apply_cta_heuristics(
    client_message: str,
    bot_reply: str,
    actions: list[QAChatAction],
    cta_relevance: int,
    cta_quality: int,
    cta_feedback: str | None,
) -> tuple[int, int, str | None]:
    """Cap inflated LLM CTA scores when obvious REPLY-FIRST violations are present."""
    feedback_parts: list[str] = []
    rel = cta_relevance
    qual = cta_quality
    client_norm = client_message.strip().lower()
    bot_asked = bot_reply.strip().endswith("?")
    clarification_question = bot_asked and not _is_social_greeting_question(bot_reply)

    for action in actions:
        payload = action.payload.strip()
        payload_norm = payload.lower()
        label_words = action.label.split()

        if payload_norm and payload_norm == client_norm:
            rel = min(rel, 35)
            feedback_parts.append(f'"{action.label}" repeats the client message.')

        if clarification_question and any(phrase in payload_norm for phrase in _GENERIC_PIVOT_PHRASES):
            rel = min(rel, 45)
            feedback_parts.append(
                f'"{action.label}" pivots to a new topic while the assistant asked a question.',
            )

        if payload and len(label_words) <= 3 and len(payload.split()) <= 4:
            qual = min(qual, 55)
            feedback_parts.append(
                f'"{action.label}" payload "{payload}" looks like a bare category label, not a natural sentence.',
            )

    if not feedback_parts:
        return rel, qual, cta_feedback

    heuristic_note = "Auto-check: " + " ".join(feedback_parts)
    if cta_feedback:
        return rel, qual, f"{heuristic_note} {cta_feedback}"
    return rel, qual, heuristic_note


async def grade_turn(
    session: QASession,
    client_message: str,
    bot_reply: str,
    bot_actions: list[QAChatAction] | None = None,
) -> TurnGrade:
    """Grade a single bot reply against the PMS snapshot."""
    snapshot_json = json.dumps(session.pms_snapshot[:80], indent=2)
    if len(session.pms_snapshot) > 80:
        snapshot_json += f"\n... and {len(session.pms_snapshot) - 80} more tasks"

    actions = bot_actions or []
    has_ctas = len(actions) > 0
    is_first_turn = len(session.turns) == 0
    cta_moment = _infer_cta_moment(client_message, bot_reply, is_first_turn)

    cta_section = (
        COVIS_QA_CTA_EVAL_RUBRIC.format(cta_moment=cta_moment)
        if has_ctas
        else "No CTA chips were offered on this reply. Set cta_relevance, cta_quality, and cta_feedback to null."
    )

    prompt = COVIS_QA_GRADER_PROMPT.format(
        pms_snapshot_json=snapshot_json,
        conversation_so_far=_format_conversation(session),
        client_message=client_message,
        bot_reply=bot_reply,
        bot_actions=_format_actions(actions),
        mode=session.mode,
        cta_instructions=cta_section,
    )

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
        model_kwargs={"response_format": {"type": "json_object"}},
    )

    response = await llm.ainvoke([
        SystemMessage(
            content=(
                "You evaluate COVIS Assist chatbot replies and CTA quick-reply chips. "
                "Grade bot reply and CTA chips independently. "
                "Apply REPLY-FIRST CTA rules strictly — do not inflate cta_relevance for "
                "generic project chips when the moment requires answers or next steps. "
                "Return JSON only."
            ),
        ),
        HumanMessage(content=prompt),
    ])

    raw = (response.content or "").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {
            "relevance": 50,
            "accuracy": 50,
            "tone": 50,
            "completeness": 50,
            "what_went_wrong": "Grader failed to parse response.",
            "expected_reply": None,
            "prompt_fix": "Ensure grader returns valid JSON.",
            "what_could_be_better": None,
            "prompt_enhancement": None,
            "capability_tag": None,
            "adversarial_tag": None,
        }

    relevance = max(0, min(100, int(data.get("relevance", 50))))
    accuracy = max(0, min(100, int(data.get("accuracy", 50))))
    tone = max(0, min(100, int(data.get("tone", 50))))
    completeness = max(0, min(100, int(data.get("completeness", 50))))

    cta_relevance: int | None = None
    cta_quality: int | None = None
    if has_ctas:
        raw_cta_rel = data.get("cta_relevance")
        raw_cta_qual = data.get("cta_quality")
        if raw_cta_rel is not None:
            cta_relevance = max(0, min(100, int(raw_cta_rel)))
        if raw_cta_qual is not None:
            cta_quality = max(0, min(100, int(raw_cta_qual)))
        if cta_relevance is None:
            cta_relevance = 50
        if cta_quality is None:
            cta_quality = 50

    cta_feedback = data.get("cta_feedback")
    if has_ctas and cta_relevance is not None and cta_quality is not None:
        cta_relevance, cta_quality, cta_feedback = _apply_cta_heuristics(
            client_message,
            bot_reply,
            actions,
            cta_relevance,
            cta_quality,
            cta_feedback,
        )

    weighted = compute_weighted_score(
        relevance,
        accuracy,
        tone,
        completeness,
        cta_relevance=cta_relevance,
        cta_quality=cta_quality,
    )
    classification = classify_score(weighted)

    return TurnGrade(
        relevance=relevance,
        accuracy=accuracy,
        tone=tone,
        completeness=completeness,
        cta_relevance=cta_relevance,
        cta_quality=cta_quality,
        weighted_score=weighted,
        classification=classification,
        what_went_wrong=data.get("what_went_wrong"),
        expected_reply=data.get("expected_reply"),
        prompt_fix=data.get("prompt_fix"),
        what_could_be_better=data.get("what_could_be_better"),
        prompt_enhancement=data.get("prompt_enhancement"),
        cta_feedback=cta_feedback,
        capability_tag=data.get("capability_tag"),
        adversarial_tag=data.get("adversarial_tag"),
    )
