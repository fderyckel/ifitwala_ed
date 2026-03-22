# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from statistics import mean
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, nowdate

from ifitwala_ed.api.student_log_dashboard import get_authorized_schools
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates
from ifitwala_ed.school_settings.doctype.academic_load_policy.academic_load_policy import (
    get_academic_load_cache_version,
    get_active_policy_for_school,
)
from ifitwala_ed.utilities.school_tree import get_descendant_schools, get_school_lineage

ALLOWED_ANALYTICS_ROLES = {
    "Academic Admin",
    "Academic Assistant",
    "Curriculum Coordinator",
    "System Manager",
    "Administrator",
}

ACADEMIC_ROLE_OPTIONS = [
    "Academic Admin",
    "Academic Assistant",
    "Curriculum Coordinator",
    "Academic Staff",
    "Instructor",
]

TIME_MODE_OPTIONS = {"current_week", "next_2_weeks", "this_month", "blended"}
CACHE_TTL_SECONDS = 300


def _parse_payload(payload: Any | None) -> dict:
    if isinstance(payload, str):
        try:
            payload = frappe.parse_json(payload) or {}
        except Exception:
            payload = {}
    payload = payload or {}
    if isinstance(payload, dict) and payload.get("filters"):
        payload = payload.get("filters") or {}
    return payload or {}


def _clean_link(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value)


def _normalize_time_mode(value: Any) -> str:
    time_mode = (_clean_link(value) or "current_week").lower()
    if time_mode not in TIME_MODE_OPTIONS:
        return "current_week"
    return time_mode


def _current_user() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access Academic Load."), frappe.PermissionError)
    return user


def _ensure_access(user: str | None = None) -> str:
    user = user or _current_user()
    roles = set(frappe.get_roles(user))
    if roles & ALLOWED_ANALYTICS_ROLES:
        return user
    frappe.throw(_("You do not have permission to access Academic Load."), frappe.PermissionError)
    return user


def _window_bounds(time_mode: str, policy) -> tuple[date, date]:
    today = getdate(nowdate())

    if time_mode == "next_2_weeks":
        return today, today + timedelta(days=13)

    if time_mode == "this_month":
        month_start = today.replace(day=1)
        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)
        return month_start, next_month - timedelta(days=1)

    if time_mode == "blended":
        lookback = max(cint(policy.meeting_window_days or 30), 1)
        horizon = max(cint(policy.future_horizon_days or 14), 1)
        return today - timedelta(days=lookback - 1), today + timedelta(days=horizon - 1)

    week_start = today - timedelta(days=today.weekday())
    return week_start, week_start + timedelta(days=6)


def _normalize_filters(payload: dict) -> dict:
    return {
        "school": _clean_link(payload.get("school")),
        "academic_year": _clean_link(payload.get("academic_year")),
        "staff_role": _clean_link(payload.get("staff_role")),
        "search": (_clean_link(payload.get("search")) or "").strip(),
        "time_mode": _normalize_time_mode(payload.get("time_mode")),
        "student_group": _clean_link(payload.get("student_group")),
        "from_datetime": _clean_link(payload.get("from_datetime")),
        "to_datetime": _clean_link(payload.get("to_datetime")),
    }


def _resolve_scope(filters: dict, user: str) -> dict:
    authorized_schools = get_authorized_schools(user) or []
    if not authorized_schools:
        frappe.throw(_("You do not have an authorized school scope for Academic Load."), frappe.PermissionError)

    selected_school = filters.get("school") or authorized_schools[0]
    if selected_school not in authorized_schools:
        frappe.throw(_("You do not have access to this school."), frappe.PermissionError)

    selected_scope = get_descendant_schools(selected_school) or [selected_school]
    school_scope = [school for school in selected_scope if school in authorized_schools]
    if not school_scope:
        frappe.throw(_("No schools remain in scope after applying your selection."), frappe.PermissionError)

    return {
        "selected_school": selected_school,
        "school_scope": school_scope,
        "authorized_schools": authorized_schools,
    }


def _query_academic_year_rows(school_scope: list[str]) -> list[dict]:
    if not school_scope:
        return []

    return frappe.db.sql(
        """
        SELECT
            ay.name,
            ay.academic_year_name AS label,
            ay.year_start_date,
            ay.year_end_date,
            ay.school
        FROM `tabAcademic Year` ay
        WHERE ay.school IN %(schools)s
        ORDER BY ay.year_start_date DESC, ay.name DESC
        """,
        {"schools": tuple(school_scope)},
        as_dict=True,
    )


def _derive_academic_year_rows_from_groups(school_scope: list[str]) -> list[dict]:
    if not school_scope:
        return []

    group_rows = frappe.db.sql(
        """
        SELECT DISTINCT sg.academic_year AS name
        FROM `tabStudent Group` sg
        WHERE sg.school IN %(schools)s
          AND COALESCE(sg.academic_year, '') != ''
        ORDER BY sg.academic_year DESC
        """,
        {"schools": tuple(school_scope)},
        as_dict=True,
    )
    if not group_rows:
        return []

    names = [row["name"] for row in group_rows if row.get("name")]
    meta_rows = frappe.get_all(
        "Academic Year",
        filters={"name": ["in", names]},
        fields=["name", "academic_year_name as label", "year_start_date", "year_end_date", "school"],
    )
    meta_by_name = {row["name"]: row for row in meta_rows}
    return [meta_by_name.get(name, {"name": name, "label": name}) for name in names]


