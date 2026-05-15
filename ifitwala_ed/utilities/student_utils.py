# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from calendar import month_name
from datetime import date

import frappe
from frappe import _
from frappe.utils import getdate, today


def get_basic_student_info(student_id: str, *, include_dob: bool = False) -> dict:
    if not student_id:
        frappe.throw(_("Student ID is required"))

    student = frappe.db.get_value(
        "Student",
        student_id,
        ["student_full_name", "student_preferred_name", "student_gender", "student_date_of_birth", "student_image"],
        as_dict=True,
    )

    if not student:
        frappe.throw(_("Student not found"))

    student["student_age"] = format_student_age(student.get("student_date_of_birth"))
    if not include_dob:
        student.pop("student_date_of_birth", None)
    return student


def _coerce_date(value):
    if not value:
        return None
    try:
        return getdate(value)
    except Exception:
        return None


def _format_age_part(value: int, unit: str) -> str:
    if unit == "year":
        return (
            _("{count} year").format(count=value)
            if value == 1
            else _("{count} years").format(count=value)
        )
    if unit == "month":
        return (
            _("{count} month").format(count=value)
            if value == 1
            else _("{count} months").format(count=value)
        )
    return (
        _("{count} day").format(count=value)
        if value == 1
        else _("{count} days").format(count=value)
    )


def get_student_age_years(student_date_of_birth, reference_date=None) -> int | None:
    birthdate = _coerce_date(student_date_of_birth)
    reference = _coerce_date(reference_date) or getdate(today())
    if not birthdate or birthdate > reference:
        return None
    years = reference.year - birthdate.year - (
        (reference.month, reference.day) < (birthdate.month, birthdate.day)
    )
    return max(years, 0)


def format_student_age(student_date_of_birth, reference_date=None) -> str:
    birthdate = _coerce_date(student_date_of_birth)
    reference = _coerce_date(reference_date) or getdate(today())
    if not birthdate or birthdate > reference:
        return ""

    years = reference.year - birthdate.year
    months = reference.month - birthdate.month
    if reference.day < birthdate.day:
        months -= 1
    if months < 0:
        years -= 1
        months += 12

    parts = []
    if years:
        parts.append(_format_age_part(years, "year"))
    if months:
        parts.append(_format_age_part(months, "month"))
    if not parts:
        parts.append(_format_age_part(max((reference - birthdate).days, 0), "day"))
    return ", ".join(parts)


def _birthday_for_year(birthdate, year: int):
    try:
        return date(year, birthdate.month, birthdate.day)
    except ValueError:
        return date(year, 2, 28)


def get_birthday_context(student_date_of_birth, *, window_days: int = 5, reference_date=None) -> dict:
    birthdate = _coerce_date(student_date_of_birth)
    reference = _coerce_date(reference_date) or getdate(today())
    if not birthdate or birthdate > reference:
        return {
            "birthday_in_window": False,
            "birthday_today": False,
            "birthday_label": "",
        }

    candidates = [
        _birthday_for_year(birthdate, reference.year - 1),
        _birthday_for_year(birthdate, reference.year),
        _birthday_for_year(birthdate, reference.year + 1),
    ]
    target = min(candidates, key=lambda candidate: abs((candidate - reference).days))
    diff_days = (target - reference).days
    birthday_today = diff_days == 0
    return {
        "birthday_in_window": abs(diff_days) <= window_days,
        "birthday_today": birthday_today,
        "birthday_label": _("Today") if birthday_today else f"{month_name[target.month]} {target.day}",
    }
