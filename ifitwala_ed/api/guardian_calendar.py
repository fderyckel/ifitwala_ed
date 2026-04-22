# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime

from ifitwala_ed.api.guardian_communications import (
    _fetch_guardian_school_events,
    _ordered_matched_children,
    _resolve_guardian_communication_context,
    _validate_selected_student,
)
from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window

DEFAULT_HOLIDAY_COLOR = "#dc2626"
DEFAULT_SCHOOL_EVENT_COLOR = "#2563eb"


def _serialize_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            return value
    return value


def _coerce_month_start(month_start: str | None) -> date:
    raw_value = month_start or now_datetime().date()
    try:
        resolved = getdate(raw_value)
    except Exception:
        frappe.throw(_("Invalid month_start. Expected YYYY-MM-DD."))
    return resolved.replace(day=1)


def _month_window(month_start: date) -> tuple[date, date]:
    if month_start.month == 12:
        next_month = date(month_start.year + 1, 1, 1)
    else:
        next_month = date(month_start.year, month_start.month + 1, 1)
    return month_start, next_month - timedelta(days=1)


def _school_filter_options(
    context: dict[str, Any],
    *,
    selected_student: str | None = None,
) -> list[dict[str, str]]:
    relevant_students = [selected_student] if selected_student else list(context.get("student_names") or [])
    schools = sorted(
        {
            child.get("school")
            for child in (context.get("children") or [])
            if child.get("student") in relevant_students and child.get("school")
        }
    )
    return [{"school": school_name, "label": school_name} for school_name in schools]


def _validate_selected_school(
    school: str | None,
    context: dict[str, Any],
    *,
    selected_student: str | None = None,
) -> str:
    school_name = str(school or "").strip()
    if not school_name:
        return ""

    valid_schools = {row["school"] for row in _school_filter_options(context, selected_student=selected_student)}
    if school_name not in valid_schools:
        frappe.throw(_("This school is not available in your guardian scope."), frappe.PermissionError)
    return school_name


def _relevant_students_for_holidays(
    context: dict[str, Any],
    *,
    selected_student: str | None = None,
    selected_school: str | None = None,
) -> list[str]:
    if selected_student:
        students = [selected_student]
    else:
        students = list(context.get("student_names") or [])

    school_name = str(selected_school or "").strip()
    if not school_name:
        return [student for student in students if student]

    return [
        student
        for student in students
        if school_name in set((context.get("student_school_names") or {}).get(student) or [])
    ]


def _fetch_guardian_holiday_items(
    context: dict[str, Any],
    *,
    month_start: date,
    month_end: date,
    selected_student: str | None = None,
    selected_school: str | None = None,
) -> list[dict[str, Any]]:
    relevant_students = _relevant_students_for_holidays(
        context,
        selected_student=selected_student,
        selected_school=selected_school,
    )
    if not relevant_students:
        return []

    calendars_by_name: dict[str, dict[str, Any]] = {}
    students_by_calendar: dict[str, set[str]] = defaultdict(set)

    for student in relevant_students:
        for school_name in sorted(set((context.get("student_school_names") or {}).get(student) or [])):
            if selected_school and school_name != selected_school:
                continue
            for calendar_row in resolve_school_calendars_for_window(school_name, month_start, month_end):
                calendar_name = str(calendar_row.get("name") or "").strip()
                if not calendar_name:
                    continue
                calendars_by_name[calendar_name] = calendar_row
                students_by_calendar[calendar_name].add(student)

    calendar_names = sorted(calendars_by_name.keys())
    if not calendar_names:
        return []

    holiday_rows = frappe.get_all(
        "School Calendar Holidays",
        filters={
            "parent": ["in", calendar_names],
            "holiday_date": ["between", [month_start, month_end]],
            "weekly_off": 0,
        },
        fields=["parent", "holiday_date", "description", "color"],
        order_by="holiday_date asc, idx asc",
        limit=max(len(calendar_names) * 40, 200),
    )

    items: list[dict[str, Any]] = []
    for row in holiday_rows or []:
        calendar_name = str(row.get("parent") or "").strip()
        holiday_date = row.get("holiday_date")
        if not calendar_name or not holiday_date:
            continue

        matched_children = _ordered_matched_children(
            context,
            set(students_by_calendar.get(calendar_name) or set()),
        )
        if not matched_children:
            continue

        child_schools = sorted({child.get("school") for child in matched_children if child.get("school")})
        items.append(
            {
                "item_id": f"holiday::{calendar_name}::{holiday_date}",
                "kind": "holiday",
                "title": row.get("description") or _("School Holiday"),
                "start": _serialize_scalar(holiday_date),
                "end": _serialize_scalar(holiday_date),
                "all_day": True,
                "color": row.get("color") or DEFAULT_HOLIDAY_COLOR,
                "school": child_schools[0] if len(child_schools) == 1 else None,
                "matched_children": matched_children,
                "description": row.get("description") or "",
                "event_category": None,
                "open_target": None,
            }
        )

    return items


