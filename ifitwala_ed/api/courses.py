# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/courses.py

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from ifitwala_ed.api import course_schedule as course_schedule_api
from ifitwala_ed.api import portal as portal_api

COURSE_PLACEHOLDER = "/assets/ifitwala_ed/images/course_placeholder.jpg"
MAX_SORT_INT = 2_147_483_647
WORK_BOARD_NOW_LIMIT = 3
WORK_BOARD_SOON_LIMIT = 6
WORK_BOARD_LATER_LIMIT = 6
WORK_BOARD_DONE_LIMIT = 6
TIMELINE_HORIZON_DAYS = 7
NOW_WINDOW_DAYS = 2
SOON_WINDOW_DAYS = 7
DONE_SUBMISSION_STATUSES = {"Submitted", "Late", "Resubmitted"}
DONE_GRADING_STATUSES = {"Finalized", "Released"}


def _serialize_scalar(value: Any) -> Any:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _safe_course_image(url: str | None) -> str:
    if url and isinstance(url, str) and (url.startswith("/files/") or url.startswith("/assets/")):
        return url
    return COURSE_PLACEHOLDER


def _build_course_href(
    course_id: str,
    *,
    learning_unit: str | None = None,
    lesson: str | None = None,
    lesson_instance: str | None = None,
) -> dict[str, Any]:
    href: dict[str, Any] = {
        "name": "student-course-detail",
        "params": {"course_id": course_id},
    }
    query = {
        "learning_unit": learning_unit,
        "lesson": lesson,
        "lesson_instance": lesson_instance,
    }
    query = {key: value for key, value in query.items() if value}
    if query:
        href["query"] = query
    return href


def _get_student_name_for_user(user: str) -> str | None:
    """Map portal user -> Student by email (lightweight, indexed)."""
    return frappe.db.get_value("Student", {"student_email": user}, "name")


def _require_student_name_for_session_user() -> str:
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to view this page."), frappe.AuthenticationError)

    roles = set(frappe.get_roles(frappe.session.user))
    if "Student" not in roles:
        frappe.throw(_("Student access is required."), frappe.PermissionError)

    student_name = _get_student_name_for_user(frappe.session.user)
    if not student_name:
        frappe.throw(_("No student profile linked to this login yet."), frappe.PermissionError)
    return student_name


def _get_academic_years(student_name: str) -> list[str]:
    """Distinct years from Program Enrollment for this student, newest first."""
    rows = frappe.db.sql(
        """
        SELECT DISTINCT academic_year
        FROM `tabProgram Enrollment`
        WHERE student = %s
        ORDER BY academic_year DESC
        """,
        (student_name,),
        as_dict=False,
    )
    return [r[0] for r in rows if r and r[0]]


def _fetch_enrolled_courses(student_name: str) -> list[dict[str, Any]]:
    return frappe.db.sql(
        """
        SELECT
            pec.course,
            COALESCE(pec.course_name, c.course_name) AS course_name,
            pe.academic_year
        FROM `tabProgram Enrollment Course` pec
        JOIN `tabProgram Enrollment` pe ON pec.parent = pe.name
        LEFT JOIN `tabCourse` c ON c.name = pec.course
        WHERE pe.student = %(student)s
          AND COALESCE(pec.status, 'Enrolled') <> 'Dropped'
          AND pec.course IS NOT NULL
        ORDER BY pe.academic_year DESC, COALESCE(pec.course_name, c.course_name, pec.course)
        """,
        {"student": student_name},
        as_dict=True,
    )


def _fetch_active_student_groups(student_name: str) -> list[dict[str, Any]]:
    return frappe.db.sql(
        """
        SELECT
            sg.name AS student_group,
            sg.student_group_name,
            sg.course,
            sg.academic_year
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
        WHERE sgs.student = %(student)s
          AND COALESCE(sgs.active, 1) = 1
          AND sg.status = 'Active'
          AND sg.course IS NOT NULL
          AND sg.group_based_on = 'Course'
        ORDER BY sg.student_group_name, sg.name
        """,
        {"student": student_name},
        as_dict=True,
    )


