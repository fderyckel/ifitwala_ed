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
from ifitwala_ed.api import student_communications as student_communications_api
from ifitwala_ed.api.student_policy import get_student_policy_home_summary

COURSE_PLACEHOLDER = "/assets/ifitwala_ed/images/course_placeholder.jpg"
WORK_BOARD_NOW_LIMIT = 3
WORK_BOARD_SOON_LIMIT = 6
WORK_BOARD_LATER_LIMIT = 6
WORK_BOARD_DONE_LIMIT = 6
TIMELINE_HORIZON_DAYS = 7
NOW_WINDOW_DAYS = 2
SOON_WINDOW_DAYS = 7
DONE_SUBMISSION_STATUSES = {"Submitted", "Late", "Resubmitted"}
DONE_GRADING_STATUSES = {"Finalized", "Released"}
OPENABLE_LEARNING_SPACE_STATUSES = {"ready", "shared_plan_only"}


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
    student_group: str | None = None,
    unit_plan: str | None = None,
    class_session: str | None = None,
) -> dict[str, Any]:
    href: dict[str, Any] = {
        "name": "student-course-detail",
        "params": {"course_id": course_id},
    }
    query = {
        "student_group": student_group,
        "unit_plan": unit_plan,
        "class_session": class_session,
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


def _student_groups_for_course_year(scope_entry: dict[str, Any], academic_year: str | None) -> list[dict[str, Any]]:
    rows = list(scope_entry.get("student_groups") or [])
    selected_year = str(academic_year or "").strip()
    if not selected_year:
        return rows

    matching = [row for row in rows if str(row.get("academic_year") or "").strip() == selected_year]
    if matching:
        return matching

    return [row for row in rows if not str(row.get("academic_year") or "").strip()]


def _fetch_active_class_plan_groups(student_groups: list[str]) -> set[str]:
    names = sorted({str(name or "").strip() for name in student_groups if str(name or "").strip()})
    if not names:
        return set()

    rows = frappe.get_all(
        "Class Teaching Plan",
        filters={"student_group": ["in", names], "planning_status": "Active"},
        fields=["student_group"],
        limit=0,
    )
    return {str(row.get("student_group") or "").strip() for row in rows if str(row.get("student_group") or "").strip()}


def _fetch_active_course_plan_counts(course_ids: list[str]) -> dict[str, int]:
    names = sorted({str(name or "").strip() for name in course_ids if str(name or "").strip()})
    if not names:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            course,
            COUNT(*) AS active_plan_count
        FROM `tabCourse Plan`
        WHERE course IN %(courses)s
          AND plan_status = 'Active'
        GROUP BY course
        """,
        {"courses": tuple(names)},
        as_dict=True,
    )
    return {str(row.get("course") or "").strip(): int(row.get("active_plan_count") or 0) for row in rows or []}


def _serialize_course_learning_space(
    course_id: str,
    *,
    academic_year: str | None,
    scope_entry: dict[str, Any] | None,
    class_plan_groups: set[str],
    course_plan_counts: dict[str, int],
) -> dict[str, Any]:
    relevant_groups = _student_groups_for_course_year(scope_entry or {}, academic_year)
    relevant_group_names = [
        str(row.get("student_group") or "").strip()
        for row in relevant_groups
        if str(row.get("student_group") or "").strip()
    ]
    default_group = relevant_group_names[0] if relevant_group_names else None
    has_class_plan = any(group in class_plan_groups for group in relevant_group_names)
    has_shared_plan = course_plan_counts.get(course_id, 0) == 1

    if has_class_plan:
        status = "ready"
        source = "class_teaching_plan"
        status_label = _("Class Ready")
        summary = _("Open your class learning space.")
        cta_label = _("Open class")
    elif has_shared_plan:
        status = "shared_plan_only"
        source = "course_plan_fallback"
        status_label = _("Shared Plan")
        if relevant_group_names:
            summary = _("Your class plan is not published yet. Open the shared course plan for now.")
        else:
            summary = _("Your class is still being assigned. Open the shared course plan for now.")
        cta_label = _("Open shared plan")
    elif relevant_group_names:
        status = "awaiting_class_plan"
        source = "unavailable"
        status_label = _("Class Plan Pending")
        summary = _(
            "Your teacher has not published this class learning space yet. Check with your teacher if this should already be available."
        )
        cta_label = _("Not ready yet")
    else:
        status = "awaiting_class_assignment"
        source = "unavailable"
        status_label = _("Class Assignment Pending")
        summary = _(
            "Your class is still being assigned. Check with your academic office if this should already be available."
        )
        cta_label = _("Not ready yet")

    can_open = int(status in OPENABLE_LEARNING_SPACE_STATUSES)
    href = _build_course_href(course_id, student_group=default_group) if can_open else None
    return {
        "source": source,
        "status": status,
        "status_label": status_label,
        "summary": summary,
        "cta_label": cta_label,
        "can_open": can_open,
        "href": href,
    }


def _attach_course_learning_space_state(
    courses: list[dict[str, Any]],
    *,
    academic_year: str | None,
    scope: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    course_ids = [
        str(course.get("course") or "").strip() for course in courses if str(course.get("course") or "").strip()
    ]
    scoped_groups: list[str] = []
    for course in courses:
        course_id = str(course.get("course") or "").strip()
        if not course_id:
            continue
        relevant_groups = _student_groups_for_course_year(scope.get(course_id) or {}, academic_year)
        scoped_groups.extend(
            str(row.get("student_group") or "").strip()
            for row in relevant_groups
            if str(row.get("student_group") or "").strip()
        )

    class_plan_groups = _fetch_active_class_plan_groups(scoped_groups)
    course_plan_counts = _fetch_active_course_plan_counts(course_ids)

    enriched: list[dict[str, Any]] = []
    for course in courses:
        course_id = str(course.get("course") or "").strip()
        if not course_id:
            enriched.append(course)
            continue
        learning_space = _serialize_course_learning_space(
            course_id,
            academic_year=academic_year,
            scope_entry=scope.get(course_id),
            class_plan_groups=class_plan_groups,
            course_plan_counts=course_plan_counts,
        )
        enriched.append(
            {
                **course,
                "href": learning_space.get("href"),
                "learning_space": learning_space,
            }
        )
    return enriched


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


def _build_student_courses_payload(
    student_name: str, academic_year: str | None = None
) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    years = _get_academic_years(student_name)
    selected = academic_year
    if not selected or selected not in years:
        selected = years[0] if years else None

    scope = _build_student_course_scope(student_name)
    courses = _get_courses_for_year(student_name, selected) if selected else []
    courses = _attach_course_learning_space_state(courses, academic_year=selected, scope=scope)

    return {
        "academic_years": years,
        "selected_year": selected,
        "courses": courses,
    }, scope


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
            td.class_session,
            t.title,
            t.task_type,
            t.unit_plan AS unit_plan,
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
        student_group=row.get("student_group"),
        unit_plan=row.get("unit_plan"),
        class_session=row.get("class_session"),
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
        "unit_plan": row.get("unit_plan"),
        "class_session": row.get("class_session"),
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
        "href": course.get("href")
        or _build_course_href(course.get("course"), student_group=course.get("student_group")),
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

    payload, _scope = _build_student_courses_payload(student_name, academic_year)
    return payload


@frappe.whitelist()
def get_student_hub_home() -> dict[str, Any]:
    student_name = _require_student_name_for_session_user()
    anchor_dt = now_datetime()

    identity = portal_api.get_student_portal_identity()
    schedule = course_schedule_api.get_today_courses()
    course_data, scope = _build_student_courses_payload(student_name)
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
    communications = {
        "center_href": {"name": "student-communications"},
        "latest_course_update": None,
        "latest_activity_update": None,
        "latest_school_update": None,
    }
    try:
        communications = student_communications_api.get_student_home_communication_summary(student_name)
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Student Hub Communication Summary Load Failed")
    next_route = None
    next_title = None
    next_subtitle = None
    next_kind = None
    next_cta_label = None
    next_status_label = None
    next_can_open = 0

    if orientation.get("current_class"):
        first = orientation["current_class"]
        next_route = first.get("href") or _build_course_href(
            first.get("course"), student_group=first.get("student_group")
        )
        next_title = first.get("course_name") or first.get("course")
        next_subtitle = "Continue from your current class"
        next_kind = "scheduled_class"
        next_cta_label = "Open class"
        next_can_open = int(bool(next_route))
    elif orientation.get("next_class"):
        first = orientation["next_class"]
        next_route = first.get("href") or _build_course_href(
            first.get("course"), student_group=first.get("student_group")
        )
        next_title = first.get("course_name") or first.get("course")
        next_subtitle = "Prepare for your next class"
        next_kind = "scheduled_class"
        next_cta_label = "Prepare"
        next_can_open = int(bool(next_route))
    elif work_board["now"]:
        first = work_board["now"][0]
        next_route = first.get("href") or _build_course_href(
            first.get("course"), student_group=first.get("student_group")
        )
        next_title = first.get("title") or first.get("task")
        next_subtitle = first.get("lane_reason") or "Continue your current work"
        next_kind = "course"
        next_cta_label = "Open now"
        next_can_open = int(bool(next_route))
    elif courses:
        first = next(
            (course for course in courses if int((course.get("learning_space") or {}).get("can_open") or 0) == 1),
            courses[0],
        )
        learning_space = first.get("learning_space") or {}
        default_route = (
            _build_course_href(first.get("course")) if int(learning_space.get("can_open") or 0) == 1 else None
        )
        next_route = learning_space.get("href") or first.get("href") or default_route
        next_title = first.get("course_name") or first.get("course")
        next_subtitle = learning_space.get("summary") or "Open your course space"
        next_kind = "course"
        next_cta_label = learning_space.get("cta_label") or ("Open course" if next_route else "Not ready yet")
        next_status_label = learning_space.get("status_label")
        next_can_open = int(learning_space.get("can_open")) if "can_open" in learning_space else int(bool(next_route))

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "date": schedule.get("date"),
            "weekday": schedule.get("weekday"),
        },
        "identity": identity,
        "policies": get_student_policy_home_summary(student_name),
        "learning": {
            "today_classes": today_courses,
            "next_learning_step": (
                {
                    "kind": next_kind,
                    "title": next_title,
                    "subtitle": next_subtitle,
                    "href": next_route,
                    "cta_label": next_cta_label,
                    "status_label": next_status_label,
                    "can_open": next_can_open,
                }
                if next_title and next_kind
                else None
            ),
            "accessible_courses_count": accessible_course_count,
            "selected_year": course_data.get("selected_year"),
            "orientation": orientation,
            "work_board": work_board,
            "timeline": timeline,
        },
        "communications": communications,
    }
