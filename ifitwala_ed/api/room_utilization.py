# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/room_utilization.py

from __future__ import annotations

from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, time_diff_in_seconds

from ifitwala_ed.api.student_log_dashboard import get_authorized_schools
from ifitwala_ed.utilities.location_utils import (
    find_room_conflicts,
    get_location_scope,
    get_visible_location_rows_for_school,
)

MAX_RANGE_DAYS = 62
LONG_RANGE_ROLES = {"System Manager", "Administrator", "Academic Admin"}
ANALYTICS_ROLES = {"Academic Admin", "Academic Assistant", "Curriculum Coordinator"}


def _parse_filters(filters: Any | None) -> dict:
    if isinstance(filters, str):
        try:
            return frappe.parse_json(filters) or {}
        except Exception:
            return {}
    return filters or {}


def _is_admin_like(user: str | None = None) -> bool:
    user = user or frappe.session.user
    roles = set(frappe.get_roles(user))
    return user == "Administrator" or "System Manager" in roles


def _user_can_use_long_range() -> bool:
    roles = set(frappe.get_roles(frappe.session.user))
    return bool(roles & LONG_RANGE_ROLES)


def _require_scope(filters: dict) -> None:
    if not filters.get("school"):
        frappe.throw(_("Please select a School to scope this query."))


def _require_location_booking_table() -> None:
    if not frappe.db.table_exists("Location Booking"):
        frappe.throw("Location Booking doctype/table missing. Migration/installation is broken.")


def _extract_capacity_needed(filters: dict) -> int | None:
    cap = filters.get("capacity_needed")
    if cap in (None, ""):
        cap = filters.get("capacity")
    if cap in (None, ""):
        cap = filters.get("min_capacity")
    try:
        cap = int(cap) if cap not in (None, "") else None
    except Exception:
        cap = None
    if cap and cap > 0:
        return cap
    return None