def _build_student_course_scope(student_name: str) -> dict[str, dict[str, Any]]:
    scope: dict[str, dict[str, Any]] = {}

    for row in _fetch_enrolled_courses(student_name):
        course = row.get("course")
        if not course:
            continue
        entry = scope.setdefault(
            course,
            {
                "course": course,
                "course_name": row.get("course_name") or course,
                "academic_years": set(),
                "student_groups": [],
            },
        )
        academic_year = row.get("academic_year")
        if academic_year:
            entry["academic_years"].add(academic_year)

    for row in _fetch_active_student_groups(student_name):
        course = row.get("course")
        if not course:
            continue
        entry = scope.setdefault(
            course,
            {
                "course": course,
                "course_name": course,
                "academic_years": set(),
                "student_groups": [],
            },
        )
        academic_year = row.get("academic_year")
        if academic_year:
            entry["academic_years"].add(academic_year)
        entry["student_groups"].append(
            {
                "student_group": row.get("student_group"),
                "student_group_name": row.get("student_group_name") or row.get("student_group"),
                "academic_year": academic_year,
            }
        )

    for entry in scope.values():
        entry["academic_years"] = sorted(entry["academic_years"], reverse=True)

    return scope


def _get_courses_for_year(student_name: str, academic_year: str) -> list[dict]:
    rows = frappe.db.sql(
        """
        SELECT
            pec.course,
            COALESCE(pec.course_name, c.course_name) AS course_name,
            c.course_group,
            c.course_image
        FROM `tabProgram Enrollment Course` pec
        JOIN `tabProgram Enrollment` pe ON pec.parent = pe.name
        LEFT JOIN `tabCourse` c ON c.name = pec.course
        WHERE pe.student = %s
          AND pe.academic_year = %s
          AND COALESCE(pec.status, 'Enrolled') <> 'Dropped'
        ORDER BY COALESCE(pec.course_name, pec.course)
        """,
        (student_name, academic_year),
        as_dict=True,
    )

    courses = []
    for row in rows:
        course = row.get("course")
        if not course:
            continue
        courses.append(
            {
                "course": course,
                "course_name": row.get("course_name") or course,
                "course_group": row.get("course_group"),
                "course_image": _safe_course_image(row.get("course_image")),
                "href": _build_course_href(course),
            }
        )
    return courses


def _serialize_delivery(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_delivery": row.get("name"),
        "student_group": row.get("student_group"),
        "available_from": _serialize_scalar(row.get("available_from")),
        "due_date": _serialize_scalar(row.get("due_date")),
        "lock_date": _serialize_scalar(row.get("lock_date")),
        "lesson_instance": row.get("lesson_instance"),
        "delivery_mode": row.get("delivery_mode"),
    }


def _serialize_task(row: dict[str, Any], deliveries: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "task": row.get("name"),
        "title": row.get("title") or row.get("name"),
        "task_type": row.get("task_type"),
        "learning_unit": row.get("learning_unit"),
        "lesson": row.get("lesson"),
        "deliveries": [_serialize_delivery(delivery) for delivery in deliveries],
    }


def _coerce_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return get_datetime(value)
    except Exception:
        return None


def _time_text_to_minutes(value: Any) -> int | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        hour_text, minute_text = raw.split(":", 1)
        return int(hour_text) * 60 + int(minute_text[:2])
    except Exception:
        return None


def _extract_class_time_bounds(course: dict[str, Any]) -> tuple[int | None, int | None]:
    starts: list[int] = []
    ends: list[int] = []
    for slot in course.get("time_slots") or []:
        start_minutes = _time_text_to_minutes(slot.get("from_time"))
        end_minutes = _time_text_to_minutes(slot.get("to_time"))
        if start_minutes is not None:
            starts.append(start_minutes)
        if end_minutes is not None:
            ends.append(end_minutes)
    return (min(starts) if starts else None, max(ends) if ends else None)


def _build_home_orientation(today_courses: list[dict[str, Any]], anchor_dt: datetime) -> dict[str, Any]:
    current_minutes = anchor_dt.hour * 60 + anchor_dt.minute
    current_class = None
    next_class = None

    for course in today_courses:
        start_minutes, end_minutes = _extract_class_time_bounds(course)
        if start_minutes is None:
            continue
        if end_minutes is not None and start_minutes <= current_minutes <= end_minutes:
            current_class = course
            break
        if start_minutes > current_minutes:
            next_class = course
            break

    if not next_class:
        for course in today_courses:
            start_minutes, _unused_end = _extract_class_time_bounds(course)
            if start_minutes is None:
                continue
            if start_minutes > current_minutes:
                next_class = course
                break

    return {
        "current_class": current_class,
        "next_class": next_class,
    }


