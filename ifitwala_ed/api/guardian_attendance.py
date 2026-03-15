# ifitwala_ed/api/guardian_attendance.py

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime

from ifitwala_ed.api.guardian_home import _coerce_time, _resolve_guardian_scope


@frappe.whitelist()
def get_guardian_attendance_snapshot(
    student: str | None = None,
    days: int | str = 60,
) -> dict[str, Any]:
    selected_student = (student or "").strip()
    window_days = _coerce_days(days)
    user = frappe.session.user
    guardian_name, children = _resolve_guardian_scope(user)

    allowed_students = [child.get("student") for child in children if child.get("student")]
    allowed_student_set = set(allowed_students)
    if selected_student and selected_student not in allowed_student_set:
        frappe.throw(_("This student is not available in your guardian scope."), frappe.PermissionError)

    scoped_students = [selected_student] if selected_student else allowed_students
    child_name_map = {
        child.get("student"): (child.get("full_name") or child.get("student") or "")
        for child in children
        if child.get("student")
    }
    student_rows, counts = _build_attendance_students(
        student_names=scoped_students,
        days=window_days,
        child_name_map=child_name_map,
    )

    anchor = frappe.utils.getdate()
    window_start = add_days(anchor, -(window_days - 1))
    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "guardian": {"name": guardian_name},
            "filters": {
                "student": selected_student or "",
                "days": window_days,
                "start_date": window_start.isoformat(),
                "end_date": anchor.isoformat(),
            },
        },
        "family": {"children": children},
        "counts": counts,
        "students": student_rows,
    }


def _coerce_days(days: int | str) -> int:
    try:
        value = int(days or 60)
    except Exception:
        frappe.throw(_("Invalid days."))
    if value < 1 or value > 120:
        frappe.throw(_("days must be between 1 and 120."))
    return value


def _build_attendance_students(
    *,
    student_names: list[str],
    days: int,
    child_name_map: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    empty_counts = {
        "tracked_days": 0,
        "present_days": 0,
        "late_days": 0,
        "absence_days": 0,
    }
    if not student_names:
        return [], empty_counts

    anchor = frappe.utils.getdate()
    window_start = add_days(anchor, -(days - 1))
    rows = frappe.get_all(
        "Student Attendance",
        filters={
            "student": ["in", student_names],
            "attendance_date": ["between", [window_start, anchor]],
        },
        fields=[
            "name",
            "student",
            "attendance_date",
            "attendance_time",
            "attendance_code",
            "whole_day",
            "course",
            "location",
            "remark",
        ],
        order_by="student asc, attendance_date asc, whole_day desc, attendance_time asc, modified desc",
        limit_page_length=10000,
    )

    code_names = sorted({row.get("attendance_code") for row in rows if row.get("attendance_code")})
    code_rows = frappe.get_all(
        "Student Attendance Code",
        filters={"name": ["in", code_names]} if code_names else {"name": ["in", [""]]},
        fields=["name", "attendance_code", "attendance_code_name", "count_as_present"],
        limit_page_length=1000,
    )
    code_map = _attendance_code_map(code_rows)

    course_names = sorted({row.get("course") for row in rows if row.get("course")})
    course_rows = frappe.get_all(
        "Course",
        filters={"name": ["in", course_names]} if course_names else {"name": ["in", [""]]},
        fields=["name", "course_name"],
        limit_page_length=1000,
    )
    course_name_map = {row.get("name"): row.get("course_name") for row in course_rows if row.get("name")}

    details_by_student_date: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        student_name = row.get("student")
        attendance_date = row.get("attendance_date")
        if not student_name or not attendance_date:
            continue

        code_meta = code_map.get(row.get("attendance_code")) or _fallback_code_meta(row.get("attendance_code"))
        details_by_student_date[student_name][str(attendance_date)].append(
            {
                "attendance": row.get("name") or "",
                "time": _coerce_time(row.get("attendance_time"), "guardian_attendance.time", []),
                "attendance_code": code_meta["attendance_code"],
                "attendance_code_name": code_meta["attendance_code_name"],
                "whole_day": bool(cint(row.get("whole_day") or 0)),
                "course": course_name_map.get(row.get("course")) or row.get("course") or None,
                "location": (row.get("location") or "").strip() or None,
                "remark": (row.get("remark") or "").strip() or None,
                "count_as_present": bool(code_meta["count_as_present"]),
                "is_late": bool(code_meta["is_late"]),
            }
        )

    students_payload: list[dict[str, Any]] = []
    total_counts = dict(empty_counts)
    for student_name in student_names:
        day_rows = details_by_student_date.get(student_name, {})
        summary = dict(empty_counts)
        days_payload: list[dict[str, Any]] = []

        for date_str in sorted(day_rows.keys()):
            details = sorted(day_rows[date_str], key=_detail_sort_key)
            state = _resolve_day_state(details)
            summary["tracked_days"] += 1
            summary[f"{state}_days"] += 1
            days_payload.append(
                {
                    "date": date_str,
                    "state": state,
                    "details": [_public_detail(detail) for detail in details],
                }
            )

        for key, value in summary.items():
            total_counts[key] += value

        students_payload.append(
            {
                "student": student_name,
                "student_name": child_name_map.get(student_name) or student_name,
                "summary": summary,
                "days": days_payload,
            }
        )

    return students_payload, total_counts


def _attendance_code_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        docname = (row.get("name") or "").strip()
        code_value = (row.get("attendance_code") or docname).strip()
        label = (row.get("attendance_code_name") or code_value or docname).strip()
        label_lower = label.lower()
        payload = {
            "attendance_code": code_value,
            "attendance_code_name": label,
            "count_as_present": cint(row.get("count_as_present") or 0),
            "is_late": "late" in label_lower or code_value.upper() == "L",
        }
        if docname:
            out[docname] = payload
        if code_value:
            out[code_value] = payload
    return out


def _fallback_code_meta(attendance_code: Any) -> dict[str, Any]:
    value = (attendance_code or "").strip()
    return {
        "attendance_code": value,
        "attendance_code_name": value,
        "count_as_present": 0,
        "is_late": False,
    }


def _detail_sort_key(detail: dict[str, Any]) -> tuple[int, str]:
    return (0 if detail.get("whole_day") else 1, detail.get("time") or "")


def _resolve_day_state(details: list[dict[str, Any]]) -> str:
    if any(not detail.get("count_as_present") and not detail.get("is_late") for detail in details):
        return "absence"
    if any(detail.get("is_late") for detail in details):
        return "late"
    return "present"


def _public_detail(detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "attendance": detail.get("attendance") or "",
        "time": detail.get("time"),
        "attendance_code": detail.get("attendance_code") or "",
        "attendance_code_name": detail.get("attendance_code_name") or detail.get("attendance_code") or "",
        "whole_day": bool(detail.get("whole_day")),
        "course": detail.get("course"),
        "location": detail.get("location"),
        "remark": detail.get("remark"),
    }
