import json
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.settings import settings

_AFFIRM_PAT = re.compile(
    r"^\s*("
    r"y|yes|yeah|yep|yup|sure|ok|okay|"
    r"go\b|go ahead|"
    r"do it|please|confirm|log it|create it|proceed|"
    r"sounds good|that works|"
    r"let'?s go|lets go"
    r")\b",
    re.IGNORECASE,
)
_NEGATIVE_PAT = re.compile(
    r"^\s*(n|no|nope|nah|cancel|skip|forget it|don\'t|dont|not now|leave it)\b",
    re.IGNORECASE,
)
_EDIT_REQUEST_PAT = re.compile(
    r"^\s*("
    r"i want to change the details|"
    r"i want to edit(\s+(the\s+)?details|\s+it|\s+this)?|"
    r"(please\s+)?(change|edit|update)(\s+(the|my))?\s+details"
    r")\.?\s*$",
    re.IGNORECASE,
)

_SINGLE_TOKEN_AFFIRMS = frozenset({
    "y",
    "yes",
    "yeah",
    "yep",
    "yup",
    "sure",
    "ok",
    "okay",
    "go",
})

_AFFIRM_LLM_PROMPT = """
The user was asked whether to log a draft task. Classify if they are confirming.

User message:
{text}

Return ONLY valid JSON: {{"is_confirm": true|false}}
"""


def is_affirmative(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(_AFFIRM_PAT.match(t))


def is_single_token_affirmative(text: str) -> bool:
    """Safety net: one-word confirmations before LLM follow-up classifier."""
    t = re.sub(r"[!.…!?]+$", "", (text or "").strip()).strip().lower()
    if not t or " " in t:
        return False
    return t in _SINGLE_TOKEN_AFFIRMS or is_affirmative(t)


def llm_is_affirmative(text: str, llm: ChatOpenAI | None = None) -> bool:
    """LLM fallback when regex does not match multi-word confirmations."""
    t = (text or "").strip()
    if not t or is_affirmative(t):
        return is_affirmative(t)
    if is_negative(t):
        return False
    if len(t) > 120:
        return False
    model = llm or ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
    )
    try:
        response = model.invoke([
            SystemMessage(content="Return only valid JSON."),
            HumanMessage(content=_AFFIRM_LLM_PROMPT.format(text=t)),
        ])
        parsed = json.loads((response.content or "").strip())
        if isinstance(parsed, dict):
            return bool(parsed.get("is_confirm"))
    except (json.JSONDecodeError, AttributeError, TypeError):
        pass
    return False


def is_negative(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    return bool(_NEGATIVE_PAT.match(t))


def is_edit_request(text: str) -> bool:
    """Meta edit intent (CTA or short phrase), not substantive field corrections."""
    t = (text or "").strip()
    if not t:
        return False
    return bool(_EDIT_REQUEST_PAT.match(t))


def looks_like_board_query(text: str) -> bool:
    t = (text or "").lower()
    return any(
        w in t
        for w in (
            "board",
            "task",
            "qa",
            "todo",
            "status",
            "progress",
            "today",
            "yesterday",
            "due",
            "assignee",
            "sprint",
            "milestone",
            "how many",
            "what's on",
            "whats on",
        )
    )
