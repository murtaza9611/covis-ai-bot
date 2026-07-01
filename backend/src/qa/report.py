from __future__ import annotations

from src.qa.prompts import NEGATIVE_ADVERSARIAL_TYPES, POSITIVE_CAPABILITIES
from src.qa.schemas import QATurnRecord
from src.qa.session_store import QASession


def _issue_block(turn: QATurnRecord) -> list[str]:
    g = turn.grade
    lines = [
        "  ┌─ ISSUE FOUND",
        f"  │  What went wrong  : {g.what_went_wrong or 'Reply did not meet quality threshold.'}",
        f'  │  Expected reply   : "{g.expected_reply or "N/A"}"',
        f"  │  Prompt fix       : {g.prompt_fix or 'Review GET_TASK_ANSWER_PROMPT and COVIS_WHATSAPP_PERSONA.'}",
        "  └─",
    ]
    return lines


def _suggestion_block(turn: QATurnRecord) -> list[str]:
    g = turn.grade
    lines = [
        "  ┌─ SUGGESTION",
        f"  │  What could be better : {g.what_could_be_better or 'Minor polish possible.'}",
        f"  │  Prompt enhancement   : {g.prompt_enhancement or 'No change required.'}",
        "  └─",
    ]
    return lines


def _capability_coverage(session: QASession) -> list[str]:
    covered = {
        t.grade.capability_tag
        for t in session.turns
        if t.grade.capability_tag
    }
    lines: list[str] = []
    for cap in POSITIVE_CAPABILITIES:
        if cap in covered:
            lines.append(f"✅ {cap}")
        else:
            lines.append(f"❌ {cap}  ← not triggered or failed")
    return lines


def _adversarial_coverage(session: QASession) -> list[str]:
    tested: dict[str, list[float]] = {}
    for turn in session.turns:
        tag = turn.grade.adversarial_tag
        if tag:
            tested.setdefault(tag, []).append(turn.grade.weighted_score)

    lines: list[str] = []
    for adv in NEGATIVE_ADVERSARIAL_TYPES:
        if adv in tested:
            avg = sum(tested[adv]) / len(tested[adv])
            handled = "bot handled" if avg >= 80 else "bot struggled"
            lines.append(f"✅ {adv} tested — {handled}")
        else:
            lines.append(f"❌ {adv} — not tested")
    return lines


def _top_issues(session: QASession) -> list[str]:
    issues = [
        (turn.turn_number, turn.grade.weighted_score, turn.grade)
        for turn in session.turns
        if turn.grade.classification == "issue"
    ]
    issues.sort(key=lambda x: x[1])

    lines: list[str] = []
    for idx, (turn_num, score, grade) in enumerate(issues[:10], start=1):
        desc = grade.what_went_wrong or "Quality threshold not met"
        fix = grade.prompt_fix or "Review relevant prompt section."
        lines.append(f"{idx}. [Turn {turn_num}] Score: {score:.0f} — {desc}")
        lines.append(f"   Fix: {fix}")
        lines.append("")
    if not lines:
        lines.append("No critical issues (all turns scored ≥80).")
    return lines


def _recommended_patches(session: QASession) -> list[str]:
    seen: set[str] = set()
    patches: list[str] = []
    issues = sorted(
        [t for t in session.turns if t.grade.classification == "issue"],
        key=lambda t: t.grade.weighted_score,
    )
    for turn in issues:
        fix = (turn.grade.prompt_fix or "").strip()
        if fix and fix not in seen:
            seen.add(fix)
            patches.append(f"{len(patches) + 1}. {fix}")
    if not patches:
        enhancements = [
            (t.grade.prompt_enhancement or "").strip()
            for t in session.turns
            if t.grade.prompt_enhancement
        ]
        for enh in enhancements[:5]:
            if enh and enh not in seen:
                seen.add(enh)
                patches.append(f"{len(patches) + 1}. {enh}")
    if not patches:
        patches.append("1. No prompt patches required — session passed all turns.")
    return patches


def build_report(session: QASession) -> str:
    """Build the structured ASCII QA session report."""
    turns_completed = len(session.turns)
    scores = [t.grade.weighted_score for t in session.turns]
    overall = round(sum(scores) / len(scores), 1) if scores else 0.0
    passed = sum(1 for s in scores if s >= 80)
    failed = sum(1 for s in scores if s < 80)

    lines: list[str] = [
        "╔══════════════════════════════════════════╗",
        "║         COVIS QA SESSION REPORT          ║",
        "╚══════════════════════════════════════════╝",
        "",
        f"Mode: {session.mode}",
        f"Drive: {session.drive_mode}",
        f"Turns Completed: {turns_completed} / {session.max_turns} (configured)",
        f"Overall Session Score: {overall}/100",
        f"Passed Turns (≥80): {passed}  |  Failed Turns (<80): {failed}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "TURN-BY-TURN BREAKDOWN",
        "",
    ]

    for turn in session.turns:
        lines.append(f"Turn {turn.turn_number}")
        source_note = ""
        if turn.client_message_source == "cta":
            label = turn.client_cta_label or "CTA"
            source_note = f" (via CTA: {label})"
        lines.append(f'  Client Message : "{turn.client_message}"{source_note}')
        lines.append(f'  Bot Reply      : "{turn.bot_reply}"')
        if turn.bot_actions:
            chips = ", ".join(f'"{a.label}"' for a in turn.bot_actions)
            lines.append(f"  CTAs Offered   : {chips}")
        lines.append(f"  Score          : {turn.grade.weighted_score:.0f}/100")
        if turn.grade.cta_relevance is not None and turn.grade.cta_quality is not None:
            lines.append(
                f"  CTA Score      : relevance {turn.grade.cta_relevance}/100, "
                f"quality {turn.grade.cta_quality}/100"
            )
            if turn.grade.cta_feedback:
                lines.append(f"  CTA Feedback   : {turn.grade.cta_feedback}")
        if turn.grade.classification == "issue":
            lines.extend(_issue_block(turn))
        else:
            lines.extend(_suggestion_block(turn))
        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "TOP ISSUES SUMMARY (scores < 80, sorted by severity)",
        "",
    ])
    lines.extend(_top_issues(session))

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ])

    if session.mode == "POSITIVE":
        lines.append("CAPABILITY COVERAGE (Positive Mode only)")
        lines.append("")
        lines.extend(_capability_coverage(session))
        lines.append("")
    else:
        lines.append("ADVERSARIAL COVERAGE (Negative Mode only)")
        lines.append("")
        lines.extend(_adversarial_coverage(session))
        lines.append("")

    lines.extend([
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        "RECOMMENDED PROMPT PATCHES",
        "",
    ])
    lines.extend(_recommended_patches(session))

    return "\n".join(lines)
