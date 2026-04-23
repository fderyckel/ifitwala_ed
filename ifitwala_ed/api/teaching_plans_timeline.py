from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any


def timeline_blocked(api, reason: str, message: str) -> dict[str, Any]:
    return {
        "status": "blocked",
        "reason": reason,
        "message": message,
        "scope": {},
        "terms": [],
        "holidays": [],
        "units": [],
        "summary": {
            "scheduled_unit_count": 0,
            "unscheduled_unit_count": 0,
            "overflow_unit_count": 0,
            "instructional_day_count": 0,
        },
    }


def timeline_weekday_js(api, value: date) -> int:
    return (value.weekday() + 1) % 7


def timeline_duration_weeks(api, value: str | None) -> int | None:
    text = api.planning.normalize_text(value)
    if not text:
        return None

    if text.isdigit():
        weeks = int(text)
        return weeks if weeks > 0 else None

    match = re.fullmatch(r"(\d+)\s*(?:week|weeks|wk|wks)\b", text.lower())
    if not match:
        return None

    weeks = int(match.group(1) or 0)
    return weeks if weeks > 0 else None


def coerce_curriculum_anchor_date(api, value: Any | None = None) -> date:
    if value in (None, ""):
        return api.now_datetime().date()

    try:
        parsed = api.get_datetime(value)
        if isinstance(parsed, datetime):
            return parsed.date()
    except Exception:
        pass

    try:
        return api.getdate(value)
    except Exception:
        return api.now_datetime().date()


def _row_value(row: Any, fieldname: str) -> Any:
    if isinstance(row, dict):
        return row.get(fieldname)
    return getattr(row, fieldname, None)


def _unit_lookup_by_plan(api, units: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        api.planning.normalize_text(unit.get("unit_plan")): unit
        for unit in units or []
        if api.planning.normalize_text(unit.get("unit_plan"))
    }


def _session_sort_key(api, unit_index: int, session: dict[str, Any]) -> tuple[int, int, str]:
    status = api.planning.normalize_text(session.get("session_status"))
    return (
        {
            "In Progress": 0,
            "Planned": 1,
            "Draft": 2,
            "Taught": 3,
            "Changed": 4,
            "Canceled": 5,
        }.get(status, 99),
        unit_index,
        int(session.get("sequence_index") or 0),
    )


def _find_session_unit_by_anchor(
    api,
    units: list[dict[str, Any]],
    *,
    anchor_date: date,
    exact_only: bool = False,
) -> dict[str, Any] | None:
    exact: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
    future: list[tuple[date, tuple[int, int, str], dict[str, Any]]] = []
    previous: list[tuple[date, tuple[int, int, str], dict[str, Any]]] = []
    undated: list[tuple[tuple[int, int, str], dict[str, Any]]] = []

    for unit_index, unit in enumerate(units or []):
        for session in unit.get("sessions") or []:
            status = api.planning.normalize_text(session.get("session_status")).lower()
            if status in {"changed", "canceled"}:
                continue

            sort_key = _session_sort_key(api, unit_index, session)
            session_date = session.get("session_date")
            if session_date:
                try:
                    resolved_date = api.getdate(session_date)
                except Exception:
                    resolved_date = None
            else:
                resolved_date = None

            if resolved_date == anchor_date:
                exact.append((sort_key, unit))
                continue
            if exact_only:
                continue
            if resolved_date and resolved_date > anchor_date:
                future.append((resolved_date, sort_key, unit))
                continue
            if resolved_date and resolved_date < anchor_date:
                previous.append((resolved_date, sort_key, unit))
                continue
            undated.append((sort_key, unit))

    if exact:
        exact.sort(key=lambda row: row[0])
        return exact[0][1]
    if exact_only:
        return None
    if future:
        future.sort(key=lambda row: (row[0], row[1]))
        return future[0][2]
    if previous:
        previous.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return previous[0][2]
    if undated:
        undated.sort(key=lambda row: row[0])
        return undated[0][1]
    return None


