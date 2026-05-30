# ifitwala_ed/admission/api/inquiry/zero_lost.py

from __future__ import annotations

from datetime import timedelta
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime, nowdate

from ifitwala_ed.admission.api.inquiry.access import _ensure_access
from ifitwala_ed.admission.api.inquiry.dashboard import _build_dashboard_data
from ifitwala_ed.admission.api.inquiry.scope import _rest_conditions

ZERO_LOST_LEAD_VIEWS = [
    {
        "id": "unassigned_new",
        "title": _("Unassigned new inquiries"),
        "tone": "danger",
        "condition": "COALESCE(i.workflow_state, 'New') = 'New' AND IFNULL(i.assigned_to, '') = ''",
        "next_action": _("Assign owner"),
    },
    {
        "id": "uncontacted_due_today",
        "title": _("Uncontacted and due today"),
        "tone": "warning",
        "condition": (
            "COALESCE(i.workflow_state, 'New') NOT IN ('Contacted', 'Qualified', 'Archived') "
            "AND i.first_contacted_at IS NULL "
            "AND i.first_contact_due_on IS NOT NULL "
            "AND i.first_contact_due_on = %(today)s"
        ),
        "next_action": _("Record first contact"),
    },
    {
        "id": "overdue_first_contact",
        "title": _("Overdue first contact"),
        "tone": "danger",
        "condition": (
            "COALESCE(i.workflow_state, 'New') NOT IN ('Contacted', 'Qualified', 'Archived') "
            "AND i.first_contacted_at IS NULL "
            "AND i.first_contact_due_on IS NOT NULL "
            "AND i.first_contact_due_on < %(today)s"
        ),
        "next_action": _("Record first contact"),
    },
    {
        "id": "contacted_no_followup",
        "title": _("Contacted but no follow-up date"),
        "tone": "warning",
        "condition": (
            "COALESCE(i.workflow_state, 'New') = 'Contacted' "
            "AND IFNULL(i.followup_due_on, '') = '' "
            "AND IFNULL(i.student_applicant, '') = ''"
        ),
        "next_action": _("Set next action, qualify, or archive"),
    },
    {
        "id": "qualified_not_invited",
        "title": _("Qualified but not invited to apply"),
        "tone": "info",
        "condition": "COALESCE(i.workflow_state, 'New') = 'Qualified' AND IFNULL(i.student_applicant, '') = ''",
        "next_action": _("Invite to apply"),
    },
    {
        "id": "invited_no_progress",
        "title": _("Invited but no applicant progress"),
        "tone": "info",
        "condition": (
            "IFNULL(i.student_applicant, '') != '' "
            "AND sa.name IS NOT NULL "
            "AND sa.application_status = 'Invited' "
            "AND sa.submitted_at IS NULL"
        ),
        "next_action": _("Open applicant"),
    },
    {
        "id": "archived_without_reason",
        "title": _("Archived without reason"),
        "tone": "danger",
        "condition": "COALESCE(i.workflow_state, 'New') = 'Archived' AND IFNULL(i.archive_reason, '') = ''",
        "next_action": _("Add archive reason"),
    },
    {
        "id": "stale_unowned",
        "title": _("Leads older than 24 hours with no owner"),
        "tone": "danger",
        "condition": (
            "COALESCE(i.workflow_state, 'New') != 'Archived' "
            "AND IFNULL(i.assigned_to, '') = '' "
            "AND COALESCE(i.submitted_at, i.creation) < %(stale_before)s"
        ),
        "next_action": _("Assign owner"),
    },
]


def _zero_lost_view_by_id(view_id: str | None) -> dict:
    requested = (view_id or "").strip()
    for view in ZERO_LOST_LEAD_VIEWS:
        if view["id"] == requested:
            return view
    return ZERO_LOST_LEAD_VIEWS[0]


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _desk_route_slug(doctype: str) -> str:
    return frappe.scrub(doctype).replace("_", "-")


def _doc_url(doctype: str, name: str | None) -> str | None:
    resolved_name = (name or "").strip()
    if not resolved_name:
        return None
    return f"/desk/{_desk_route_slug(doctype)}/{quote(resolved_name, safe='')}"


def _lead_title(row: dict) -> str:
    parts = [(row.get("first_name") or "").strip(), (row.get("last_name") or "").strip()]
    title = " ".join(part for part in parts if part).strip()
    return title or (row.get("name") or "")


def _stringify_dt(value):
    return str(value) if value else None


def _age_hours(value, now_value) -> float | None:
    if not value:
        return None
    try:
        return round((get_datetime(now_value) - get_datetime(value)).total_seconds() / 3600.0, 1)
    except Exception:
        return None