def _load_academic_year_options(school_scope: list[str], selected_school: str | None = None) -> list[dict]:
    if not school_scope:
        return []

    if rows := _query_academic_year_rows(school_scope):
        return rows

    anchor_school = (selected_school or "").strip() or (school_scope[0] if len(school_scope) == 1 else None)
    if anchor_school:
        for ancestor_school in get_school_lineage(anchor_school):
            ancestor_rows = _query_academic_year_rows([ancestor_school])
            if ancestor_rows:
                return ancestor_rows

    return _derive_academic_year_rows_from_groups(school_scope)


def _resolve_academic_year(filters: dict, scope: dict, options: list[dict]) -> str | None:
    selected = filters.get("academic_year")
    names = {row.get("name") for row in options}
    if selected and selected in names:
        return selected

    school_current = frappe.db.get_value("School", scope["selected_school"], "current_academic_year")
    if school_current and school_current in names:
        return school_current

    return options[0]["name"] if options else None


def _policy_summary(policy) -> dict:
    return {
        "name": policy.name,
        "school": policy.school,
        "meeting_window_days": cint(policy.meeting_window_days or 0),
        "future_horizon_days": cint(policy.future_horizon_days or 0),
        "meeting_blend_mode": policy.meeting_blend_mode,
        "is_system_default": cint(policy.is_system_default or 0),
        "was_customized": cint(policy.was_customized or 0),
    }


def _cache_key(prefix: str, user: str, payload: dict) -> str:
    version = get_academic_load_cache_version()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return f"ifitwala_ed:academic_load:{prefix}:v{version}:{user}:{encoded}"


def _load_student_group_options(school_scope: list[str], academic_year: str | None) -> list[dict]:
    if not school_scope:
        return []

    params: dict[str, Any] = {"schools": tuple(school_scope)}
    conditions = [
        "sg.school IN %(schools)s",
        "(sg.status IS NULL OR sg.status = 'Active')",
        "sg.group_based_on = 'Course'",
    ]
    if academic_year:
        params["academic_year"] = academic_year
        conditions.append("sg.academic_year = %(academic_year)s")

    return frappe.db.sql(
        f"""
        SELECT
            sg.name,
            sg.student_group_name AS label,
            sg.course,
            sg.program,
            sg.school
        FROM `tabStudent Group` sg
        WHERE {" AND ".join(conditions)}
        ORDER BY sg.student_group_name ASC, sg.name ASC
        """,
        params,
        as_dict=True,
    )


def _hours_between(start_dt: datetime, end_dt: datetime) -> float:
    if end_dt <= start_dt:
        return 0.0
    return round((end_dt - start_dt).total_seconds() / 3600, 4)


def _overlap_hours(start_dt: datetime, end_dt: datetime, window_start: datetime, window_end: datetime) -> float:
    overlap_start = max(start_dt, window_start)
    overlap_end = min(end_dt, window_end)
    return _hours_between(overlap_start, overlap_end)


def _weekly_hours(total_hours: float, start_date: date, end_date: date) -> float:
    days = max((end_date - start_date).days + 1, 1)
    return round(total_hours / (days / 7.0), 2)


