# ifitwala_ed/api/guardian_monitoring.py

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, now_datetime, strip_html

from ifitwala_ed.api.guardian_home import (
    _coerce_time,
    _plain_summary,
    _resolve_guardian_scope,
)
from ifitwala_ed.api.student_log import _upsert_student_log_read_receipt
from ifitwala_ed.assessment import task_feedback_service

DEFAULT_PAGE_LENGTH = 12


@frappe.whitelist()
def get_guardian_monitoring_snapshot(
    student: str | None = None,
    days: int | str = 30,
    page_length: int | str = DEFAULT_PAGE_LENGTH,
    prioritize_unread: bool | int | str | None = None,
) -> dict[str, Any]:
    context = _resolve_monitoring_context(student=student, days=days)
    page_len = _coerce_page_length(page_length)
    prioritize_unread_logs = _coerce_prioritize_unread(prioritize_unread)
    log_page = _get_monitoring_logs_page(
        user=context["user"],
        student_names=context["scoped_students"],
        days=context["window_days"],
        start=0,
        page_length=page_len,
        prioritize_unread=prioritize_unread_logs,
    )
    result_page = _get_monitoring_results_page(
        student_names=context["scoped_students"],
        days=context["window_days"],
        start=0,
        page_length=page_len,
    )

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "guardian": {"name": context["guardian_name"]},
            "filters": {
                "student": context["selected_student"] or "",
                "days": context["window_days"],
            },
        },
        "family": {"children": context["children"]},
        "counts": {
            "visible_student_logs": log_page["total_count"],
            "unread_visible_student_logs": log_page["unread_total_count"],
            "published_results": result_page["total_count"],
        },
        "student_logs": _serialize_page(log_page),
        "published_results": _serialize_page(result_page),
    }


@frappe.whitelist()
def get_guardian_monitoring_student_logs(
    student: str | None = None,
    days: int | str = 30,
    start: int | str = 0,
    page_length: int | str = DEFAULT_PAGE_LENGTH,
    prioritize_unread: bool | int | str | None = None,
) -> dict[str, Any]:
    context = _resolve_monitoring_context(student=student, days=days)
    return _serialize_page(
        _get_monitoring_logs_page(
            user=context["user"],
            student_names=context["scoped_students"],
            days=context["window_days"],
            start=_coerce_start(start),
            page_length=_coerce_page_length(page_length),
            prioritize_unread=_coerce_prioritize_unread(prioritize_unread),
        )
    )


@frappe.whitelist()
def get_guardian_monitoring_published_results(
    student: str | None = None,
    days: int | str = 30,
    start: int | str = 0,
    page_length: int | str = DEFAULT_PAGE_LENGTH,
) -> dict[str, Any]:
    context = _resolve_monitoring_context(student=student, days=days)
    return _serialize_page(
        _get_monitoring_results_page(
            student_names=context["scoped_students"],
            days=context["window_days"],
            start=_coerce_start(start),
            page_length=_coerce_page_length(page_length),
        )
    )


def _resolve_monitoring_context(*, student: str | None, days: int | str) -> dict[str, Any]:
    selected_student = (student or "").strip()
    window_days = _coerce_days(days)
    user = frappe.session.user
    guardian_name, children = _resolve_guardian_scope(user)

    allowed_students = {child.get("student") for child in children if child.get("student")}
    if selected_student and selected_student not in allowed_students:
        frappe.throw(_("This student is not available in your guardian scope."), frappe.PermissionError)

    scoped_students = [selected_student] if selected_student else sorted(allowed_students)
    return {
        "user": user,
        "guardian_name": guardian_name,
        "children": children,
        "selected_student": selected_student,
        "window_days": window_days,
        "scoped_students": scoped_students,
    }


def _coerce_days(days: int | str) -> int:
    try:
        value = int(days or 30)
    except Exception:
        frappe.throw(_("Invalid days."))
    if value < 1 or value > 90:
        frappe.throw(_("days must be between 1 and 90."))
    return value


def _coerce_start(start: int | str | None) -> int:
    try:
        value = int(start or 0)
    except Exception:
        frappe.throw(_("Invalid start."))
    if value < 0:
        frappe.throw(_("start must be 0 or greater."))
    return value


def _coerce_page_length(page_length: int | str | None) -> int:
    try:
        value = int(page_length or DEFAULT_PAGE_LENGTH)
    except Exception:
        frappe.throw(_("Invalid page_length."))
    if value < 1 or value > 50:
        frappe.throw(_("page_length must be between 1 and 50."))
    return value


def _coerce_prioritize_unread(value: bool | int | str | None) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, "", 0, "0", "false", "False", "FALSE", "no", "No", "NO"):
        return False
    if value in (1, "1", "true", "True", "TRUE", "yes", "Yes", "YES"):
        return True
    frappe.throw(_("Invalid prioritize_unread flag."))


