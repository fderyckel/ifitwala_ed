# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/room_utilization.py

from __future__ import annotations

from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, time_diff_in_seconds

from ifitwala_ed.utilities.location_utils import find_room_conflicts


MAX_RANGE_DAYS = 62
LONG_RANGE_ROLES = {"System Manager", "Administrator", "Academic Admin"}


def _parse_filters(filters: Any | None) -> dict:
	if isinstance(filters, str):
		try:
			return frappe.parse_json(filters) or {}
		except Exception:
			return {}
	return filters or {}


def _user_can_use_long_range() -> bool:
	roles = set(frappe.get_roles(frappe.session.user))
	return bool(roles & LONG_RANGE_ROLES)


def _require_scope(filters: dict) -> None:
	if not (filters.get("school") or filters.get("building")):
		frappe.throw(_("Please select a School or Building to scope this query."))


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
		frappe.throw(
			_("Date range too large. Please keep it within {0} days.").format(MAX_RANGE_DAYS)
		)

	return start, end, days


def _get_candidate_rooms(filters: dict) -> list[dict]:
	room_filters: dict[str, Any] = {"is_group": 0}

	if filters.get("school"):
		scope = _get_school_scope(filters["school"])
		if scope:
			room_filters["school"] = ["in", scope]

	if filters.get("building"):
		# No explicit building field in Location; treat building as parent_location.
		room_filters["parent_location"] = filters["building"]

	cap = filters.get("capacity_needed")
	try:
		cap = int(cap) if cap not in (None, "") else None
	except Exception:
		cap = None
	if cap and cap > 0:
		room_filters["maximum_capacity"] = [">=", cap]

	return frappe.get_all(
		"Location",
		filters=room_filters,
		fields=["name", "location_name", "parent_location", "maximum_capacity"],
		order_by="location_name",
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
	from ifitwala_ed.api.student_log_dashboard import get_authorized_schools

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

	return {"schools": school_rows, "default_school": default_school}


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

	rooms = _get_candidate_rooms(filters)
	if not rooms:
		payload = {
			"window": {"start": str(window_start), "end": str(window_end)},
			"rooms": [],
			"classes_checked": False,
		}
		return _attach_debug(payload, busy_count=0, candidate_count=0)

	room_names = [r["name"] for r in rooms]
	employee_booking_checked = bool(
		frappe.db.table_exists("Employee Booking")
		and frappe.db.has_column("Employee Booking", "location")
	)

	# Record the sources that were queried (for debug output only).
	if frappe.db.table_exists("Employee Booking") and frappe.db.has_column(
		"Employee Booking",
		"location",
	):
		sources_used.append("Employee Booking")
	if frappe.db.table_exists("Meeting"):
		sources_used.append("Meeting")
	if frappe.db.table_exists("School Event"):
		sources_used.append("School Event")

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
			}
		)

	payload = {
		"window": {"start": str(window_start), "end": str(window_end)},
		"rooms": available_rooms,
		# classes_checked:
		# True if teaching bookings (Employee Booking) were queried as a concrete source.
		"classes_checked": employee_booking_checked,
	}
	return _attach_debug(
		payload,
		busy_count=len(busy_rooms),
		candidate_count=len(rooms),
	)


