# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/course_schedule.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, List, Optional

import frappe
from frappe import _
from frappe.utils import formatdate, getdate, nowdate

from ifitwala_ed.schedule.schedule_utils import get_effective_schedule_for_ay, get_rotation_dates
from ifitwala_ed.schedule.student_group_scheduling import get_school_for_student_group

COURSE_PLACEHOLDER = "/assets/ifitwala_ed/images/course_placeholder.jpg"
COURSE_SCHEDULE_CACHE_PREFIX = "ifw:course_schedule:"
COURSE_SCHEDULE_TERM_PREFIX = f"{COURSE_SCHEDULE_CACHE_PREFIX}term:"
COURSE_SCHEDULE_ROTATION_PREFIX = f"{COURSE_SCHEDULE_CACHE_PREFIX}rotation:"
COURSE_SCHEDULE_DEPENDENT_PREFIXES = (
    COURSE_SCHEDULE_CACHE_PREFIX,
    "ifw:eff_sched_ay:",
    "effective_schedule::",
)
COURSE_SCHEDULE_CACHE_TTL = 21600
COURSE_SCHEDULE_CACHE_MISS = "__none__"
EFFECTIVE_SCHEDULE_AY_PREFIX = "ifw:eff_sched_ay:"
EFFECTIVE_SCHEDULE_CALENDAR_PREFIX = "effective_schedule::"


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


def _course_schedule_cache():
    return frappe.cache()


def _cache_key_for_term(term_name: str) -> str:
    return f"{COURSE_SCHEDULE_TERM_PREFIX}{term_name}"


def _cache_key_for_rotation(schedule_name: str, academic_year: str) -> str:
    return f"{COURSE_SCHEDULE_ROTATION_PREFIX}{schedule_name}:{academic_year}"


def _cache_shared_value(key: str, value):
    cached_value = value if value is not None else COURSE_SCHEDULE_CACHE_MISS
    _course_schedule_cache().set_value(key, cached_value, expires_in_sec=COURSE_SCHEDULE_CACHE_TTL)


def _get_cached_shared_value(key: str):
    cached = _course_schedule_cache().get_value(key)
    if cached == COURSE_SCHEDULE_CACHE_MISS:
        return True, None
    if cached is not None:
        return True, cached
    return False, None


def _get_term_window(term_name: str) -> dict:
    found, cached = _get_cached_shared_value(_cache_key_for_term(term_name))
    if found:
        return cached or {}

    info = (
        frappe.db.get_value(
            "Term",
            term_name,
            ["term_start_date", "term_end_date"],
            as_dict=True,
        )
        or None
    )
    _cache_shared_value(_cache_key_for_term(term_name), info)
    return info or {}


def _within_term(term_name: Optional[str], today: date) -> bool:
    if not term_name:
        return True

    info = _get_term_window(term_name)
    start, end = info.get("term_start_date"), info.get("term_end_date")
    if start and today < getdate(start):
        return False
    if end and today > getdate(end):
        return False
    return True