def _fetch_student_hub_task_rows(student_name: str, student_groups: list[str]) -> list[dict[str, Any]]:
    if not student_groups:
        return []

    return frappe.db.sql(
        """
        SELECT
            td.name AS task_delivery,
            td.task,
            td.student_group,
            COALESCE(td.course, t.default_course) AS course,
            td.delivery_mode,
            td.requires_submission,
            td.require_grading,
            td.available_from,
            td.due_date,
            td.lock_date,
            td.lesson_instance,
            t.title,
            t.task_type,
            t.learning_unit,
            t.lesson,
            COALESCE(c.course_name, td.course, t.default_course) AS course_name,
            o.name AS task_outcome,
            o.submission_status,
            o.grading_status,
            o.has_submission,
            o.has_new_submission,
            o.is_complete,
            o.completed_on
        FROM `tabTask Delivery` td
        INNER JOIN `tabTask` t ON t.name = td.task
        LEFT JOIN `tabCourse` c ON c.name = COALESCE(td.course, t.default_course)
        LEFT JOIN `tabTask Outcome` o ON o.task_delivery = td.name AND o.student = %(student)s
        WHERE td.docstatus = 1
          AND td.student_group IN %(student_groups)s
          AND COALESCE(t.is_archived, 0) = 0
        ORDER BY COALESCE(td.due_date, td.lock_date, td.available_from, td.modified) ASC, td.name ASC
        LIMIT 200
        """,
        {"student": student_name, "student_groups": tuple(student_groups)},
        as_dict=True,
    )


def _is_work_item_done(row: dict[str, Any]) -> bool:
    if int(row.get("is_complete") or 0) == 1:
        return True

    grading_status = str(row.get("grading_status") or "").strip()
    if grading_status in DONE_GRADING_STATUSES:
        return True

    submission_status = str(row.get("submission_status") or "").strip()
    if submission_status in DONE_SUBMISSION_STATUSES:
        return True

    if int(row.get("has_submission") or 0) == 1:
        return True

    return False


def _build_work_item_href(row: dict[str, Any]) -> dict[str, Any] | None:
    course_id = row.get("course")
    if not course_id:
        return None
    return _build_course_href(
        course_id,
        learning_unit=row.get("learning_unit"),
        lesson=row.get("lesson"),
        lesson_instance=row.get("lesson_instance"),
    )


def _build_work_item_status_label(row: dict[str, Any], anchor_dt: datetime) -> str:
    due_dt = _coerce_datetime(row.get("due_date"))
    available_dt = _coerce_datetime(row.get("available_from"))
    grading_status = str(row.get("grading_status") or "").strip()
    submission_status = str(row.get("submission_status") or "").strip()

    if int(row.get("is_complete") or 0) == 1:
        return "Completed"
    if grading_status in DONE_GRADING_STATUSES:
        return grading_status
    if submission_status in DONE_SUBMISSION_STATUSES:
        return submission_status
    if due_dt and due_dt < anchor_dt:
        return "Overdue"
    if due_dt and due_dt.date() == anchor_dt.date():
        return "Due Today"
    if due_dt:
        return "Upcoming"
    if available_dt and available_dt > anchor_dt:
        return "Not Yet Open"
    return "Open"


def _classify_work_item_lane(row: dict[str, Any], anchor_dt: datetime) -> tuple[str, str]:
    if _is_work_item_done(row):
        return "done", "Completed or submitted recently"

    due_dt = _coerce_datetime(row.get("due_date"))
    available_dt = _coerce_datetime(row.get("available_from"))
    available_now = not available_dt or available_dt <= anchor_dt
    now_window_end = anchor_dt + timedelta(days=NOW_WINDOW_DAYS)
    soon_window_end = anchor_dt + timedelta(days=SOON_WINDOW_DAYS)

    if due_dt and due_dt < anchor_dt:
        return "now", "Overdue and needs attention"
    if due_dt and due_dt.date() == anchor_dt.date() and available_now:
        return "now", "Due today"
    if due_dt and available_now and due_dt <= now_window_end:
        return "now", "Due soon"
    if available_dt and anchor_dt <= available_dt <= soon_window_end:
        return "soon", "Becomes available soon"
    if due_dt and due_dt <= soon_window_end:
        return "soon", "Due this week"
    if available_dt and available_dt > soon_window_end:
        return "later", "Planned for later"
    return "later", "Open without an immediate deadline"


