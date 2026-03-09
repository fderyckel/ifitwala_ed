# ifitwala_ed/api/calendar_prefs.py

from __future__ import annotations

from typing import List, Optional

import frappe
from frappe.utils import getdate, now_datetime

from ifitwala_ed.api.calendar_core import (
    _resolve_employee_for_user,
    _resolve_window,
    _system_tzinfo,
    _time_to_str,
)
from ifitwala_ed.api.calendar_details import _resolve_sg_booking_context
from ifitwala_ed.api.calendar_staff_feed import _collect_staff_holiday_events, _collect_student_group_events
from ifitwala_ed.schedule.schedule_utils import get_weekend_days_for_calendar
from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window
from ifitwala_ed.utilities.school_tree import get_school_lineage


def debug_staff_calendar_window(from_datetime: Optional[str] = None, to_datetime: Optional[str] = None):
    """
    Lightweight debug endpoint: returns detected instructor ids, matched
    student groups, and a small sample of events for the current user.
    Useful for quick browser testing.
    """
    user = frappe.session.user
    tzinfo = _system_tzinfo()
    start, end = _resolve_window(from_datetime, to_datetime, tzinfo)

    instr = set(
        frappe.get_all("Instructor", filters={"linked_user_id": user}, pluck="name", ignore_permissions=True) or []
    )
    employee_row = _resolve_employee_for_user(user, fields=["name"])
    emp = (employee_row or {}).get("name")
    if emp:
        instr.update(
            frappe.get_all("Instructor", filters={"employee": emp}, pluck="name", ignore_permissions=True) or []
        )

    sgi = set(
        frappe.get_all(
            "Student Group Instructor",
            filters={"parenttype": "Student Group", "instructor": ["in", list(instr) or [""]]},
            pluck="parent",
            ignore_permissions=True,
        )
        or []
    )

    sample = _collect_student_group_events(user, start, end, tzinfo)[:10]
    holiday_events = _collect_staff_holiday_events(
        user,
        start,
        end,
        tzinfo,
        employee_id=emp,
    )
    holiday_sample = holiday_events[:5]
    booking_samples = []
    if emp and frappe.db.table_exists("Employee Booking"):
        booking_rows = frappe.get_all(
            "Employee Booking",
            filters={
                "employee": emp,
                "source_doctype": "Student Group",
                "docstatus": ["<", 2],
                "from_datetime": ["<", end],
                "to_datetime": [">", start],
            },
            fields=["name", "source_name", "from_datetime", "to_datetime"],
            order_by="from_datetime desc",
            limit=5,
            ignore_permissions=True,
        )
        for row in booking_rows:
            context = _resolve_sg_booking_context(f"sg-booking::{row.name}", tzinfo, debug=True)
            booking_samples.append(
                {
                    "booking": row.name,
                    "student_group": row.source_name,
                    "from": row.from_datetime,
                    "to": row.to_datetime,
                    "rotation_day": context.get("rotation_day"),
                    "block_number": context.get("block_number"),
                    "location": context.get("location"),
                    "resolution": context.get("_debug"),
                }
            )

    return {
        "user": user,
        "system_tz": tzinfo.zone,
        "window": {"from": start.isoformat(), "to": end.isoformat()},
        "instructor_ids": sorted(instr),
        "sg_instructor_groups": sorted(sgi),
        "sample_events": [e.as_dict() for e in sample],
        "staff_holiday_count": len(holiday_events),
        "staff_holiday_sample": [e.as_dict() for e in holiday_sample],
        "booking_samples": booking_samples,
    }


def get_portal_calendar_prefs(from_datetime: Optional[str] = None, to_datetime: Optional[str] = None):
    """
    Return portal calendar preferences for the logged-in employee:
    - timezone (System Settings)
    - weekendDays (FullCalendar day indices to hide when weekends are off)
    - defaultSlotMin/Max (from School settings)
    """
    user = frappe.session.user
    tzinfo = _system_tzinfo()

    employee_row = _resolve_employee_for_user(user, fields=["school"])
    school = (employee_row or {}).get("school") or frappe.db.get_value("Instructor", {"linked_user_id": user}, "school")

    calendar_name = None
    if school:
        today_value = getdate(now_datetime())
        calendar_rows = resolve_school_calendars_for_window(school, today_value, today_value)
        if calendar_rows:
            calendar_name = calendar_rows[0].get("name")

    default_min = "07:00:00"
    default_max = "17:00:00"

    # Avoid per-school db hits by loading lineage settings in a single query.
    if school:
        lineage = get_school_lineage(school)
        school_rows = (
            frappe.get_all(
                "School",
                filters={"name": ["in", lineage]},
                fields=[
                    "name",
                    "current_school_calendar",
                    "portal_calendar_start_time",
                    "portal_calendar_end_time",
                ],
                limit_page_length=max(len(lineage), 1),
            )
            if lineage
            else []
        )
        school_by_name = {row.name: row for row in school_rows}

        if not calendar_name:
            for school_name in lineage:
                row = school_by_name.get(school_name)
                candidate = row.current_school_calendar if row else None
                if candidate:
                    calendar_name = candidate
                    break

        for school_name in lineage:
            row = school_by_name.get(school_name)
            if not row:
                continue
            start_raw = row.portal_calendar_start_time
            end_raw = row.portal_calendar_end_time
            if not start_raw and not end_raw:
                continue
            default_min = _time_to_str(start_raw, default_min)
            default_max = _time_to_str(end_raw, default_max)
            break

    weekend_fc_days: List[int] = (
        get_weekend_days_for_calendar(calendar_name) if calendar_name else get_weekend_days_for_calendar(None)
    )

    return {
        "timezone": tzinfo.zone,
        "weekendDays": weekend_fc_days,
        "defaultSlotMin": default_min,
        "defaultSlotMax": default_max,
    }
