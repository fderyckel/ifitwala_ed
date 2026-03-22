# ifitwala_ed/api/calendar_details.py

from __future__ import annotations

from typing import Dict, List, Optional

import frappe
import pytz
from frappe import _
from frappe.utils import cint, format_datetime, getdate

from ifitwala_ed.api.calendar_core import (
    CAL_MIN_DURATION,
    _coerce_time,
    _combine,
    _course_meta_map,
    _meeting_window,
    _resolve_employee_for_user,
    _resolve_instructor_ids,
    _student_group_memberships,
    _system_tzinfo,
    _to_system_datetime,
)
from ifitwala_ed.utilities.school_tree import get_ancestor_schools


def get_meeting_details(meeting: str):
    """
    Return a rich payload for a single Meeting that can be rendered inside
    the portal modal. Access is granted if:
    - the user is explicitly listed as a participant,
    - or the user's Employee record is listed on a participant row,
    - or the user otherwise has read permission on the Meeting (desk role).
    """
    if not meeting:
        frappe.throw(_("Missing meeting id"), frappe.ValidationError)

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view meetings."), frappe.PermissionError)

    try:
        doc = frappe.get_doc("Meeting", meeting)
    except frappe.DoesNotExistError:
        frappe.throw(_("Meeting {0} was not found.").format(meeting), frappe.DoesNotExistError)

    if doc.docstatus == 2 or doc.status == "Cancelled":
        frappe.throw(_("This meeting is no longer available."), frappe.PermissionError)

    participants = frappe.get_all(
        "Meeting Participant",
        filters={"parent": doc.name, "parenttype": "Meeting"},
        fields=[
            "participant",
            "participant_name",
            "employee",
            "role_in_meeting",
            "attendance_status",
        ],
        order_by="idx asc",
    )

    employee_row = _resolve_employee_for_user(
        user,
        fields=["name"],
        employment_status_filter=["!=", "Inactive"],
    )
    employee_id = (employee_row or {}).get("name")

    if not _meeting_access_allowed(doc, participants, user, employee_id):
        frappe.throw(_("You are not a participant of this meeting."), frappe.PermissionError)

    tzinfo = _system_tzinfo()
    start_dt, end_dt = _meeting_window(doc, tzinfo)

    team_meta = _get_team_meta(doc.team) if doc.team else {}
    leader_roles = {"chair", "leader", "meeting leader"}
    leaders = [row for row in participants if (row.get("role_in_meeting") or "").strip().lower() in leader_roles]

    payload = {
        "name": doc.name,
        "title": doc.meeting_name or doc.name,
        "status": doc.status or "Scheduled",
        "date": doc.date,
        "start": start_dt.isoformat() if start_dt else None,
        "end": end_dt.isoformat() if end_dt else None,
        "start_label": format_datetime(start_dt) if start_dt else None,
        "end_label": format_datetime(end_dt) if end_dt else None,
        "location": doc.location,
        "virtual_link": doc.virtual_meeting_link,
        "meeting_category": doc.meeting_category,
        "agenda": doc.agenda or "",
        "minutes": doc.minutes or "",
        "timezone": tzinfo.zone,
        "participants": participants,
        "participant_count": len(participants),
        "leaders": leaders,
        "team": doc.team,
        "team_name": team_meta.get("team_name") or doc.team,
        "team_color": team_meta.get("meeting_color"),
        "school": doc.school,
        "academic_year": doc.academic_year,
    }

    return payload