def _serialize_work_item(row: dict[str, Any], anchor_dt: datetime, lane: str, lane_reason: str) -> dict[str, Any]:
    return {
        "task_delivery": row.get("task_delivery"),
        "task": row.get("task"),
        "task_outcome": row.get("task_outcome"),
        "title": row.get("title") or row.get("task"),
        "task_type": row.get("task_type"),
        "course": row.get("course"),
        "course_name": row.get("course_name") or row.get("course"),
        "student_group": row.get("student_group"),
        "delivery_mode": row.get("delivery_mode"),
        "requires_submission": int(row.get("requires_submission") or 0),
        "require_grading": int(row.get("require_grading") or 0),
        "learning_unit": row.get("learning_unit"),
        "lesson": row.get("lesson"),
        "lesson_instance": row.get("lesson_instance"),
        "available_from": _serialize_scalar(row.get("available_from")),
        "due_date": _serialize_scalar(row.get("due_date")),
        "lock_date": _serialize_scalar(row.get("lock_date")),
        "href": _build_work_item_href(row),
        "lane": lane,
        "lane_reason": lane_reason,
        "status_label": _build_work_item_status_label(row, anchor_dt),
        "outcome": {
            "submission_status": row.get("submission_status"),
            "grading_status": row.get("grading_status"),
            "has_submission": int(row.get("has_submission") or 0),
            "has_new_submission": int(row.get("has_new_submission") or 0),
            "is_complete": int(row.get("is_complete") or 0),
            "completed_on": _serialize_scalar(row.get("completed_on")),
        },
    }


def _work_item_sort_key(item: dict[str, Any], done: bool = False) -> tuple[Any, ...]:
    primary = item.get("due_date") or item.get("available_from") or item.get("lock_date") or ""
    if done:
        primary = item.get("outcome", {}).get("completed_on") or primary
        return (primary, item.get("title") or "", item.get("task_delivery") or "")
    return (primary, item.get("title") or "", item.get("task_delivery") or "")


def _build_work_board_payload(task_rows: list[dict[str, Any]], anchor_dt: datetime) -> dict[str, list[dict[str, Any]]]:
    lanes: dict[str, list[dict[str, Any]]] = {
        "now": [],
        "soon": [],
        "later": [],
        "done": [],
    }

    for row in task_rows:
        lane, lane_reason = _classify_work_item_lane(row, anchor_dt)
        lanes[lane].append(_serialize_work_item(row, anchor_dt, lane, lane_reason))

    lanes["now"] = sorted(lanes["now"], key=_work_item_sort_key)[:WORK_BOARD_NOW_LIMIT]
    lanes["soon"] = sorted(lanes["soon"], key=_work_item_sort_key)[:WORK_BOARD_SOON_LIMIT]
    lanes["later"] = sorted(lanes["later"], key=_work_item_sort_key)[:WORK_BOARD_LATER_LIMIT]
    lanes["done"] = sorted(lanes["done"], key=lambda item: _work_item_sort_key(item, done=True), reverse=True)[
        :WORK_BOARD_DONE_LIMIT
    ]
    return lanes


def _task_timeline_item(
    *,
    row: dict[str, Any],
    event_kind: str,
    event_dt: datetime,
    anchor_dt: datetime,
) -> dict[str, Any]:
    if event_kind == "task_due":
        subtitle = "Due work"
    else:
        subtitle = "Opens for work"

    return {
        "kind": event_kind,
        "date": event_dt.date().isoformat(),
        "date_time": event_dt.isoformat(sep=" "),
        "title": row.get("title") or row.get("task"),
        "subtitle": f"{row.get('course_name') or row.get('course') or _('Course')} · {subtitle}",
        "time_label": event_dt.strftime("%H:%M"),
        "status_label": _build_work_item_status_label(row, anchor_dt),
        "href": _build_work_item_href(row),
    }


def _class_timeline_item(course: dict[str, Any], anchor_dt: datetime) -> dict[str, Any]:
    first_slot = (course.get("time_slots") or [{}])[0]
    return {
        "kind": "scheduled_class",
        "date": anchor_dt.date().isoformat(),
        "date_time": anchor_dt.replace(
            hour=int(str(first_slot.get("from_time") or "00:00")[:2] or 0),
            minute=int(str(first_slot.get("from_time") or "00:00")[3:5] or 0),
            second=0,
            microsecond=0,
        ).isoformat(sep=" "),
        "title": course.get("course_name") or course.get("course"),
        "subtitle": course.get("student_group_name") or _("Scheduled class"),
        "time_label": first_slot.get("time_range") or None,
        "status_label": "Class",
        "href": course.get("href") or _build_course_href(course.get("course")),
    }