def resolve_timeline_current_unit(
    api,
    timeline: dict[str, Any],
    *,
    anchor_date: Any | None = None,
) -> dict[str, Any] | None:
    if (timeline or {}).get("status") != "ready":
        return None

    resolved_anchor = api._coerce_curriculum_anchor_date(anchor_date)
    scheduled_units: list[tuple[date, date, dict[str, Any]]] = []
    for unit in (timeline or {}).get("units") or []:
        start_date = unit.get("start_date")
        end_date = unit.get("end_date")
        if not start_date or not end_date:
            continue
        try:
            scheduled_units.append((api.getdate(start_date), api.getdate(end_date), unit))
        except Exception:
            continue

    if not scheduled_units:
        return None

    scheduled_units.sort(
        key=lambda row: (
            row[0],
            int(row[2].get("unit_order") or 0) <= 0,
            int(row[2].get("unit_order") or 0),
            api.planning.normalize_text(row[2].get("unit_plan") or row[2].get("title")),
        )
    )

    active = [row for row in scheduled_units if row[0] <= resolved_anchor <= row[1]]
    if active:
        return active[0][2]

    previous = [row for row in scheduled_units if row[1] < resolved_anchor]
    if previous:
        return previous[-1][2]

    upcoming = [row for row in scheduled_units if row[0] > resolved_anchor]
    if upcoming:
        return upcoming[0][2]

    return scheduled_units[0][2]


def resolve_current_curriculum_unit(
    api,
    units: list[dict[str, Any]],
    *,
    course_plan_row: dict[str, Any] | None = None,
    student_group: str | None = None,
    class_unit_rows: list[Any] | None = None,
    anchor_date: Any | None = None,
    allow_live_session: bool = True,
) -> dict[str, Any]:
    resolved_anchor = api._coerce_curriculum_anchor_date(anchor_date)
    unit_lookup = _unit_lookup_by_plan(api, units)
    timeline_payload = None

    if allow_live_session:
        live_candidates: list[tuple[tuple[int, int, str], dict[str, Any]]] = []
        for unit_index, unit in enumerate(units or []):
            for session in unit.get("sessions") or []:
                if api.planning.normalize_text(session.get("session_status")).lower() != "in progress":
                    continue
                live_candidates.append((_session_sort_key(api, unit_index, session), unit))
        if live_candidates:
            live_candidates.sort(key=lambda row: row[0])
            selected_unit = live_candidates[0][1]
            unit_plan = api.planning.normalize_text(selected_unit.get("unit_plan"))
            return {
                "unit_plan": unit_plan or None,
                "unit": unit_lookup.get(unit_plan) or selected_unit,
                "source": "live_session",
                "timeline": None,
            }

    progress_source = class_unit_rows if class_unit_rows is not None else units
    in_progress_units: list[str] = []
    for row in progress_source or []:
        if api.planning.normalize_text(_row_value(row, "pacing_status")).lower() != "in progress":
            continue
        unit_plan = api.planning.normalize_text(_row_value(row, "unit_plan"))
        if unit_plan and unit_plan in unit_lookup and unit_plan not in in_progress_units:
            in_progress_units.append(unit_plan)
    if len(in_progress_units) == 1:
        unit_plan = in_progress_units[0]
        return {
            "unit_plan": unit_plan,
            "unit": unit_lookup.get(unit_plan),
            "source": "in_progress_unit",
            "timeline": None,
        }

    if course_plan_row and units:
        timeline_payload = api._build_course_plan_timeline(
            course_plan_row,
            units,
            student_group=api.planning.normalize_text(student_group) or None,
        )
        timeline_unit = api._resolve_timeline_current_unit(timeline_payload, anchor_date=resolved_anchor)
        if timeline_unit:
            unit_plan = api.planning.normalize_text(timeline_unit.get("unit_plan"))
            return {
                "unit_plan": unit_plan or None,
                "unit": unit_lookup.get(unit_plan),
                "source": "calendar",
                "timeline": timeline_payload,
            }

    exact_session_unit = _find_session_unit_by_anchor(api, units, anchor_date=resolved_anchor, exact_only=True)
    if exact_session_unit:
        unit_plan = api.planning.normalize_text(exact_session_unit.get("unit_plan"))
        return {
            "unit_plan": unit_plan or None,
            "unit": unit_lookup.get(unit_plan) or exact_session_unit,
            "source": "dated_session",
            "timeline": timeline_payload,
        }

    nearest_session_unit = _find_session_unit_by_anchor(api, units, anchor_date=resolved_anchor, exact_only=False)
    if nearest_session_unit:
        unit_plan = api.planning.normalize_text(nearest_session_unit.get("unit_plan"))
        return {
            "unit_plan": unit_plan or None,
            "unit": unit_lookup.get(unit_plan) or nearest_session_unit,
            "source": "nearest_session",
            "timeline": timeline_payload,
        }

    return {
        "unit_plan": None,
        "unit": None,
        "source": "none",
        "timeline": timeline_payload,
    }


