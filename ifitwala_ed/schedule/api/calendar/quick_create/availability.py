# ifitwala_ed/schedule/api/calendar/quick_create/availability.py

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime

from ifitwala_ed.schedule.api.calendar.core import _course_meta_map
from ifitwala_ed.schedule.api.calendar.quick_create.attendees import _resolve_attendee_contexts
from ifitwala_ed.schedule.api.calendar.quick_create.constants import (
    DEFAULT_DAY_END_TIME,
    DEFAULT_DAY_START_TIME,
    MAX_SLOT_ATTENDEES,
    MAX_SLOT_FALLBACKS,
    MAX_SLOT_SEARCH_DAYS,
    MAX_SLOT_SUGGESTIONS,
    SLOT_INCREMENT_MINUTES,
    SLOT_SUGGESTION_CACHE_TTL_SECONDS,
    StudentAvailabilityConflictError,
)
from ifitwala_ed.schedule.api.calendar.quick_create.dto import (
    _coerce_date_required,
    _coerce_flag,
    _coerce_minutes,
    _coerce_time_required,
    _combine_date_and_time_local,
    _format_slot_label,
    _json_cache_key,
    _parse_attendee_list,
    _safe_text,
)
from ifitwala_ed.schedule.api.calendar.quick_create.scope import (
    _ensure_allowed_location_type,
    _ensure_allowed_school,
    _ensure_can_create_meeting,
    _school_lineage,
)
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots


def _overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def _append_busy_window(
    busy_by_user: dict[str, list[tuple[datetime, datetime]]], user_id: str, start_dt, end_dt
) -> None:
    if not user_id or not start_dt or not end_dt:
        return
    start_value = get_datetime(start_dt)
    end_value = get_datetime(end_dt)
    if not start_value or not end_value or end_value <= start_value:
        return
    busy_by_user[user_id].append((start_value, end_value))


def _collect_employee_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    employee_to_user = {ctx["employee"]: ctx["user"] for ctx in contexts if ctx.get("employee")}
    if not employee_to_user or not frappe.db.table_exists("Employee Booking"):
        return

    rows = frappe.get_all(
        "Employee Booking",
        filters={
            "employee": ["in", list(employee_to_user.keys())],
            "from_datetime": ["<", window_end],
            "to_datetime": [">", window_start],
            "blocks_availability": 1,
        },
        fields=["employee", "from_datetime", "to_datetime"],
        limit=max(len(employee_to_user) * 20, 50),
    )
    for row in rows:
        user_id = employee_to_user.get(row.employee)
        if not user_id:
            continue
        _append_busy_window(busy_by_user, user_id, row.from_datetime, row.to_datetime)


def _collect_student_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    group_to_users: dict[str, set[str]] = defaultdict(set)
    for ctx in contexts:
        if ctx.get("kind") != "student":
            continue
        for group_name in ctx.get("student_groups") or set():
            group_to_users[group_name].add(ctx["user"])

    if not group_to_users:
        return

    start_date = window_start.date()
    end_date = window_end.date()
    for group_name, users in group_to_users.items():
        slots = iter_student_group_room_slots(group_name, start_date, end_date)
        for slot in slots:
            slot_start = get_datetime(slot.get("start"))
            slot_end = get_datetime(slot.get("end"))
            if not slot_start or not slot_end:
                continue
            if not _overlaps(slot_start, slot_end, window_start, window_end):
                continue
            for user_id in users:
                _append_busy_window(busy_by_user, user_id, slot_start, slot_end)


def _collect_meeting_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    users = [ctx["user"] for ctx in contexts if ctx.get("kind") != "employee"]
    if not users:
        return

    rows = frappe.db.sql(
        """
        SELECT
            mp.participant,
            m.from_datetime,
            m.to_datetime
        FROM `tabMeeting Participant` mp
        INNER JOIN `tabMeeting` m ON m.name = mp.parent
        WHERE
            mp.parenttype = 'Meeting'
            AND mp.participant IN %(users)s
            AND m.docstatus < 2
            AND COALESCE(m.status, 'Scheduled') != 'Cancelled'
            AND m.from_datetime < %(window_end)s
            AND m.to_datetime > %(window_start)s
        """,
        {
            "users": tuple(users),
            "window_start": window_start,
            "window_end": window_end,
        },
        as_dict=True,
    )
    for row in rows:
        _append_busy_window(busy_by_user, row.get("participant"), row.get("from_datetime"), row.get("to_datetime"))


