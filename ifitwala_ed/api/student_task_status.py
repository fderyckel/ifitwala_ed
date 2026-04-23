from __future__ import annotations

from datetime import date, datetime
from typing import Any

from frappe.utils import get_datetime

DONE_SUBMISSION_STATUSES = {"Submitted", "Late", "Resubmitted"}
DONE_GRADING_STATUSES = {"Finalized", "Released"}


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