def _plain_guardian_log_text(value: Any) -> str:
    text = strip_html(value or "")
    return " ".join(text.split()).strip()


def _empty_page() -> dict[str, Any]:
    return {
        "items": [],
        "total_count": 0,
        "unread_total_count": 0,
        "has_more": False,
        "start": 0,
        "page_length": DEFAULT_PAGE_LENGTH,
    }


def _serialize_page(page: dict[str, Any]) -> dict[str, Any]:
    return {
        "items": page.get("items") or [],
        "total_count": int(page.get("total_count") or 0),
        "has_more": bool(page.get("has_more")),
        "start": int(page.get("start") or 0),
        "page_length": int(page.get("page_length") or DEFAULT_PAGE_LENGTH),
    }


def _count_monitoring_logs(*, user: str, student_names: list[str], days: int) -> dict[str, int]:
    if not student_names:
        return {"total_count": 0, "unread_total_count": 0}

    anchor = frappe.utils.getdate()
    window_start = add_days(anchor, -(days - 1))
    row = (
        frappe.db.sql(
            """
            SELECT
                COUNT(*) AS total_count,
                COALESCE(SUM(CASE WHEN prr.name IS NULL THEN 1 ELSE 0 END), 0) AS unread_total_count
            FROM `tabStudent Log` sl
            LEFT JOIN `tabPortal Read Receipt` prr
              ON prr.user = %(user)s
             AND prr.reference_doctype = 'Student Log'
             AND prr.reference_name = sl.name
            WHERE sl.student IN %(students)s
              AND sl.visible_to_guardians = 1
              AND sl.date BETWEEN %(window_start)s AND %(anchor)s
            """,
            {
                "user": user,
                "students": tuple(student_names),
                "window_start": window_start,
                "anchor": anchor,
            },
            as_dict=True,
        )
        or [{}]
    )[0]
    return {
        "total_count": cint(row.get("total_count") or 0),
        "unread_total_count": cint(row.get("unread_total_count") or 0),
    }