def _collect_school_event_busy_windows(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> None:
    student_contexts = [ctx for ctx in contexts if ctx.get("kind") == "student"]
    guardian_contexts = [ctx for ctx in contexts if ctx.get("kind") == "guardian"]
    if not student_contexts and not guardian_contexts:
        return

    rows = frappe.db.sql(
        """
        SELECT
            name,
            school,
            starts_on,
            ends_on
        FROM `tabSchool Event`
        WHERE
            docstatus < 2
            AND starts_on < %(window_end)s
            AND ends_on > %(window_start)s
        """,
        {"window_start": window_start, "window_end": window_end},
        as_dict=True,
    )
    if not rows:
        return

    event_names = [row.get("name") for row in rows if row.get("name")]
    participants = frappe.get_all(
        "School Event Participant",
        filters={"parent": ["in", event_names]},
        fields=["parent", "participant"],
        limit=max(len(event_names) * 3, 20),
    )
    participant_map: dict[str, set[str]] = defaultdict(set)
    for row in participants:
        if row.parent and row.participant:
            participant_map[row.parent].add(row.participant)

    audience_rows = frappe.get_all(
        "School Event Audience",
        filters={"parent": ["in", event_names]},
        fields=["parent", "audience_type", "student_group", "include_guardians"],
        limit=max(len(event_names) * 3, 20),
    )
    audience_map: dict[str, list[dict]] = defaultdict(list)
    for row in audience_rows:
        if row.parent:
            audience_map[row.parent].append(row)

    student_lineage_map = {
        ctx["user"]: set(_school_lineage(ctx.get("school") or "")) for ctx in student_contexts if ctx.get("school")
    }
    guardian_lineage_map = {
        ctx["user"]: {
            lineage_school
            for school in (ctx.get("guardian_schools") or set())
            for lineage_school in _school_lineage(school)
        }
        for ctx in guardian_contexts
    }

    for row in rows:
        event_name = row.get("name")
        if not event_name:
            continue
        event_school = _safe_text(row.get("school"))
        start_dt = get_datetime(row.get("starts_on"))
        end_dt = get_datetime(row.get("ends_on"))
        if not start_dt or not end_dt or end_dt <= start_dt:
            continue

        explicit_users = participant_map.get(event_name) or set()
        for user_id in explicit_users:
            _append_busy_window(busy_by_user, user_id, start_dt, end_dt)

        for audience in audience_map.get(event_name) or []:
            audience_type = _safe_text(audience.get("audience_type"))
            student_group = _safe_text(audience.get("student_group"))
            include_guardians = cint(audience.get("include_guardians"))

            if audience_type in {"All Students", "All Students, Guardians, and Employees"}:
                for ctx in student_contexts:
                    lineage = student_lineage_map.get(ctx["user"]) or set()
                    if event_school and lineage and event_school not in lineage:
                        continue
                    _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)

            if audience_type in {"All Guardians", "All Students, Guardians, and Employees"}:
                for ctx in guardian_contexts:
                    lineage = guardian_lineage_map.get(ctx["user"]) or set()
                    if event_school and lineage and event_school not in lineage:
                        continue
                    _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)

            if audience_type == "Students in Student Group" and student_group:
                for ctx in student_contexts:
                    groups = ctx.get("student_groups") or set()
                    if student_group in groups:
                        _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)
                if include_guardians:
                    for ctx in guardian_contexts:
                        groups = ctx.get("guardian_groups") or set()
                        if student_group in groups:
                            _append_busy_window(busy_by_user, ctx["user"], start_dt, end_dt)


