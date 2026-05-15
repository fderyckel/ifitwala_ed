# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.api import courses as courses_api
from ifitwala_ed.assessment import task_outcome_service


@frappe.whitelist()
def mark_assign_only_complete(payload=None, **kwargs):
    data = _normalize_payload(payload, kwargs)
    outcome_id = _clean_text(data.get("task_outcome") or data.get("outcome_id") or data.get("outcome"))
    if not outcome_id:
        frappe.throw(_("Task Outcome is required."))

    student = courses_api._require_student_name_for_session_user()
    result = task_outcome_service.set_assign_only_completion(
        outcome_id,
        is_complete=1,
        expected_student=student,
        ignore_permissions=True,
    )
    return {
        "task_outcome": result.get("outcome"),
        "is_complete": int(result.get("is_complete") or 0),
        "completed_on": courses_api._serialize_scalar(result.get("completed_on")),
    }


def _normalize_payload(payload, kwargs):
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