def _get_monitoring_logs(
    *,
    user: str,
    student_names: list[str],
    days: int,
    start: int = 0,
    page_length: int = DEFAULT_PAGE_LENGTH,
    prioritize_unread: bool = False,
) -> list[dict[str, Any]]:
    if not student_names:
        return []

    anchor = frappe.utils.getdate()
    window_start = add_days(anchor, -(days - 1))
    order_prefix = "CASE WHEN prr.name IS NULL THEN 0 ELSE 1 END ASC, " if prioritize_unread else ""
    rows = frappe.db.sql(
        f"""
        SELECT
            sl.name,
            sl.student,
            sl.student_name,
            sl.date,
            sl.time,
            sl.follow_up_status,
            sl.log,
            CASE WHEN prr.name IS NULL THEN 1 ELSE 0 END AS is_unread
        FROM `tabStudent Log` sl
        LEFT JOIN `tabPortal Read Receipt` prr
          ON prr.user = %(user)s
         AND prr.reference_doctype = 'Student Log'
         AND prr.reference_name = sl.name
        WHERE sl.student IN %(students)s
          AND sl.visible_to_guardians = 1
          AND sl.date BETWEEN %(window_start)s AND %(anchor)s
        ORDER BY {order_prefix}sl.date DESC, sl.time DESC, sl.modified DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {
            "user": user,
            "students": tuple(student_names),
            "window_start": window_start,
            "anchor": anchor,
            "limit": page_length,
            "offset": start,
        },
        as_dict=True,
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
                "summary": _plain_guardian_log_text(row.get("log")),
                "follow_up_status": row.get("follow_up_status") or "",
                "is_unread": bool(cint(row.get("is_unread") or 0)),
            }
        )
    if out:
        from ifitwala_ed.students.doctype.student_log.evidence import get_student_log_evidence_map

        evidence_map = get_student_log_evidence_map(
            [row.get("student_log") for row in out],
            audience="guardian",
        )
        for row in out:
            attachments = evidence_map.get(row.get("student_log")) or []
            row["attachments"] = attachments
            row["attachment_count"] = len(attachments)
    return out


def _get_monitoring_logs_page(
    *,
    user: str,
    student_names: list[str],
    days: int,
    start: int,
    page_length: int,
    prioritize_unread: bool = False,
) -> dict[str, Any]:
    if not student_names:
        page = _empty_page()
        page["page_length"] = page_length
        return page

    counts = _count_monitoring_logs(user=user, student_names=student_names, days=days)
    items = _get_monitoring_logs(
        user=user,
        student_names=student_names,
        days=days,
        start=start,
        page_length=page_length,
        prioritize_unread=prioritize_unread,
    )
    total_count = counts["total_count"]
    return {
        "items": items,
        "total_count": total_count,
        "unread_total_count": counts["unread_total_count"],
        "has_more": (start + page_length) < total_count,
        "start": start,
        "page_length": page_length,
    }


def _get_monitoring_results(*, student_names: list[str], days: int) -> list[dict[str, Any]]:
    if not student_names:
        return []

    anchor = frappe.utils.getdate()
    window_start = add_days(anchor, -(days - 1))
    legacy_rows = frappe.get_all(
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
        limit=0,
    )
    workspace_rows = frappe.db.sql(
        """
        SELECT
            task_outcome,
            task,
            student,
            task_submission,
            modified,
            modified_by
        FROM `tabTask Feedback Workspace`
        WHERE student IN %(students)s
          AND modified BETWEEN %(window_start)s AND %(window_end)s
          AND (
            feedback_visibility = 'student_and_guardian'
            OR grade_visibility = 'student_and_guardian'
          )
        ORDER BY modified DESC
        """,
        {
            "students": tuple(student_names),
            "window_start": f"{window_start} 00:00:00",
            "window_end": f"{anchor} 23:59:59",
        },
        as_dict=True,
    )

    candidate_rows: dict[str, dict[str, Any]] = {}
    for row in legacy_rows:
        outcome_id = row.get("name")
        if not outcome_id:
            continue
        candidate_rows[outcome_id] = {
            "task_outcome": outcome_id,
            "student": row.get("student"),
            "task": row.get("task"),
            "published_on": row.get("published_on"),
            "published_by": row.get("published_by"),
            "task_submission": None,
        }
    for row in workspace_rows:
        outcome_id = row.get("task_outcome")
        if not outcome_id:
            continue
        candidate_rows[outcome_id] = {
            "task_outcome": outcome_id,
            "student": row.get("student"),
            "task": row.get("task"),
            "published_on": row.get("modified"),
            "published_by": row.get("modified_by"),
            "task_submission": row.get("task_submission"),
        }

    rows = list(candidate_rows.values())
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
        released = task_feedback_service.build_released_result_payload(
            row.get("task_outcome") or "",
            audience="guardian",
            submission_id=row.get("task_submission"),
        )
        if not released.get("grade_visible") and not released.get("feedback_visible"):
            continue

        score = None
        if released.get("official", {}).get("score") not in (None, ""):
            score = {"value": released.get("official", {}).get("score")}
        elif released.get("official", {}).get("grade"):
            score = {"value": released.get("official", {}).get("grade")}

        narrative = (
            (((released.get("feedback") or {}).get("summary") or {}).get("overall"))
            or released.get("official", {}).get("feedback")
            or ""
        )

        out.append(
            {
                "task_outcome": row.get("task_outcome") or "",
                "student": row.get("student") or "",
                "student_name": student_name_map.get(row.get("student")) or row.get("student") or "",
                "title": task_map.get(row.get("task"), {}).get("title")
                or row.get("task")
                or row.get("task_outcome")
                or "",
                "published_on": str(row.get("published_on") or ""),
                "published_by": row.get("published_by") or "",
                "score": score,
                "narrative": _plain_summary(narrative),
                "grade_visible": bool(released.get("grade_visible")),
                "feedback_visible": bool(released.get("feedback_visible")),
            }
        )
    return sorted(out, key=lambda row: str(row.get("published_on") or ""), reverse=True)


def _get_monitoring_results_page(
    *,
    student_names: list[str],
    days: int,
    start: int,
    page_length: int,
) -> dict[str, Any]:
    rows = _get_monitoring_results(student_names=student_names, days=days)
    total_count = len(rows)
    return {
        "items": rows[start : start + page_length],
        "total_count": total_count,
        "unread_total_count": 0,
        "has_more": (start + page_length) < total_count,
        "start": start,
        "page_length": page_length,
    }


@frappe.whitelist()
def mark_guardian_student_log_read(log_name: str) -> dict[str, Any]:
    student_log_name = (log_name or "").strip()
    if not student_log_name:
        frappe.throw(_("log_name is required."))

    user = frappe.session.user
    _guardian_name, children = _resolve_guardian_scope(user)
    allowed_students = {child.get("student") for child in children if child.get("student")}
    log_row = frappe.db.get_value(
        "Student Log",
        student_log_name,
        ["name", "student", "visible_to_guardians"],
        as_dict=True,
    )
    if not log_row:
        frappe.throw(_("Log not found."), frappe.DoesNotExistError)

    if log_row.get("student") not in allowed_students or cint(log_row.get("visible_to_guardians") or 0) != 1:
        frappe.throw(_("You do not have permission to update this log."), frappe.PermissionError)

    read_at = now_datetime()
    _upsert_student_log_read_receipt(user=user, log_name=student_log_name, read_at=read_at)
    return {"ok": True, "student_log": student_log_name, "read_at": read_at}
