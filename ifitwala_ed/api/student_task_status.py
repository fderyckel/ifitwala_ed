from __future__ import annotations

from datetime import date, datetime
from typing import Any

from frappe.utils import get_datetime

DONE_SUBMISSION_STATUSES = {"Submitted", "Late", "Resubmitted"}
DONE_GRADING_STATUSES = {"Finalized", "Released"}


def coerce_bool_flag(value: Any) -> bool:
    try:
        return int(value or 0) == 1
    except Exception:
        return str(value or "").strip().lower() in {"true", "yes"}


def _has_explicit_flag(row: dict[str, Any], fieldname: str) -> bool:
    return fieldname in row and row.get(fieldname) not in (None, "")


def is_student_work_done(row: dict[str, Any]) -> bool:
    if _has_explicit_flag(row, "is_done"):
        return coerce_bool_flag(row.get("is_done"))
    if coerce_bool_flag(row.get("is_complete")) or coerce_bool_flag(row.get("complete")):
        return True
    if coerce_bool_flag(row.get("has_submission")):
        return True

    submission_status = str(row.get("submission_status") or "").strip()
    if submission_status in DONE_SUBMISSION_STATUSES:
        return True

    grading_status = str(row.get("grading_status") or "").strip()
    if grading_status in DONE_GRADING_STATUSES:
        return True

    status_label = str(row.get("status_label") or "").strip()
    return status_label in {"Completed", "Submitted", "Late", "Resubmitted"}


def is_student_quiz_state_actionable(quiz_state: dict[str, Any] | None) -> bool:
    state = quiz_state or {}
    return any(coerce_bool_flag(state.get(flag)) for flag in ("can_continue", "can_retry", "can_start"))


def is_student_work_actionable(row: dict[str, Any]) -> bool:
    if _has_explicit_flag(row, "is_actionable"):
        return coerce_bool_flag(row.get("is_actionable"))
    task_type = str(row.get("task_type") or "").strip()
    if task_type == "Quiz":
        return is_student_quiz_state_actionable(row.get("quiz_state") or {})
    return not is_student_work_done(row)


def _coerce_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    try:
        return get_datetime(value)
    except Exception:
        return None


def build_student_task_status_label(row: dict[str, Any], anchor_dt: datetime) -> str:
    due_dt = _coerce_datetime(row.get("due_date"))
    available_dt = _coerce_datetime(row.get("available_from"))
    submission_status = str(row.get("submission_status") or "").strip()
    grading_status = str(row.get("grading_status") or "").strip()

    if int(row.get("is_complete") or 0) == 1:
        return "Completed"
    if submission_status in DONE_SUBMISSION_STATUSES:
        return submission_status
    if grading_status in DONE_GRADING_STATUSES:
        return "Completed"
    if int(row.get("has_submission") or 0) == 1:
        return "Submitted"
    if available_dt and available_dt > anchor_dt:
        return "Not Yet Open"
    if due_dt and due_dt < anchor_dt:
        return "Overdue"
    if due_dt and due_dt.date() == anchor_dt.date():
        return "Due Today"
    if due_dt:
        return "Upcoming"
    return "Open"