def resolve_course_plan_timeline_scope(
    api,
    course_plan_row: dict[str, Any],
    *,
    student_group: str | None = None,
) -> dict[str, Any]:
    academic_year = api.planning.normalize_text(course_plan_row.get("academic_year"))
    if not academic_year:
        return api._timeline_blocked(
            "missing_academic_year",
            api._("Add an Academic Year to this course plan before using the curriculum timeline."),
        )

    academic_year_row = api.frappe.db.get_value(
        "Academic Year",
        academic_year,
        ["name", "year_start_date", "year_end_date"],
        as_dict=True,
    )
    if (
        not academic_year_row
        or not academic_year_row.get("year_start_date")
        or not academic_year_row.get("year_end_date")
    ):
        return api._timeline_blocked(
            "missing_academic_year_window",
            api._(
                "This Academic Year is missing its start or end date, so the curriculum timeline cannot be shown yet."
            ),
        )

    scope = {
        "mode": "academic_year",
        "academic_year": academic_year,
        "school": api.planning.normalize_text(course_plan_row.get("school")) or None,
        "student_group": None,
        "student_group_label": None,
        "term": None,
        "term_label": None,
        "window_start": api._serialize_scalar(academic_year_row.get("year_start_date")),
        "window_end": api._serialize_scalar(academic_year_row.get("year_end_date")),
    }

    selected_school = api.planning.normalize_text(course_plan_row.get("school"))
    selected_term = ""
    if student_group:
        api._assert_staff_group_access(student_group)
        group_row = api.planning.get_student_group_row(student_group)
        if api.planning.normalize_text(group_row.get("course")) != api.planning.normalize_text(
            course_plan_row.get("course")
        ):
            api.frappe.throw(api._("Selected class does not belong to this course plan."), api.frappe.ValidationError)
        group_academic_year = api.planning.normalize_text(group_row.get("academic_year"))
        if group_academic_year and group_academic_year != academic_year:
            api.frappe.throw(
                api._("Selected class does not belong to this course plan academic year."),
                api.frappe.ValidationError,
            )

        selected_school = api.planning.normalize_text(group_row.get("school")) or selected_school
        selected_term = api.planning.normalize_text(group_row.get("term"))
        scope["student_group"] = api.planning.normalize_text(group_row.get("name")) or None
        scope["student_group_label"] = (
            api.planning.normalize_text(group_row.get("student_group_name"))
            or api.planning.normalize_text(group_row.get("student_group_abbreviation"))
            or api.planning.normalize_text(group_row.get("name"))
            or None
        )

    if selected_term:
        term_row = api.frappe.db.get_value(
            "Term",
            selected_term,
            ["name", "term_start_date", "term_end_date", "academic_year"],
            as_dict=True,
        )
        if term_row and term_row.get("term_start_date") and term_row.get("term_end_date"):
            term_academic_year = api.planning.normalize_text(term_row.get("academic_year"))
            if not term_academic_year or term_academic_year == academic_year:
                scope["mode"] = "student_group_term"
                scope["term"] = api.planning.normalize_text(term_row.get("name")) or None
                scope["term_label"] = api.planning.normalize_text(term_row.get("name")) or None
                scope["window_start"] = api._serialize_scalar(term_row.get("term_start_date"))
                scope["window_end"] = api._serialize_scalar(term_row.get("term_end_date"))

    if not selected_school:
        return api._timeline_blocked(
            "missing_school",
            api._("This course plan is missing its school scope, so the curriculum timeline cannot be resolved."),
        )
    scope["school"] = selected_school
    return {"status": "ready", "scope": scope}


def fetch_timeline_calendar_terms(
    api,
    school_calendar: str,
    *,
    window_start: date,
    window_end: date,
) -> list[dict[str, Any]]:
    rows = api.frappe.get_all(
        "School Calendar Term",
        filters={
            "parent": school_calendar,
            "parenttype": "School Calendar",
            "parentfield": "terms",
        },
        fields=["term", "start", "end", "number_of_instructional_days"],
        order_by="start asc, idx asc",
        limit=0,
    )
    payload: list[dict[str, Any]] = []
    for row in rows or []:
        start_value = row.get("start")
        end_value = row.get("end")
        if not start_value or not end_value:
            continue
        start_date = max(window_start, api.getdate(start_value))
        end_date = min(window_end, api.getdate(end_value))
        if end_date < window_start or start_date > window_end or end_date < start_date:
            continue
        payload.append(
            {
                "term": row.get("term"),
                "label": row.get("term"),
                "start_date": api._serialize_scalar(start_date),
                "end_date": api._serialize_scalar(end_date),
                "instructional_days": int(row.get("number_of_instructional_days") or 0),
            }
        )
    return payload