def _dedupe_busy_windows(
    busy_by_user: dict[str, list[tuple[datetime, datetime]]],
) -> dict[str, list[tuple[datetime, datetime]]]:
    deduped: dict[str, list[tuple[datetime, datetime]]] = {}
    for user_id, windows in busy_by_user.items():
        seen = set()
        normalized: list[tuple[datetime, datetime]] = []
        for start_dt, end_dt in sorted(windows, key=lambda item: (item[0], item[1])):
            key = (start_dt.isoformat(), end_dt.isoformat())
            if key in seen:
                continue
            seen.add(key)
            normalized.append((start_dt, end_dt))
        deduped[user_id] = normalized
    return deduped


def _format_conflict_reason(prefix: str, title: str, start_dt, end_dt) -> str:
    label = _safe_text(title) or prefix
    return _("{prefix}: {title} ({slot})").format(
        prefix=prefix,
        title=label,
        slot=_format_slot_label(get_datetime(start_dt), get_datetime(end_dt)),
    )


def _collect_student_schedule_conflict_labels(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, set[str]]:
    group_to_users: dict[str, set[str]] = defaultdict(set)
    for ctx in contexts:
        if ctx.get("kind") != "student":
            continue
        for group_name in ctx.get("student_groups") or set():
            group_to_users[group_name].add(ctx["user"])

    if not group_to_users:
        return {}

    group_rows = frappe.get_all(
        "Student Group",
        filters={"name": ["in", list(group_to_users.keys())]},
        fields=["name", "student_group_name", "course"],
        limit=max(len(group_to_users), 1),
    )
    group_meta = {row.name: row for row in group_rows if row.name}
    course_map = _course_meta_map(row.course for row in group_rows if row.course)

    reasons_by_user: dict[str, set[str]] = defaultdict(set)
    start_date = window_start.date()
    end_date = window_end.date()
    for group_name, users in group_to_users.items():
        meta = group_meta.get(group_name)
        course = course_map.get(meta.course) if meta and meta.course else None
        title = (course.course_name if course else None) or (meta.student_group_name if meta else None) or group_name
        for slot in iter_student_group_room_slots(group_name, start_date, end_date):
            slot_start = get_datetime(slot.get("start"))
            slot_end = get_datetime(slot.get("end"))
            if not slot_start or not slot_end or not _overlaps(slot_start, slot_end, window_start, window_end):
                continue
            reason = _format_conflict_reason(_("Class"), title, slot_start, slot_end)
            for user_id in users:
                reasons_by_user[user_id].add(reason)

    return reasons_by_user


