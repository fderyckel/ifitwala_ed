# ifitwala_ed/schedule/api/calendar/quick_create/rooms.py

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.schedule.api.calendar.quick_create.availability import (
    _append_busy_window,
    _dedupe_busy_windows,
    _overlaps,
)
from ifitwala_ed.schedule.api.calendar.quick_create.dto import (
    _coerce_date_required,
    _coerce_minutes,
    _coerce_time_required,
    _combine_date_and_time_local,
)
from ifitwala_ed.schedule.api.calendar.quick_create.scope import (
    _ensure_allowed_location,
    _ensure_allowed_location_type,
    _ensure_allowed_school,
    _ensure_can_create_meeting,
)
from ifitwala_ed.utilities.location_utils import (
    find_room_conflicts,
    get_location_scope,
    get_visible_location_rows_for_school,
)


def _room_rows_for_school_scope(school: str, capacity_needed: int, *, location_type: str | None = None) -> list[dict]:
    return get_visible_location_rows_for_school(
        school,
        include_groups=False,
        only_schedulable=True,
        location_types=[location_type] if location_type else None,
        capacity_needed=capacity_needed if capacity_needed > 0 else None,
        fields=[
            "name",
            "location_name",
            "parent_location",
            "maximum_capacity",
            "location_type",
            "is_group",
        ],
        order_by="location_name asc",
        limit=300,
    )


def _rank_room_suggestions(room_rows: list[dict], *, capacity_needed: int) -> list[dict]:
    ranked: list[dict] = []
    for row in room_rows:
        room_name = row.get("name")
        if not room_name:
            continue
        max_capacity = cint(row.get("maximum_capacity")) if row.get("maximum_capacity") is not None else None
        capacity_delta = (
            max(max_capacity - capacity_needed, 0) if max_capacity is not None and capacity_needed > 0 else 9999
        )
        ranked.append(
            {
                "value": room_name,
                "label": row.get("location_name") or room_name,
                "building": row.get("parent_location"),
                "location_type": row.get("location_type"),
                "location_type_name": row.get("location_type_name"),
                "max_capacity": max_capacity,
                "_capacity_delta": capacity_delta,
            }
        )

    ranked.sort(
        key=lambda item: (
            item.get("_capacity_delta", 9999),
            item.get("max_capacity") is None,
            item.get("label") or "",
        )
    )

    return [
        {
            "value": row["value"],
            "label": row["label"],
            "building": row.get("building"),
            "location_type": row.get("location_type"),
            "location_type_name": row.get("location_type_name"),
            "max_capacity": row.get("max_capacity"),
        }
        for row in ranked
    ]


def _collect_room_conflicts_by_candidate(
    room_names: list[str],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, list[tuple[datetime, datetime]]]:
    if not room_names:
        return {}

    location_to_rooms: dict[str, set[str]] = defaultdict(set)
    scoped_locations: set[str] = set()
    for room_name in room_names:
        scope = get_location_scope(room_name, include_children=True) or [room_name]
        for location in scope:
            if not location:
                continue
            scoped_locations.add(location)
            location_to_rooms[location].add(room_name)

    if not scoped_locations:
        return {}

    busy_by_room: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    conflicts = find_room_conflicts(
        None,
        window_start,
        window_end,
        locations=scoped_locations,
        include_children=False,
    )
    for row in conflicts:
        for room_name in location_to_rooms.get(row.get("location"), set()):
            _append_busy_window(busy_by_room, room_name, row.get("from"), row.get("to"))
    return _dedupe_busy_windows(busy_by_room)


def _collect_room_busy_windows(
    room_suggestions: list[dict],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, list[tuple[datetime, datetime]]]:
    room_names = [row.get("value") for row in room_suggestions if row.get("value")]
    return _collect_room_conflicts_by_candidate(room_names, window_start, window_end)


def _available_room_suggestions_for_slot(
    slot_start: datetime,
    slot_end: datetime,
    ranked_rooms: list[dict],
    busy_by_room: dict[str, list[tuple[datetime, datetime]]],
) -> list[dict]:
    available: list[dict] = []
    for room in ranked_rooms:
        room_name = room.get("value")
        room_windows = busy_by_room.get(room_name) or []
        if any(_overlaps(slot_start, slot_end, busy_start, busy_end) for busy_start, busy_end in room_windows):
            continue
        available.append(room)
    return available


def suggest_meeting_rooms(
    *,
    school: str | None = None,
    date: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    location_type: str | None = None,
    selected_location: str | None = None,
    capacity_needed: int | None = None,
    limit: int | None = None,
):
    user = frappe.session.user
    _ensure_can_create_meeting(user)

    school_value = _ensure_allowed_school(user, school)
    if not school_value:
        frappe.throw(_("Host school is required before suggesting rooms."))
    location_type_value = _ensure_allowed_location_type(user, school_value, location_type)
    selected_location_value = _ensure_allowed_location(user, school_value, selected_location)

    target_date = _coerce_date_required(date, _("Meeting date"))
    start_value = _coerce_time_required(start_time, _("Start time"))
    end_value = _coerce_time_required(end_time, _("End time"))
    start_dt = _combine_date_and_time_local(target_date, start_value)
    end_dt = _combine_date_and_time_local(target_date, end_value)
    if end_dt <= start_dt:
        frappe.throw(_("End time must be later than start time."))

    room_limit = _coerce_minutes(limit, default=8, minimum=1, maximum=20, label=_("Room limit"))
    cap_needed = (
        _coerce_minutes(capacity_needed, default=0, minimum=0, maximum=200, label=_("Capacity"))
        if capacity_needed not in (None, "")
        else 0
    )

    rows = _room_rows_for_school_scope(
        school_value,
        cap_needed,
        location_type=location_type_value,
    )
    if not rows:
        payload = {
            "rooms": [],
            "notes": [_("No rooms are configured for the selected school scope.")],
        }
        return payload

    candidate_room_names = [row.name for row in rows if row.name]
    if selected_location_value and selected_location_value not in candidate_room_names:
        candidate_room_names.append(selected_location_value)

    busy_by_room = _collect_room_conflicts_by_candidate(
        candidate_room_names,
        start_dt,
        end_dt,
    )
    busy_rooms = {room_name for room_name, windows in busy_by_room.items() if windows}

    available_rooms = [
        room for room in _rank_room_suggestions(rows, capacity_needed=cap_needed) if room.get("value") not in busy_rooms
    ]

    payload = {
        "rooms": available_rooms[:room_limit],
        "selected_location": selected_location_value,
        "selected_location_available": (selected_location_value not in busy_rooms if selected_location_value else None),
        "notes": (
            [
                _("Room suggestions are limited to location type {location_type}.").format(
                    location_type=location_type_value
                )
            ]
            if location_type_value
            else []
        ),
    }
    return payload
