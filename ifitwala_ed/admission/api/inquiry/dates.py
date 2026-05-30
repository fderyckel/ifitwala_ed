# ifitwala_ed/admission/api/inquiry/dates.py

from __future__ import annotations

import frappe
from frappe.utils import add_days, getdate, nowdate


def _ay_bounds(academic_year: str):
    if not academic_year:
        return None, None
    start, end = frappe.db.get_value("Academic Year", academic_year, ["year_start_date", "year_end_date"])
    return start, end


PRESET_ALIASES = {
    "last_7": "7d",
    "last_30": "30d",
    "last_90": "90d",
    "ytd": "year",
    "all_time": "all",
}


def _normalize_preset(value: str | None):
    if not value:
        return None
    preset = value.strip().lower()
    return PRESET_ALIASES.get(preset, preset)


def _preset_bounds(preset: str):
    preset = _normalize_preset(preset)
    if not preset:
        return None, None

    today = getdate(nowdate())
    if preset == "7d":
        return add_days(today, -7), today
    if preset == "30d":
        return add_days(today, -30), today
    if preset == "90d":
        return add_days(today, -90), today
    if preset == "year":
        return getdate(f"{today.year}-01-01"), today
    if preset == "all":
        return getdate("1900-01-01"), today
    return None, None


def _resolve_window(filters: dict):
    mode = (filters.get("date_mode") or "").strip()
    preset = filters.get("date_preset")
    fd = filters.get("from_date")
    td = filters.get("to_date")
    ay = filters.get("academic_year")

    if mode == "preset" and preset:
        fd, td = _preset_bounds(preset)
    elif mode == "academic_year" and ay:
        fd, td = _ay_bounds(ay)
    elif mode == "custom" and fd and td:
        fd, td = fd, td
    else:
        td = getdate(nowdate())
        fd = add_days(td, -365)

    if not fd or not td:
        td = getdate(nowdate())
        fd = add_days(td, -365)

    return getdate(fd), getdate(td)