def _resolve_schedule_name(
    row: frappe._dict,
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

    return get_effective_schedule_for_ay(
        row.academic_year,
        base_school,
    )


def _get_rotation_lookup(schedule_name: str, academic_year: str) -> Dict[str, int]:
    key = _cache_key_for_rotation(schedule_name, academic_year)
    found, cached = _get_cached_shared_value(key)
    if found:
        return cached or {}

    rot_dates = (
        get_rotation_dates(
            schedule_name,
            academic_year,
            include_holidays=False,
        )
        or []
    )
    rotation_lookup = {rd["date"].isoformat(): int(rd["rotation_day"]) for rd in rot_dates}
    _cache_shared_value(key, rotation_lookup or None)
    return rotation_lookup


def _rotation_day_for(
    schedule_name: str,
    academic_year: str,
    today_iso: str,
) -> Optional[int]:
    return _get_rotation_lookup(schedule_name, academic_year).get(today_iso)


def _delete_cache_prefix(prefix: str) -> None:
    cache = _course_schedule_cache()
    for key in cache.get_keys(f"{prefix}*"):
        cache.delete_value(key)


def _delete_cache_key(key: str | None) -> None:
    if key:
        _course_schedule_cache().delete_value(key)


def _doc_value(doc, fieldname: str) -> str:
    value = getattr(doc, fieldname, None)
    if value is None and isinstance(doc, dict):
        value = doc.get(fieldname)
    return (value or "").strip()


def _academic_year_for_calendar(calendar_name: str) -> str:
    if not calendar_name:
        return ""
    return (frappe.db.get_value("School Calendar", calendar_name, "academic_year") or "").strip()


def _schedule_names_for_calendar(calendar_name: str) -> list[str]:
    if not calendar_name:
        return []
    rows = frappe.get_all(
        "School Schedule",
        filters={"school_calendar": calendar_name},
        fields=["name"],
    )
    return [(row.get("name") or "").strip() for row in rows or [] if (row.get("name") or "").strip()]


def _calendar_names_for_academic_year(academic_year: str) -> list[str]:
    if not academic_year:
        return []
    rows = frappe.get_all(
        "School Calendar",
        filters={"academic_year": academic_year},
        fields=["name"],
    )
    return [(row.get("name") or "").strip() for row in rows or [] if (row.get("name") or "").strip()]


def _delete_term_window_cache(term_name: str) -> None:
    _delete_cache_key(_cache_key_for_term(term_name))


def _delete_rotation_caches_for_schedule(schedule_name: str) -> None:
    if schedule_name:
        _delete_cache_prefix(f"{COURSE_SCHEDULE_ROTATION_PREFIX}{schedule_name}:")


def _delete_rotation_caches_for_calendar(calendar_name: str) -> None:
    for schedule_name in _schedule_names_for_calendar(calendar_name):
        _delete_rotation_caches_for_schedule(schedule_name)


def _delete_rotation_caches_for_academic_year(academic_year: str) -> None:
    for calendar_name in _calendar_names_for_academic_year(academic_year):
        _delete_rotation_caches_for_calendar(calendar_name)


def _delete_effective_schedule_caches_for_calendar(calendar_name: str) -> None:
    if calendar_name:
        _delete_cache_prefix(f"{EFFECTIVE_SCHEDULE_CALENDAR_PREFIX}{calendar_name}::")


def _delete_effective_schedule_caches_for_academic_year(academic_year: str) -> None:
    if academic_year:
        _delete_cache_prefix(f"{EFFECTIVE_SCHEDULE_AY_PREFIX}{academic_year}:")


def invalidate_course_schedule_cache(doc=None, _=None):
    """
    Clear shared course-schedule inputs plus the schedule-resolution keys this
    endpoint depends on.
    """
    if doc is not None:
        doctype = _doc_value(doc, "doctype")
        if doctype == "Term":
            _delete_term_window_cache(_doc_value(doc, "name"))
            return

        if doctype == "School Schedule":
            schedule_name = _doc_value(doc, "name")
            calendar_name = _doc_value(doc, "school_calendar")
            academic_year = _academic_year_for_calendar(calendar_name)
            _delete_rotation_caches_for_schedule(schedule_name)
            _delete_effective_schedule_caches_for_calendar(calendar_name)
            _delete_effective_schedule_caches_for_academic_year(academic_year)
            return

        if doctype == "School Calendar":
            calendar_name = _doc_value(doc, "name")
            academic_year = _doc_value(doc, "academic_year") or _academic_year_for_calendar(calendar_name)
            _delete_rotation_caches_for_calendar(calendar_name)
            _delete_effective_schedule_caches_for_calendar(calendar_name)
            _delete_effective_schedule_caches_for_academic_year(academic_year)
            return

        if doctype in {"School Calendar Holiday", "School Calendar Holidays"}:
            calendar_name = _doc_value(doc, "parent")
            academic_year = _academic_year_for_calendar(calendar_name)
            _delete_rotation_caches_for_calendar(calendar_name)
            _delete_effective_schedule_caches_for_calendar(calendar_name)
            _delete_effective_schedule_caches_for_academic_year(academic_year)
            return

        if doctype == "Academic Year":
            academic_year = _doc_value(doc, "name")
            _delete_rotation_caches_for_academic_year(academic_year)
            _delete_effective_schedule_caches_for_academic_year(academic_year)
            return

        if doctype == "School":
            _delete_cache_prefix(EFFECTIVE_SCHEDULE_AY_PREFIX)
            _delete_cache_prefix(EFFECTIVE_SCHEDULE_CALENDAR_PREFIX)
            return

    for prefix in COURSE_SCHEDULE_DEPENDENT_PREFIXES:
        _delete_cache_prefix(prefix)


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

    active_groups: Dict[str, dict] = {}
    for row in groups:
        if not _within_term(row.get("term"), today_dt):
            continue

        schedule_name = _resolve_schedule_name(row)

        if not schedule_name:
            continue

        rotation_day = _rotation_day_for(
            schedule_name,
            row.academic_year,
            today_iso,
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
