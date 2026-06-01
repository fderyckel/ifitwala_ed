# ifitwala_ed/schedule/api/calendar/quick_create/school_events.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.api.org_communication_quick_create import get_org_communication_quick_create_capability
from ifitwala_ed.schedule.api.calendar.core import _system_tzinfo, _to_system_datetime
from ifitwala_ed.schedule.api.calendar.quick_create.dto import (
    _parse_user_list,
    _run_idempotent_create,
    _safe_text,
    _target_payload,
)
from ifitwala_ed.schedule.api.calendar.quick_create.scope import _ensure_allowed_location, _ensure_allowed_school
from ifitwala_ed.school_settings.doctype.school_event.school_event import publish_companion_org_communication_for_event


def create_school_event_quick(
    *,
    subject: str | None = None,
    school: str | None = None,
    starts_on: str | None = None,
    ends_on: str | None = None,
    audience_type: str | None = None,
    event_category: str | None = None,
    all_day: int | None = 0,
    location: str | None = None,
    description: str | None = None,
    audience_team: str | None = None,
    audience_student_group: str | None = None,
    include_guardians: int | None = 0,
    include_students: int | None = 0,
    reference_type: str | None = None,
    reference_name: str | None = None,
    custom_participants: object | None = None,
    publish_announcement: int | None = 0,
    announcement_message: str | None = None,
    client_request_id: str | None = None,
):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to create school events."), frappe.PermissionError)

    if not frappe.has_permission("School Event", ptype="create", user=user):
        frappe.throw(_("You do not have permission to create school events."), frappe.PermissionError)

    subject_value = _safe_text(subject)
    school_value = _safe_text(school)
    starts_value = _safe_text(starts_on)
    ends_value = _safe_text(ends_on)
    audience_value = _safe_text(audience_type)
    request_id = _safe_text(client_request_id)
    reference_type_value = _safe_text(reference_type)
    reference_name_value = _safe_text(reference_name)
    team_value = _safe_text(audience_team)
    student_group_value = _safe_text(audience_student_group)
    publish_announcement_flag = cint(publish_announcement)

    if publish_announcement_flag:
        publish_capability = get_org_communication_quick_create_capability(user=user)
        if not publish_capability.get("enabled"):
            frappe.throw(
                _safe_text(publish_capability.get("blocked_reason"))
                or _("You do not have permission to publish announcements from this workflow."),
                frappe.PermissionError,
            )

    if not request_id:
        frappe.throw(_("client_request_id is required."), frappe.ValidationError)
    if not subject_value:
        frappe.throw(_("Event subject is required."), frappe.ValidationError)
    if not school_value:
        frappe.throw(_("School is required."), frappe.ValidationError)
    if not starts_value or not ends_value:
        frappe.throw(_("Start and end datetime are required."), frappe.ValidationError)
    if not audience_value:
        frappe.throw(_("Audience type is required."), frappe.ValidationError)
    if reference_type_value and not reference_name_value:
        frappe.throw(_("Reference name is required when reference type is set."), frappe.ValidationError)
    if reference_name_value and not reference_type_value:
        frappe.throw(_("Reference type is required when reference name is set."), frappe.ValidationError)

    if audience_value == "Employees in Team" and not team_value:
        frappe.throw(_("Team is required for 'Employees in Team' audience."), frappe.ValidationError)
    if audience_value == "Students in Student Group" and not student_group_value:
        frappe.throw(_("Student Group is required for 'Students in Student Group' audience."), frappe.ValidationError)

    school_value = _ensure_allowed_school(user, school_value)
    location_value = _ensure_allowed_location(user, school_value, location)
    participants = _parse_user_list(custom_participants)
    if audience_value == "Custom Users" and not participants:
        participants = [user]

    def _create():
        published_communication = None
        audience_row = {
            "audience_type": audience_value,
            "include_guardians": cint(include_guardians),
            "include_students": cint(include_students),
        }
        if team_value:
            audience_row["team"] = team_value
        if student_group_value:
            audience_row["student_group"] = student_group_value

        payload = {
            "doctype": "School Event",
            "subject": subject_value,
            "school": school_value,
            "starts_on": starts_value,
            "ends_on": ends_value,
            "event_category": _safe_text(event_category) or "Other",
            "all_day": cint(all_day),
            "audience": [audience_row],
        }
        if location_value:
            payload["location"] = location_value
        if _safe_text(description):
            payload["description"] = description
        if reference_type_value:
            payload["reference_type"] = reference_type_value
        if reference_name_value:
            payload["reference_name"] = reference_name_value
        if participants:
            payload["participants"] = [{"participant": user_id} for user_id in participants]

        doc = frappe.get_doc(payload)
        doc.insert()
        if publish_announcement_flag:
            published_communication = publish_companion_org_communication_for_event(
                event_doc=doc,
                request_id=request_id,
                announcement_message=announcement_message,
            )

        start_dt = _to_system_datetime(doc.starts_on, _system_tzinfo()) if getattr(doc, "starts_on", None) else None
        end_dt = _to_system_datetime(doc.ends_on, _system_tzinfo()) if getattr(doc, "ends_on", None) else None

        return {
            "ok": True,
            "status": "created",
            "idempotent": False,
            "doctype": "School Event",
            "name": doc.name,
            "title": doc.subject or doc.name,
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
            "published_communication": published_communication,
            **_target_payload(
                doctype="School Event",
                name=doc.name,
                label=doc.subject or doc.name,
            ),
        }

    return _run_idempotent_create(
        doctype="School Event",
        user=user,
        client_request_id=request_id,
        create_fn=_create,
    )