def _zero_lost_row_payload(row: dict, *, active_view: dict, now_value) -> dict:
    inquiry_name = (row.get("name") or "").strip()
    applicant_name = (row.get("student_applicant") or "").strip()
    return {
        "name": inquiry_name,
        "lead_title": _lead_title(row),
        "email": row.get("email"),
        "phone_number": row.get("phone_number"),
        "type_of_inquiry": row.get("type_of_inquiry"),
        "source": row.get("source"),
        "organization": row.get("organization"),
        "school": row.get("school"),
        "workflow_state": row.get("workflow_state") or "New",
        "sla_status": row.get("sla_status"),
        "assigned_to": row.get("assigned_to"),
        "assignment_lane": row.get("assignment_lane") or "Admission",
        "student_applicant": applicant_name or None,
        "student_applicant_status": row.get("student_applicant_status"),
        "submitted_at": _stringify_dt(row.get("submitted_at")),
        "first_contact_due_on": _stringify_dt(row.get("first_contact_due_on")),
        "followup_due_on": _stringify_dt(row.get("followup_due_on")),
        "first_contacted_at": _stringify_dt(row.get("first_contacted_at")),
        "applicant_submitted_at": _stringify_dt(row.get("applicant_submitted_at")),
        "archive_reason": row.get("archive_reason"),
        "next_action_note": row.get("next_action_note"),
        "age_hours": _age_hours(row.get("submitted_at") or row.get("creation"), now_value),
        "open_url": _doc_url("Inquiry", inquiry_name),
        "student_applicant_url": _doc_url("Student Applicant", applicant_name),
        "next_action": {
            "label": active_view.get("next_action"),
            "target_url": _doc_url("Student Applicant", applicant_name)
            if active_view.get("id") == "invited_no_progress" and applicant_name
            else _doc_url("Inquiry", inquiry_name),
        },
    }


def _zero_lost_params() -> dict:
    now_value = now_datetime()
    return {
        "today": nowdate(),
        "stale_before": now_value - timedelta(hours=24),
        "now": now_value,
    }


def _build_zero_lost_lead_payload(filters: dict, *, user: str, active_view: str | None, start=0, limit=25) -> dict:
    base_where, base_params = _rest_conditions(filters, user=user)
    active = _zero_lost_view_by_id(active_view)

    start_value = max(_to_int(start, 0), 0)
    limit_value = _to_int(limit, 25)
    if limit_value < 1:
        limit_value = 25
    if limit_value > 100:
        limit_value = 100

    runtime_params = _zero_lost_params()
    count_params = {**base_params, **runtime_params}

    views = []
    active_total = 0
    for view in ZERO_LOST_LEAD_VIEWS:
        total = frappe.db.sql(
            """
            SELECT COUNT(*)
            FROM `tabInquiry` i
            LEFT JOIN `tabStudent Applicant` sa ON sa.name = i.student_applicant
            WHERE ({base_where}) AND ({view_condition})
            """.format(base_where=base_where, view_condition=view["condition"]),
            count_params,
            as_dict=False,
        )[0][0]
        total = int(total or 0)
        if view["id"] == active["id"]:
            active_total = total
        views.append(
            {
                "id": view["id"],
                "title": view["title"],
                "tone": view["tone"],
                "count": total,
                "next_action": view["next_action"],
            }
        )

    row_params = {**count_params, "start": start_value, "limit": limit_value}
    rows = frappe.db.sql(
        """
        SELECT
            i.name,
            i.creation,
            i.first_name,
            i.last_name,
            i.email,
            i.phone_number,
            i.type_of_inquiry,
            i.source,
            i.organization,
            i.school,
            i.workflow_state,
            i.sla_status,
            i.assigned_to,
            i.assignment_lane,
            i.student_applicant,
            i.submitted_at,
            i.first_contact_due_on,
            i.followup_due_on,
            i.first_contacted_at,
            i.archive_reason,
            i.next_action_note,
            sa.application_status AS student_applicant_status,
            sa.submitted_at AS applicant_submitted_at
        FROM `tabInquiry` i
        LEFT JOIN `tabStudent Applicant` sa ON sa.name = i.student_applicant
        WHERE ({base_where}) AND ({view_condition})
        ORDER BY
            COALESCE(i.first_contact_due_on, DATE(i.submitted_at), DATE(i.creation)) ASC,
            COALESCE(i.submitted_at, i.creation) ASC,
            i.modified DESC
        LIMIT %(start)s, %(limit)s
        """.format(base_where=base_where, view_condition=active["condition"]),
        row_params,
        as_dict=True,
    )

    return {
        "views": views,
        "active_view": active["id"],
        "rows": [_zero_lost_row_payload(row, active_view=active, now_value=runtime_params["now"]) for row in rows],
        "pagination": {
            "start": start_value,
            "limit": limit_value,
            "total": active_total,
            "has_next": start_value + limit_value < active_total,
        },
        "generated_at": _stringify_dt(runtime_params["now"]),
        "scope": {
            "operational_date_mode": "all_time",
        },
    }


def get_zero_lost_lead_context(filters=None, active_view: str | None = None, start=0, limit=25):
    user = _ensure_access()
    parsed_filters = frappe.parse_json(filters) or {}
    return {
        "command_center": _build_zero_lost_lead_payload(
            parsed_filters,
            user=user,
            active_view=active_view,
            start=start,
            limit=limit,
        ),
        "analytics": _build_dashboard_data(parsed_filters, user=user),
    }
