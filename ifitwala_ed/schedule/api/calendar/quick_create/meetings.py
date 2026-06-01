# ifitwala_ed/schedule/api/calendar/quick_create/meetings.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.schedule.api.calendar.core import _system_tzinfo, _to_system_datetime
from ifitwala_ed.schedule.api.calendar.quick_create.attendees import _resolve_attendee_contexts
from ifitwala_ed.schedule.api.calendar.quick_create.availability import _assert_students_available_for_meeting
from ifitwala_ed.schedule.api.calendar.quick_create.dto import (
    _coerce_date_required,
    _coerce_flag,
    _coerce_time_required,
    _combine_date_and_time_local,
    _parse_attendee_list,
    _run_idempotent_create,
    _safe_text,
    _target_payload,
)
from ifitwala_ed.schedule.api.calendar.quick_create.scope import (
    _ensure_allowed_location,
    _ensure_allowed_school,
    _ensure_allowed_team,
    _ensure_can_create_meeting,
    _get_quick_create_scope,
)


def _build_participant_rows(user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []

    employee_rows = frappe.get_all(
        "Employee",
        filters={"user_id": ["in", user_ids], "employment_status": "Active"},
        fields=["name", "user_id", "employee_full_name"],
        limit=max(len(user_ids), 1),
    )
    employee_by_user = {row.user_id: row for row in employee_rows if row.user_id}

    user_rows = frappe.get_all(
        "User",
        filters={"name": ["in", user_ids]},
        fields=["name", "full_name"],
        limit=max(len(user_ids), 1),
    )
    user_label_map = {row.name: (row.full_name or row.name) for row in user_rows if row.name}

    rows = []
    for user_id in user_ids:
        employee_row = employee_by_user.get(user_id)
        payload = {
            "participant": user_id,
            "participant_name": (
                (employee_row.employee_full_name if employee_row else None) or user_label_map.get(user_id) or user_id
            ),
        }
        if employee_row:
            payload["employee"] = employee_row.name
        rows.append(payload)
    return rows


def _resolve_meeting_participants(*, organizer_user: str, team: str | None, explicit_users: list[str]) -> list[str]:
    users: list[str] = []
    seen = set()

    if team:
        from ifitwala_ed.setup.doctype.meeting.meeting import get_team_participants

        for row in get_team_participants(team) or []:
            user_id = _safe_text(row.get("user_id"))
            if not user_id or user_id in seen:
                continue
            seen.add(user_id)
            users.append(user_id)

    for user_id in explicit_users:
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        users.append(user_id)

    if organizer_user not in seen:
        users.append(organizer_user)

    return users


def _assert_meeting_attendee_scope_flags(
    *,
    attendee_rows: list[dict],
    organizer_user: str,
    include_students: bool,
    include_guardians: bool,
) -> list[dict]:
    explicit_users = {_safe_text(row.get("user")) for row in attendee_rows if _safe_text(row.get("user"))}
    explicit_users.discard(_safe_text(organizer_user))
    if not explicit_users:
        return []

    contexts = _resolve_attendee_contexts(attendee_rows, organizer_user)
    blocked_students = []
    blocked_guardians = []
    for ctx in contexts:
        user_id = _safe_text(ctx.get("user"))
        if user_id not in explicit_users:
            continue
        label = _safe_text(ctx.get("label")) or user_id
        if ctx.get("kind") == "student" and not include_students:
            blocked_students.append(label)
        if ctx.get("kind") == "guardian" and not include_guardians:
            blocked_guardians.append(label)

    messages = []
    if blocked_students:
        messages.append(
            _("Enable Students before inviting student attendees: {students}.").format(
                students=", ".join(sorted(blocked_students))
            )
        )
    if blocked_guardians:
        messages.append(
            _("Enable Guardians before inviting guardian attendees: {guardians}.").format(
                guardians=", ".join(sorted(blocked_guardians))
            )
        )
    if messages:
        messages.append(_("This guardrail prevents accidentally inviting students or guardians to a private meeting."))
        frappe.throw("\n".join(messages), frappe.ValidationError)
    return contexts


def create_meeting_quick(
    *,
    meeting_name: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    team: str | None = None,
    school: str | None = None,
    location: str | None = None,
    meeting_category: str | None = None,
    virtual_meeting_link: str | None = None,
    agenda: str | None = None,
    visibility_scope: str | None = None,
    participants: object | None = None,
    include_students: object | None = 0,
    include_guardians: object | None = 0,
    client_request_id: str | None = None,
):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    title = _safe_text(meeting_name)
    meeting_date = _safe_text(date)
    start_value = _safe_text(start_time)
    end_value = _safe_text(end_time)
    team_value = _ensure_allowed_team(user, team)
    school_value = _ensure_allowed_school(user, school)
    location_value = _ensure_allowed_location(user, school_value, location)
    request_id = _safe_text(client_request_id)
    include_student_attendees = _coerce_flag(include_students)
    include_guardian_attendees = _coerce_flag(include_guardians)

    if not request_id:
        frappe.throw(_("client_request_id is required."), frappe.ValidationError)
    if not title:
        frappe.throw(_("Meeting name is required."), frappe.ValidationError)
    if not meeting_date:
        frappe.throw(_("Meeting date is required."), frappe.ValidationError)
    if not start_value or not end_value:
        frappe.throw(_("Start time and end time are required."), frappe.ValidationError)

    attendee_rows = _parse_attendee_list(participants)
    attendee_contexts = _assert_meeting_attendee_scope_flags(
        attendee_rows=attendee_rows,
        organizer_user=user,
        include_students=include_student_attendees,
        include_guardians=include_guardian_attendees,
    )
    proposed_date = _coerce_date_required(meeting_date, _("Meeting date"))
    proposed_start_time = _coerce_time_required(start_value, _("Start time"))
    proposed_end_time = _coerce_time_required(end_value, _("End time"))
    proposed_start = _combine_date_and_time_local(proposed_date, proposed_start_time)
    proposed_end = _combine_date_and_time_local(proposed_date, proposed_end_time)
    _assert_students_available_for_meeting(
        attendees=attendee_rows,
        organizer_user=user,
        window_start=proposed_start,
        window_end=proposed_end,
        attendee_contexts=attendee_contexts,
    )
    participant_users = [row["user"] for row in attendee_rows if row.get("user")]
    meeting_participants = _resolve_meeting_participants(
        organizer_user=user,
        team=team_value,
        explicit_users=participant_users,
    )
    visibility_value = _safe_text(visibility_scope) or ("Team & Participants" if team_value else "Participants Only")

    def _create():
        payload = {
            "doctype": "Meeting",
            "meeting_name": title,
            "date": meeting_date,
            "start_time": start_value,
            "end_time": end_value,
            "status": "Scheduled",
            "visibility_scope": visibility_value,
            "participants": _build_participant_rows(meeting_participants),
        }

        if team_value:
            payload["team"] = team_value
        elif school_value:
            # Ad-hoc meetings need a host school so AY + visibility metadata stay anchored.
            payload["school"] = school_value
        else:
            scope = _get_quick_create_scope(user)
            fallback_school = _safe_text(scope.get("base_school"))
            if fallback_school:
                payload["school"] = fallback_school

        if location_value:
            payload["location"] = location_value
        if _safe_text(meeting_category):
            payload["meeting_category"] = _safe_text(meeting_category)
        if _safe_text(virtual_meeting_link):
            payload["virtual_meeting_link"] = _safe_text(virtual_meeting_link)
        if _safe_text(agenda):
            payload["agenda"] = agenda

        doc = frappe.get_doc(payload)
        doc.insert()

        start_dt = (
            _to_system_datetime(doc.from_datetime, _system_tzinfo()) if getattr(doc, "from_datetime", None) else None
        )
        end_dt = _to_system_datetime(doc.to_datetime, _system_tzinfo()) if getattr(doc, "to_datetime", None) else None

        return {
            "ok": True,
            "status": "created",
            "idempotent": False,
            "doctype": "Meeting",
            "name": doc.name,
            "title": doc.meeting_name or doc.name,
            "start": start_dt.isoformat() if start_dt else None,
            "end": end_dt.isoformat() if end_dt else None,
            **_target_payload(
                doctype="Meeting",
                name=doc.name,
                label=doc.meeting_name or doc.name,
            ),
        }

    return _run_idempotent_create(
        doctype="Meeting",
        user=user,
        client_request_id=request_id,
        create_fn=_create,
    )
