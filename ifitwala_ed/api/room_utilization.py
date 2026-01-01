# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/room_utilization.py

from __future__ import annotations

from datetime import date
from typing import Any

import frappe
from frappe import _
from frappe.utils import add_days, get_datetime, getdate, time_diff_in_seconds


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


def _normalize_date(value) -> date | None:
	if not value:
		return None
	try:
		return getdate(value)
	except Exception:
		return None


def _best_effort_rotation_day(filters: dict, target_date: date) -> int | None:
	"""Resolve rotation_day using existing schedule utilities (no custom calendar math)."""
	school = filters.get("school") or None
	if not school and filters.get("building"):
		school = frappe.db.get_value("Location", filters["building"], "school")
	if not school:
		return None

	from ifitwala_ed.setup.doctype.meeting.meeting import get_academic_year_for_date
	from ifitwala_ed.schedule.schedule_utils import (
		get_effective_schedule_for_ay,
		get_rotation_dates,
	)

	academic_year = get_academic_year_for_date(school, target_date)
	if not academic_year:
		return None

	schedule_name = get_effective_schedule_for_ay(academic_year, school)
	if not schedule_name:
		return None

	rotation_dates = get_rotation_dates(
		schedule_name,
		academic_year,
		include_holidays=False,
	)
	rotation_map = {
		getdate(row.get("date")).isoformat(): int(row["rotation_day"])
		for row in rotation_dates
		if row.get("date") and row.get("rotation_day") is not None
	}
	return rotation_map.get(target_date.isoformat())


def _resolve_rotation_day(filters: dict, target_date: date) -> int | None:
	if filters.get("rotation_day") not in (None, ""):
		try:
			rotation_day = int(filters["rotation_day"])
		except (TypeError, ValueError):
			frappe.throw(_("rotation_day must be an integer."))
		if rotation_day <= 0:
			frappe.throw(_("rotation_day must be a positive integer."))
		return rotation_day

	scope = filters.get("school") or filters.get("building")
	if not (scope and target_date):
		return None

	cache_key = f"room_utilization:rotation_day:{scope}:{target_date.isoformat()}"
	rc = frappe.cache()
	cached = rc.get_value(cache_key)
	if cached is not None:
		return None if cached == "__none__" else int(cached)

	rotation_day = _best_effort_rotation_day(filters, target_date)
	rc.set_value(
		cache_key,
		rotation_day if rotation_day is not None else "__none__",
		expires_in_sec=300,
	)
	return rotation_day


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
		room_filters["school"] = filters["school"]
	if filters.get("building"):
		# No explicit building field in Location; treat building as parent_location.
		room_filters["parent_location"] = filters["building"]

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

	if not (filters.get("date") and filters.get("start_time") and filters.get("end_time")):
		frappe.throw(_("Date, Start Time, and End Time are required."))

	window_start = get_datetime(f"{filters['date']} {filters['start_time']}")
	window_end = get_datetime(f"{filters['date']} {filters['end_time']}")

	if window_end <= window_start:
		frappe.throw(_("End Time must be after Start Time."))

	target_date = _normalize_date(filters.get("date"))
	rotation_day_missing = filters.get("rotation_day") in (None, "")
	rotation_day = _resolve_rotation_day(filters, target_date) if target_date else None
	if rotation_day is None:
		reason = "rotation_day missing in request; resolver could not determine it."
		frappe.throw(
			_(
				"Rotation day is required for availability checks. "
				"date={0}, start_time={1}, end_time={2}, school={3}, building={4}, reason={5}"
			).format(
				filters.get("date"),
				filters.get("start_time"),
				filters.get("end_time"),
				filters.get("school") or "—",
				filters.get("building") or "—",
				reason if rotation_day_missing else "rotation_day provided but invalid.",
			)
		)

	rooms = _get_candidate_rooms(filters)
	if not rooms:
		return {"window": {"start": str(window_start), "end": str(window_end)}, "rooms": []}

	room_names = [r["name"] for r in rooms]
	params = {
		"rooms": tuple(room_names),
		"window_start": window_start,
		"window_end": window_end,
		"start_time": filters["start_time"],
		"end_time": filters["end_time"],
		"rotation_day": rotation_day,
	}

	meeting_school_clause = ""
	if filters.get("school"):
		meeting_school_clause = " AND school = %(school)s"
		params["school"] = filters["school"]

	meeting_rows = frappe.db.sql(
		f"""
		SELECT DISTINCT location
		FROM `tabMeeting`
		WHERE docstatus < 2
			AND status != 'Cancelled'
			AND location IN %(rooms)s
			AND from_datetime < %(window_end)s
			AND to_datetime > %(window_start)s
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
		SELECT DISTINCT location
		FROM `tabSchool Event`
		WHERE docstatus < 2
			AND location IN %(rooms)s
			AND starts_on < %(window_end)s
			AND ends_on > %(window_start)s
			{event_school_clause}
		""",
		params,
		as_dict=True,
	)

	schedule_rows = frappe.db.sql(
		"""
		SELECT DISTINCT location
		FROM `tabStudent Group Schedule`
		WHERE location IN %(rooms)s
			AND rotation_day = %(rotation_day)s
			AND from_time < TIME(%(end_time)s)
			AND to_time > TIME(%(start_time)s)
		""",
		params,
		as_dict=True,
	)

	busy_rooms = {r["location"] for r in meeting_rows if r.get("location")}
	busy_rooms.update({r["location"] for r in event_rows if r.get("location")})
	busy_rooms.update({r["location"] for r in schedule_rows if r.get("location")})

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

	return {
		"window": {"start": str(window_start), "end": str(window_end)},
		"rooms": available_rooms,
	}


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
