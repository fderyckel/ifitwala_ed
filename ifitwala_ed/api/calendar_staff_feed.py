# ifitwala_ed/api/calendar_staff_feed.py

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Dict, List, MutableMapping, Optional

import frappe
import pytz
from frappe import _
from frappe.utils import getdate, now_datetime

from ifitwala_ed.api.calendar_core import (
    CACHE_TTL_SECONDS,
    CAL_MIN_DURATION,
    CalendarEvent,
    _attach_duration,
    _cache_key,
    _combine,
    _course_meta_map,
    _localize_datetime,
    _meeting_window,
    _normalize_sources,
    _resolve_employee_for_user,
    _resolve_window,
    _student_group_title_and_color,
    _system_tzinfo,
    _to_system_datetime,
)
from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_school_lineage


def get_staff_calendar(
    from_datetime: Optional[str] = None,
    to_datetime: Optional[str] = None,
    sources=None,
    force_refresh: bool = False,
):
    """Return a merged list of calendar entries for the logged-in staff user."""
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Please sign in to view your calendar."), frappe.PermissionError)

    employee = _resolve_employee_for_user(
        user,
        fields=["name", "employee_full_name"],
        employment_status_filter=["!=", "Inactive"],
    )
    employee_id = employee["name"] if employee else None
    if not employee_id and user != "Administrator":
        frappe.throw(_("Your user is not linked to an Employee record."), frappe.PermissionError)

    tzinfo = _system_tzinfo()
    tzname = tzinfo.zone
    window_start, window_end = _resolve_window(from_datetime, to_datetime, tzinfo)
    source_list = _normalize_sources(sources)

    cache_scope_subject = employee_id or f"user:{user}"
    cache_key = _cache_key(cache_scope_subject, window_start, window_end, source_list)
    if not force_refresh:
        if cached := frappe.cache().get_value(cache_key):
            try:
                return frappe.parse_json(cached)
            except Exception:
                pass

    events: List[CalendarEvent] = []
    source_counts: MutableMapping[str, int] = defaultdict(int)

    if "student_group" in source_list:
        sg_events = _collect_student_group_events(
            user,
            window_start,
            window_end,
            tzinfo,
            employee_id=employee_id,
        )
        for evt in sg_events:
            events.append(evt)
            source_counts[evt.source] += 1

    if "staff_holiday" in source_list:
        holiday_events = _collect_staff_holiday_events(
            user,
            window_start,
            window_end,
            tzinfo,
            employee_id=employee_id,
        )
        for evt in holiday_events:
            events.append(evt)
            source_counts[evt.source] += 1

    if "meeting" in source_list:
        meeting_events = _collect_meeting_events(user, window_start, window_end, tzinfo)
        for evt in meeting_events:
            events.append(evt)
            source_counts[evt.source] += 1

    if "school_event" in source_list:
        se_events = _collect_school_events(user, window_start, window_end, tzinfo)
        for evt in se_events:
            events.append(evt)
            source_counts[evt.source] += 1

    events.sort(key=lambda ev: (ev.start, ev.end, ev.id))

    payload = {
        "timezone": tzname,
        "window": {
            "from": window_start.isoformat(),
            "to": window_end.isoformat(),
        },
        "generated_at": _localize_datetime(now_datetime(), tzinfo).isoformat(),
        "events": [evt.as_dict() for evt in events],
        "sources": source_list,
        "counts": dict(source_counts),
    }

    frappe.cache().set_value(cache_key, frappe.as_json(payload), expires_in_sec=CACHE_TTL_SECONDS)
    return payload


def _resolve_staff_calendar_for_employee(
    employee_id: str,
    start_date: date,
    end_date: date,
) -> Optional[dict]:
    """
    Return the single best Staff Calendar match for this employee and window.

    Rule:
    - employee_group must match
    - calendar must overlap [start_date, end_date]
    - calendar school is chosen by nearest match in the employee school's ancestor chain
      (employee school first, then parent, then grandparent...)
    """
    if not employee_id:
        return None

    emp_rows = frappe.get_all(
        "Employee",
        filters={"name": employee_id},
        fields=["name", "school", "employee_group"],
        limit=1,
        ignore_permissions=True,
    )

    if not emp_rows:
        return None

    emp = emp_rows[0]
    employee_school = emp.get("school")
    employee_group = emp.get("employee_group")

    if not employee_school or not employee_group:
        return None

    school_chain = get_school_lineage(employee_school)

    cals = frappe.get_all(
        "Staff Calendar",
        filters={
            "employee_group": employee_group,
            "school": ["in", school_chain],
            "from_date": ["<=", end_date],
            "to_date": [">=", start_date],
        },
        fields=["name", "school", "employee_group", "from_date", "to_date"],
        ignore_permissions=True,
    )

    if not cals:
        return None

    rank = {school: i for i, school in enumerate(school_chain)}
    cals.sort(key=lambda r: rank.get(r.get("school"), 10**9))

    if len(cals) > 1:
        frappe.logger("ifitwala_ed.calendar").warning(
            "Multiple Staff Calendar matches; using nearest school match",
            {
                "employee": employee_id,
                "employee_school": employee_school,
                "employee_group": employee_group,
                "window_start": start_date.isoformat(),
                "window_end": end_date.isoformat(),
                "matches": [c.get("name") for c in cals[:10]],
            },
        )

    best = cals[0]
    return {
        "name": best.get("name"),
        "school": best.get("school"),
        "employee_group": best.get("employee_group"),
    }


