# ifitwala_ed/api/guardian_monitoring.py

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, now_datetime

from ifitwala_ed.api.guardian_home import (
    _coerce_time,
    _get_unread_reference_names,
    _plain_summary,
    _resolve_guardian_scope,
)


@frappe.whitelist()
def get_guardian_monitoring_snapshot(student: str | None = None, days: int | str = 30) -> dict[str, Any]:
    selected_student = (student or "").strip()
    window_days = _coerce_days(days)
    user = frappe.session.user
    guardian_name, children = _resolve_guardian_scope(user)

    allowed_students = {child.get("student") for child in children if child.get("student")}
    if selected_student and selected_student not in allowed_students:
        frappe.throw(_("This student is not available in your guardian scope."), frappe.PermissionError)

    scoped_students = [selected_student] if selected_student else sorted(allowed_students)
    log_rows = _get_monitoring_logs(user=user, student_names=scoped_students, days=window_days)
    result_rows = _get_monitoring_results(student_names=scoped_students, days=window_days)

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "guardian": {"name": guardian_name},
            "filters": {
                "student": selected_student or "",
                "days": window_days,
            },
        },
        "family": {"children": children},
        "counts": {
            "visible_student_logs": len(log_rows),
            "unread_visible_student_logs": sum(1 for row in log_rows if row.get("is_unread")),
            "published_results": len(result_rows),
        },
        "student_logs": log_rows,
        "published_results": result_rows,
    }


def _coerce_days(days: int | str) -> int:
    try:
        value = int(days or 30)
    except Exception:
        frappe.throw(_("Invalid days."))
    if value < 1 or value > 90:
        frappe.throw(_("days must be between 1 and 90."))
    return value


def _get_monitoring_logs(*, user: str, student_names: list[str], days: int) -> list[dict[str, Any]]:
    if not student_names:
        return []

    anchor = frappe.utils.getdate()
    window_start = add_days(anchor, -(days - 1))
    rows = frappe.get_all(
        "Student Log",
        filters={
            "student": ["in", student_names],
            "visible_to_guardians": 1,
            "date": ["between", [window_start, anchor]],
        },
        fields=["name", "student", "student_name", "date", "time", "follow_up_status", "log"],
        order_by="date desc, time desc, modified desc",
        limit_page_length=200,
    )
    unread_names = set(
        _get_unread_reference_names(user, "Student Log", [row.get("name") for row in rows if row.get("name")])
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        name = row.get("name")
        if not name:
            continue
        out.append(
            {
                "student_log": name,
                "student": row.get("student") or "",
                "student_name": row.get("student_name") or row.get("student") or "",
                "date": str(row.get("date") or ""),
                "time": _coerce_time(row.get("time"), "guardian_monitoring.student_log.time", []),
                "summary": _plain_summary(row.get("log")),
                "follow_up_status": row.get("follow_up_status") or "",
                "is_unread": name in unread_names,
            }
        )
    return out


def _get_monitoring_results(*, student_names: list[str], days: int) -> list[dict[str, Any]]:
    if not student_names:
        return []

    anchor = frappe.utils.getdate()
    window_start = add_days(anchor, -(days - 1))
    rows = frappe.get_all(
        "Task Outcome",
        filters={
            "student": ["in", student_names],
            "is_published": 1,
            "published_on": ["between", [f"{window_start} 00:00:00", f"{anchor} 23:59:59"]],
        },
        fields=[
            "name",
            "student",
            "task",
            "published_on",
            "published_by",
            "official_score",
            "official_grade",
            "official_feedback",
        ],
        order_by="published_on desc, modified desc",
        limit_page_length=200,
    )
    task_names = sorted({(row.get("task") or "").strip() for row in rows if (row.get("task") or "").strip()})
    task_rows = frappe.get_all(
        "Task",
        filters={"name": ["in", task_names]} if task_names else {"name": ["in", [""]]},
        fields=["name", "title"],
    )
    task_map = {row.get("name"): row for row in task_rows if row.get("name")}

    student_rows = frappe.get_all(
        "Student",
        filters={"name": ["in", student_names]},
        fields=["name", "student_full_name"],
    )
    student_name_map = {row.get("name"): row.get("student_full_name") for row in student_rows if row.get("name")}

    out: list[dict[str, Any]] = []
    for row in rows:
        score = None
        if row.get("official_score") not in (None, ""):
            score = {"value": row.get("official_score")}
        elif row.get("official_grade"):
            score = {"value": row.get("official_grade")}

        out.append(
            {
                "task_outcome": row.get("name") or "",
                "student": row.get("student") or "",
                "student_name": student_name_map.get(row.get("student")) or row.get("student") or "",
                "title": task_map.get(row.get("task"), {}).get("title") or row.get("task") or row.get("name") or "",
                "published_on": str(row.get("published_on") or ""),
                "published_by": row.get("published_by") or "",
                "score": score,
                "narrative": _plain_summary(row.get("official_feedback")),
            }
        )
    return out
