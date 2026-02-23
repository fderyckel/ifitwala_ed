# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/course_schedule.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, nowdate

from ifitwala_ed.schedule.schedule_utils import get_effective_schedule_for_ay, get_rotation_dates
from ifitwala_ed.schedule.student_group_scheduling import get_school_for_student_group

COURSE_PLACEHOLDER = "/assets/ifitwala_ed/images/course_placeholder.jpg"


@dataclass(slots=True)
class TimeSlot:
    block_number: Optional[int]
    from_time: Optional[str]
    to_time: Optional[str]
    location: Optional[str]
    instructor: Optional[str]

    @property
    def time_range(self) -> Optional[str]:
        if self.from_time and self.to_time:
            return f"{self.from_time} - {self.to_time}"
        if self.from_time:
            return self.from_time
        return None


def _resolve_current_student() -> str:
    """Securely map the logged-in portal user to a Student record."""
    user_id = frappe.session.user
    if user_id == "Guest":
        frappe.throw(
            _("You must be logged in as a student to view this page."),
            frappe.PermissionError,
        )

    user_email = frappe.db.get_value("User", user_id, "email") or user_id
    student_name = frappe.db.get_value("Student", {"student_email": user_email}, "name")

    if not student_name:
        frappe.throw(
            _("No Student record found for your account."),
            frappe.PermissionError,
        )

    return student_name


def _fetch_student_course_groups(student: str) -> List[frappe._dict]:
    """
    Return active (course-based) student groups the learner belongs to.
    Uses lean SQL to minimise ORM overhead.
    """
    return frappe.db.sql(
        """
        SELECT
            sg.name                               AS student_group,
            sg.student_group_name                 AS student_group_name,
            sg.group_based_on                     AS group_based_on,
            sg.status                             AS status,
            sg.course                             AS course,
            sg.program                            AS program,
            sg.program_offering                   AS program_offering,
            sg.school                             AS school,
            sg.school_schedule                    AS school_schedule,
            sg.academic_year                      AS academic_year,
            sg.term                               AS term,
            c.course_name                         AS course_name,
            c.course_group                        AS course_group,
            c.course_image                        AS course_image
        FROM `tabStudent Group Student` sgs
        INNER JOIN `tabStudent Group` sg ON sg.name = sgs.parent
        LEFT JOIN `tabCourse` c ON c.name = sg.course
        WHERE sgs.student = %(student)s
          AND COALESCE(sgs.active, 1) = 1
          AND sg.status = 'Active'
          AND sg.course IS NOT NULL
          AND sg.group_based_on = 'Course'
        """,
        {"student": student},
        as_dict=True,
    )


def _within_term(term_name: Optional[str], today: date, cache: Dict[str, dict]) -> bool:
    if not term_name:
        return True

    if term_name not in cache:
        cache[term_name] = (
            frappe.db.get_value(
                "Term",
                term_name,
                ["term_start_date", "term_end_date"],
                as_dict=True,
            )
            or {}
        )

    info = cache[term_name]
    start, end = info.get("term_start_date"), info.get("term_end_date")
    if start and today < getdate(start):
        return False
    if end and today > getdate(end):
        return False
    return True


def _resolve_schedule_name(
    row: frappe._dict,
    schedule_cache: Dict[Tuple[str, str], Optional[str]],
) -> Optional[str]:
    # 1) Explicit schedule on the group wins
    if row.get("school_schedule"):
        return row.school_schedule

    # 2) Use shared helper to resolve the base school
    if not row.get("student_group") or not row.get("academic_year"):
        return None

    base_school = get_school_for_student_group(row.student_group)
    if not base_school:
        return None

    key = (row.academic_year, base_school)
    if key not in schedule_cache:
        schedule_cache[key] = get_effective_schedule_for_ay(
            row.academic_year,
            base_school,
        )

    return schedule_cache[key]


def _rotation_day_for(
    schedule_name: str,
    academic_year: str,
    today_iso: str,
    cache: Dict[Tuple[str, str], Dict[str, int]],
) -> Optional[int]:
    key = (schedule_name, academic_year)
    if key not in cache:
        rot_dates = get_rotation_dates(
            schedule_name,
            academic_year,
            include_holidays=False,
        )
        cache[key] = {rd["date"].isoformat(): int(rd["rotation_day"]) for rd in rot_dates}
    return cache[key].get(today_iso)


def _time_to_str(raw: Optional[object]) -> Optional[str]:
    if not raw:
        return None
    if isinstance(raw, str):
        # Frappe stores as HH:MM:SS; keep HH:MM for UI
        return raw[:5]
    if hasattr(raw, "strftime"):
        return raw.strftime("%H:%M")
    return None


