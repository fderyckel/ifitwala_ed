# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from datetime import timedelta

import frappe
from frappe.utils import add_days, format_time, getdate


@frappe.whitelist()
def get_schedule_events(school: str | None = None, academic_year: str | None = None):
    """
    Return FullCalendar-compatible events for all School Schedules
    (optionally filtered by school and/or academic_year).
    """
    filters = {}
    if school:
        filters["school"] = school

    schedules = frappe.get_all(
        "School Schedule",
        filters=filters,
        fields=[
            "name",
            "rotation_days",
            "include_holidays_in_rotation",
            "school_calendar",
            "school",
            "first_day_rotation_day",
        ],
    )

    all_events: list[dict] = []

    for sched in schedules:
        # School Calendar + AY for the schedule
        calendar = frappe.get_doc("School Calendar", sched.school_calendar)
        ay = frappe.get_doc("Academic Year", calendar.academic_year)

        # If the client passed academic_year, skip non-matching schedules
        if academic_year and str(ay.name) != str(academic_year):
            continue

        # Build quick lookup sets for holidays & weekend/weekly off
        holidays = {getdate(h.holiday_date) for h in calendar.holidays if not h.weekly_off}
        weekends = {getdate(h.holiday_date) for h in calendar.holidays if h.weekly_off}

        # All blocks for this schedule
        blocks = frappe.get_all(
            "School Schedule Block",
            filters={"parent": sched.name},
            fields=["rotation_day", "block_number", "from_time", "to_time", "block_type"],
        )

        total_rotation_days = int(sched.rotation_days or 0)
        if total_rotation_days <= 0:
            frappe.logger().warning(
                f"[School Schedule Calendar] Skipping schedule '{sched.name}' with 0 rotation days."
            )
            continue

        # Group blocks by rotation day for fast lookup
        block_map: dict[int, list] = {}
        for b in blocks:
            block_map.setdefault(int(b.rotation_day), []).append(b)

        # Fetch school-level default colors (guard if fields are missing)
        school_colors = (
            frappe.db.get_value("School", sched.school, ["weekend_color", "break_color"], as_dict=True) or {}
        )

        # Background events for holidays and weekly offs
        for h in calendar.holidays:
            date_str = str(h.holiday_date)
            desc = h.description or ("Weekly Off" if h.weekly_off else "Holiday")
            color = h.color
            if not color:
                color = school_colors.get("weekend_color") if h.weekly_off else school_colors.get("break_color")

            all_events.append(
                {
                    "title": desc,
                    "start": date_str,
                    "allDay": True,
                    "display": "background",
                    "color": color or "#e0e0e0",  # final fallback
                }
            )

        # Walk the academic year date range and place rotation blocks
        date_cursor = getdate(ay.year_start_date)
        end_date = getdate(ay.year_end_date)
        rotation_index = 0  # increments by 1 per day, possibly including holidays

        while date_cursor <= end_date:
            is_holiday = date_cursor in holidays
            is_weekend = date_cursor in weekends

            # Skip weekends entirely (no rotation increment)
            if is_weekend:
                date_cursor = add_days(date_cursor, 1)
                continue

            # On holidays, optionally advance rotation (per schedule setting), but no blocks
            if is_holiday:
                date_cursor += timedelta(days=1)
                if sched.include_holidays_in_rotation:
                    rotation_index += 1
                continue

            # Compute rotation day number (1..total_rotation_days)
            offset = int(sched.first_day_rotation_day or 1) - 1
            rotation_day_num = ((rotation_index + offset) % total_rotation_days) + 1

            # Emit events for the day's blocks
            day_blocks = block_map.get(rotation_day_num, [])
            color_map = {
                "Course": "#4caf50",
                "Activity": "#2196f3",
                "Recess": "#ff9800",
                "Assembly": "#9c27b0",
            }

            for block in sorted(day_blocks, key=lambda b: int(b.block_number or 0)):
                start_time = format_time(block.from_time) if block.from_time else "08:00"
                end_time = format_time(block.to_time) if block.to_time else "09:00"

                all_events.append(
                    {
                        "title": f"Day {rotation_day_num} • Block {block.block_number} • {block.block_type}",
                        "start": f"{date_cursor}T{start_time}",
                        "end": f"{date_cursor}T{end_time}",
                        "color": color_map.get(block.block_type, "#9e9e9e"),
                    }
                )

            # Advance to next day and rotation
            date_cursor += timedelta(days=1)
            rotation_index += 1

    return all_events