def fetch_timeline_holiday_spans(
    api,
    school_calendar: str,
    *,
    window_start: date,
    window_end: date,
    weekend_days: list[int] | tuple[int, ...] | set[int] | None = None,
) -> list[dict[str, Any]]:
    rows = api.frappe.get_all(
        "School Calendar Holidays",
        filters={
            "parent": school_calendar,
            "parenttype": "School Calendar",
            "parentfield": "holidays",
            "weekly_off": 0,
            "holiday_date": ["between", [window_start, window_end]],
        },
        fields=["holiday_date", "description"],
        order_by="holiday_date asc, idx asc",
        limit=0,
    )
    spans: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    seen_titles: set[str] = set()
    weekend_day_set = {int(day) for day in (weekend_days or [])}

    for row in rows or []:
        holiday_date = row.get("holiday_date")
        if not holiday_date:
            continue
        holiday_day = api.getdate(holiday_date)
        title = api.planning.normalize_text(row.get("description")) or api._("Holiday")
        if not current:
            current = {
                "start_date": holiday_day,
                "end_date": holiday_day,
                "titles": [title],
                "day_count": 1,
            }
            seen_titles = {title}
            continue
        gap_is_weekend_bridge = False
        if holiday_day > current["end_date"] + timedelta(days=1):
            gap_cursor = current["end_date"] + timedelta(days=1)
            gap_is_weekend_bridge = True
            while gap_cursor < holiday_day:
                if api._timeline_weekday_js(gap_cursor) not in weekend_day_set:
                    gap_is_weekend_bridge = False
                    break
                gap_cursor += timedelta(days=1)

        if holiday_day == current["end_date"] + timedelta(days=1) or gap_is_weekend_bridge:
            current["end_date"] = holiday_day
            current["day_count"] = (current["end_date"] - current["start_date"]).days + 1
            if title not in seen_titles:
                current["titles"].append(title)
                seen_titles.add(title)
            continue
        spans.append(
            {
                "start_date": api._serialize_scalar(current["start_date"]),
                "end_date": api._serialize_scalar(current["end_date"]),
                "titles": current["titles"],
                "day_count": current["day_count"],
            }
        )
        current = {
            "start_date": holiday_day,
            "end_date": holiday_day,
            "titles": [title],
            "day_count": 1,
        }
        seen_titles = {title}

    if current:
        spans.append(
            {
                "start_date": api._serialize_scalar(current["start_date"]),
                "end_date": api._serialize_scalar(current["end_date"]),
                "titles": current["titles"],
                "day_count": current["day_count"],
            }
        )
    return spans