def get_school_event_details(event: str):
    """
    Return detailed metadata for a School Event visible to the current portal user.
    Requires either explicit participant visibility, school visibility, or desk read permission.
    """
    if not event:
        frappe.throw(_("Missing school event id"), frappe.ValidationError)

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view school events."), frappe.PermissionError)

    try:
        doc = frappe.get_doc("School Event", event)
    except frappe.DoesNotExistError:
        frappe.throw(_("School Event {0} was not found.").format(event), frappe.DoesNotExistError)

    if doc.docstatus == 2:
        frappe.throw(_("This school event is no longer available."), frappe.PermissionError)

    if not _school_event_access_allowed(doc, user):
        frappe.throw(_("You are not allowed to view this school event."), frappe.PermissionError)

    tzinfo = _system_tzinfo()
    start_dt = _to_system_datetime(doc.starts_on, tzinfo) if doc.starts_on else None
    end_dt = _to_system_datetime(doc.ends_on, tzinfo) if doc.ends_on else None
    if start_dt and end_dt and end_dt <= start_dt:
        end_dt = start_dt + CAL_MIN_DURATION

    color = (doc.color or "").strip() or "#059669"

    return {
        "name": doc.name,
        "subject": doc.subject or _("School Event"),
        "school": doc.school,
        "location": doc.location,
        "event_category": doc.event_category,
        "event_type": doc.event_type,
        "all_day": bool(doc.all_day),
        "color": color,
        "description": doc.description or "",
        "start": start_dt.isoformat() if start_dt else None,
        "end": end_dt.isoformat() if end_dt else None,
        "start_label": format_datetime(start_dt) if start_dt else None,
        "end_label": format_datetime(end_dt) if end_dt else None,
        "reference_type": doc.reference_type,
        "reference_name": doc.reference_name,
        "timezone": tzinfo.zone,
    }


def get_student_group_event_details(
    event_id: Optional[str] = None,
    eventId: Optional[str] = None,
    id: Optional[str] = None,
):
    """
    Resolve a class (Student Group) calendar entry into a richer payload for the portal modal.
    Supports Employee Booking ids (sg-booking::...) and schedule ids (sg::...).
    """
    resolved_event_id = (
        event_id
        or eventId
        or id
        or frappe.form_dict.get("event_id")
        or frappe.form_dict.get("eventId")
        or frappe.form_dict.get("id")
    )

    if not resolved_event_id:
        frappe.throw(_("Missing class event id."), frappe.ValidationError)

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view classes."), frappe.PermissionError)

    tzinfo = _system_tzinfo()

    debug_booking = bool(frappe.form_dict.get("debug_booking") or frappe.form_dict.get("debug"))

    if resolved_event_id.startswith("sg::"):
        context = _resolve_sg_schedule_context(resolved_event_id, tzinfo)
    elif resolved_event_id.startswith("sg-booking::"):
        context = _resolve_sg_booking_context(resolved_event_id, tzinfo, debug=debug_booking)
    else:
        frappe.throw(_("Unsupported class event format."), frappe.ValidationError)

    group_name = context.get("student_group")
    if not group_name:
        frappe.throw(_("Unable to resolve the student group for this event."), frappe.ValidationError)

    if not _user_has_student_group_access(user, group_name):
        frappe.throw(_("You are not allowed to view this class."), frappe.PermissionError)

    group_row = frappe.db.get_value(
        "Student Group",
        group_name,
        [
            "name",
            "student_group_name",
            "group_based_on",
            "program",
            "course",
            "cohort",
            "school",
        ],
        as_dict=True,
    )
    if not group_row:
        frappe.throw(_("Student Group {0} was not found.").format(group_name), frappe.DoesNotExistError)

    course_meta = _course_meta_map([group_row.course] if group_row.course else [])
    course_label = None
    if group_row.course:
        course_label = (course_meta.get(group_row.course) or {}).get("course_name") or group_row.course

    start_dt = context.get("start")
    end_dt = context.get("end")
    if start_dt and end_dt and end_dt <= start_dt:
        end_dt = start_dt + CAL_MIN_DURATION

    return {
        "id": resolved_event_id,
        "student_group": group_row.name,
        "title": group_row.student_group_name or group_row.name,
        "class_type": group_row.group_based_on,
        "program": group_row.program,
        "course": group_row.course,
        "course_name": course_label,
        "cohort": group_row.cohort,
        "school": group_row.school,
        "rotation_day": context.get("rotation_day"),
        "block_number": context.get("block_number"),
        "block_label": context.get("block_label"),
        "session_date": context.get("session_date"),
        "location": context.get("location"),
        "location_missing_reason": context.get("location_missing_reason"),
        "start": start_dt.isoformat() if start_dt else None,
        "end": end_dt.isoformat() if end_dt else None,
        "start_label": format_datetime(start_dt) if start_dt else None,
        "end_label": format_datetime(end_dt) if end_dt else None,
        "timezone": tzinfo.zone,
        "_debug": context.get("_debug") if debug_booking else None,
    }


