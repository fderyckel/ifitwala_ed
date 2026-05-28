from __future__ import annotations

import frappe
from frappe.utils import cint

from ifitwala_ed.admission.api.communication.context import _safe_datetime, _to_text
from ifitwala_ed.admission.api.communication.messages import _sender_direction, _truncate_preview
from ifitwala_ed.setup.doctype.communication_interaction_entry.communication_interaction_entry import (
    DOCTYPE as ENTRY_DOCTYPE,
)


def get_admissions_thread_summaries_for_applicants(*, applicant_rows: list[dict], user: str) -> dict[str, dict]:
    """Return communication summaries keyed by Student Applicant name for Cockpit cards."""
    applicant_names = sorted({_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))})
    if not applicant_names:
        return {}

    applicant_user_by_name = {
        _to_text(row.get("name")): _to_text(row.get("applicant_user"))
        for row in applicant_rows
        if _to_text(row.get("name"))
    }

    summary_by_applicant = {
        applicant_name: {
            "thread_name": None,
            "unread_count": 0,
            "last_message_at": None,
            "last_message_preview": "",
            "last_message_from": None,
            "needs_reply": False,
        }
        for applicant_name in applicant_names
    }

    thread_rows = frappe.get_all(
        "Org Communication",
        filters={
            "admission_context_doctype": "Student Applicant",
            "admission_context_name": ["in", applicant_names],
        },
        fields=["name", "admission_context_name"],
        order_by="creation asc",
        limit=10000,
    )

    thread_by_applicant: dict[str, str] = {}
    applicant_by_thread: dict[str, str] = {}
    for row in thread_rows:
        applicant_name = _to_text(row.get("admission_context_name"))
        thread_name = _to_text(row.get("name"))
        if not applicant_name or not thread_name:
            continue
        if applicant_name in thread_by_applicant:
            continue
        thread_by_applicant[applicant_name] = thread_name
        applicant_by_thread[thread_name] = applicant_name
        summary_by_applicant[applicant_name]["thread_name"] = thread_name

    if not applicant_by_thread:
        return summary_by_applicant

    thread_names = sorted(applicant_by_thread.keys())
    read_rows = frappe.get_all(
        "Portal Read Receipt",
        filters={
            "user": user,
            "reference_doctype": "Org Communication",
            "reference_name": ["in", thread_names],
        },
        fields=["reference_name", "read_at"],
        limit=10000,
    )
    read_at_by_thread = {
        _to_text(row.get("reference_name")): _safe_datetime(row.get("read_at"))
        for row in read_rows
        if _to_text(row.get("reference_name"))
    }

    entry_rows = frappe.db.sql(
        f"""
        SELECT
            i.org_communication,
            i.user,
            i.note,
            i.visibility,
            i.creation,
            u.full_name
        FROM `tab{ENTRY_DOCTYPE}` i
        LEFT JOIN `tabUser` u
          ON u.name = i.user
        WHERE i.org_communication IN %(thread_names)s
          AND COALESCE(TRIM(i.note), '') != ''
          AND i.visibility != 'Hidden'
        ORDER BY i.creation DESC
        """,
        {"thread_names": tuple(thread_names)},
        as_dict=True,
    )

    latest_by_thread: dict[str, dict] = {}
    for row in entry_rows or []:
        thread_name = _to_text(row.get("org_communication"))
        if not thread_name:
            continue
        applicant_name = applicant_by_thread.get(thread_name)
        if not applicant_name:
            continue

        if thread_name not in latest_by_thread:
            latest_by_thread[thread_name] = row

        applicant_user = applicant_user_by_name.get(applicant_name, "")
        if not applicant_user:
            continue

        if _to_text(row.get("user")) != applicant_user:
            continue

        read_at = read_at_by_thread.get(thread_name)
        created_at = _safe_datetime(row.get("creation"))
        if read_at and created_at and created_at <= read_at:
            continue
        summary_by_applicant[applicant_name]["unread_count"] += 1

    for thread_name, latest in latest_by_thread.items():
        applicant_name = applicant_by_thread.get(thread_name)
        if not applicant_name:
            continue

        applicant_user = applicant_user_by_name.get(applicant_name, "")
        sender_user = _to_text(latest.get("user"))
        visibility = _to_text(latest.get("visibility"))
        direction = _sender_direction(
            sender_user=sender_user,
            applicant_user=applicant_user,
            visibility=visibility,
        )
        last_from = "applicant" if direction == "ApplicantToStaff" else "staff"
        unread_count = cint(summary_by_applicant[applicant_name]["unread_count"] or 0)

        summary_by_applicant[applicant_name]["last_message_at"] = latest.get("creation")
        summary_by_applicant[applicant_name]["last_message_preview"] = _truncate_preview(_to_text(latest.get("note")))
        summary_by_applicant[applicant_name]["last_message_from"] = last_from
        summary_by_applicant[applicant_name]["needs_reply"] = bool(unread_count > 0 and last_from == "applicant")

    return summary_by_applicant