def _build_learning_timeline(
    *,
    today_courses: list[dict[str, Any]],
    task_rows: list[dict[str, Any]],
    anchor_dt: datetime,
) -> list[dict[str, Any]]:
    days: dict[str, list[dict[str, Any]]] = defaultdict(list)
    horizon_end = anchor_dt + timedelta(days=TIMELINE_HORIZON_DAYS)

    for course in today_courses:
        item = _class_timeline_item(course, anchor_dt)
        days[item["date"]].append(item)

    for row in task_rows:
        if _is_work_item_done(row):
            continue

        due_dt = _coerce_datetime(row.get("due_date"))
        available_dt = _coerce_datetime(row.get("available_from"))

        if due_dt and due_dt <= horizon_end and (due_dt >= anchor_dt or due_dt.date() == anchor_dt.date()):
            item = _task_timeline_item(row=row, event_kind="task_due", event_dt=due_dt, anchor_dt=anchor_dt)
            days[item["date"]].append(item)
            continue

        if available_dt and anchor_dt <= available_dt <= horizon_end:
            item = _task_timeline_item(
                row=row,
                event_kind="task_available",
                event_dt=available_dt,
                anchor_dt=anchor_dt,
            )
            days[item["date"]].append(item)

    ordered_days = []
    for date_key in sorted(days.keys()):
        items = sorted(days[date_key], key=lambda item: (item.get("date_time") or "", item.get("title") or ""))
        ordered_days.append(
            {
                "date": date_key,
                "items": items[:8],
            }
        )
    return ordered_days