def build_course_plan_timeline(
    api,
    course_plan_row: dict[str, Any],
    units: list[dict[str, Any]],
    *,
    student_group: str | None = None,
) -> dict[str, Any]:
    from ifitwala_ed.schedule.schedule_utils import get_calendar_holiday_set, get_weekend_days_for_calendar
    from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window

    scope_payload = api._resolve_course_plan_timeline_scope(course_plan_row, student_group=student_group)
    if scope_payload.get("status") != "ready":
        return scope_payload

    scope = scope_payload["scope"]
    window_start = api.get_datetime(scope["window_start"]).date()
    window_end = api.get_datetime(scope["window_end"]).date()

    calendar_rows = resolve_school_calendars_for_window(scope.get("school"), window_start, window_end)
    school_calendar_row = next(
        (
            row
            for row in (calendar_rows or [])
            if api.planning.normalize_text(row.get("academic_year"))
            == api.planning.normalize_text(scope.get("academic_year"))
        ),
        None,
    )
    if not school_calendar_row:
        return api._timeline_blocked(
            "missing_school_calendar",
            api._(
                "No School Calendar is available for this timeline window. Add or resolve the school calendar first."
            ),
        )

    school_calendar = api.planning.normalize_text(school_calendar_row.get("name"))
    weekend_days = get_weekend_days_for_calendar(school_calendar)
    holiday_dates = {
        holiday_date
        for holiday_date in get_calendar_holiday_set(school_calendar)
        if window_start <= holiday_date <= window_end
    }
    instructional_dates: list[date] = []
    cursor = window_start
    while cursor <= window_end:
        if api._timeline_weekday_js(cursor) not in weekend_days and cursor not in holiday_dates:
            instructional_dates.append(cursor)
        cursor += timedelta(days=1)

    if not instructional_dates:
        return api._timeline_blocked(
            "empty_instructional_window",
            api._(
                "No instructional days are available in this timeline window after weekends and holidays are applied."
            ),
        )

    instructional_days_per_week = max(1, 7 - len(set(weekend_days)))
    holiday_spans = api._fetch_timeline_holiday_spans(
        school_calendar,
        window_start=window_start,
        window_end=window_end,
        weekend_days=weekend_days,
    )
    term_rows = api._fetch_timeline_calendar_terms(
        school_calendar,
        window_start=window_start,
        window_end=window_end,
    )

    current_instructional_index = 0
    blocked_by_unresolved = False
    payload_units: list[dict[str, Any]] = []
    scheduled_unit_count = 0
    unscheduled_unit_count = 0
    overflow_unit_count = 0

    for unit in units:
        unit_duration_weeks = api._timeline_duration_weeks(unit.get("duration"))
        unit_payload = {
            "unit_plan": unit.get("unit_plan"),
            "title": unit.get("title") or unit.get("unit_plan"),
            "unit_order": unit.get("unit_order"),
            "duration_label": unit.get("duration"),
            "duration_weeks": unit_duration_weeks,
            "unit_status": unit.get("unit_status"),
            "is_published": int(unit.get("is_published") or 0),
            "start_date": None,
            "end_date": None,
            "instructional_day_count": None,
            "calendar_day_span": None,
            "overflow": 0,
            "is_current": 0,
            "schedule_state": "scheduled",
            "message": None,
        }

        if blocked_by_unresolved:
            unit_payload["schedule_state"] = "blocked"
            unit_payload["message"] = api._(
                "A previous unit is missing a usable week duration, so the remaining sequence cannot be scheduled yet."
            )
            unscheduled_unit_count += 1
            payload_units.append(unit_payload)
            continue

        if not unit_duration_weeks:
            unit_payload["schedule_state"] = "unscheduled_duration"
            unit_payload["message"] = api._(
                "Add a numeric week duration such as '6 weeks' before this unit can appear on the curriculum timeline."
            )
            blocked_by_unresolved = True
            unscheduled_unit_count += 1
            payload_units.append(unit_payload)
            continue

        needed_instructional_days = unit_duration_weeks * instructional_days_per_week
        unit_payload["instructional_day_count"] = needed_instructional_days

        if current_instructional_index >= len(instructional_dates):
            unit_payload["schedule_state"] = "overflow"
            unit_payload["overflow"] = 1
            unit_payload["message"] = api._(
                "This unit starts after the selected timeline window because earlier units already use all available instructional days."
            )
            unscheduled_unit_count += 1
            overflow_unit_count += 1
            payload_units.append(unit_payload)
            continue

        end_index = current_instructional_index + needed_instructional_days - 1
        start_date = instructional_dates[current_instructional_index]
        overflow = end_index >= len(instructional_dates)
        end_date = instructional_dates[min(end_index, len(instructional_dates) - 1)]

        unit_payload["start_date"] = api._serialize_scalar(start_date)
        unit_payload["end_date"] = api._serialize_scalar(end_date)
        unit_payload["calendar_day_span"] = (end_date - start_date).days + 1
        unit_payload["overflow"] = 1 if overflow else 0
        if overflow:
            unit_payload["schedule_state"] = "overflow"
            unit_payload["message"] = api._(
                "This unit extends past the selected timeline window after holidays and other non-instructional days are applied."
            )
            overflow_unit_count += 1
        else:
            scheduled_unit_count += 1

        payload_units.append(unit_payload)
        current_instructional_index = min(end_index + 1, len(instructional_dates))

    payload = {
        "status": "ready",
        "reason": None,
        "message": None,
        "scope": {
            **scope,
            "school_calendar": school_calendar,
        },
        "terms": term_rows,
        "holidays": holiday_spans,
        "units": payload_units,
        "summary": {
            "scheduled_unit_count": scheduled_unit_count,
            "unscheduled_unit_count": unscheduled_unit_count,
            "overflow_unit_count": overflow_unit_count,
            "instructional_day_count": len(instructional_dates),
        },
    }
    current_unit = api._resolve_timeline_current_unit(payload, anchor_date=api.now_datetime())
    current_unit_plan = api.planning.normalize_text((current_unit or {}).get("unit_plan"))
    for unit in payload_units:
        unit["is_current"] = int(api.planning.normalize_text(unit.get("unit_plan")) == current_unit_plan)
    return payload