def _get_team_meta(team: Optional[str]) -> Dict[str, str]:
    if not team:
        return {}
    row = frappe.db.get_value("Team", team, ["name", "team_name", "meeting_color"], as_dict=True)
    return row or {}


def _meeting_access_allowed(meeting, participants: List[Dict[str, str]], user: str, employee_id: Optional[str]) -> bool:
    if frappe.has_permission("Meeting", doc=meeting, ptype="read"):
        return True

    for row in participants:
        if row.get("participant") == user:
            return True
        if employee_id and row.get("employee") == employee_id:
            return True

    return False


def _resolve_sg_schedule_context(event_id: str, tzinfo: pytz.timezone) -> Dict[str, object]:
    """Resolve schedule-based Student Group ids into class modal context."""
    event_id = event_id.replace("sg/", "sg::", 1) if event_id.startswith("sg/") else event_id
    parts = event_id.split("::")
    if len(parts) == 3:
        group_name = parts[1]
        start_dt = _to_system_datetime(parts[2], tzinfo)
        end_dt = start_dt + CAL_MIN_DURATION if start_dt else None
        session_date = start_dt.date() if start_dt else None
        return {
            "student_group": group_name,
            "rotation_day": None,
            "block_number": None,
            "block_label": None,
            "session_date": session_date.isoformat() if session_date else None,
            "location": None,
            "start": start_dt,
            "end": end_dt,
        }

    if len(parts) < 5:
        frappe.throw(_("Invalid class event id."), frappe.ValidationError)

    group_name = parts[1]
    try:
        rotation_day = int(parts[2])
    except ValueError:
        rotation_day = None
    try:
        block_number = int(parts[3])
    except ValueError:
        block_number = None

    try:
        session_date = getdate(parts[4])
    except Exception:
        session_date = None

    slot = None
    if group_name and rotation_day is not None and block_number is not None:
        slots = frappe.get_all(
            "Student Group Schedule",
            filters={
                "parent": group_name,
                "rotation_day": rotation_day,
                "block_number": block_number,
            },
            fields=["location", "from_time", "to_time"],
            limit=1,
            ignore_permissions=True,
        )
        slot = slots[0] if slots else None

    from_time = _coerce_time(slot.from_time) if slot else None
    to_time = _coerce_time(slot.to_time) if slot else None

    start_dt = _combine(session_date, from_time, tzinfo) if session_date else None
    end_dt = _combine(session_date, to_time, tzinfo) if session_date and to_time else None

    return {
        "student_group": group_name,
        "rotation_day": rotation_day,
        "block_number": block_number,
        "block_label": _("Block {0}").format(block_number) if block_number is not None else None,
        "session_date": session_date.isoformat() if session_date else None,
        "location": slot.location if slot else None,
        "start": start_dt,
        "end": end_dt,
    }


def _resolve_sg_booking_context(
    event_id: str,
    tzinfo: pytz.timezone,
    *,
    debug: bool = False,
) -> Dict[str, object]:
    booking_name = event_id.split("::", 1)[1]
    row = frappe.db.get_value(
        "Employee Booking",
        booking_name,
        ["source_doctype", "source_name", "from_datetime", "to_datetime", "location"],
        as_dict=True,
    )
    if not row or row.source_doctype != "Student Group":
        frappe.throw(
            _("Employee Booking {0} was not found for a class.").format(booking_name),
            frappe.DoesNotExistError,
        )

    start_dt = _to_system_datetime(row.from_datetime, tzinfo) if row.from_datetime else None
    end_dt = _to_system_datetime(row.to_datetime, tzinfo) if row.to_datetime else None

    location = row.get("location") or None
    location_missing_reason = None if location else "booking-missing-location"

    context = {
        "student_group": row.source_name,
        "rotation_day": None,
        "block_number": None,
        "block_label": None,
        "session_date": start_dt.date().isoformat() if start_dt else None,
        "location": location,
        "location_missing_reason": location_missing_reason,
        "start": start_dt,
        "end": end_dt,
    }

    if debug:
        context["_debug"] = {
            "booking_name": booking_name,
            "location_present": bool(location),
            "location_missing_reason": location_missing_reason,
        }

    return context


