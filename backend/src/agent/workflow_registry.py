from __future__ import annotations

from dataclasses import dataclass, field

from src.agent.task_labels import workflow_status_phrase
from src.pms_client.schemas import BoardColumn
from src.settings import settings

_INTEGRATION_KEYWORDS = frozenset(
    {"integrate", "integration", "rti", "ready to integrate", "ready for integration"}
)
_TESTING_KEYWORDS = frozenset({"qa", "quality assurance", "testing", "test", "in test"})

_DEFAULT_DONE_KEYWORDS = ("done", "completed", "complete", "closed", "finished")
_DEFAULT_IN_PROGRESS_KEYWORDS = ("in progress", "in-progress", "inprogress")


def _parse_csv_keywords(raw: str, defaults: tuple[str, ...]) -> tuple[str, ...]:
    text = (raw or "").strip()
    if not text:
        return defaults
    return tuple(k.strip().lower() for k in text.split(",") if k.strip())


def _parse_csv_ids(raw: str) -> set[int]:
    out: set[int] = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


def _column_text(column: BoardColumn) -> str:
    parts = [(column.title or "").strip(), (column.taskBoardStatusName or "").strip()]
    return " ".join(p for p in parts if p).lower()


def _matches_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(k in text for k in keywords)


def _is_integration_column(text: str) -> bool:
    return _matches_any(text, tuple(_INTEGRATION_KEYWORDS))


def _is_testing_column(text: str) -> bool:
    return _matches_any(text, tuple(_TESTING_KEYWORDS))


def _is_done_column(text: str, done_keywords: tuple[str, ...]) -> bool:
    return _matches_any(text, done_keywords)


def _is_in_progress_column(text: str, in_progress_keywords: tuple[str, ...]) -> bool:
    if _is_integration_column(text) or _is_testing_column(text):
        return False
    return _matches_any(text, in_progress_keywords)


@dataclass
class WorkflowRegistry:
    board_labels: dict[int, str] = field(default_factory=dict)
    in_progress_board_ids: set[int] = field(default_factory=set)
    done_board_ids: set[int] = field(default_factory=set)
    sort_order: dict[int, int] = field(default_factory=dict)

    @classmethod
    def from_board_columns(cls, columns: list[BoardColumn]) -> WorkflowRegistry:
        done_keywords = _parse_csv_keywords(
            settings.PMS_DONE_BOARD_KEYWORDS, _DEFAULT_DONE_KEYWORDS
        )
        in_progress_keywords = _parse_csv_keywords(
            settings.PMS_IN_PROGRESS_BOARD_KEYWORDS, _DEFAULT_IN_PROGRESS_KEYWORDS
        )
        done_ids = _parse_csv_ids(settings.PMS_DONE_BOARD_IDS)
        in_progress_ids = _parse_csv_ids(settings.PMS_IN_PROGRESS_BOARD_IDS)

        board_labels: dict[int, str] = {}
        in_progress_board_ids: set[int] = set(in_progress_ids)
        done_board_ids: set[int] = set(done_ids)
        sort_order: dict[int, int] = {}

        for idx, column in enumerate(columns or []):
            if column.id is None or column.id <= 0:
                continue
            text = _column_text(column)
            label = (column.title or column.taskBoardStatusName or "").strip()
            if label:
                board_labels[column.id] = label
            sort_order[column.id] = idx

            if column.id in done_ids or _is_done_column(text, done_keywords):
                done_board_ids.add(column.id)
            if column.id in in_progress_ids or _is_in_progress_column(
                text, in_progress_keywords
            ):
                in_progress_board_ids.add(column.id)

        return cls(
            board_labels=board_labels,
            in_progress_board_ids=in_progress_board_ids,
            done_board_ids=done_board_ids,
            sort_order=sort_order,
        )

    def label_for(self, board_id: int) -> str:
        label = self.board_labels.get(board_id)
        if label:
            return label
        return workflow_status_phrase(board_id)

    def sort_key_for_card(self, board_id: int, due_date: str | None, task_id: int) -> tuple:
        stage = self.sort_order.get(board_id, 99)
        due = due_date or "9999-99-99"
        return (stage, due, task_id)