@frappe.whitelist()
def get_room_time_utilization(filters=None):
	filters = _parse_filters(filters)
	_require_scope(filters)

	from_date, to_date, day_count = _validate_date_range(
		filters.get("from_date"), filters.get("to_date")
	)

	day_start = filters.get("day_start_time") or "07:00:00"
	day_end = filters.get("day_end_time") or "16:00:00"

	day_window_seconds = time_diff_in_seconds(day_end, day_start)
	if day_window_seconds <= 0:
		frappe.throw(_("Day End Time must be after Day Start Time."))

	day_window_minutes = int(day_window_seconds / 60)
	available_minutes = day_count * day_window_minutes

	# NOTE: Student Group schedules are not included in v1 utilization windows.
	rooms = _get_candidate_rooms(filters)
	if not rooms:
		return {
			"range": {"from": str(from_date), "to": str(to_date)},
			"day_window": {"start": day_start, "end": day_end},
			"rooms": [],
		}

	room_names = [r["name"] for r in rooms]
	params = {
		"rooms": tuple(room_names),
		"range_start": get_datetime(f"{from_date} 00:00:00"),
		"range_end": get_datetime(f"{to_date} 23:59:59"),
	}

	meeting_school_clause = ""
	if filters.get("school"):
		meeting_school_clause = " AND school = %(school)s"
		params["school"] = filters["school"]

	meeting_rows = frappe.db.sql(
		f"""
		SELECT name, location, from_datetime, to_datetime
		FROM `tabMeeting`
		WHERE docstatus < 2
			AND status != 'Cancelled'
			AND location IN %(rooms)s
			AND from_datetime < %(range_end)s
			AND to_datetime > %(range_start)s
			{meeting_school_clause}
		""",
		params,
		as_dict=True,
	)

	event_school_clause = ""
	if filters.get("school"):
		event_school_clause = " AND school = %(school)s"

	event_rows = frappe.db.sql(
		f"""
		SELECT name, location, starts_on, ends_on
		FROM `tabSchool Event`
		WHERE docstatus < 2
			AND location IN %(rooms)s
			AND starts_on < %(range_end)s
			AND ends_on > %(range_start)s
			{event_school_clause}
		""",
		params,
		as_dict=True,
	)

	booked_minutes = {name: 0 for name in room_names}

	for row in meeting_rows:
		loc = row.get("location")
		if not loc:
			continue
		start_dt = max(get_datetime(row.get("from_datetime")), params["range_start"])
		end_dt = min(get_datetime(row.get("to_datetime")), params["range_end"])
		booked_minutes[loc] += _window_overlap_minutes(start_dt, end_dt, day_start, day_end)

	for row in event_rows:
		loc = row.get("location")
		if not loc:
			continue
		start_dt = max(get_datetime(row.get("starts_on")), params["range_start"])
		end_dt = min(get_datetime(row.get("ends_on")), params["range_end"])
		booked_minutes[loc] += _window_overlap_minutes(start_dt, end_dt, day_start, day_end)

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
	filters = _parse_filters(filters)
	_require_scope(filters)

	from_date, to_date, _ = _validate_date_range(filters.get("from_date"), filters.get("to_date"))

	# NOTE: Capacity utilization uses Meeting Participant counts only in v1.
	rooms = _get_candidate_rooms(filters)
	if not rooms:
		return {"range": {"from": str(from_date), "to": str(to_date)}, "rooms": []}

	room_names = [r["name"] for r in rooms]
	params = {
		"rooms": tuple(room_names),
		"range_start": get_datetime(f"{from_date} 00:00:00"),
		"range_end": get_datetime(f"{to_date} 23:59:59"),
	}

	meeting_school_clause = ""
	if filters.get("school"):
		meeting_school_clause = " AND school = %(school)s"
		params["school"] = filters["school"]

	meeting_rows = frappe.db.sql(
		f"""
		SELECT name, location
		FROM `tabMeeting`
		WHERE docstatus < 2
			AND status != 'Cancelled'
			AND location IN %(rooms)s
			AND from_datetime < %(range_end)s
			AND to_datetime > %(range_start)s
			{meeting_school_clause}
		""",
		params,
		as_dict=True,
	)

	meeting_names = [row["name"] for row in meeting_rows]
	participant_counts = {}

	if meeting_names:
		participant_rows = frappe.db.sql(
			"""
			SELECT parent AS meeting, COUNT(*) AS attendees
			FROM `tabMeeting Participant`
			WHERE parent IN %(meetings)s
			GROUP BY parent
			""",
			{"meetings": tuple(meeting_names)},
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

	for row in meeting_rows:
		loc = row.get("location")
		if not loc:
			continue
		attendees = participant_counts.get(row["name"], 0)
		room_stats = stats[loc]
		room_stats["meetings"] += 1
		room_stats["attendees_total"] += attendees
		room_stats["peak_attendees"] = max(room_stats["peak_attendees"], attendees)

		r_cap = capacity_by_room.get(loc, 0)
		if r_cap and attendees > r_cap:
			room_stats["over_capacity_count"] += 1

	room_payload = []
	for room in rooms:
		room_stats = stats[room["name"]]
		meeting_count = room_stats["meetings"]
		avg_attendees = 0.0
		if meeting_count:
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
				"max_capacity": max_capacity or None,
				"meetings": meeting_count,
				"avg_attendees": avg_attendees,
				"peak_attendees": room_stats["peak_attendees"],
				"avg_capacity_pct": avg_capacity_pct,
				"peak_capacity_pct": peak_capacity_pct,
				"over_capacity_count": room_stats["over_capacity_count"],
			}
		)

	room_payload.sort(key=lambda r: (r["avg_capacity_pct"] or 0), reverse=True)

	return {
		"range": {"from": str(from_date), "to": str(to_date)},
		"rooms": room_payload,
	}
