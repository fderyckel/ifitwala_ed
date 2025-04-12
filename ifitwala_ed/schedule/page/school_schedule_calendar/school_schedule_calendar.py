# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, format_time
from datetime import timedelta

@frappe.whitelist()
def get_schedule_events():
    schedules = frappe.get_all("School Schedule", fields=["name", "rotation_days", "include_holidays_in_rotation", "school_calendar"])
    all_events = []

    for sched in schedules:
        calendar = frappe.get_doc("School Calendar", sched.school_calendar)
        ay = frappe.get_doc("Academic Year", calendar.academic_year)
        holidays = {getdate(h.holiday_date) for h in calendar.holidays}
        rotation_days = frappe.get_all("School Schedule Day", filters={"parent": sched.name}, fields=["rotation_day", "number_of_blocks"])
        blocks = frappe.get_all("School Schedule Block", filters={"parent": sched.name}, fields=["rotation_day", "block_number", "from_time", "to_time", "block_type"])

        # Group blocks by rotation day
        block_map = {}
        for b in blocks:
            block_map.setdefault(b.rotation_day, []).append(b)

        date_cursor = getdate(ay.year_start_date)
        end_date = getdate(ay.year_end_date)
        rotation_index = 0
        total_rotation_days = sched.rotation_days

        while date_cursor <= end_date:
            is_holiday = date_cursor in holidays

            if is_holiday and not sched.include_holidays_in_rotation:
                date_cursor += timedelta(days=1)
                continue

            rotation_day_num = (rotation_index % total_rotation_days) + 1
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
