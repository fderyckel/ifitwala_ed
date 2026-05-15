# ifitwala_ed/api/calendar_prefs.py

from __future__ import annotations

from typing import List, Optional

import frappe
from frappe.utils import getdate, now_datetime

from ifitwala_ed.api.calendar_core import (
    _resolve_employee_for_user,
    _system_tzinfo,
    _time_to_str,
)
from ifitwala_ed.schedule.schedule_utils import get_weekend_days_for_calendar
from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window
from ifitwala_ed.utilities.school_tree import get_school_lineage


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
                limit=max(len(lineage), 1),
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