def _build_curriculum_payload(
    *,
    units: list[dict[str, Any]],
    lessons: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    deliveries: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    deliveries_by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for delivery in deliveries:
        task_name = delivery.get("task")
        if task_name:
            deliveries_by_task[task_name].append(delivery)

    units_by_name: dict[str, dict[str, Any]] = {}
    lessons_by_name: dict[str, dict[str, Any]] = {}
    activities_by_name: dict[str, dict[str, Any]] = {}

    curriculum_units: list[dict[str, Any]] = []
    for unit in units:
        item = {
            "name": unit.get("name"),
            "unit_name": unit.get("unit_name") or unit.get("name"),
            "unit_order": unit.get("unit_order"),
            "duration": unit.get("duration"),
            "estimated_duration": unit.get("estimated_duration"),
            "unit_status": unit.get("unit_status"),
            "is_published": int(unit.get("is_published") or 0),
            "unit_overview": unit.get("unit_overview"),
            "essential_understanding": unit.get("essential_understanding"),
            "misconceptions": unit.get("misconceptions"),
            "linked_tasks": [],
            "lessons": [],
        }
        curriculum_units.append(item)
        if item["name"]:
            units_by_name[item["name"]] = item

    for lesson in lessons:
        item = {
            "name": lesson.get("name"),
            "learning_unit": lesson.get("learning_unit"),
            "title": lesson.get("title") or lesson.get("name"),
            "lesson_type": lesson.get("lesson_type"),
            "lesson_order": lesson.get("lesson_order"),
            "duration": lesson.get("duration"),
            "start_date": _serialize_scalar(lesson.get("start_date")),
            "is_published": int(lesson.get("is_published") or 0),
            "linked_tasks": [],
            "lesson_activities": [],
        }
        if item["name"]:
            lessons_by_name[item["name"]] = item
        parent = units_by_name.get(item["learning_unit"])
        if parent:
            parent["lessons"].append(item)

    for activity in activities:
        item = {
            "name": activity.get("name"),
            "lesson": activity.get("lesson"),
            "title": activity.get("title"),
            "activity_type": activity.get("activity_type"),
            "lesson_activity_order": activity.get("lesson_activity_order"),
            "estimated_duration": activity.get("estimated_duration"),
            "is_required": int(activity.get("is_required") or 0),
            "reading_content": activity.get("reading_content"),
            "video_url": activity.get("video_url"),
            "external_link": activity.get("external_link"),
            "discussion_prompt": activity.get("discussion_prompt"),
        }
        if item["name"]:
            activities_by_name[item["name"]] = item
        parent = lessons_by_name.get(item["lesson"])
        if parent:
            parent["lesson_activities"].append(item)

    course_tasks: list[dict[str, Any]] = []
    unit_task_count = 0
    lesson_task_count = 0
    course_task_count = 0

    for task in tasks:
        task_name = task.get("name")
        deliveries_for_task = deliveries_by_task.get(task_name, [])
        serialized = _serialize_task(task, deliveries_for_task)

        lesson_name = task.get("lesson")
        unit_name = task.get("learning_unit")
        if lesson_name and lesson_name in lessons_by_name:
            lessons_by_name[lesson_name]["linked_tasks"].append(serialized)
            lesson_task_count += 1
            continue
        if unit_name and unit_name in units_by_name:
            units_by_name[unit_name]["linked_tasks"].append(serialized)
            unit_task_count += 1
            continue
        course_tasks.append(serialized)
        course_task_count += 1

    counts = {
        "units": len(curriculum_units),
        "lessons": len(lessons_by_name),
        "activities": len(activities_by_name),
        "course_tasks": course_task_count,
        "unit_tasks": unit_task_count,
        "lesson_tasks": lesson_task_count,
        "deliveries": len(deliveries),
    }

    return (
        {
            "counts": counts,
            "course_tasks": course_tasks,
            "units": curriculum_units,
        },
        {
            "units": units_by_name,
            "lessons": lessons_by_name,
            "activities": activities_by_name,
        },
    )


def _resolve_deep_link_context(
    *,
    requested_learning_unit: str | None,
    requested_lesson: str | None,
    requested_lesson_instance: str | None,
    units_by_name: dict[str, dict[str, Any]],
    lessons_by_name: dict[str, dict[str, Any]],
    activities_by_name: dict[str, dict[str, Any]],
    lesson_instances_by_name: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    resolved_learning_unit = None
    resolved_lesson = None
    resolved_lesson_instance = None
    source = "course_only"

    if requested_lesson_instance:
        lesson_instance = lesson_instances_by_name.get(requested_lesson_instance)
        if lesson_instance:
            resolved_lesson_instance = lesson_instance.get("name")
            resolved_lesson = lesson_instance.get("lesson")
            if not resolved_lesson and lesson_instance.get("lesson_activity"):
                activity = activities_by_name.get(lesson_instance.get("lesson_activity"))
                resolved_lesson = activity.get("lesson") if activity else None
            if resolved_lesson and resolved_lesson in lessons_by_name:
                resolved_learning_unit = lessons_by_name[resolved_lesson].get("learning_unit")
            source = "lesson_instance"

    if source == "course_only" and requested_lesson and requested_lesson in lessons_by_name:
        resolved_lesson = requested_lesson
        resolved_learning_unit = lessons_by_name[requested_lesson].get("learning_unit")
        source = "lesson"

    if source == "course_only" and requested_learning_unit and requested_learning_unit in units_by_name:
        resolved_learning_unit = requested_learning_unit
        source = "learning_unit"

    if source == "course_only" and units_by_name:
        ordered_units = sorted(
            units_by_name.values(),
            key=lambda row: (
                row.get("unit_order") if row.get("unit_order") is not None else MAX_SORT_INT,
                row.get("unit_name") or row.get("name") or "",
            ),
        )
        first_unit = ordered_units[0]
        resolved_learning_unit = first_unit.get("name")
        source = "first_available"
        lessons = first_unit.get("lessons") or []
        if lessons:
            ordered_lessons = sorted(
                lessons,
                key=lambda row: (
                    row.get("lesson_order") if row.get("lesson_order") is not None else MAX_SORT_INT,
                    row.get("title") or row.get("name") or "",
                ),
            )
            resolved_lesson = ordered_lessons[0].get("name")

    return {
        "requested": {
            "learning_unit": requested_learning_unit or None,
            "lesson": requested_lesson or None,
            "lesson_instance": requested_lesson_instance or None,
        },
        "resolved": {
            "learning_unit": resolved_learning_unit,
            "lesson": resolved_lesson,
            "lesson_instance": resolved_lesson_instance,
            "source": source,
        },
    }


def _get_course_row(course_id: str) -> dict[str, Any]:
    course = frappe.db.get_value(
        "Course",
        course_id,
        [
            "name",
            "course_name",
            "course_group",
            "course_image",
            "description",
            "status",
            "is_published",
        ],
        as_dict=True,
    )
    if not course:
        frappe.throw(_("Course not found."), frappe.DoesNotExistError)
    return course


def _fetch_course_units(course_id: str) -> list[dict[str, Any]]:
    return frappe.db.sql(
        """
        SELECT
            name,
            unit_name,
            unit_order,
            duration,
            estimated_duration,
            unit_status,
            is_published,
            unit_overview,
            essential_understanding,
            misconceptions
        FROM `tabLearning Unit`
        WHERE course = %(course)s
        ORDER BY COALESCE(unit_order, %(max_sort)s) ASC, unit_name ASC, name ASC
        """,
        {"course": course_id, "max_sort": MAX_SORT_INT},
        as_dict=True,
    )


def _fetch_course_lessons(unit_names: list[str]) -> list[dict[str, Any]]:
    if not unit_names:
        return []
    return frappe.db.sql(
        """
        SELECT
            name,
            learning_unit,
            title,
            lesson_type,
            lesson_order,
            duration,
            start_date,
            is_published
        FROM `tabLesson`
        WHERE learning_unit IN %(units)s
        ORDER BY learning_unit ASC, COALESCE(lesson_order, %(max_sort)s) ASC, title ASC, name ASC
        """,
        {"units": tuple(unit_names), "max_sort": MAX_SORT_INT},
        as_dict=True,
    )


def _fetch_lesson_activities(lesson_names: list[str]) -> list[dict[str, Any]]:
    if not lesson_names:
        return []
    return frappe.db.sql(
        """
        SELECT
            name,
            parent AS lesson,
            title,
            activity_type,
            lesson_activity_order,
            estimated_duration,
            is_required,
            reading_content,
            video_url,
            external_link,
            discussion_prompt,
            idx
        FROM `tabLesson Activity`
        WHERE parenttype = 'Lesson'
          AND parentfield = 'lesson_activities'
          AND parent IN %(lessons)s
        ORDER BY parent ASC, COALESCE(lesson_activity_order, %(max_sort)s) ASC, idx ASC, name ASC
        """,
        {"lessons": tuple(lesson_names), "max_sort": MAX_SORT_INT},
        as_dict=True,
    )


def _fetch_course_tasks(course_id: str) -> list[dict[str, Any]]:
    return frappe.get_all(
        "Task",
        filters={"default_course": course_id, "is_archived": 0},
        fields=["name", "title", "task_type", "learning_unit", "lesson"],
        order_by="title asc, name asc",
    )


def _fetch_task_deliveries_for_course(
    course_id: str, task_names: list[str], student_groups: list[str]
) -> list[dict[str, Any]]:
    if not task_names or not student_groups:
        return []
    return frappe.get_all(
        "Task Delivery",
        filters={
            "docstatus": 1,
            "course": course_id,
            "task": ["in", task_names],
            "student_group": ["in", student_groups],
        },
        fields=[
            "name",
            "task",
            "student_group",
            "available_from",
            "due_date",
            "lock_date",
            "lesson_instance",
            "delivery_mode",
        ],
        order_by="due_date asc, available_from asc, name asc",
    )


def _fetch_lesson_instances_for_course(
    course_id: str, student_groups: list[str], requested_lesson_instance: str | None
) -> list[dict[str, Any]]:
    names = set()
    if requested_lesson_instance:
        names.add(requested_lesson_instance)

    if student_groups:
        deliveries = frappe.get_all(
            "Lesson Instance",
            filters={
                "course": course_id,
                "student_group": ["in", student_groups],
            },
            fields=["name", "lesson", "lesson_activity", "student_group"],
        )
        for row in deliveries:
            names.add(row.get("name"))

    if not names:
        return []

    return frappe.get_all(
        "Lesson Instance",
        filters={"name": ["in", list(names)], "course": course_id},
        fields=["name", "lesson", "lesson_activity", "student_group"],
    )


@frappe.whitelist()
def get_courses_data(academic_year: str | None = None) -> dict:
    """Fetch courses data for the logged-in student."""
    if frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in to view this page."), frappe.AuthenticationError)

    roles = set(frappe.get_roles(frappe.session.user))
    student_name = _get_student_name_for_user(frappe.session.user) if "Student" in roles else None
    if not student_name:
        return {
            "academic_years": [],
            "selected_year": None,
            "courses": [],
            "error": _("No student profile linked to this login yet."),
        }

    years = _get_academic_years(student_name)
    selected = academic_year
    if not selected or selected not in years:
        selected = years[0] if years else None

    courses = _get_courses_for_year(student_name, selected) if selected else []
    return {
        "academic_years": years,
        "selected_year": selected,
        "courses": courses,
    }


@frappe.whitelist()
def get_student_hub_home() -> dict[str, Any]:
    student_name = _require_student_name_for_session_user()
    anchor_dt = now_datetime()

    identity = portal_api.get_student_portal_identity()
    schedule = course_schedule_api.get_today_courses()
    course_data = get_courses_data()
    scope = _build_student_course_scope(student_name)
    accessible_course_count = len(scope)
    student_groups = sorted(
        {
            row.get("student_group")
            for entry in scope.values()
            for row in entry.get("student_groups") or []
            if row.get("student_group")
        }
    )

    today_courses = schedule.get("courses") or []
    courses = course_data.get("courses") or []
    task_rows = _fetch_student_hub_task_rows(student_name, student_groups)
    work_board = _build_work_board_payload(task_rows, anchor_dt)
    timeline = _build_learning_timeline(today_courses=today_courses, task_rows=task_rows, anchor_dt=anchor_dt)
    orientation = _build_home_orientation(today_courses, anchor_dt)
    next_route = None
    next_title = None
    next_subtitle = None
    next_kind = None

    if orientation.get("current_class"):
        first = orientation["current_class"]
        next_route = first.get("href") or _build_course_href(first.get("course"))
        next_title = first.get("course_name") or first.get("course")
        next_subtitle = "Continue from your current class"
        next_kind = "scheduled_class"
    elif orientation.get("next_class"):
        first = orientation["next_class"]
        next_route = first.get("href") or _build_course_href(first.get("course"))
        next_title = first.get("course_name") or first.get("course")
        next_subtitle = "Prepare for your next class"
        next_kind = "scheduled_class"
    elif work_board["now"]:
        first = work_board["now"][0]
        next_route = first.get("href") or _build_course_href(first.get("course"))
        next_title = first.get("title") or first.get("task")
        next_subtitle = first.get("lane_reason") or "Continue your current work"
        next_kind = "course"
    elif courses:
        first = courses[0]
        next_route = first.get("href") or _build_course_href(first.get("course"))
        next_title = first.get("course_name") or first.get("course")
        next_subtitle = "Open your course space"
        next_kind = "course"

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "date": schedule.get("date"),
            "weekday": schedule.get("weekday"),
        },
        "identity": identity,
        "learning": {
            "today_classes": today_courses,
            "next_learning_step": (
                {
                    "kind": next_kind,
                    "title": next_title,
                    "subtitle": next_subtitle,
                    "href": next_route,
                }
                if next_route and next_title and next_kind
                else None
            ),
            "accessible_courses_count": accessible_course_count,
            "selected_year": course_data.get("selected_year"),
            "orientation": orientation,
            "work_board": work_board,
            "timeline": timeline,
        },
    }