def _extract_location_types(filters: dict) -> list[str]:
    raw = filters.get("location_type")
    if raw in (None, ""):
        raw = filters.get("location_types")
    if raw in (None, ""):
        return []

    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                raw = frappe.parse_json(text)
            except Exception:
                raw = [part.strip() for part in text.split(",")]
        else:
            raw = [part.strip() for part in text.split(",")]

    if not isinstance(raw, list):
        raw = [raw]

    seen = set()
    out: list[str] = []
    for item in raw:
        value = str(item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _get_schedulable_location_type_options() -> list[dict]:
    rows = frappe.get_all(
        "Location Type",
        filters={"is_schedulable": 1},
        fields=["name", "location_type_name"],
        order_by="location_type_name asc",
        limit=200,
    )
    return [{"value": row.name, "label": row.location_type_name or row.name} for row in rows]


def _has_room_utilization_analytics_access(user: str | None = None) -> bool:
    if not user:
        user = frappe.session.user
    roles = set(frappe.get_roles(user))
    return bool(roles & ANALYTICS_ROLES)


def _require_room_utilization_analytics_access() -> None:
    if not _has_room_utilization_analytics_access():
        frappe.throw(_("Not permitted"), frappe.PermissionError)


def _ensure_allowed_school(school: str | None) -> str:
    school_value = str(school or "").strip()
    if not school_value:
        frappe.throw(_("School is required."), frappe.PermissionError)

    if _is_admin_like():
        return school_value

    allowed = set(get_authorized_schools(frappe.session.user) or [])
    if school_value not in allowed:
        frappe.throw(
            _("You are not allowed to use school {school} in room utilization.").format(school=school_value),
            frappe.PermissionError,
        )
    return school_value


def _get_school_scope(school: str) -> list[str]:
    """Return [school] + descendant schools (NestedSet)."""
    if not school:
        return []
    try:
        doc = frappe.get_cached_doc("School", school)
    except Exception:
        return [school]

    if getattr(doc, "lft", None) and getattr(doc, "rgt", None):
        rows = frappe.get_all(
            "School",
            filters={"lft": [">=", doc.lft], "rgt": ["<=", doc.rgt]},
            pluck="name",
            order_by="lft",
        )
        return rows or [school]

    return [school]


def _normalize_date(value) -> date | None:
    if not value:
        return None
    try:
        return getdate(value)
    except Exception:
        return None


def _validate_date_range(from_date, to_date, *, enforce_scope: bool = True) -> tuple[date, date, int]:
    if not from_date or not to_date:
        frappe.throw(_("Please provide both From Date and To Date."))

    start = _normalize_date(from_date)
    end = _normalize_date(to_date)
    if not (start and end):
        frappe.throw(_("Invalid date range."))

    if end < start:
        frappe.throw(_("To Date must be on or after From Date."))

    days = (end - start).days + 1
    if enforce_scope and days > MAX_RANGE_DAYS and not _user_can_use_long_range():
        frappe.throw(_("Date range too large. Please keep it within {max_days} days.").format(max_days=MAX_RANGE_DAYS))

    return start, end, days


def _get_candidate_rooms(filters: dict) -> list[dict]:
    selected_school = _ensure_allowed_school(filters.get("school"))
    location_types = _extract_location_types(filters)
    scope_location = str(filters.get("building") or filters.get("location") or "").strip() or None
    cap = _extract_capacity_needed(filters)

    return get_visible_location_rows_for_school(
        selected_school,
        include_groups=False,
        only_schedulable=True,
        within_location=scope_location,
        location_types=location_types,
        capacity_needed=cap,
        fields=[
            "name",
            "location_name",
            "parent_location",
            "maximum_capacity",
            "location_type",
            "is_group",
        ],
        order_by="location_name asc",
        limit=800,
    )


def _window_overlap_minutes(start_dt, end_dt, day_start, day_end) -> int:
    if end_dt <= start_dt:
        return 0

    day_cursor = start_dt.date()
    last_day = end_dt.date()
    minutes = 0

    while day_cursor <= last_day:
        window_start = get_datetime(f"{day_cursor} {day_start}")
        window_end = get_datetime(f"{day_cursor} {day_end}")

        seg_start = max(start_dt, window_start)
        seg_end = min(end_dt, window_end)

        if seg_end > seg_start:
            minutes += int((seg_end - seg_start).total_seconds() / 60)

        day_cursor = add_days(day_cursor, 1)

    return minutes


@frappe.whitelist()
def get_room_utilization_filter_meta():
    """Return allowed schools for the current user."""
    user = frappe.session.user
    allowed = get_authorized_schools(user)

    school_rows = []
    default_school = None
    if allowed:
        school_rows = frappe.get_all(
            "School",
            filters={"name": ["in", allowed]},
            fields=["name", "school_name as label"],
            order_by="lft",
        )
        default_school = allowed[0]

    return {
        "schools": school_rows,
        "default_school": default_school,
        "location_types": _get_schedulable_location_type_options(),
    }


@frappe.whitelist()
def can_view_room_utilization_analytics():
    return {"allowed": 1 if _has_room_utilization_analytics_access() else 0}


@frappe.whitelist()
def get_free_rooms(filters=None):
    filters = _parse_filters(filters)
    debug_enabled = bool(filters.get("debug"))
    sources_used: list[str] = []

    def _attach_debug(payload: dict, *, busy_count: int, candidate_count: int) -> dict:
        if debug_enabled:
            # Debug payload is intentionally read-only and non-persistent.
            payload["debug"] = {
                "sources_used": sources_used,
                "busy_rooms_count": busy_count,
                "candidate_rooms_count": candidate_count,
            }
        return payload

    if not (filters.get("date") and filters.get("start_time") and filters.get("end_time")):
        frappe.throw(_("Date, Start Time, and End Time are required."))

    window_start = get_datetime(f"{filters['date']} {filters['start_time']}")
    window_end = get_datetime(f"{filters['date']} {filters['end_time']}")

    if window_end <= window_start:
        frappe.throw(_("End Time must be after Start Time."))

    _require_location_booking_table()
    sources_used.append("Location Booking")

    rooms = _get_candidate_rooms(filters)
    if not rooms:
        payload = {
            "window": {"start": str(window_start), "end": str(window_end)},
            "rooms": [],
            "classes_checked": True,
        }
        return _attach_debug(payload, busy_count=0, candidate_count=0)

    room_names = [r["name"] for r in rooms]

    conflicts = find_room_conflicts(
        None,
        window_start,
        window_end,
        locations=room_names,
        include_children=False,
    )
    busy_rooms = {c["location"] for c in conflicts if c.get("location")}

    # Guardrail: if there are no overlapping concrete bookings, all rooms are free.
    available_rooms = []
    for room in rooms:
        if room["name"] in busy_rooms:
            continue
        available_rooms.append(
            {
                "room": room["name"],
                "room_name": room.get("location_name") or room["name"],
                "building": room.get("parent_location"),
                "max_capacity": room.get("maximum_capacity"),
                "location_type": room.get("location_type"),
                "location_type_name": room.get("location_type_name"),
            }
        )

    payload = {
        "window": {"start": str(window_start), "end": str(window_end)},
        "rooms": available_rooms,
        # classes_checked:
        # True if teaching bookings are available via Location Booking.
        "classes_checked": True,
    }
    return _attach_debug(
        payload,
        busy_count=len(busy_rooms),
        candidate_count=len(rooms),
    )


@frappe.whitelist()
def get_room_time_utilization(filters=None):
    _require_room_utilization_analytics_access()
    filters = _parse_filters(filters)
    _require_scope(filters)

    from_date, to_date, day_count = _validate_date_range(filters.get("from_date"), filters.get("to_date"))

    day_start = filters.get("day_start_time") or "07:00:00"
    day_end = filters.get("day_end_time") or "16:00:00"

    day_window_seconds = time_diff_in_seconds(day_end, day_start)
    if day_window_seconds <= 0:
        frappe.throw(_("Day End Time must be after Day Start Time."))

    day_window_minutes = int(day_window_seconds / 60)
    available_minutes = day_count * day_window_minutes

    # NOTE: Student Group schedules count only if materialized into Location Booking.
    rooms = _get_candidate_rooms(filters)
    if not rooms:
        return {
            "range": {"from": str(from_date), "to": str(to_date)},
            "day_window": {"start": day_start, "end": day_end},
            "rooms": [],
        }

    room_names = [r["name"] for r in rooms]

    # Location Booking is the only source of room occupancy.
    _require_location_booking_table()
    range_start = get_datetime(f"{from_date} 00:00:00")
    range_end = get_datetime(f"{to_date} 23:59:59")

    filters_lb = {
        "location": ["in", tuple(room_names)],
        "from_datetime": ["<", range_end],
        "to_datetime": [">", range_start],
    }
    if frappe.db.has_column("Location Booking", "docstatus"):
        filters_lb["docstatus"] = ["<", 2]

    rows = frappe.db.get_all(
        "Location Booking",
        filters=filters_lb,
        fields=["location", "from_datetime", "to_datetime"],
    )

    booked_minutes = {name: 0 for name in room_names}

    for row in rows:
        loc = row.get("location")
        if not loc:
            continue

        # Ensure we don't crash on bad data
        if not row.get("from_datetime") or not row.get("to_datetime"):
            continue

        s = get_datetime(row["from_datetime"])
        e = get_datetime(row["to_datetime"])

        # Clamp to query range first
        s = max(s, range_start)
        e = min(e, range_end)

        minutes = _window_overlap_minutes(s, e, day_start, day_end)
        booked_minutes[loc] += minutes

    room_payload = []
    for room in rooms:
        minutes = booked_minutes.get(room["name"], 0)
        util_pct = 0.0
        if available_minutes > 0:
            util_pct = round((minutes / available_minutes) * 100, 2)
        room_payload.append(
            {
                "room": room["name"],
                "room_name": room.get("location_name") or room["name"],
                "building": room.get("parent_location"),
                "location_type": room.get("location_type"),
                "location_type_name": room.get("location_type_name"),
                "booked_minutes": minutes,
                "available_minutes": available_minutes,
                "utilization_pct": util_pct,
            }
        )

    room_payload.sort(key=lambda r: r["utilization_pct"], reverse=True)

    return {
        "range": {"from": str(from_date), "to": str(to_date)},
        "day_window": {"start": day_start, "end": day_end},
        "rooms": room_payload,
    }


@frappe.whitelist()
def get_room_capacity_utilization(filters=None):
    _require_room_utilization_analytics_access()
    filters = _parse_filters(filters)
    _require_scope(filters)

    from_date, to_date, _range_days = _validate_date_range(filters.get("from_date"), filters.get("to_date"))

    rooms = _get_candidate_rooms(filters)
    if not rooms:
        return {"range": {"from": str(from_date), "to": str(to_date)}, "rooms": []}

    room_names = [r["name"] for r in rooms]
    range_start = get_datetime(f"{from_date} 00:00:00")
    range_end = get_datetime(f"{to_date} 23:59:59")

    _require_location_booking_table()
    filters_lb = {
        "location": ["in", tuple(room_names)],
        "from_datetime": ["<", range_end],
        "to_datetime": [">", range_start],
    }
    if frappe.db.has_column("Location Booking", "docstatus"):
        filters_lb["docstatus"] = ["<", 2]
    if frappe.db.has_column("Location Booking", "occupancy_type"):
        filters_lb["occupancy_type"] = ["in", ["Meeting", "Teaching"]]

    rows = frappe.db.get_all(
        "Location Booking",
        filters=filters_lb,
        fields=["location", "source_doctype", "source_name", "occupancy_type"],
    )

    meeting_names = [
        r.get("source_name")
        for r in rows
        if (r.get("occupancy_type") == "Meeting" or r.get("source_doctype") == "Meeting") and r.get("source_name")
    ]
    participant_counts = {}

    if meeting_names:
        participant_rows = frappe.db.sql(
            """
			SELECT parent AS meeting, COUNT(*) AS attendees
			FROM `tabMeeting Participant`
			WHERE parent IN %(meetings)s
			GROUP BY parent
			""",
            {"meetings": tuple(set(meeting_names))},
            as_dict=True,
        )
        participant_counts = {row["meeting"]: int(row["attendees"]) for row in participant_rows}

    capacity_by_room = {room["name"]: room.get("maximum_capacity") or 0 for room in rooms}
    stats = {
        room["name"]: {
            "meetings": 0,
            "attendees_total": 0,
            "peak_attendees": 0,
            "over_capacity_count": 0,
        }
        for room in rooms
    }

    for row in rows:
        loc = row.get("location")
        if not loc:
            continue

        stats[loc]["meetings"] += 1

        if row.get("occupancy_type") != "Meeting" and row.get("source_doctype") != "Meeting":
            continue

        attendees = participant_counts.get(row.get("source_name"), 0)
        stats[loc]["attendees_total"] += attendees
        stats[loc]["peak_attendees"] = max(stats[loc]["peak_attendees"], attendees)

        r_cap = capacity_by_room.get(loc, 0)
        if r_cap and attendees > r_cap:
            stats[loc]["over_capacity_count"] += 1

    room_payload = []
    for room in rooms:
        room_stats = stats[room["name"]]
        meeting_count = room_stats["meetings"]

        avg_attendees = 0.0
        if meeting_count:
            # Note: this average is diluted if teaching events (0 attendees in this logic) are high.
            # But it correctly reflects "average participants per booked slot" where we don't know class size.
            avg_attendees = round(room_stats["attendees_total"] / meeting_count, 1)

        max_capacity = room.get("maximum_capacity") or 0
        avg_capacity_pct = None
        peak_capacity_pct = None
        if max_capacity:
            avg_capacity_pct = round((avg_attendees / max_capacity) * 100, 1)
            peak_capacity_pct = round((room_stats["peak_attendees"] / max_capacity) * 100, 1)

        room_payload.append(
            {
                "room": room["name"],
                "room_name": room.get("location_name") or room["name"],
                "building": room.get("parent_location"),
                "location_type": room.get("location_type"),
                "location_type_name": room.get("location_type_name"),
                "max_capacity": max_capacity or None,
                "meetings": meeting_count,
                "avg_attendees": avg_attendees,
                "peak_attendees": room_stats["peak_attendees"],
                "avg_capacity_pct": avg_capacity_pct,
                "peak_capacity_pct": peak_capacity_pct,
                "over_capacity_count": room_stats["over_capacity_count"],
            }
        )

    room_payload.sort(key=lambda r: r["avg_capacity_pct"] or 0, reverse=True)

    return {
        "range": {"from": str(from_date), "to": str(to_date)},
        "rooms": room_payload,
    }


def _occupancy_title(row: dict, location_label: str | None, *, single_location: bool) -> str:
    occupancy = str(row.get("occupancy_type") or row.get("source_doctype") or _("Busy")).strip() or _("Busy")
    if single_location or not location_label:
        return occupancy
    return _("{occupancy} · {location}").format(occupancy=occupancy, location=location_label)


def _occupancy_color(row: dict) -> str:
    occupancy = str(row.get("occupancy_type") or row.get("source_doctype") or "").strip().lower()
    if occupancy == "teaching":
        return "#2563eb"
    if occupancy == "meeting":
        return "#0f766e"
    if occupancy == "school event":
        return "#7c3aed"
    if occupancy == "room booking":
        return "#ea580c"
    return "#475569"


@frappe.whitelist()
def get_location_calendar(filters=None):
    filters = _parse_filters(filters)
    _require_scope(filters)

    selected_school = _ensure_allowed_school(filters.get("school"))
    location_rows = get_visible_location_rows_for_school(
        selected_school,
        include_groups=True,
        only_schedulable=False,
        fields=[
            "name",
            "location_name",
            "parent_location",
            "location_type",
            "is_group",
        ],
        order_by="location_name asc",
        limit=800,
    )
    location_options = [
        {
            "value": row.get("name"),
            "label": row.get("location_name") or row.get("name"),
            "is_group": cint(row.get("is_group") or 0),
            "parent_location": row.get("parent_location"),
            "location_type": row.get("location_type"),
            "location_type_name": row.get("location_type_name"),
        }
        for row in location_rows
        if row.get("name")
    ]

    from_date, to_date, _range_days = _validate_date_range(filters.get("from_date"), filters.get("to_date"))
    selected_location = str(filters.get("location") or "").strip() or None
    if not selected_location:
        return {
            "range": {"from": str(from_date), "to": str(to_date)},
            "locations": location_options,
            "selected_location": None,
            "selected_location_label": None,
            "note": _("Select a location or building to load its calendar."),
            "events": [],
        }

    selected_row = next((row for row in location_options if row.get("value") == selected_location), None)
    if not selected_row:
        frappe.throw(
            _("You are not allowed to view location {location}.").format(location=selected_location),
            frappe.PermissionError,
        )

    include_children = bool(cint(selected_row.get("is_group") or 0))
    scope_names = get_location_scope(selected_location, include_children=include_children)
    visible_name_set = {row.get("value") for row in location_options if row.get("value")}
    scoped_locations = [name for name in scope_names if name in visible_name_set]

    if not scoped_locations:
        return {
            "range": {"from": str(from_date), "to": str(to_date)},
            "locations": location_options,
            "selected_location": selected_location,
            "selected_location_label": selected_row.get("label"),
            "note": _("No visible locations are available under this selection."),
            "events": [],
        }

    range_start = get_datetime(f"{from_date} 00:00:00")
    range_end = get_datetime(f"{to_date} 23:59:59")
    _require_location_booking_table()

    lb_filters = {
        "location": ["in", tuple(scoped_locations)],
        "from_datetime": ["<", range_end],
        "to_datetime": [">", range_start],
    }
    if frappe.db.has_column("Location Booking", "docstatus"):
        lb_filters["docstatus"] = ["<", 2]

    rows = frappe.get_all(
        "Location Booking",
        filters=lb_filters,
        fields=["name", "location", "from_datetime", "to_datetime", "occupancy_type", "source_doctype"],
        order_by="from_datetime asc",
        limit=1500,
    )

    label_map = {row.get("value"): row.get("label") for row in location_options if row.get("value")}
    events = []
    for row in rows:
        location_name = row.get("location")
        location_label = label_map.get(location_name) or location_name
        events.append(
            {
                "id": row.get("name"),
                "title": _occupancy_title(row, location_label, single_location=not include_children),
                "start": str(row.get("from_datetime")),
                "end": str(row.get("to_datetime")),
                "allDay": False,
                "color": _occupancy_color(row),
                "meta": {
                    "occupancy_type": row.get("occupancy_type") or row.get("source_doctype") or _("Busy"),
                    "location": location_name,
                    "location_label": location_label,
                },
            }
        )

    note = (
        _("Showing bookings for the selected location and all descendant spaces.")
        if include_children
        else _("Showing bookings for the selected location.")
    )
    return {
        "range": {"from": str(from_date), "to": str(to_date)},
        "locations": location_options,
        "selected_location": selected_location,
        "selected_location_label": selected_row.get("label"),
        "note": note,
        "events": events,
    }