def _collect_student_meeting_conflict_labels(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, set[str]]:
    users = [ctx["user"] for ctx in contexts if ctx.get("kind") == "student" and ctx.get("user")]
    if not users:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            mp.participant,
            m.meeting_name,
            m.from_datetime,
            m.to_datetime
        FROM `tabMeeting Participant` mp
        INNER JOIN `tabMeeting` m ON m.name = mp.parent
        WHERE
            mp.parenttype = 'Meeting'
            AND mp.participant IN %(users)s
            AND m.docstatus < 2
            AND COALESCE(m.status, 'Scheduled') != 'Cancelled'
            AND m.from_datetime < %(window_end)s
            AND m.to_datetime > %(window_start)s
        """,
        {
            "users": tuple(users),
            "window_start": window_start,
            "window_end": window_end,
        },
        as_dict=True,
    )
    if not rows:
        return {}

    reasons_by_user: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        participant = _safe_text(row.get("participant"))
        if not participant:
            continue
        reasons_by_user[participant].add(
            _format_conflict_reason(
                _("Meeting"),
                _safe_text(row.get("meeting_name")) or _("Meeting"),
                row.get("from_datetime"),
                row.get("to_datetime"),
            )
        )

    return reasons_by_user


def _collect_student_school_event_conflict_labels(
    contexts: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, set[str]]:
    student_contexts = [ctx for ctx in contexts if ctx.get("kind") == "student"]
    if not student_contexts:
        return {}

    rows = frappe.db.sql(
        """
        SELECT
            name,
            subject,
            school,
            starts_on,
            ends_on
        FROM `tabSchool Event`
        WHERE
            docstatus < 2
            AND starts_on < %(window_end)s
            AND ends_on > %(window_start)s
        """,
        {"window_start": window_start, "window_end": window_end},
        as_dict=True,
    )
    if not rows:
        return {}

    event_names = [row.get("name") for row in rows if row.get("name")]
    participant_rows = frappe.get_all(
        "School Event Participant",
        filters={"parent": ["in", event_names]},
        fields=["parent", "participant"],
        limit=max(len(event_names) * 3, 20),
    )
    participant_map: dict[str, set[str]] = defaultdict(set)
    for row in participant_rows:
        if row.parent and row.participant:
            participant_map[row.parent].add(row.participant)

    audience_rows = frappe.get_all(
        "School Event Audience",
        filters={"parent": ["in", event_names]},
        fields=["parent", "audience_type", "student_group"],
        limit=max(len(event_names) * 3, 20),
    )
    audience_map: dict[str, list[dict]] = defaultdict(list)
    for row in audience_rows:
        if row.parent:
            audience_map[row.parent].append(row)

    student_lineage_map = {
        ctx["user"]: set(_school_lineage(ctx.get("school") or "")) for ctx in student_contexts if ctx.get("user")
    }
    reasons_by_user: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        event_name = _safe_text(row.get("name"))
        if not event_name:
            continue

        reason = _format_conflict_reason(
            _("School event"),
            _safe_text(row.get("subject")) or _("School Event"),
            row.get("starts_on"),
            row.get("ends_on"),
        )
        for user_id in participant_map.get(event_name) or set():
            reasons_by_user[user_id].add(reason)

        event_school = _safe_text(row.get("school"))
        for audience in audience_map.get(event_name) or []:
            audience_type = _safe_text(audience.get("audience_type"))
            student_group = _safe_text(audience.get("student_group"))

            if audience_type in {"All Students", "All Students, Guardians, and Employees"}:
                for ctx in student_contexts:
                    lineage = student_lineage_map.get(ctx["user"]) or set()
                    if event_school and lineage and event_school not in lineage:
                        continue
                    reasons_by_user[ctx["user"]].add(reason)
                continue

            if audience_type == "Students in Student Group" and student_group:
                for ctx in student_contexts:
                    if student_group in (ctx.get("student_groups") or set()):
                        reasons_by_user[ctx["user"]].add(reason)

    return reasons_by_user


def _summarize_conflict_reasons(reasons: set[str]) -> str:
    ordered = sorted(reason for reason in reasons if _safe_text(reason))
    if not ordered:
        return _("Another school commitment in the selected window.")
    if len(ordered) <= 3:
        return "; ".join(ordered)
    return _("{visible}; and {remaining} more.").format(
        visible="; ".join(ordered[:3]),
        remaining=len(ordered) - 3,
    )


def _assert_students_available_for_meeting(
    *,
    attendees: list[dict],
    organizer_user: str,
    window_start: datetime,
    window_end: datetime,
    attendee_contexts: list[dict] | None = None,
) -> None:
    if not attendees or not window_start or not window_end or window_end <= window_start:
        return

    resolved_contexts = attendee_contexts or _resolve_attendee_contexts(attendees, organizer_user)
    contexts = [ctx for ctx in resolved_contexts if ctx.get("kind") == "student"]
    if not contexts:
        return

    busy_by_user: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    _collect_student_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_meeting_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_school_event_busy_windows(contexts, window_start, window_end, busy_by_user)
    busy_by_user = _dedupe_busy_windows(busy_by_user)
    reasons_by_user = defaultdict(set)
    for reason_map in (
        _collect_student_schedule_conflict_labels(contexts, window_start, window_end),
        _collect_student_meeting_conflict_labels(contexts, window_start, window_end),
        _collect_student_school_event_conflict_labels(contexts, window_start, window_end),
    ):
        for user_id, reasons in (reason_map or {}).items():
            reasons_by_user[user_id].update(reasons or set())

    blocked_lines: list[str] = []
    for ctx in contexts:
        user_id = _safe_text(ctx.get("user"))
        if not any(
            _overlaps(window_start, window_end, busy_start, busy_end)
            for busy_start, busy_end in (busy_by_user.get(user_id) or [])
        ):
            continue
        blocked_lines.append(
            _("{student}: {reasons}").format(
                student=_safe_text(ctx.get("label")) or user_id,
                reasons=_summarize_conflict_reasons(reasons_by_user.get(user_id) or set()),
            )
        )

    if not blocked_lines:
        return

    frappe.throw(
        "\n".join(
            [
                _("Student availability conflict for {slot}.").format(
                    slot=_format_slot_label(window_start, window_end),
                ),
                _("These students already have school commitments in that window:"),
                *blocked_lines,
                _("Choose another time or use Find common times first."),
            ]
        ),
        StudentAvailabilityConflictError,
    )


def _build_slot_payload(
    start_dt: datetime,
    end_dt: datetime,
    blocked_count: int,
    *,
    available_room_count: int | None = None,
    suggested_room: dict | None = None,
) -> dict:
    payload = {
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
        "date": start_dt.date().isoformat(),
        "start_time": start_dt.strftime("%H:%M"),
        "end_time": end_dt.strftime("%H:%M"),
        "label": _format_slot_label(start_dt, end_dt),
        "blocked_count": blocked_count,
    }
    if available_room_count is not None:
        payload["available_room_count"] = available_room_count
        payload["suggested_room"] = suggested_room
    return payload


def suggest_meeting_slots(
    *,
    attendees: object | None = None,
    duration_minutes: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    day_start_time: str | None = None,
    day_end_time: str | None = None,
    school: str | None = None,
    location_type: str | None = None,
    require_room: object | None = None,
):
    from ifitwala_ed.schedule.api.calendar.quick_create.rooms import (
        _available_room_suggestions_for_slot,
        _collect_room_busy_windows,
        _rank_room_suggestions,
        _room_rows_for_school_scope,
    )

    user = frappe.session.user
    _ensure_can_create_meeting(user)

    attendee_rows = _parse_attendee_list(attendees)
    attendee_count = len(attendee_rows)
    if attendee_count == 0:
        frappe.throw(_("Add at least one attendee before asking for common times."))
    if attendee_count > MAX_SLOT_ATTENDEES:
        frappe.throw(
            _("Quick scheduling supports up to {max_attendees} attendees at a time.").format(
                max_attendees=MAX_SLOT_ATTENDEES
            )
        )

    duration = _coerce_minutes(
        duration_minutes,
        default=60,
        minimum=15,
        maximum=240,
        label=_("Duration"),
    )
    start_date = _coerce_date_required(date_from, _("Start date"))
    end_date = _coerce_date_required(date_to, _("End date"))
    if end_date < start_date:
        frappe.throw(_("End date must be on or after Start date."))
    if (end_date - start_date).days + 1 > MAX_SLOT_SEARCH_DAYS:
        frappe.throw(_("Search window cannot exceed {max_days} days.").format(max_days=MAX_SLOT_SEARCH_DAYS))

    day_start = _coerce_time_required(day_start_time or DEFAULT_DAY_START_TIME, _("Earliest start"))
    day_end = _coerce_time_required(day_end_time or DEFAULT_DAY_END_TIME, _("Latest end"))
    if _combine_date_and_time_local(start_date, day_end) <= _combine_date_and_time_local(start_date, day_start):
        frappe.throw(_("Latest end must be later than earliest start."))

    require_room_value = _coerce_flag(require_room)
    school_value = None
    location_type_value = None
    if require_room_value:
        school_value = _ensure_allowed_school(user, school)
        if not school_value:
            frappe.throw(_("Host school is required before room-aware common times can be ranked."))
        location_type_value = _ensure_allowed_location_type(user, school_value, location_type)

    cache_key = _json_cache_key(
        "ifitwala_ed:event_quick_create:slot_suggestions",
        {
            "user": user,
            "attendees": attendee_rows,
            "duration": duration,
            "date_from": start_date.isoformat(),
            "date_to": end_date.isoformat(),
            "day_start_time": str(day_start),
            "day_end_time": str(day_end),
            "school": school_value,
            "location_type": location_type_value,
            "require_room": require_room_value,
        },
    )
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    window_start = _combine_date_and_time_local(start_date, day_start)
    window_end = _combine_date_and_time_local(end_date, day_end)
    contexts = _resolve_attendee_contexts(attendee_rows, user)

    busy_by_user: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    _collect_employee_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_student_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_meeting_busy_windows(contexts, window_start, window_end, busy_by_user)
    _collect_school_event_busy_windows(contexts, window_start, window_end, busy_by_user)
    busy_by_user = _dedupe_busy_windows(busy_by_user)

    ranked_room_candidates: list[dict] = []
    busy_by_room: dict[str, list[tuple[datetime, datetime]]] = {}
    room_capacity_target = attendee_count + 1
    if require_room_value and school_value:
        ranked_room_candidates = _rank_room_suggestions(
            _room_rows_for_school_scope(
                school_value,
                room_capacity_target,
                location_type=location_type_value,
            ),
            capacity_needed=room_capacity_target,
        )
        busy_by_room = _collect_room_busy_windows(ranked_room_candidates, window_start, window_end)

    duration_delta = timedelta(minutes=duration)
    exact_slots: list[dict] = []
    fallback_slots: list[dict] = []
    room_blocked_exact_slots = 0
    cursor_day = start_date
    while cursor_day <= end_date:
        cursor = _combine_date_and_time_local(cursor_day, day_start)
        day_end_dt = _combine_date_and_time_local(cursor_day, day_end)
        while cursor + duration_delta <= day_end_dt:
            slot_end = cursor + duration_delta
            blocked_count = 0
            for ctx in contexts:
                user_windows = busy_by_user.get(ctx["user"]) or []
                if any(_overlaps(cursor, slot_end, busy_start, busy_end) for busy_start, busy_end in user_windows):
                    blocked_count += 1
            available_rooms = []
            available_room_count = None
            suggested_room = None
            if require_room_value:
                available_rooms = _available_room_suggestions_for_slot(
                    cursor,
                    slot_end,
                    ranked_room_candidates,
                    busy_by_room,
                )
                available_room_count = len(available_rooms)
                suggested_room = available_rooms[0] if available_rooms else None

            payload = _build_slot_payload(
                cursor,
                slot_end,
                blocked_count,
                available_room_count=available_room_count,
                suggested_room=suggested_room,
            )
            if blocked_count == 0 and require_room_value and not available_rooms:
                room_blocked_exact_slots += 1
            elif blocked_count == 0 and len(exact_slots) < MAX_SLOT_SUGGESTIONS:
                exact_slots.append(payload)
            elif blocked_count > 0 and len(fallback_slots) < 50:
                fallback_slots.append(payload)
            cursor += timedelta(minutes=SLOT_INCREMENT_MINUTES)
        cursor_day += timedelta(days=1)

    fallback_slots.sort(key=lambda item: (item.get("blocked_count") or 0, item.get("start") or ""))
    fallback_slots = fallback_slots[:MAX_SLOT_FALLBACKS]

    notes: list[str] = []
    if any(ctx.get("kind") == "student" for ctx in contexts):
        notes.append(_("Student availability is checked against school timetable, meetings, and school events."))
    if any(ctx.get("kind") == "guardian" for ctx in contexts):
        notes.append(_("Guardian availability is limited to known school-side meetings and events."))
    if require_room_value:
        if ranked_room_candidates:
            notes.append(_("Exact matches already include at least one free room in the selected school scope."))
        else:
            notes.append(_("No rooms are configured for the selected school scope."))
        if location_type_value:
            notes.append(
                _("Room ranking is limited to location type {location_type}.").format(location_type=location_type_value)
            )
        if room_blocked_exact_slots:
            notes.append(
                _(
                    "{blocked_slots} attendee-free slot(s) were excluded because no room was free in the selected school scope."
                ).format(blocked_slots=room_blocked_exact_slots)
            )

    payload = {
        "slots": exact_slots,
        "fallback_slots": fallback_slots,
        "notes": notes,
        "duration_minutes": duration,
        "attendees": [
            {
                "user": ctx["user"],
                "label": ctx["label"],
                "kind": ctx["kind"],
                "availability_mode": ctx["availability_mode"],
            }
            for ctx in contexts
        ],
    }
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=SLOT_SUGGESTION_CACHE_TTL_SECONDS)
    return payload