@frappe.whitelist()
def get_student_course_detail(
    course_id: str,
    learning_unit: str | None = None,
    lesson: str | None = None,
    lesson_instance: str | None = None,
) -> dict[str, Any]:
    if not course_id:
        frappe.throw(_("Course is required."), frappe.ValidationError)

    student_name = _require_student_name_for_session_user()
    scope = _build_student_course_scope(student_name)
    course_scope = scope.get(course_id)
    if not course_scope:
        frappe.throw(_("You do not have access to this course."), frappe.PermissionError)

    course = _get_course_row(course_id)
    student_groups = [
        row["student_group"] for row in course_scope.get("student_groups") or [] if row.get("student_group")
    ]

    units = _fetch_course_units(course_id)
    unit_names = [row.get("name") for row in units if row.get("name")]
    lessons = _fetch_course_lessons(unit_names)
    lesson_names = [row.get("name") for row in lessons if row.get("name")]
    activities = _fetch_lesson_activities(lesson_names)
    tasks = _fetch_course_tasks(course_id)
    task_names = [row.get("name") for row in tasks if row.get("name")]
    deliveries = _fetch_task_deliveries_for_course(course_id, task_names, student_groups)
    lesson_instances = _fetch_lesson_instances_for_course(course_id, student_groups, lesson_instance)

    curriculum, maps = _build_curriculum_payload(
        units=units,
        lessons=lessons,
        activities=activities,
        tasks=tasks,
        deliveries=deliveries,
    )

    lesson_instances_by_name = {row["name"]: row for row in lesson_instances if row.get("name")}
    deep_link = _resolve_deep_link_context(
        requested_learning_unit=learning_unit,
        requested_lesson=lesson,
        requested_lesson_instance=lesson_instance,
        units_by_name=maps["units"],
        lessons_by_name=maps["lessons"],
        activities_by_name=maps["activities"],
        lesson_instances_by_name=lesson_instances_by_name,
    )

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "course_id": course_id,
        },
        "course": {
            "course": course.get("name"),
            "course_name": course.get("course_name") or course.get("name"),
            "course_group": course.get("course_group"),
            "course_image": _safe_course_image(course.get("course_image")),
            "description": course.get("description"),
            "status": course.get("status"),
            "is_published": int(course.get("is_published") or 0),
        },
        "access": {
            "student": student_name,
            "academic_years": course_scope.get("academic_years") or [],
            "student_groups": course_scope.get("student_groups") or [],
        },
        "deep_link": deep_link,
        "curriculum": curriculum,
    }