def _time_to_minutes(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        hour, minute = value.split(":", 1)
        return int(hour) * 60 + int(minute)
    except Exception:
        return None


def _safe_image(url: Optional[str]) -> str:
    if url and isinstance(url, str) and (url.startswith("/files/") or url.startswith("/assets/")):
        return url
    return COURSE_PLACEHOLDER


def _collect_instructors(rows: Iterable[frappe._dict]) -> Dict[str, str]:
    names = {row.instructor for row in rows if row.get("instructor")}
    if not names:
        return {}
    data = frappe.db.get_all(
        "Instructor",
        filters={"name": ["in", list(names)]},
        fields=["name", "instructor_name"],
    )
    return {row["name"]: (row.get("instructor_name") or row["name"]) for row in data}


@frappe.whitelist()
def get_today_courses() -> dict:
    """
    Return the list of courses (student groups) the logged-in student has
    scheduled for the server's current day.
    """
    student = _resolve_current_student()

    today_iso = nowdate()
    today_dt = getdate(today_iso)

    groups = _fetch_student_course_groups(student)
    if not groups:
        return {
            "date": today_iso,
            "weekday": formatdate(today_dt, "dddd"),
            "courses": [],
        }

    schedule_cache: Dict[Tuple[str, str], Optional[str]] = {}
    rotation_cache: Dict[Tuple[str, str], Dict[str, int]] = {}
    term_cache: Dict[str, dict] = {}

    active_groups: Dict[str, dict] = {}
    for row in groups:
        if not _within_term(row.get("term"), today_dt, term_cache):
            continue

        schedule_name = _resolve_schedule_name(row, schedule_cache)

        if not schedule_name:
            continue

        rotation_day = _rotation_day_for(
            schedule_name,
            row.academic_year,
            today_iso,
            rotation_cache,
        )
        if not rotation_day:
            continue

        row.rotation_day = rotation_day
        active_groups[row.student_group] = row

    if not active_groups:
        return {
            "date": today_iso,
            "weekday": formatdate(today_dt, "dddd"),
            "courses": [],
        }

    group_names = list(active_groups.keys())
    schedule_rows = frappe.db.get_all(
        "Student Group Schedule",
        filters={"parent": ["in", group_names]},
        fields=[
            "parent",
            "rotation_day",
            "block_number",
            "from_time",
            "to_time",
            "instructor",
            "location",
        ],
        order_by="parent asc, rotation_day asc, block_number asc",
    )

    if not schedule_rows:
        return {
            "date": today_iso,
            "weekday": formatdate(today_dt, "dddd"),
            "courses": [],
        }

    instructor_map = _collect_instructors(schedule_rows)

    by_group: Dict[str, List[TimeSlot]] = {name: [] for name in group_names}
    for row in schedule_rows:
        rotation_day = active_groups[row.parent].rotation_day
        if int(row.rotation_day or 0) != int(rotation_day):
            continue

        block_number = row.block_number
        block_number = int(block_number) if block_number is not None else None

        from_time = _time_to_str(row.from_time)
        to_time = _time_to_str(row.to_time)
        instructor = instructor_map.get(row.instructor) if row.instructor else None

        by_group[row.parent].append(
            TimeSlot(
                block_number=block_number,
                from_time=from_time,
                to_time=to_time,
                location=row.location,
                instructor=instructor,
            )
        )

    courses_payload: List[dict] = []
    for name, row in active_groups.items():
        slots = by_group.get(name) or []
        if not slots:
            continue

        # Keep predictable order
        slots.sort(key=lambda s: (s.block_number or 0, s.from_time or ""))

        instructors = [slot.instructor for slot in slots if slot.instructor]
        # Deduplicate while preserving order
        seen = set()
        unique_instructors: List[str] = []
        for instructor in instructors:
            if instructor not in seen:
                seen.add(instructor)
                unique_instructors.append(instructor)

        first_slot = slots[0]
        sort_minutes = _time_to_minutes(first_slot.from_time) or 24 * 60

    courses_payload.append(
        {
            "course": row.course,
            "course_name": row.course_name or row.student_group_name or row.course,
            "student_group": name,
            "student_group_name": row.student_group_name,
            "rotation_day": int(row.rotation_day),
            "instructors": unique_instructors,
            "time_slots": [
                {
                    "block_number": slot.block_number,
                    "from_time": slot.from_time,
                    "to_time": slot.to_time,
                    "time_range": slot.time_range,
                    "location": slot.location,
                    "instructor": slot.instructor,
                }
                for slot in slots
            ],
            "course_group": row.course_group,
            "course_image": _safe_image(row.course_image),
            "href": {
                "name": "student-course-detail",
                "params": {"course_id": row.course},
            },
            "_sort_minutes": sort_minutes,
        }
    )

    courses_payload.sort(
        key=lambda item: (
            item["_sort_minutes"],
            item.get("course_name") or item.get("course"),
        )
    )
    for item in courses_payload:
        item.pop("_sort_minutes", None)

    return {
        "date": today_iso,
        "weekday": formatdate(today_dt, "dddd"),
        "courses": courses_payload,
    }
