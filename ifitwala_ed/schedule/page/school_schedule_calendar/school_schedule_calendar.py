# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, format_time
from datetime import timedelta

@frappe.whitelist()
def get_schedule_events(school=None):
    filters = {}
    if school:
        filters["school"] = school

    schedules = frappe.get_all("School Schedule", filters=filters,
        fields=["name", "rotation_days", "include_holidays_in_rotation", "school_calendar", "school"])

    all_events = []

    for sched in schedules:
        calendar = frappe.get_doc("School Calendar", sched.school_calendar)
        ay = frappe.get_doc("Academic Year", calendar.academic_year)
        holidays = {getdate(h.holiday_date) for h in calendar.holidays if not h.weekly_off} 
        weekends = {getdate(h.holiday_date) for h in calendar.holidays if h.weekly_off}

        blocks = frappe.get_all("School Schedule Block", filters={"parent": sched.name}, fields=["rotation_day", "block_number", "from_time", "to_time", "block_type"])

        total_rotation_days = sched.rotation_days

        # Skip if invalid configuration
        if not total_rotation_days or total_rotation_days == 0:
            frappe.logger().warning(f"[School Schedule Calendar] Skipping schedule '{sched.name}' with 0 rotation days.")
            continue

        # Group blocks by rotation day
        block_map = {}
        for b in blocks:
            block_map.setdefault(b.rotation_day, []).append(b)

        # Fetch school-level default colors
        school_colors = frappe.db.get_value("School", sched.school, ["weekend_color", "break_color"], as_dict=True)

        for h in calendar.holidays:
            date_str = str(h.holiday_date)
            desc = h.description or ("Weekly Off" if h.weekly_off else "Holiday")
            color = h.color

            # Fallback to School default colors
            if not color:
                color = school_colors.weekend_color if h.weekly_off else school_colors.break_color

            all_events.append({
                "title": desc,
                "start": date_str,
                "allDay": True,
                "display": "background",
                "color": color or "#e0e0e0"  # Fallback to light gray if really nothing is set
            })    

        date_cursor = getdate(ay.year_start_date)
        end_date = getdate(ay.year_end_date)
        rotation_index = 0

        while date_cursor <= end_date:
            is_holiday = getdate(date_cursor) in holidays
            is_weekend = getdate(date_cursor) in weekends
            if is_holiday and not sched.include_holidays_in_rotation:
                date_cursor += timedelta(days=1)
                continue

            # Always skip weekends regardless of holiday config
            if is_weekend: 
                date_cursor += timedelta(days=1)
                continue

            offset = (sched.first_day_rotation_day or 1) - 1
            rotation_day_num = ((rotation_index + offset) % total_rotation_days) + 1

            day_blocks = block_map.get(rotation_day_num, [])

            for block in sorted(day_blocks, key=lambda b: b.block_number):
                color_map = {
                    "Course": "#4caf50",
                    "Activity": "#2196f3",
                    "Recess": "#ff9800",
                    "Assembly": "#9c27b0"
                }
                event = {
                    "title": f"Day {rotation_day_num} • Block {block.block_number} • {block.block_type}",
                    "start": f"{date_cursor}T{format_time(block.from_time) if block.from_time else '08:00'}",
                    "end": f"{date_cursor}T{format_time(block.to_time) if block.to_time else '09:00'}",
                    "color": color_map.get(block.block_type, "#9e9e9e")
                }
                all_events.append(event)

            date_cursor += timedelta(days=1)
            rotation_index += 1

    return all_events

