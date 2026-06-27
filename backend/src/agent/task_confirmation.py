import re

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