def _collect_student_group_events(
    user: str,
    window_start: datetime,
    window_end: datetime,
    tzinfo: pytz.timezone,
    *,
    employee_id: Optional[str] = None,
) -> List[CalendarEvent]:
    if not employee_id:
        employee_row = _resolve_employee_for_user(user, fields=["name"])
        employee_id = (employee_row or {}).get("name")
    return _collect_student_group_events_from_bookings(employee_id, window_start, window_end, tzinfo)


def _collect_student_group_events_from_bookings(
    employee_id: Optional[str],
    window_start: datetime,
    window_end: datetime,
    tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
    if not employee_id or not frappe.db.table_exists("Employee Booking"):
        return []

    rows = frappe.db.sql(
        """
        SELECT
            eb.name            AS booking_name,
            eb.from_datetime   AS from_datetime,
            eb.to_datetime     AS to_datetime,
            eb.location        AS location,
            eb.source_name     AS student_group,
            sg.student_group_name,
            sg.course,
            sg.program,
            sg.program_offering,
            sg.school,
            sg.school_schedule,
            sg.academic_year,
            sg.status
        FROM `tabEmployee Booking` eb
        LEFT JOIN `tabStudent Group` sg ON sg.name = eb.source_name
        WHERE eb.employee = %(employee)s
            AND eb.source_doctype = 'Student Group'
            AND eb.docstatus < 2
            AND eb.from_datetime < %(window_end)s
            AND eb.to_datetime > %(window_start)s
            AND (sg.status IS NULL OR sg.status = 'Active')
        """,
        {"employee": employee_id, "window_start": window_start, "window_end": window_end},
        as_dict=True,
    )

    if not rows:
        return []

    course_meta = _course_meta_map(row.course for row in rows if row.course)
    events: List[CalendarEvent] = []

    for row in rows:
        sg_name = row.student_group or row.booking_name
        title, color = _student_group_title_and_color(
            sg_name,
            row.student_group_name,
            row.course,
            course_meta,
        )

        start_dt = _to_system_datetime(row.from_datetime, tzinfo)
        end_dt = _to_system_datetime(row.to_datetime, tzinfo) if row.to_datetime else None
        duration = _attach_duration(start_dt, end_dt)

        events.append(
            CalendarEvent(
                id=f"sg-booking::{row.booking_name}",
                title=title,
                start=start_dt,
                end=start_dt + duration,
                source="student_group",
                color=color,
                all_day=False,
                meta={
                    "student_group": row.student_group,
                    "course": row.course,
                    "booking": row.booking_name,
                    "location": row.location,
                },
            )
        )

    return events


def _collect_staff_holiday_events(
    user: str,
    window_start: datetime,
    window_end: datetime,
    tzinfo: pytz.timezone,
    employee_id: Optional[str] = None,
) -> List[CalendarEvent]:
    if not employee_id:
        return []

    start_date = getdate(window_start)
    end_date = getdate(window_end - timedelta(seconds=1))

    default_color = "#64748B"

    cal = _resolve_staff_calendar_for_employee(employee_id, start_date, end_date)
    if cal:
        holiday_rows = frappe.get_all(
            "Staff Calendar Holidays",
            filters={
                "parent": cal["name"],
                "holiday_date": ["between", [start_date, end_date]],
            },
            fields=["holiday_date", "description", "color", "weekly_off"],
            order_by="holiday_date asc",
            ignore_permissions=True,
        )

        if holiday_rows:
            events: List[CalendarEvent] = []
            for row in holiday_rows:
                hd = getdate(row.get("holiday_date"))
                if not hd:
                    continue

                start_dt = _combine(hd, time(0, 0, 0), tzinfo)
                end_dt = _combine(hd + timedelta(days=1), time(0, 0, 0), tzinfo)
                title = (row.get("description") or "").strip() or _("Holiday")
                color = (row.get("color") or "").strip() or default_color

                events.append(
                    CalendarEvent(
                        id=f"staff_holiday::{cal['name']}::{hd.isoformat()}",
                        title=title,
                        start=start_dt,
                        end=end_dt,
                        source="staff_holiday",
                        color=color,
                        all_day=True,
                        meta={
                            "staff_calendar": cal["name"],
                            "holiday_date": hd.isoformat(),
                            "weekly_off": int(row.get("weekly_off") or 0),
                            "employee_group": cal["employee_group"],
                            "school": cal["school"],
                        },
                    )
                )
            return events

    employee_school = frappe.db.get_value("Employee", employee_id, "school")
    if not employee_school:
        return []

    calendar_rows = resolve_school_calendars_for_window(employee_school, start_date, end_date)
    if not calendar_rows:
        frappe.logger("ifitwala_ed.calendar").info(
            "No effective School Calendar found for staff holiday fallback",
            {
                "employee": employee_id,
                "employee_school": employee_school,
                "window_start": start_date.isoformat(),
                "window_end": end_date.isoformat(),
            },
        )
        return []

    calendar_by_name = {row.get("name"): row for row in calendar_rows if row.get("name")}
    calendar_names = list(calendar_by_name.keys())
    if not calendar_names:
        return []

    school_holiday_rows = frappe.get_all(
        "School Calendar Holidays",
        filters={
            "parent": ["in", calendar_names],
            "holiday_date": ["between", [start_date, end_date]],
        },
        fields=["parent", "holiday_date", "description", "color", "weekly_off"],
        order_by="holiday_date asc",
        ignore_permissions=True,
    )
    if not school_holiday_rows:
        return []

    events: List[CalendarEvent] = []
    seen: set[tuple[str, str]] = set()

    for row in school_holiday_rows:
        hd = getdate(row.get("holiday_date"))
        calendar_name = (row.get("parent") or "").strip()
        if not hd or not calendar_name:
            continue

        key = (calendar_name, hd.isoformat())
        if key in seen:
            continue
        seen.add(key)

        start_dt = _combine(hd, time(0, 0, 0), tzinfo)
        end_dt = _combine(hd + timedelta(days=1), time(0, 0, 0), tzinfo)
        title = (row.get("description") or "").strip() or _("Holiday")
        color = (row.get("color") or "").strip() or default_color

        calendar_meta = calendar_by_name.get(calendar_name) or {}
        events.append(
            CalendarEvent(
                id=f"staff_holiday::school_calendar::{calendar_name}::{hd.isoformat()}",
                title=title,
                start=start_dt,
                end=end_dt,
                source="staff_holiday",
                color=color,
                all_day=True,
                meta={
                    "school_calendar": calendar_name,
                    "calendar_school": calendar_meta.get("school"),
                    "academic_year": calendar_meta.get("academic_year"),
                    "holiday_date": hd.isoformat(),
                    "weekly_off": int(row.get("weekly_off") or 0),
                    "fallback": "school_calendar",
                },
            )
        )

    return events


def _collect_meeting_events(
    user: str,
    window_start: datetime,
    window_end: datetime,
    tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
    employee_row = _resolve_employee_for_user(user, fields=["name"])
    employee_id = (employee_row or {}).get("name")

    params = {
        "user": user,
        "emp": employee_id or "",
        "start": window_start,
        "end": window_end,
    }

    rows = frappe.db.sql(
        """
        SELECT
            m.name,
            m.meeting_name,
            m.date,
            m.start_time,
            m.end_time,
            m.from_datetime,
            m.to_datetime,
            m.location,
            m.school,
            m.team,
            m.virtual_meeting_link
        FROM `tabMeeting Participant` mp
        INNER JOIN `tabMeeting` m ON mp.parent = m.name
        WHERE mp.parenttype = 'Meeting'
            AND (
                mp.participant = %(user)s
                OR (%(emp)s != '' AND mp.employee = %(emp)s)
            )
            AND m.docstatus < 2
            AND (
                (m.from_datetime BETWEEN %(start)s AND %(end)s)
                OR (m.to_datetime BETWEEN %(start)s AND %(end)s)
                OR (m.from_datetime <= %(start)s AND m.to_datetime >= %(end)s)
                OR (m.date BETWEEN %(start)s AND %(end)s)
            )
            AND (m.status IS NULL OR m.status != 'Cancelled')
        """,
        params,
        as_dict=True,
    )

    if not rows:
        return []

    team_meta_by_name: Dict[str, dict] = {}
    teams = {row.team for row in rows if row.team}
    if teams:
        team_rows = frappe.get_all(
            "Team",
            filters={"name": ["in", list(teams)]},
            fields=["name", "meeting_color", "school"],
            ignore_permissions=True,
        )
        team_meta_by_name = {row.name: row for row in team_rows}

    school_color_by_name: Dict[str, str] = {}
    school_names = {(row.school or "").strip() for row in rows if (row.school or "").strip()}
    school_names.update(
        {(row.get("school") or "").strip() for row in team_meta_by_name.values() if (row.get("school") or "").strip()}
    )
    if school_names:
        school_rows = frappe.get_all(
            "School",
            filters={"name": ["in", list(school_names)]},
            fields=["name", "meeting_color"],
            ignore_permissions=True,
        )
        school_color_by_name = {row.name: (row.meeting_color or "").strip() for row in school_rows}

    events: List[CalendarEvent] = []
    for row in rows:
        start_dt, end_dt = _meeting_window(row, tzinfo)
        if not start_dt:
            continue

        team_meta = team_meta_by_name.get(row.team) or {}
        team_color = (team_meta.get("meeting_color") or "").strip()
        effective_school = (row.school or team_meta.get("school") or "").strip()
        school_color = (school_color_by_name.get(effective_school) or "").strip()
        event_color = team_color or school_color or "#7c3aed"

        events.append(
            CalendarEvent(
                id=f"meeting::{row.name}",
                title=row.meeting_name or _("Meeting"),
                start=start_dt,
                end=end_dt,
                source="meeting",
                color=event_color,
                all_day=False,
                meta={
                    "location": row.location,
                    "team": row.team,
                    "team_color": team_color,
                    "school": effective_school,
                    "virtual_link": row.virtual_meeting_link,
                },
            )
        )

    return events


def _collect_school_events(
    user: str,
    window_start: datetime,
    window_end: datetime,
    tzinfo: pytz.timezone,
) -> List[CalendarEvent]:
    emp_row = _resolve_employee_for_user(
        user,
        fields=["name", "school"],
        employment_status_filter=["!=", "Inactive"],
    )
    employee_school = (emp_row or {}).get("school") if emp_row else None
    allowed_schools = get_ancestor_schools(employee_school) if employee_school else []
    params = {
        "user": user,
        "start": window_start,
        "end": window_end,
    }
    visibility_clauses = ["sep.participant IS NOT NULL"]
    if allowed_schools:
        params["schools"] = allowed_schools
        visibility_clauses.append(
            "(COALESCE(se.reference_type, '') != 'Applicant Interview' AND se.school IN %(schools)s)"
        )
    visibility_sql = " OR ".join(visibility_clauses)

    rows = frappe.db.sql(
        f"""
        SELECT
            se.name,
            se.subject,
            se.starts_on,
            se.ends_on,
            se.all_day,
            se.location,
            se.color,
            se.school,
            se.reference_type,
            se.reference_name,
            sep.participant_name
        FROM `tabSchool Event` se
        LEFT JOIN `tabSchool Event Participant` sep
            ON sep.parent = se.name
            AND sep.parenttype = 'School Event'
            AND sep.participant = %(user)s
        WHERE se.docstatus < 2
            AND ({visibility_sql})
            AND (
                (se.starts_on BETWEEN %(start)s AND %(end)s)
                OR (se.ends_on BETWEEN %(start)s AND %(end)s)
                OR (se.starts_on <= %(start)s AND se.ends_on >= %(end)s)
            )
        """,
        params,
        as_dict=True,
    )

    if not rows:
        return []

    events: List[CalendarEvent] = []
    for row in rows:
        start_dt = _to_system_datetime(row.starts_on, tzinfo) if row.starts_on else window_start
        end_dt_raw = row.ends_on or row.starts_on
        end_dt = _to_system_datetime(end_dt_raw, tzinfo) if end_dt_raw else (start_dt + CAL_MIN_DURATION)
        if end_dt <= start_dt:
            end_dt = start_dt + CAL_MIN_DURATION
        color = (row.color or "").strip() or "#059669"
        events.append(
            CalendarEvent(
                id=f"school_event::{row.name}",
                title=row.subject or _("School Event"),
                start=start_dt,
                end=end_dt,
                source="school_event",
                color=color,
                all_day=bool(row.all_day),
                meta={
                    "location": row.location,
                    "participant_name": row.participant_name,
                    "school": row.school,
                    "reference_type": row.reference_type,
                    "reference_name": row.reference_name,
                },
            )
        )

    return events