def _serialize_school_event_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for item in items:
        school_event = item.get("school_event") or {}
        serialized.append(
            {
                "item_id": item.get("item_id"),
                "kind": "school_event",
                "title": school_event.get("subject") or _("School Event"),
                "start": school_event.get("starts_on"),
                "end": school_event.get("ends_on") or school_event.get("starts_on"),
                "all_day": bool(school_event.get("all_day")),
                "color": DEFAULT_SCHOOL_EVENT_COLOR,
                "school": school_event.get("school"),
                "matched_children": item.get("matched_children") or [],
                "description": school_event.get("snippet") or school_event.get("description") or "",
                "event_category": school_event.get("event_category"),
                "open_target": {
                    "type": "school-event",
                    "name": school_event.get("name"),
                },
            }
        )
    return serialized


def _sort_calendar_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kind_order = {"holiday": 0, "school_event": 1}
    return sorted(
        items,
        key=lambda item: (
            kind_order.get(str(item.get("kind") or ""), 99),
            str(item.get("start") or item.get("end") or ""),
            str(item.get("title") or ""),
            str(item.get("item_id") or ""),
        ),
    )


@frappe.whitelist()
def get_guardian_calendar_overlay(
    month_start: str | None = None,
    student: str | None = None,
    school: str | None = None,
    include_holidays: int = 1,
    include_school_events: int = 1,
) -> dict[str, Any]:
    context = _resolve_guardian_communication_context()
    selected_student = _validate_selected_student(student, context)
    selected_school = _validate_selected_school(school, context, selected_student=selected_student or None)

    resolved_month_start = _coerce_month_start(month_start)
    resolved_month_start, resolved_month_end = _month_window(resolved_month_start)

    include_holiday_items = int(include_holidays or 0) == 1
    include_school_event_items = int(include_school_events or 0) == 1

    items: list[dict[str, Any]] = []
    if include_holiday_items:
        items.extend(
            _fetch_guardian_holiday_items(
                context,
                month_start=resolved_month_start,
                month_end=resolved_month_end,
                selected_student=selected_student or None,
                selected_school=selected_school or None,
            )
        )
    if include_school_event_items:
        items.extend(
            _serialize_school_event_items(
                _fetch_guardian_school_events(
                    context,
                    selected_student=selected_student or None,
                    selected_school=selected_school or None,
                    start_date=resolved_month_start,
                    end_date=resolved_month_end,
                )
            )
        )

    items = _sort_calendar_items(items)

    return {
        "meta": {
            "generated_at": _serialize_scalar(now_datetime()),
            "timezone": frappe.utils.get_system_timezone(),
            "month_start": _serialize_scalar(resolved_month_start),
            "month_end": _serialize_scalar(resolved_month_end),
            "filters": {
                "student": selected_student or None,
                "school": selected_school or None,
                "include_holidays": include_holiday_items,
                "include_school_events": include_school_event_items,
            },
        },
        "family": {
            "children": context.get("children") or [],
        },
        "filter_options": {
            "students": context.get("children") or [],
            "schools": _school_filter_options(context, selected_student=selected_student or None),
        },
        "summary": {
            "holiday_count": sum(1 for item in items if item.get("kind") == "holiday"),
            "school_event_count": sum(1 for item in items if item.get("kind") == "school_event"),
        },
        "items": items,
    }
