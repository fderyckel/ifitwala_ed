# ifitwala_ed/api/calendar_core.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import frappe
import pytz
from frappe.utils import get_datetime, get_system_timezone, getdate, now_datetime

VALID_SOURCES = {"student_group", "meeting", "school_event", "staff_holiday"}

DEFAULT_WINDOW_DAYS = 30
LOOKBACK_DAYS = 3
CACHE_TTL_SECONDS = 600
CAL_MIN_DURATION = timedelta(minutes=45)


@dataclass(slots=True)
class CalendarEvent:
    id: str
    title: str
    start: datetime
    end: datetime
    source: str
    color: str
    all_day: bool = False
    meta: Optional[dict] = None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "allDay": self.all_day,
            "source": self.source,
            "color": self.color,
            "meta": self.meta or {},
        }


def _resolve_employee_for_user(
    user: str,
    *,
    fields: Sequence[str] | None = None,
    employment_status_filter=None,
) -> Optional[dict]:
    """
    Resolve employee linkage for a user with legacy-safe fallback.

    Primary path:
    - Employee.user_id == user

    Fallback path (legacy data):
    - exactly one Employee matches employee_professional_email == User.email
    - user_id on that row is blank or already points to this same user
    """
    wanted_fields = list(fields or ["name"])
    if "name" not in wanted_fields:
        wanted_fields.append("name")

    direct_filters = {"user_id": user}
    if employment_status_filter is not None:
        direct_filters["employment_status"] = employment_status_filter

    direct_row = frappe.db.get_value("Employee", direct_filters, wanted_fields, as_dict=True)
    if direct_row:
        return direct_row

    login_email = (frappe.db.get_value("User", user, "email") or user or "").strip()
    if not login_email:
        return None

    fallback_filters = {"employee_professional_email": login_email}
    if employment_status_filter is not None:
        fallback_filters["employment_status"] = employment_status_filter

    fallback_rows = frappe.get_all(
        "Employee",
        filters=fallback_filters,
        fields=[*wanted_fields, "user_id"],
        limit_page_length=2,
    )
    if len(fallback_rows) != 1:
        return None

    row = fallback_rows[0]
    mapped_user = str(row.get("user_id") or "").strip()
    if mapped_user and mapped_user != user:
        return None

    return {field: row.get(field) for field in wanted_fields}


def _system_tzinfo() -> pytz.timezone:
    return pytz.timezone(get_system_timezone())


def _normalize_sources(raw) -> List[str]:
    if raw is None:
        return sorted(VALID_SOURCES)

    if isinstance(raw, str):
        parts = [part.strip() for part in raw.split(",")]
    else:
        parts = [str(part).strip() for part in (raw or [])]

    sources = [src for src in parts if src in VALID_SOURCES]
    if not sources:
        return sorted(VALID_SOURCES)

    ordered = []
    seen = set()
    for src in sources:
        if src not in seen:
            seen.add(src)
            ordered.append(src)
    return ordered


def _cache_key(employee: str, start: datetime, end: datetime, sources: Sequence[str]) -> str:
    src = "|".join(sorted(sources))
    return f"ifitwala_ed:portal_calendar:{employee}:{start.isoformat()}:{end.isoformat()}:{src}"


def _resolve_window(
    from_datetime: Optional[str],
    to_datetime: Optional[str],
    tzinfo: pytz.timezone,
) -> Tuple[datetime, datetime]:
    now = _localize_datetime(now_datetime(), tzinfo)

    if from_datetime:
        start = _to_system_datetime(from_datetime, tzinfo)
    else:
        start = tzinfo.localize(datetime.combine((now - timedelta(days=LOOKBACK_DAYS)).date(), time.min))

    if to_datetime:
        end = _to_system_datetime(to_datetime, tzinfo)
    else:
        end = start + timedelta(days=DEFAULT_WINDOW_DAYS)

    if end <= start:
        end = start + timedelta(days=DEFAULT_WINDOW_DAYS)

    return start, end


def _to_system_datetime(value: str | datetime, tzinfo: pytz.timezone) -> datetime:
    dt = get_datetime(value)
    if dt.tzinfo:
        return dt.astimezone(tzinfo)
    return tzinfo.localize(dt)


def _localize_datetime(dt: datetime, tzinfo: pytz.timezone) -> datetime:
    if dt.tzinfo:
        return dt.astimezone(tzinfo)
    return tzinfo.localize(dt)