def _serialize_datetime(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.isoformat(sep=" ", timespec="seconds")


def _load_educators(filters: dict, school_scope: list[str]) -> list[dict]:
    role_filter = filters.get("staff_role")
    params: dict[str, Any] = {
        "schools": tuple(school_scope),
        "roles": tuple(ACADEMIC_ROLE_OPTIONS),
    }

    conditions = [
        "e.employment_status = 'Active'",
        "e.school IN %(schools)s",
        "hr.role IN %(roles)s",
    ]
    if role_filter:
        params["role_filter"] = role_filter
        conditions.append("hr.role = %(role_filter)s")

    search = (filters.get("search") or "").strip()
    if search:
        params["search"] = f"%{search}%"
        conditions.append("(e.employee_full_name LIKE %(search)s OR e.name LIKE %(search)s)")

    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT
            e.name,
            e.employee_full_name,
            e.school,
            e.user_id,
            e.employee_group
        FROM `tabEmployee` e
        JOIN `tabHas Role` hr
            ON hr.parent = e.user_id
           AND hr.parenttype = 'User'
        WHERE {" AND ".join(conditions)}
        ORDER BY e.employee_full_name ASC, e.name ASC
        """,
        params,
        as_dict=True,
    )

    if not rows:
        return []

    names = [row["name"] for row in rows]
    role_rows = frappe.db.sql(
        """
        SELECT
            e.name AS employee,
            hr.role
        FROM `tabEmployee` e
        JOIN `tabHas Role` hr
            ON hr.parent = e.user_id
           AND hr.parenttype = 'User'
        WHERE e.name IN %(employees)s
          AND hr.role IN %(roles)s
        """,
        {"employees": tuple(names), "roles": tuple(ACADEMIC_ROLE_OPTIONS)},
        as_dict=True,
    )
    roles_by_employee: dict[str, list[str]] = defaultdict(list)
    for row in role_rows:
        employee = row.get("employee")
        role = row.get("role")
        if employee and role and role not in roles_by_employee[employee]:
            roles_by_employee[employee].append(role)

    for row in rows:
        row["roles"] = roles_by_employee.get(row["name"], [])
    return rows


def _load_group_student_counts(group_names: list[str]) -> dict[str, int]:
    if not group_names:
        return {}

    rows = frappe.db.sql(
        """
        SELECT parent AS student_group, COUNT(*) AS student_count
        FROM `tabStudent Group Student`
        WHERE parent IN %(groups)s
          AND COALESCE(active, 0) = 1
        GROUP BY parent
        """,
        {"groups": tuple(group_names)},
        as_dict=True,
    )
    return {row["student_group"]: cint(row["student_count"] or 0) for row in rows}


def _load_student_group_booking_rows(
    employee_names: list[str],
    school_scope: list[str],
    academic_year: str | None,
    window_start: datetime,
    window_end: datetime,
) -> list[dict]:
    if not employee_names:
        return []

    params: dict[str, Any] = {
        "employees": tuple(employee_names),
        "schools": tuple(school_scope),
        "window_start": window_start,
        "window_end": window_end,
    }

    conditions = [
        "eb.employee IN %(employees)s",
        "eb.source_doctype = 'Student Group'",
        "eb.booking_type = 'Teaching'",
        "eb.from_datetime < %(window_end)s",
        "eb.to_datetime > %(window_start)s",
        "sg.school IN %(schools)s",
        "(sg.status IS NULL OR sg.status = 'Active')",
    ]

    if academic_year:
        params["academic_year"] = academic_year
        conditions.append("sg.academic_year = %(academic_year)s")

    return frappe.db.sql(
        f"""
        SELECT
            eb.employee,
            eb.from_datetime,
            eb.to_datetime,
            sg.name AS student_group,
            sg.student_group_name,
            sg.group_based_on,
            sg.course,
            sg.program,
            sg.program_offering,
            sg.school
        FROM `tabEmployee Booking` eb
        JOIN `tabStudent Group` sg ON sg.name = eb.source_name
        WHERE {" AND ".join(conditions)}
        ORDER BY eb.employee ASC, eb.from_datetime ASC
        """,
        params,
        as_dict=True,
    )


def _load_meeting_rows(employee_names: list[str], school_scope: list[str], policy) -> list[dict]:
    if not employee_names:
        return []

    today = getdate(nowdate())
    past_start = datetime.combine(today - timedelta(days=max(cint(policy.meeting_window_days or 30) - 1, 0)), time.min)
    future_end = datetime.combine(today + timedelta(days=max(cint(policy.future_horizon_days or 14) - 1, 0)), time.max)

    params: dict[str, Any] = {
        "employees": tuple(employee_names),
        "schools": tuple(school_scope),
        "window_start": past_start,
        "window_end": future_end,
    }
    conditions = [
        "mp.employee IN %(employees)s",
        "m.school IN %(schools)s",
        "m.from_datetime IS NOT NULL",
        "m.to_datetime IS NOT NULL",
        "m.from_datetime < %(window_end)s",
        "m.to_datetime > %(window_start)s",
    ]
    if cint(policy.exclude_cancelled_meetings or 0) == 1:
        conditions.append("COALESCE(m.status, 'Scheduled') != 'Cancelled'")

    return frappe.db.sql(
        f"""
        SELECT
            mp.employee,
            m.name,
            m.meeting_name,
            m.meeting_category,
            m.status,
            m.school,
            m.from_datetime,
            m.to_datetime
        FROM `tabMeeting Participant` mp
        JOIN `tabMeeting` m ON m.name = mp.parent
        WHERE {" AND ".join(conditions)}
        ORDER BY m.from_datetime ASC, m.name ASC
        """,
        params,
        as_dict=True,
    )


def _load_school_event_rows(employee_names: list[str], school_scope: list[str], policy) -> list[dict]:
    if not employee_names:
        return []

    today = getdate(nowdate())
    future_end = datetime.combine(today + timedelta(days=max(cint(policy.future_horizon_days or 14) - 1, 0)), time.max)
    future_start = datetime.combine(today, time.min)

    return frappe.db.sql(
        """
        SELECT
            e.name AS employee,
            se.name,
            se.subject,
            se.event_category,
            se.school,
            se.starts_on,
            se.ends_on
        FROM `tabSchool Event Participant` sep
        JOIN `tabSchool Event` se ON se.name = sep.parent
        JOIN `tabEmployee` e ON e.user_id = sep.participant
        WHERE e.name IN %(employees)s
          AND se.school IN %(schools)s
          AND se.starts_on < %(window_end)s
          AND se.ends_on > %(window_start)s
        ORDER BY se.starts_on ASC, se.name ASC
        """,
        {
            "employees": tuple(employee_names),
            "schools": tuple(school_scope),
            "window_start": future_start,
            "window_end": future_end,
        },
        as_dict=True,
    )


def _load_hard_booking_rows(employee_names: list[str], window_start: datetime, window_end: datetime) -> list[dict]:
    if not employee_names:
        return []

    return frappe.db.sql(
        """
        SELECT employee, from_datetime, to_datetime, source_doctype, source_name, booking_type
        FROM `tabEmployee Booking`
        WHERE employee IN %(employees)s
          AND blocks_availability = 1
          AND from_datetime < %(window_end)s
          AND to_datetime > %(window_start)s
        ORDER BY employee ASC, from_datetime ASC
        """,
        {
            "employees": tuple(employee_names),
            "window_start": window_start,
            "window_end": window_end,
        },
        as_dict=True,
    )


def _score_band(total_score: float, policy) -> str:
    if total_score < flt(policy.underutilized_threshold):
        return "Low"
    if total_score < flt(policy.high_load_threshold):
        return "Normal"
    if total_score < flt(policy.overload_threshold):
        return "High"
    return "Critical"


def _cover_label(rank: int | None) -> str:
    if rank is None:
        return "Unavailable"
    if rank == 0:
        return "Strong fit"
    if rank in {1, 2}:
        return "Possible"
    return "Last resort"


def _build_schedule_windows(
    school_scope: list[str], academic_year: str | None, window_start: date, window_end: date
) -> dict[str, list[tuple[datetime, datetime]]]:
    if not academic_year or window_end < window_start:
        return {}

    schedules = frappe.db.sql(
        """
        SELECT
            ss.name,
            ss.school
        FROM `tabSchool Schedule` ss
        JOIN `tabSchool Calendar` sc ON sc.name = ss.school_calendar
        WHERE ss.school IN %(schools)s
          AND sc.academic_year = %(academic_year)s
        ORDER BY ss.school ASC, ss.name ASC
        """,
        {"schools": tuple(school_scope), "academic_year": academic_year},
        as_dict=True,
    )
    if not schedules:
        return {}

    blocks = frappe.db.sql(
        """
        SELECT
            parent AS schedule_name,
            rotation_day,
            block_number,
            from_time,
            to_time,
            block_type
        FROM `tabSchool Schedule Block`
        WHERE parent IN %(schedules)s
          AND block_type IN ('Course', 'Activity')
        ORDER BY parent ASC, rotation_day ASC, block_number ASC
        """,
        {"schedules": tuple(row["name"] for row in schedules)},
        as_dict=True,
    )
    blocks_by_schedule: dict[str, list[dict]] = defaultdict(list)
    for row in blocks:
        blocks_by_schedule[row["schedule_name"]].append(row)

    windows_by_school: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    for row in schedules:
        rotation_rows = get_rotation_dates(row["name"], academic_year) or []
        blocks_for_schedule = blocks_by_schedule.get(row["name"], [])
        if not blocks_for_schedule:
            continue

        for rotation_row in rotation_rows:
            slot_date = getdate(rotation_row.get("date"))
            if slot_date < window_start or slot_date > window_end:
                continue

            rotation_day = cint(rotation_row.get("rotation_day") or 0)
            for block in blocks_for_schedule:
                if cint(block.get("rotation_day") or 0) != rotation_day:
                    continue
                start_dt = get_datetime(f"{slot_date} {block.get('from_time')}")
                end_dt = get_datetime(f"{slot_date} {block.get('to_time')}")
                if end_dt <= start_dt:
                    continue
                windows_by_school[row["school"]].append((start_dt, end_dt))

    return windows_by_school


def _count_free_blocks(
    educators: list[dict],
    hard_bookings: list[dict],
    school_scope: list[str],
    academic_year: str | None,
    window_start: date,
    window_end: date,
) -> dict[str, int]:
    future_start = max(window_start, getdate(nowdate()))
    if future_start > window_end:
        return {row["name"]: 0 for row in educators}

    windows_by_school = _build_schedule_windows(school_scope, academic_year, future_start, window_end)
    if not windows_by_school:
        return {row["name"]: 0 for row in educators}

    bookings_by_employee: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    for row in hard_bookings:
        bookings_by_employee[row["employee"]].append(
            (get_datetime(row["from_datetime"]), get_datetime(row["to_datetime"]))
        )

    counts: dict[str, int] = {}
    for educator in educators:
        windows = windows_by_school.get(educator.get("school"), [])
        free_blocks = 0
        for start_dt, end_dt in windows:
            if not any(
                start_dt < booking_end and end_dt > booking_start
                for booking_start, booking_end in bookings_by_employee.get(educator["name"], [])
            ):
                free_blocks += 1
        counts[educator["name"]] = free_blocks
    return counts


def _build_rows(filters: dict, scope: dict, academic_year: str | None, policy) -> tuple[list[dict], dict]:
    educators = _load_educators(filters, scope["school_scope"])
    if not educators:
        return [], {"window": None, "teaching_groups": {}}

    window_start_date, window_end_date = _window_bounds(filters["time_mode"], policy)
    window_start_dt = datetime.combine(window_start_date, time.min)
    window_end_dt = datetime.combine(window_end_date, time.max)

    employee_names = [row["name"] for row in educators]
    sg_booking_rows = _load_student_group_booking_rows(
        employee_names,
        scope["school_scope"],
        academic_year,
        window_start_dt,
        window_end_dt,
    )

    meeting_rows = _load_meeting_rows(employee_names, scope["school_scope"], policy)
    event_rows = _load_school_event_rows(employee_names, scope["school_scope"], policy)
    hard_booking_rows = _load_hard_booking_rows(employee_names, window_start_dt, window_end_dt)

    group_names = sorted({row["student_group"] for row in sg_booking_rows if row.get("student_group")})
    group_student_counts = _load_group_student_counts(group_names)

    rows_by_employee: dict[str, dict] = {}
    for educator in educators:
        rows_by_employee[educator["name"]] = {
            "educator": {
                "employee": educator["name"],
                "user": educator.get("user_id"),
                "full_name": educator.get("employee_full_name") or educator["name"],
                "school": educator.get("school"),
                "employee_group": educator.get("employee_group"),
                "roles": educator.get("roles", []),
            },
            "facts": {
                "teaching_hours": 0.0,
                "students_taught": 0,
                "activity_hours": 0.0,
                "meeting_weekly_avg_hours": 0.0,
                "event_weekly_avg_hours": 0.0,
                "free_blocks_count": 0,
            },
            "scores": {
                "teaching_units": 0.0,
                "student_units": 0.0,
                "activity_units": 0.0,
                "meeting_units": 0.0,
                "event_units": 0.0,
                "non_teaching_units": 0.0,
                "total_load_score": 0.0,
            },
            "bands": {
                "load_band": "Low",
            },
            "_detail": {
                "teaching": defaultdict(lambda: {"hours": 0.0}),
                "activities": defaultdict(lambda: {"hours": 0.0}),
                "meetings": [],
                "events": [],
                "teaching_groups": set(),
            },
        }

    for booking in sg_booking_rows:
        employee = booking["employee"]
        if employee not in rows_by_employee:
            continue

        overlap = _overlap_hours(
            get_datetime(booking["from_datetime"]),
            get_datetime(booking["to_datetime"]),
            window_start_dt,
            window_end_dt,
        )
        if overlap <= 0:
            continue

        detail = rows_by_employee[employee]["_detail"]
        group_payload = {
            "student_group": booking["student_group"],
            "student_group_name": booking.get("student_group_name") or booking["student_group"],
            "course": booking.get("course"),
            "program": booking.get("program"),
            "program_offering": booking.get("program_offering"),
            "school": booking.get("school"),
            "student_count": group_student_counts.get(booking["student_group"], 0),
        }
        if (booking.get("group_based_on") or "").strip() == "Activity":
            rows_by_employee[employee]["facts"]["activity_hours"] += overlap
            activity_row = detail["activities"][booking["student_group"]]
            activity_row.update(group_payload)
            activity_row["hours"] = round(activity_row.get("hours", 0.0) + overlap, 2)
            continue

        detail["teaching_groups"].add(booking["student_group"])
        rows_by_employee[employee]["facts"]["teaching_hours"] += overlap
        teaching_row = detail["teaching"][booking["student_group"]]
        teaching_row.update(group_payload)
        teaching_row["hours"] = round(teaching_row.get("hours", 0.0) + overlap, 2)

    today = getdate(nowdate())
    meeting_past_days = max(cint(policy.meeting_window_days or 30), 1)
    meeting_future_days = max(cint(policy.future_horizon_days or 14), 1)
    past_start_dt = datetime.combine(today - timedelta(days=meeting_past_days - 1), time.min)
    past_end_dt = datetime.combine(today, time.min)
    future_start_dt = datetime.combine(today, time.min)
    future_end_dt = datetime.combine(today + timedelta(days=meeting_future_days - 1), time.max)

    past_meeting_hours: Counter[str] = Counter()
    future_meeting_hours: Counter[str] = Counter()
    for row in meeting_rows:
        employee = row["employee"]
        if employee not in rows_by_employee:
            continue

        start_dt = get_datetime(row["from_datetime"])
        end_dt = get_datetime(row["to_datetime"])
        past_hours = _overlap_hours(start_dt, end_dt, past_start_dt, past_end_dt)
        future_hours = _overlap_hours(start_dt, end_dt, future_start_dt, future_end_dt)
        past_meeting_hours[employee] += past_hours
        future_meeting_hours[employee] += future_hours
        rows_by_employee[employee]["_detail"]["meetings"].append(
            {
                "name": row["name"],
                "meeting_name": row.get("meeting_name") or row["name"],
                "meeting_category": row.get("meeting_category"),
                "status": row.get("status"),
                "hours": round(_hours_between(start_dt, end_dt), 2),
                "from_datetime": _serialize_datetime(start_dt),
                "to_datetime": _serialize_datetime(end_dt),
            }
        )

    future_event_hours: Counter[str] = Counter()
    for row in event_rows:
        employee = row["employee"]
        if employee not in rows_by_employee:
            continue

        start_dt = get_datetime(row["starts_on"])
        end_dt = get_datetime(row["ends_on"])
        future_event_hours[employee] += _overlap_hours(start_dt, end_dt, future_start_dt, future_end_dt)
        rows_by_employee[employee]["_detail"]["events"].append(
            {
                "name": row["name"],
                "subject": row.get("subject") or row["name"],
                "event_category": row.get("event_category"),
                "hours": round(_hours_between(start_dt, end_dt), 2),
                "starts_on": _serialize_datetime(start_dt),
                "ends_on": _serialize_datetime(end_dt),
            }
        )

    free_blocks = _count_free_blocks(
        educators,
        hard_booking_rows,
        scope["school_scope"],
        academic_year,
        window_start_date,
        window_end_date,
    )

    rows: list[dict] = []
    for employee_name, row in rows_by_employee.items():
        teaching_groups = row["_detail"]["teaching_groups"]
        row["facts"]["students_taught"] = sum(group_student_counts.get(group, 0) for group in teaching_groups)
        row["facts"]["teaching_hours"] = _weekly_hours(
            row["facts"]["teaching_hours"], window_start_date, window_end_date
        )
        row["facts"]["activity_hours"] = _weekly_hours(
            row["facts"]["activity_hours"], window_start_date, window_end_date
        )

        past_avg = round(past_meeting_hours.get(employee_name, 0.0) / (meeting_past_days / 7.0), 2)
        future_avg = round(future_meeting_hours.get(employee_name, 0.0) / (meeting_future_days / 7.0), 2)
        blend_mode = (policy.meeting_blend_mode or "Blended Past + Future").strip()
        if blend_mode == "Past Average Only":
            row["facts"]["meeting_weekly_avg_hours"] = past_avg
        elif blend_mode == "Future Scheduled Only":
            row["facts"]["meeting_weekly_avg_hours"] = future_avg
        else:
            row["facts"]["meeting_weekly_avg_hours"] = round((past_avg + future_avg) / 2.0, 2)

        row["facts"]["event_weekly_avg_hours"] = round(
            future_event_hours.get(employee_name, 0.0) / (meeting_future_days / 7.0), 2
        )
        row["facts"]["free_blocks_count"] = cint(free_blocks.get(employee_name, 0))

        row["scores"]["teaching_units"] = round(flt(policy.teaching_weight) * flt(row["facts"]["teaching_hours"]), 2)
        row["scores"]["student_units"] = round(
            flt(policy.student_weight)
            * (flt(row["facts"]["students_taught"]) / flt(policy.student_ratio_divisor or 1)),
            2,
        )
        row["scores"]["activity_units"] = round(flt(policy.activity_weight) * flt(row["facts"]["activity_hours"]), 2)
        row["scores"]["meeting_units"] = round(
            flt(policy.meeting_weight) * flt(row["facts"]["meeting_weekly_avg_hours"]),
            2,
        )
        row["scores"]["event_units"] = round(
            flt(policy.school_event_weight) * flt(row["facts"]["event_weekly_avg_hours"]),
            2,
        )
        row["scores"]["non_teaching_units"] = round(
            row["scores"]["activity_units"] + row["scores"]["meeting_units"] + row["scores"]["event_units"],
            2,
        )
        row["scores"]["total_load_score"] = round(
            row["scores"]["teaching_units"]
            + row["scores"]["student_units"]
            + row["scores"]["activity_units"]
            + row["scores"]["meeting_units"]
            + row["scores"]["event_units"],
            2,
        )
        row["bands"]["load_band"] = _score_band(row["scores"]["total_load_score"], policy)
        rows.append(row)

    rows.sort(
        key=lambda item: (
            -flt(item["scores"]["total_load_score"]),
            item["educator"]["full_name"],
            item["educator"]["employee"],
        )
    )
    return rows, {
        "window": {
            "start_date": str(window_start_date),
            "end_date": str(window_end_date),
            "time_mode": filters["time_mode"],
        }
    }


def _strip_dashboard_rows(rows: list[dict]) -> list[dict]:
    stripped = []
    for row in rows:
        stripped.append(
            {
                "educator": row["educator"],
                "facts": row["facts"],
                "scores": row["scores"],
                "bands": row["bands"],
                "availability": {
                    "free_blocks_count": row["facts"]["free_blocks_count"],
                },
            }
        )
    return stripped


def _build_fairness(rows: list[dict]) -> dict:
    if not rows:
        return {
            "distribution": [],
            "scatter": [],
            "ranked": [],
        }

    scores = [flt(row["scores"]["total_load_score"]) for row in rows]
    max_score = max(scores) if scores else 0
    bucket_size = max(round(max_score / 6.0, 2), 5.0)
    distribution: Counter[str] = Counter()
    for score in scores:
        bucket_start = int(score // bucket_size) * bucket_size
        bucket_end = bucket_start + bucket_size
        label = f"{bucket_start:.0f}-{bucket_end:.0f}"
        distribution[label] += 1

    return {
        "distribution": [{"bucket": bucket, "count": count} for bucket, count in sorted(distribution.items())],
        "scatter": [
            {
                "employee": row["educator"]["employee"],
                "label": row["educator"]["full_name"],
                "teaching_units": row["scores"]["teaching_units"],
                "non_teaching_units": row["scores"]["non_teaching_units"],
                "total_load_score": row["scores"]["total_load_score"],
            }
            for row in rows
        ],
        "ranked": [
            {
                "employee": row["educator"]["employee"],
                "label": row["educator"]["full_name"],
                "school": row["educator"]["school"],
                "total_load_score": row["scores"]["total_load_score"],
                "load_band": row["bands"]["load_band"],
            }
            for row in rows[:20]
        ],
    }


def _build_summary(rows: list[dict], policy) -> tuple[dict, list[dict]]:
    staff_count = len(rows)
    overloaded = sum(1 for row in rows if flt(row["scores"]["total_load_score"]) >= flt(policy.overload_threshold))
    underloaded = sum(1 for row in rows if flt(row["scores"]["total_load_score"]) < flt(policy.underutilized_threshold))
    no_cover = sum(1 for row in rows if cint(row["facts"]["free_blocks_count"]) <= 0)
    avg_teaching = round(mean([flt(row["facts"]["teaching_hours"]) for row in rows]) if rows else 0.0, 2)
    avg_total = round(mean([flt(row["scores"]["total_load_score"]) for row in rows]) if rows else 0.0, 2)

    return (
        {
            "staff_count": staff_count,
            "avg_total_load": avg_total,
            "overloaded_count": overloaded,
            "underloaded_count": underloaded,
            "no_cover_capacity_count": no_cover,
        },
        [
            {"id": "staff_count", "label": "Staff in Scope", "value": staff_count},
            {"id": "avg_teaching", "label": "Avg Weekly Teaching", "value": avg_teaching, "unit": "hrs"},
            {"id": "avg_total", "label": "Avg Total Load", "value": avg_total},
            {"id": "overloaded", "label": "Overloaded", "value": overloaded},
            {"id": "underloaded", "label": "Underloaded", "value": underloaded},
            {"id": "no_cover", "label": "No Free Cover Capacity", "value": no_cover},
        ],
    )


def _build_dataset(filters: dict, user: str) -> dict:
    scope = _resolve_scope(filters, user)
    options = _load_academic_year_options(scope["school_scope"], scope["selected_school"])
    academic_year = _resolve_academic_year(filters, scope, options)
    policy = get_active_policy_for_school(scope["selected_school"])
    rows, meta = _build_rows(filters, scope, academic_year, policy)
    summary, kpis = _build_summary(rows, policy)

    return {
        "policy": _policy_summary(policy),
        "summary": summary,
        "kpis": kpis,
        "rows": rows,
        "fairness": _build_fairness(rows),
        "effective_filters": {
            "school": scope["selected_school"],
            "academic_year": academic_year,
            "time_mode": filters["time_mode"],
            "staff_role": filters.get("staff_role"),
            "search": filters.get("search") or "",
        },
        "meta": meta,
    }


@frappe.whitelist()
def get_academic_load_filter_meta(payload=None):
    user = _ensure_access()
    filters = _normalize_filters(_parse_payload(payload))
    scope = _resolve_scope(filters, user)
    academic_year_options = _load_academic_year_options(scope["school_scope"], scope["selected_school"])
    academic_year = _resolve_academic_year(filters, scope, academic_year_options)
    policy = get_active_policy_for_school(scope["selected_school"])
    student_groups = _load_student_group_options(scope["school_scope"], academic_year)

    schools = frappe.get_all(
        "School",
        filters={"name": ["in", scope["authorized_schools"]]},
        fields=["name", "school_name as label"],
        order_by="lft",
    )

    return {
        "schools": schools,
        "default_school": scope["selected_school"],
        "academic_years": academic_year_options,
        "default_academic_year": academic_year,
        "time_modes": [
            {"value": "current_week", "label": "Current Week"},
            {"value": "next_2_weeks", "label": "Next 2 Weeks"},
            {"value": "this_month", "label": "This Month"},
            {"value": "blended", "label": "Last 30 / Next 14 (Blended)"},
        ],
        "staff_roles": [{"value": role, "label": role} for role in ACADEMIC_ROLE_OPTIONS],
        "student_groups": student_groups,
        "policy": _policy_summary(policy),
    }


@frappe.whitelist()
def get_academic_load_dashboard(payload=None, start=0, page_length=50):
    user = _ensure_access()
    filters = _normalize_filters(_parse_payload(payload))
    payload_key = {
        "filters": filters,
        "start": cint(start),
        "page_length": cint(page_length),
    }
    cache_key = _cache_key("dashboard", user, payload_key)
    cache = frappe.cache()
    if cached := cache.get_value(cache_key):
        try:
            return frappe.parse_json(cached)
        except Exception:
            pass

    dataset = _build_dataset(filters, user)
    rows = dataset["rows"]
    start = max(cint(start), 0)
    page_length = max(cint(page_length or 50), 1)
    response = {
        "policy": dataset["policy"],
        "summary": dataset["summary"],
        "kpis": dataset["kpis"],
        "rows": _strip_dashboard_rows(rows[start : start + page_length]),
        "fairness": dataset["fairness"],
        "effective_filters": dataset["effective_filters"],
        "meta": {
            "total_rows": len(rows),
            **dataset["meta"],
        },
    }
    cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=CACHE_TTL_SECONDS)
    return response


@frappe.whitelist()
def get_academic_load_staff_detail(payload=None, employee=None):
    user = _ensure_access()
    employee = (employee or "").strip()
    if not employee:
        frappe.throw(_("Employee is required."))

    filters = _normalize_filters(_parse_payload(payload))
    cache_key = _cache_key("detail", user, {"filters": filters, "employee": employee})
    cache = frappe.cache()
    if cached := cache.get_value(cache_key):
        try:
            return frappe.parse_json(cached)
        except Exception:
            pass

    dataset = _build_dataset(filters, user)
    match = next((row for row in dataset["rows"] if row["educator"]["employee"] == employee), None)
    if not match:
        frappe.throw(_("Employee is not available in the current Academic Load scope."), frappe.DoesNotExistError)

    timeline = []
    for teaching in match["_detail"]["teaching"].values():
        timeline.append(
            {
                "kind": "teaching",
                "label": teaching.get("student_group_name") or teaching.get("student_group"),
                "hours": round(flt(teaching.get("hours")), 2),
            }
        )
    for activity in match["_detail"]["activities"].values():
        timeline.append(
            {
                "kind": "activity",
                "label": activity.get("student_group_name") or activity.get("student_group"),
                "hours": round(flt(activity.get("hours")), 2),
            }
        )
    for meeting in match["_detail"]["meetings"]:
        timeline.append(
            {
                "kind": "meeting",
                "label": meeting.get("meeting_name") or meeting.get("name"),
                "from_datetime": meeting.get("from_datetime"),
                "to_datetime": meeting.get("to_datetime"),
                "hours": meeting.get("hours"),
            }
        )
    for event in match["_detail"]["events"]:
        timeline.append(
            {
                "kind": "event",
                "label": event.get("subject") or event.get("name"),
                "from_datetime": event.get("starts_on"),
                "to_datetime": event.get("ends_on"),
                "hours": event.get("hours"),
            }
        )

    detail_payload = {
        "policy": dataset["policy"],
        "educator": match["educator"],
        "facts": match["facts"],
        "scores": match["scores"],
        "bands": match["bands"],
        "breakdown": {
            "teaching": sorted(
                match["_detail"]["teaching"].values(),
                key=lambda row: row.get("student_group_name") or row.get("student_group"),
            ),
            "activities": sorted(
                match["_detail"]["activities"].values(),
                key=lambda row: row.get("student_group_name") or row.get("student_group"),
            ),
            "meetings": sorted(match["_detail"]["meetings"], key=lambda row: row.get("from_datetime") or ""),
            "events": sorted(match["_detail"]["events"], key=lambda row: row.get("starts_on") or ""),
            "timeline": timeline[:30],
            "assignment_notes": [
                _("Student adjustment uses a divisor of {0}.").format(
                    flt(get_active_policy_for_school(dataset["policy"]["school"]).student_ratio_divisor)
                ),
                _("Cover suitability is ranked from exact group fit, then course/program fit, then current load."),
            ],
        },
    }
    cache.set_value(cache_key, frappe.as_json(detail_payload), expires_in_sec=CACHE_TTL_SECONDS)
    return detail_payload


@frappe.whitelist()
def get_academic_load_cover_candidates(payload=None, student_group=None, from_datetime=None, to_datetime=None):
    user = _ensure_access()
    filters = _normalize_filters(_parse_payload(payload))
    student_group = (student_group or filters.get("student_group") or "").strip()
    from_datetime = from_datetime or filters.get("from_datetime")
    to_datetime = to_datetime or filters.get("to_datetime")

    if not student_group or not from_datetime or not to_datetime:
        frappe.throw(_("Student Group, From Datetime, and To Datetime are required."))

    slot_start = get_datetime(from_datetime)
    slot_end = get_datetime(to_datetime)
    if slot_end <= slot_start:
        frappe.throw(_("To Datetime must be later than From Datetime."))

    cache_key = _cache_key(
        "cover",
        user,
        {
            "filters": filters,
            "student_group": student_group,
            "from_datetime": _serialize_datetime(slot_start),
            "to_datetime": _serialize_datetime(slot_end),
        },
    )
    cache = frappe.cache()
    if cached := cache.get_value(cache_key):
        try:
            return frappe.parse_json(cached)
        except Exception:
            pass

    dataset = _build_dataset(filters, user)
    scope = _resolve_scope(filters, user)
    target_group = frappe.db.get_value(
        "Student Group",
        student_group,
        ["name", "student_group_name", "school", "course", "program", "academic_year"],
        as_dict=True,
    )
    if not target_group:
        frappe.throw(_("Student Group not found."), frappe.DoesNotExistError)
    if target_group.school not in scope["school_scope"]:
        frappe.throw(_("Student Group is outside the current school scope."), frappe.PermissionError)

    experience_rows = frappe.db.sql(
        """
        SELECT
            sgi.employee,
            sg.name AS student_group,
            sg.course,
            sg.program
        FROM `tabStudent Group Instructor` sgi
        JOIN `tabStudent Group` sg ON sg.name = sgi.parent
        WHERE sgi.employee IN %(employees)s
          AND sg.school IN %(schools)s
          AND (sg.status IS NULL OR sg.status = 'Active')
        """,
        {
            "employees": tuple(row["educator"]["employee"] for row in dataset["rows"]) or ("",),
            "schools": tuple(scope["school_scope"]),
        },
        as_dict=True,
    )
    experience_by_employee: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"groups": set(), "courses": set(), "programs": set()}
    )
    for row in experience_rows:
        employee = row.get("employee")
        if not employee:
            continue
        if row.get("student_group"):
            experience_by_employee[employee]["groups"].add(row["student_group"])
        if row.get("course"):
            experience_by_employee[employee]["courses"].add(row["course"])
        if row.get("program"):
            experience_by_employee[employee]["programs"].add(row["program"])

    hard_booking_rows = _load_hard_booking_rows(
        [row["educator"]["employee"] for row in dataset["rows"]],
        slot_start,
        slot_end,
    )
    busy_by_employee: dict[str, list[dict]] = defaultdict(list)
    for row in hard_booking_rows:
        busy_by_employee[row["employee"]].append(row)

    candidates = []
    for row in dataset["rows"]:
        employee = row["educator"]["employee"]
        conflicts = busy_by_employee.get(employee, [])
        if conflicts:
            candidates.append(
                {
                    "educator": row["educator"],
                    "cover_suitability": "Unavailable",
                    "fit_rank": None,
                    "total_load_score": row["scores"]["total_load_score"],
                    "reasons": [
                        _("Conflicting hard booking in the requested block."),
                    ],
                }
            )
            continue

        fit_rank = 3
        reasons = [_("No current exact match found; ranking falls back to lower current load.")]
        experience = experience_by_employee.get(employee, {})
        if student_group in experience.get("groups", set()):
            fit_rank = 0
            reasons = [_("Currently assigned to the same student group.")]
        elif target_group.get("course") and target_group["course"] in experience.get("courses", set()):
            fit_rank = 1
            reasons = [_("Teaches the same course within the current scope.")]
        elif target_group.get("program") and target_group["program"] in experience.get("programs", set()):
            fit_rank = 2
            reasons = [_("Works in the same program within the current scope.")]

        candidates.append(
            {
                "educator": row["educator"],
                "cover_suitability": _cover_label(fit_rank),
                "fit_rank": fit_rank,
                "total_load_score": row["scores"]["total_load_score"],
                "free_blocks_count": row["facts"]["free_blocks_count"],
                "reasons": reasons,
            }
        )

    candidates.sort(
        key=lambda item: (
            9 if item["fit_rank"] is None else item["fit_rank"],
            flt(item["total_load_score"]),
            item["educator"]["full_name"],
            item["educator"]["employee"],
        )
    )
    response = {
        "student_group": {
            "name": target_group.get("name"),
            "label": target_group.get("student_group_name") or target_group.get("name"),
            "course": target_group.get("course"),
            "program": target_group.get("program"),
            "school": target_group.get("school"),
        },
        "window": {
            "from_datetime": _serialize_datetime(slot_start),
            "to_datetime": _serialize_datetime(slot_end),
        },
        "rows": candidates,
    }
    cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=CACHE_TTL_SECONDS)
    return response
