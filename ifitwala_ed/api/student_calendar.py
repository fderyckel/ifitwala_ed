# ifitwala_ed/api/student_calendar.py

"""
API for the Student Portal Calendar.
Focus: High concurrency, aggressive caching, efficient SQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import frappe
import pytz
from frappe import _
from frappe.utils import getdate, now_datetime

# Reuse existing utilities for schedule expansion
from ifitwala_ed.api.calendar_core import (
    CalendarEvent,
    _course_meta_map,
    _resolve_window,
    _system_tzinfo,
    _to_system_datetime,
)
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots

CACHE_TTL = 600  # 10 minutes
STUDENT_CALENDAR_INVALIDATE_EVENT = "student_calendar:invalidate"


def _resolve_student_rows(
    *,
    student: str | None = None,
    user: str | None = None,
    users: list[str] | None = None,
) -> list[frappe._dict]:
    student_rows: dict[str, frappe._dict] = {}

    student_value = (student or "").strip()
    if student_value:
        row = frappe.db.get_value("Student", student_value, ["name", "student_email"], as_dict=True)
        if row:
            student_rows[row.get("name") or student_value] = frappe._dict(row)
        else:
            student_rows[student_value] = frappe._dict({"name": student_value, "student_email": None})

    candidate_users = {(user or "").strip()} if user else set()
    candidate_users.update((candidate or "").strip() for candidate in (users or []) if candidate)
    candidate_users.discard("")

    if candidate_users:
        rows = frappe.get_all(
            "Student",
            filters={"student_email": ["in", sorted(candidate_users)]},
            fields=["name", "student_email"],
            limit=max(len(candidate_users), 1),
        )
        for row in rows:
            if row.name:
                student_rows[row.name] = row

    return list(student_rows.values())


def invalidate_student_calendar_cache(
    *,
    student: str | None = None,
    user: str | None = None,
    users: list[str] | None = None,
) -> None:
    rows = _resolve_student_rows(student=student, user=user, users=users)
    if not rows:
        return

    cache = frappe.cache()
    for row in rows:
        student_name = (row.get("name") or "").strip()
        if not student_name:
            continue
        for key in cache.get_keys(f"ifw:stud-cal:{student_name}:*"):
            cache.delete_value(key)


def refresh_student_calendar_views(
    *,
    student: str | None = None,
    user: str | None = None,
    users: list[str] | None = None,
    source: str | None = None,
    source_name: str | None = None,
) -> None:
    rows = _resolve_student_rows(student=student, user=user, users=users)
    if not rows:
        return

    invalidate_student_calendar_cache(student=student, user=user, users=users)

    payload = {"source": (source or "calendar").strip() or "calendar"}
    if (source_name or "").strip():
        payload["source_name"] = source_name.strip()

    seen_users: set[str] = set()
    for row in rows:
        student_user = (row.get("student_email") or "").strip()
        if not student_user or student_user in seen_users:
            continue
        seen_users.add(student_user)
        frappe.publish_realtime(
            STUDENT_CALENDAR_INVALIDATE_EVENT,
            message=payload,
            user=student_user,
            after_commit=True,
        )


@frappe.whitelist()
def get_student_calendar(
    from_datetime: Optional[str] = None,
    to_datetime: Optional[str] = None,
    force_refresh: bool = False,
):
    """
    Return calendar events for the currently logged-in student.
    Aggregates:
      - Classes (Student Groups)
      - School Events
      - Meetings
    """
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view your calendar."), frappe.PermissionError)

    # 1. Resolve Student
    student = frappe.db.get_value("Student", {"student_email": user}, "name")
    if not student:
        return _empty_payload()

    # 2. Resolve Window
    tzinfo = _system_tzinfo()
    window_start, window_end = _resolve_window(from_datetime, to_datetime, tzinfo)

    # 3. Cache Check
    cache_key = f"ifw:stud-cal:{student}:{window_start.date()}:{window_end.date()}"
    if not force_refresh:
        cached = frappe.cache().get_value(cache_key)
        if cached:
            return cached

    # 4. Fetch Data
    events: List[CalendarEvent] = []

    # Pre-fetch enrolled groups for both Classes and Event Audience checks
    enrolled_groups = _get_student_enrolled_groups(student)

    # A) Classes
    events.extend(_fetch_classes(student, enrolled_groups, window_start, window_end, tzinfo))

    # B) School Events
    events.extend(_fetch_school_events(student, enrolled_groups, window_start, window_end, tzinfo))

    # C) Meetings
    events.extend(_fetch_meetings(user, student, window_start, window_end, tzinfo))

    # D) Holidays
    # Determine applicable calendars from enrolled groups
    calendars = set()
    if sg_data := frappe.get_all(
        "Student Group", filters={"name": ["in", enrolled_groups]}, fields=["school_schedule"]
    ):
        schedules = [d.school_schedule for d in sg_data if d.school_schedule]
        if schedules:
            # Get calendars for these schedules
            # Optimization: Cache this mapping? For now, fetch.
            cal_data = frappe.get_all(
                "School Schedule", filters={"name": ["in", schedules]}, fields=["school_calendar"]
            )
            calendars.update(d.school_calendar for d in cal_data if d.school_calendar)

    if calendars:
        events.extend(_fetch_holidays(calendars, window_start, window_end, tzinfo))

    # 5. Build Response
    events.sort(key=lambda x: (x.start, x.end))

    payload = {
        "events": [evt.as_dict() for evt in events],
        "meta": {
            "tz": tzinfo.zone,
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "cached_at": now_datetime().isoformat(),
        },
    }

    # 6. Cache
    frappe.cache().set_value(cache_key, payload, expires_in_sec=CACHE_TTL)

    return payload


def _empty_payload():
    return {"events": [], "meta": {}}


def _fetch_holidays(calendars: set[str], start: datetime, end: datetime, tzinfo: pytz.timezone) -> List[CalendarEvent]:
    """
    Fetch holidays with descriptions directly from School Calendar Holidays.
    """
    if not calendars:
        return []

    holidays = []

    # Query School Calendar Holidays directly
    # Filters: parent in calendars, holiday_date in window, weekly_off=0 (usually)
    rows = frappe.db.sql(
        """
        SELECT parent, description, holiday_date
        FROM `tabSchool Calendar Holidays`
        WHERE
            parent IN %s
            AND holiday_date BETWEEN %s AND %s
            AND weekly_off = 0
        """,
        (tuple(calendars), start.date(), end.date()),
        as_dict=True,
    )

    for r in rows:
        d = r.holiday_date
        if isinstance(d, str):
            d = getdate(d)

        dt_start = tzinfo.localize(datetime.combine(d, datetime.min.time()))
        dt_end = dt_start + timedelta(days=1)

        holidays.append(
            CalendarEvent(
                id=f"holiday::{r.parent}::{d.isoformat()}",
                title=r.description or "Holiday",
                start=dt_start,
                end=dt_end,
                source="holiday",
                color="#ef4444",  # Red for holiday
                all_day=True,
                meta={"calendar": r.parent},
            )
        )

    return holidays


def _get_student_enrolled_groups(student):
    return [
        r.parent
        for r in frappe.db.sql(
            """SELECT parent FROM `tabStudent Group Student` WHERE student = %s AND active = 1""",
            (student,),
            as_dict=True,
        )
    ]


def _fetch_classes(
    student: str, sg_names: List[str], start: datetime, end: datetime, tzinfo: pytz.timezone
) -> List[CalendarEvent]:
    """
    Fetch active Student Group enrollments and expand them into slots.
    """
    if not sg_names:
        return []

    # Get details for these groups (Course, Color, etc.)
    group_meta = frappe.get_all(
        "Student Group",
        filters={"name": ["in", sg_names]},
        fields=["name", "student_group_name", "course"],
    )
    course_map = _course_meta_map(g.course for g in group_meta if g.course)

    meta_by_name = {g.name: g for g in group_meta}

    events = []

    start_date = start.date()
    end_date = end.date()

    for sg_name in sg_names:
        slots = iter_student_group_room_slots(sg_name, start_date, end_date)

        g_meta = meta_by_name.get(sg_name)
        if not g_meta:
            continue

        # Determine Title & Color
        course = course_map.get(g_meta.course)
        title = course.course_name if course else (g_meta.student_group_name or sg_name)
        color = (course.calendar_event_color if course else None) or "#3b82f6"

        for slot in slots:
            s_start = slot["start"]
            s_end = slot["end"]

            if s_start.tzinfo is None:
                s_start = tzinfo.localize(s_start)
            if s_end.tzinfo is None:
                s_end = tzinfo.localize(s_end)

            rotation_day = slot.get("rotation_day")
            block_number = slot.get("block_number")
            session_date = s_start.date().isoformat()

            events.append(
                CalendarEvent(
                    id=f"sg::{sg_name}::{rotation_day}::{block_number}::{session_date}",
                    title=title,
                    start=s_start,
                    end=s_end,
                    source="student_group",
                    color=color,
                    all_day=False,
                    meta={
                        "student_group": sg_name,
                        "location": slot.get("location"),
                        "course": g_meta.course,
                    },
                )
            )

    return events


def _fetch_school_events(
    student: str, enrolled_groups: List[str], start: datetime, end: datetime, tzinfo: pytz.timezone
) -> List[CalendarEvent]:
    """
    Fetch School Events visible to this student.
    """
    events_data = frappe.db.sql(
        """
        SELECT
            name, subject, starts_on, ends_on, color,
            description, location, all_day
        FROM `tabSchool Event`
        WHERE
            docstatus < 2
            AND (
                (starts_on BETWEEN %(start)s AND %(end)s)
                OR (ends_on BETWEEN %(start)s AND %(end)s)
            )
        """,
        {"start": start, "end": end},
        as_dict=True,
    )

    valid_events = []

    # Optimisation: Pre-convert group list to set for O(1) checking
    my_groups = set(enrolled_groups)

    for evt in events_data:
        # Load full doc to check child table 'audience'
        # Optimisation TODO: In high-scale, we'd query Audience table directly via JOIN.
        # But doc load here is safer for logic correctness in this phase.
        try:
            doc = frappe.get_doc("School Event", evt.name)
        except frappe.DoesNotExistError:
            continue

        if _is_student_audience(doc, student, my_groups):
            start_dt = _to_system_datetime(evt.starts_on, tzinfo)
            end_dt = _to_system_datetime(evt.ends_on, tzinfo) if evt.ends_on else start_dt + timedelta(hours=1)

            valid_events.append(
                CalendarEvent(
                    id=f"school_event::{evt.name}",
                    title=evt.subject,
                    start=start_dt,
                    end=end_dt,
                    source="school_event",
                    color=evt.color or "#10b981",
                    all_day=bool(evt.all_day),
                    meta={"location": evt.location, "description": evt.description},
                )
            )

    return valid_events


def _is_student_audience(doc, student_name, my_groups):
    """
    Check if student is in the audience of the event.
    doc: School Event document
    student_name: Name of student
    my_groups: Set of student group names the student is in
    """
    if not hasattr(doc, "audience"):
        return False

    for aud in doc.audience:
        atype = aud.audience_type

        # Public
        if atype in ("All Students, Guardians, and Employees", "All Students"):
            return True

        # Group based
        if atype == "Students in Student Group" and aud.student_group:
            if aud.student_group in my_groups:
                return True

        # Custom link? (Not fully defined in schema provided, assuming no per-student link in audience table directly)

    # Check Participants child table
    if hasattr(doc, "participants"):
        for p in doc.participants:
            # Check for generic participant field or specific link
            if p.get("participant") and p.participant == frappe.session.user:
                return True

    return False


def _fetch_meetings(
    user: str, student: str, start: datetime, end: datetime, tzinfo: pytz.timezone
) -> List[CalendarEvent]:
    """
    Fetch meetings where the student (or their user) is a participant.
    """
    meetings = frappe.db.sql(
        """
        SELECT
            m.name, m.meeting_name, m.from_datetime, m.to_datetime, m.location, m.virtual_meeting_link
        FROM `tabMeeting` m
        JOIN `tabMeeting Participant` mp ON mp.parent = m.name
        WHERE
            m.docstatus < 2
            AND m.status != 'Cancelled'
            AND mp.participant = %s
            AND m.from_datetime < %s
            AND m.to_datetime > %s
        """,
        (user, end, start),
        as_dict=True,
    )

    events = []
    seen = set()

    for m in meetings:
        if m.name in seen:
            continue
        seen.add(m.name)

        s_dt = _to_system_datetime(m.from_datetime, tzinfo)
        e_dt = _to_system_datetime(m.to_datetime, tzinfo)

        events.append(
            CalendarEvent(
                id=f"meeting::{m.name}",
                title=m.meeting_name,
                start=s_dt,
                end=e_dt,
                source="meeting",
                color="#8b5cf6",  # Violet
                all_day=False,
                meta={"location": m.location, "virtual_link": m.virtual_meeting_link},
            )
        )

    return events