def _user_has_student_group_access(user: str, group_name: str) -> bool:
    if not user or user == "Guest":
        return False

    student_name = _resolve_student_for_user(user)
    if student_name and _student_has_active_group_membership(student_name, group_name):
        return True

    guardian_students = _guardian_students_for_user(user)
    if guardian_students and _any_student_has_active_group_membership(guardian_students, group_name):
        return True

    employee_row = _resolve_employee_for_user(user, fields=["name"])
    employee_id = (employee_row or {}).get("name")
    instructor_ids = _resolve_instructor_ids(user, employee_id)
    group_names, _ = _student_group_memberships(user, employee_id, instructor_ids)
    if group_name in group_names:
        return True
    try:
        doc = frappe.get_doc("Student Group", group_name)
    except frappe.DoesNotExistError:
        return False
    except Exception:
        return False
    return frappe.has_permission("Student Group", doc=doc, ptype="read")


def _resolve_student_for_user(user: str) -> Optional[str]:
    if not user or user == "Guest":
        return None
    student = frappe.db.get_value("Student", {"student_email": user}, "name")
    if student:
        return student
    user_email = frappe.db.get_value("User", user, "email") or user
    return frappe.db.get_value("Student", {"student_email": user_email}, "name")


def _guardian_students_for_user(user: str) -> set[str]:
    if not user or user == "Guest":
        return set()

    guardian_name = frappe.db.get_value("Guardian", {"user": user}, "name")
    if not guardian_name:
        guardian_name = frappe.db.get_value("Guardian", {"guardian_email": user}, "name")
    if not guardian_name:
        return set()

    student_guardian_rows = frappe.get_all(
        "Student Guardian",
        filters={"guardian": guardian_name, "parenttype": "Student"},
        fields=["parent"],
        ignore_permissions=True,
    )
    guardian_student_rows = frappe.get_all(
        "Guardian Student",
        filters={"parent": guardian_name, "parenttype": "Guardian"},
        fields=["student"],
        ignore_permissions=True,
    )

    return {
        *[row.get("parent") for row in student_guardian_rows if row.get("parent")],
        *[row.get("student") for row in guardian_student_rows if row.get("student")],
    }


def _student_has_active_group_membership(student_name: str, group_name: str) -> bool:
    if not student_name or not group_name:
        return False
    row = frappe.db.get_value(
        "Student Group Student",
        {
            "parent": group_name,
            "parenttype": "Student Group",
            "student": student_name,
        },
        ["active"],
        as_dict=True,
    )
    return bool(row and cint(row.get("active")))


def _any_student_has_active_group_membership(student_names: set[str], group_name: str) -> bool:
    if not student_names or not group_name:
        return False
    row = frappe.get_all(
        "Student Group Student",
        filters={
            "parent": group_name,
            "parenttype": "Student Group",
            "student": ["in", list(student_names)],
            "active": 1,
        },
        fields=["name"],
        limit=1,
        ignore_permissions=True,
    )
    return bool(row)


def _school_event_access_allowed(event_doc, user: str) -> bool:
    if (event_doc.reference_type or "").strip() == "Applicant Interview":
        user_roles = set(frappe.get_roles(user))
        if user == "Administrator" or "System Manager" in user_roles or "Academic Admin" in user_roles:
            return True

        return bool(
            frappe.db.exists(
                "School Event Participant",
                {"parent": event_doc.name, "parenttype": "School Event", "participant": user},
            )
        )

    if frappe.has_permission("School Event", doc=event_doc, ptype="read"):
        return True

    is_participant = frappe.db.exists(
        "School Event Participant",
        {"parent": event_doc.name, "parenttype": "School Event", "participant": user},
    )
    if is_participant:
        return True

    emp_row = _resolve_employee_for_user(
        user,
        fields=["school"],
        employment_status_filter=["!=", "Inactive"],
    )
    employee_school = (emp_row or {}).get("school")
    if employee_school and event_doc.school:
        allowed_schools = get_ancestor_schools(employee_school) or []
        if event_doc.school in allowed_schools:
            return True

    return False