def _coerce_time(value) -> Optional[time]:
    if value is None:
        return None

    if isinstance(value, time):
        return value

    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        if total < 0:
            return None
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return time(h % 24, m, s)

    if isinstance(value, datetime):
        return value.time().replace(tzinfo=None)

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="ignore")

    if isinstance(value, str):
        txt = value.strip()
        if not txt:
            return None
        try:
            parsed = get_datetime(f"2000-01-01 {txt}")
            return parsed.time().replace(tzinfo=None)
        except Exception:
            return None

    return None


def _time_to_str(raw, fallback: str = "00:00:00") -> str:
    parsed = _coerce_time(raw)
    if not parsed:
        return fallback
    return parsed.strftime("%H:%M:%S")


def _combine(date_obj: date, time_obj: Optional[time], tzinfo: pytz.timezone) -> datetime:
    t = time_obj or time.min
    return tzinfo.localize(datetime.combine(date_obj, t))


def _attach_duration(start_dt: datetime, end_dt: Optional[datetime]) -> timedelta:
    if not end_dt or end_dt <= start_dt:
        return CAL_MIN_DURATION
    return max(end_dt - start_dt, CAL_MIN_DURATION)


def _course_meta_map(course_ids: Iterable[str]) -> Dict[str, frappe._dict]:
    ids = sorted({cid for cid in course_ids if cid})
    if not ids:
        return {}

    rows = frappe.get_all(
        "Course",
        filters={"name": ["in", ids]},
        fields=["name", "course_name", "calendar_event_color"],
        ignore_permissions=True,
    )
    return {row.name: row for row in rows}


def _student_group_title_and_color(
    group_name: str,
    group_label: Optional[str],
    course_id: Optional[str],
    course_map: Dict[str, frappe._dict],
) -> Tuple[str, str]:
    course = course_map.get(course_id)
    title = (course.course_name if course and course.course_name else None) or group_label or group_name
    color = (course.calendar_event_color if course and course.calendar_event_color else None) or "#2563eb"
    return title, color


def _resolve_instructor_ids(user: str, employee_id: Optional[str]) -> set[str]:
    ids = set(
        frappe.get_all("Instructor", filters={"linked_user_id": user}, pluck="name", ignore_permissions=True) or []
    )
    if employee_id:
        ids.update(
            frappe.get_all("Instructor", filters={"employee": employee_id}, pluck="name", ignore_permissions=True) or []
        )
    return {i for i in ids if i}


def _student_group_memberships(
    user: str,
    employee_id: Optional[str],
    instructor_ids: set[str],
) -> Tuple[set[str], set[str]]:
    group_names: set[str] = set()

    def _consume(rows):
        for row in rows or []:
            parent = row.get("parent") if isinstance(row, dict) else None
            if parent:
                group_names.add(parent)
            uid = row.get("user_id") if isinstance(row, dict) else None
            if uid:
                instructor_ids.add(uid)

    fields = ["parent", "user_id"]

    base_filters = {"parenttype": "Student Group"}

    _consume(
        frappe.get_all(
            "Student Group Instructor",
            filters={**base_filters, "user_id": user},
            fields=fields,
            ignore_permissions=True,
        )
    )

    if employee_id:
        _consume(
            frappe.get_all(
                "Student Group Instructor",
                filters={**base_filters, "employee": employee_id},
                fields=fields,
                ignore_permissions=True,
            )
        )

    if instructor_ids:
        _consume(
            frappe.get_all(
                "Student Group Instructor",
                filters={**base_filters, "instructor": ["in", list(instructor_ids)]},
                fields=fields,
                ignore_permissions=True,
            )
        )

    return group_names, instructor_ids


def _meeting_window(
    meeting: frappe.model.document.Document, tzinfo: pytz.timezone
) -> Tuple[Optional[datetime], Optional[datetime]]:
    """
    Resolve Meeting start/end datetimes with sensible fallbacks so portal consumers
    can always display a window.
    """
    start_dt = None
    end_dt = None

    if meeting.from_datetime:
        start_dt = _to_system_datetime(meeting.from_datetime, tzinfo)
    elif meeting.date:
        start_dt = _combine(getdate(meeting.date), _coerce_time(meeting.start_time), tzinfo)

    if meeting.to_datetime:
        end_dt = _to_system_datetime(meeting.to_datetime, tzinfo)
    elif meeting.date:
        end_dt = _combine(getdate(meeting.date), _coerce_time(meeting.end_time), tzinfo)

    if start_dt and (not end_dt or end_dt <= start_dt):
        duration = _attach_duration(start_dt, end_dt)
        end_dt = start_dt + duration

    return start_dt, end_dt
