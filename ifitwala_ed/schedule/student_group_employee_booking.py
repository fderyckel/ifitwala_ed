# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/student_group_employee_booking.py

"""
Student Group -> Employee Booking materialization.

This module is the ONLY place where abstract schedules
are intentionally converted into concrete bookings.

If this module is not called:
- teaching exists only as an abstract timetable
- room and staff availability must treat teaching as free (no read-time inference)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Optional, List, Set, Tuple

import frappe
from frappe.utils import getdate, get_datetime

from ifitwala_ed.utilities.employee_booking import (
	upsert_employee_booking,
)
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots
from ifitwala_ed.utilities.location_utils import is_bookable_room
from ifitwala_ed.stock.doctype.location_booking.location_booking import (
	build_source_key,
	build_slot_key_instance,
	delete_location_bookings_for_source_in_window,
	upsert_location_booking,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

BOOKING_SOURCE_DOCTYPE = "Student Group"

def _normalize_dt(value) -> datetime:
	if isinstance(value, datetime):
		return value
	return get_datetime(value)

def _get_ay_date_range(academic_year: str) -> tuple[date, date]:
	"""
	Return [start_date, end_date] for the given Academic Year.

	Uses year_start_date / year_end_date from your Academic Year Doctype.
	Falls back to today's date if misconfigured (shouldn't happen in production).
	"""
	if not academic_year:
		today = getdate()
		return today, today

	year_start, year_end = frappe.db.get_value(
		"Academic Year",
		academic_year,
		["year_start_date", "year_end_date"],
	) or (None, None)

	if not year_start or not year_end:
		today = getdate()
		return today, today

	return getdate(year_start), getdate(year_end)


def _build_schedule_index(student_group: str) -> Dict[tuple[int, int], dict]:
	"""
	Preload Student Group Schedule rows for one group and index them by
	(rotation_day, block_number).

	We intentionally avoid frappe.get_all() and do a single SQL query.

	We only fetch fields we actually need for bookings.
	"""
	rows = frappe.db.sql(
		"""
		select
			name,
			parent,
			rotation_day,
			block_number,
			instructor,
			employee,
			location
		from `tabStudent Group Schedule`
		where parent = %s
		""",
		student_group,
		as_dict=True,
	)

	index: Dict[tuple[int, int], dict] = {}
	for r in rows:
		rd = r.get("rotation_day")
		bn = r.get("block_number")
		if rd is None or bn is None:
			continue

		key = (int(rd), int(bn))
		# One instructor per (rotation_day, block_number) per group by design.
		index[key] = r

	return index


def _resolve_employee_from_instructor(
	instructor_name: str,
	cache: Dict[str, Optional[str]],
) -> Optional[str]:
	"""
	Given an Instructor name, return the linked Employee if any.

	Uses a small in-memory cache per rebuild to avoid repeated lookups.
	"""
	if not instructor_name:
		return None

	if instructor_name in cache:
		return cache[instructor_name]

	emp = frappe.db.get_value("Instructor", instructor_name, "employee")
	cache[instructor_name] = emp
	return emp


def _delete_obsolete_teaching_bookings(
	*,
	student_group: str,
	start_dt: datetime,
	end_dt: datetime,
	target_keys: Set[Tuple[str, datetime, datetime]],
) -> int:
	"""
	Delete Teaching bookings for this group within the window
	that are not in target_keys.

	target_keys items: (employee, from_datetime, to_datetime)
	"""
	rows = frappe.db.sql(
		"""
		select name, employee, from_datetime, to_datetime
		from `tabEmployee Booking`
		where source_doctype = %s
		  and source_name = %s
		  and booking_type = %s
		  and from_datetime >= %s
		  and to_datetime <= %s
		""",
		[BOOKING_SOURCE_DOCTYPE, student_group, "Teaching", start_dt, end_dt],
		as_dict=True,
	)

	to_delete: List[str] = []
	for r in rows:
		key = (
			r.get("employee"),
			_normalize_dt(r.get("from_datetime")),
			_normalize_dt(r.get("to_datetime")),
		)
		if key not in target_keys:
			to_delete.append(r["name"])

	if not to_delete:
		return 0

	deleted = 0
	chunk = 200
	for i in range(0, len(to_delete), chunk):
		names = to_delete[i : i + chunk]
		frappe.db.sql(
			"delete from `tabEmployee Booking` where name in %(names)s",
			{"names": tuple(names)},
		)
		deleted += len(names)

	return deleted


# ─────────────────────────────────────────────────────────────
# Per–Student Group materialization
# ─────────────────────────────────────────────────────────────

# MATERIALIZATION BOUNDARY:
# Calling this function commits the schedule into concrete reality.
def rebuild_employee_bookings_for_student_group(
	student_group: str,
	*,
	start_date: Optional[date] = None,
	end_date: Optional[date] = None,
	strict_location: bool = True,
) -> None:
	"""
	Materialize all teaching slots for a given Student Group into Employee Booking.

	Strategy (no transient emptiness):
	1. Determine the date window (defaults to full Academic Year of the group).
	2. Preload Student Group Schedule rows and validate locations.
	3. Use iter_student_group_room_slots() to expand the timetable to concrete slots.
	4. Upsert Employee Booking rows (unique by slot).
	5. Delete obsolete bookings in the same window only.

	Notes:
	- Call this from the Student Group controller when the schedule is “stable enough”
	  (e.g. on_update / after_save when schedule rows or instructors change).
	- We treat all Student Group teaching as blocks_availability = 1 (hard conflicts).
	"""
	if not student_group:
		return

	sg = frappe.get_doc("Student Group", student_group)

	# 1) Date window: full Academic Year by default
	if start_date is None or end_date is None:
		ay_start, ay_end = _get_ay_date_range(sg.academic_year)
		if start_date is None:
			start_date = ay_start
		if end_date is None:
			end_date = ay_end

	start_date = getdate(start_date) if start_date else None
	end_date = getdate(end_date) if end_date else None

	if not start_date or not end_date or start_date > end_date:
		# Nothing sensible to do
		return

	# 2) Preload schedule rows and build index
	sched_index = _build_schedule_index(student_group)
	if not sched_index:
		# No schedule → delete any existing bookings in window
		window_start = _normalize_dt(get_datetime(f"{start_date} 00:00:00"))
		window_end = _normalize_dt(get_datetime(f"{end_date} 23:59:59"))
		_delete_obsolete_teaching_bookings(
			student_group=student_group,
			start_dt=window_start,
			end_dt=window_end,
			target_keys=set(),
		)
		delete_location_bookings_for_source_in_window(
			source_doctype=BOOKING_SOURCE_DOCTYPE,
			source_name=student_group,
			start_dt=window_start,
			end_dt=window_end,
			keep_slot_keys=set(),
		)
		return

	instructor_cache: Dict[str, Optional[str]] = {}

	# Base context for bookings
	# sg.school is Data but should correspond to School.name in your setup.
	school = sg.school or None
	academic_year = sg.academic_year or None
	source_key = build_source_key(BOOKING_SOURCE_DOCTYPE, student_group)

	# 3) Validate schedule locations up-front (Teaching requires a real room)
	if strict_location:
		missing = []
		invalid = []
		for row in sched_index.values():
			loc = row.get("location")
			rd = row.get("rotation_day")
			bn = row.get("block_number")
			label = f"rd={rd} block={bn}"
			if not loc:
				missing.append(label)
				continue
			if not is_bookable_room(loc):
				invalid.append(f"{label} ({loc})")
		if missing or invalid:
			msg = []
			if missing:
				msg.append("Missing location for: " + ", ".join(sorted(missing)))
			if invalid:
				msg.append("Non-bookable location for: " + ", ".join(sorted(invalid)))
			frappe.throw(" | ".join(msg))

	# 4) Expand timetable into concrete slots
	target_keys: Set[Tuple[str, datetime, datetime]] = set()
	target_location_slot_keys: Set[str] = set()
	for slot in iter_student_group_room_slots(student_group, start_date, end_date):
		rd = slot.get("rotation_day")
		bn = slot.get("block_number")
		if rd is None or bn is None:
			continue

		key = (int(rd), int(bn))
		row = sched_index.get(key)
		if not row:
			# No matching schedule row (shouldn't happen if schedule is consistent)
			continue

		start_dt = slot.get("start")
		end_dt = slot.get("end")
		if not start_dt or not end_dt:
			continue

		location = slot.get("location") or row.get("location")
		if not location:
			if strict_location:
				frappe.throw(
					f"Missing location for Teaching slot: {student_group} rd={rd} block={bn}"
				)
			continue

		# 5) Upsert Location Booking row (room truth)
		slot_key = build_slot_key_instance(source_key, location, start_dt, end_dt)
		upsert_location_booking(
			location=location,
			from_datetime=start_dt,
			to_datetime=end_dt,
			occupancy_type="Teaching",
			source_doctype=BOOKING_SOURCE_DOCTYPE,
			source_name=student_group,
			slot_key=slot_key,
			school=school,
			academic_year=academic_year,
			blocks_availability=1,
		)
		target_location_slot_keys.add(slot_key)

		instructor_name = row.get("instructor")
		employee = row.get("employee")
		if not employee:
			if not instructor_name:
				# No instructor assigned for this block
				continue
			employee = _resolve_employee_from_instructor(instructor_name, instructor_cache)
		if not employee:
			# Instructor without linked employee → skip for now
			continue

		# 6) Upsert Employee Booking row
		booking_name = upsert_employee_booking(
			employee=employee,
			start=start_dt,
			end=end_dt,
			source_doctype=BOOKING_SOURCE_DOCTYPE,
			source_name=student_group,
			location=location,
			booking_type="Teaching",
			blocks_availability=1,
			school=school,
			academic_year=academic_year,
			unique_by_slot=True,
		)
		if booking_name:
			start_norm = _normalize_dt(start_dt)
			end_norm = _normalize_dt(end_dt)
			target_keys.add((employee, start_norm, end_norm))

	# 7) Delete obsolete bookings in the window
	window_start = _normalize_dt(get_datetime(f"{start_date} 00:00:00"))
	window_end = _normalize_dt(get_datetime(f"{end_date} 23:59:59"))
	_delete_obsolete_teaching_bookings(
		student_group=student_group,
		start_dt=window_start,
		end_dt=window_end,
		target_keys=target_keys,
	)
	delete_location_bookings_for_source_in_window(
		source_doctype=BOOKING_SOURCE_DOCTYPE,
		source_name=student_group,
		start_dt=window_start,
		end_dt=window_end,
		keep_slot_keys=target_location_slot_keys,
	)


# ─────────────────────────────────────────────────────────────
# Bulk backfill for console use
# ─────────────────────────────────────────────────────────────

def rebuild_employee_bookings_for_all_student_groups(
	*,
	academic_year: Optional[str] = None,
	only_active: bool = True,
	skip_archived_ay: bool = True,
	start_date: Optional[date] = None,
	end_date: Optional[date] = None,
	strict_location: bool = True,
) -> None:
	"""
	Backfill Employee Booking for many Student Groups.

	Designed to be called from bench console, e.g.:

	Args:
	    academic_year: optional filter; if given, restrict to this AY.
	    only_active: if True, restrict to Student Groups with status = "Active".
	    skip_archived_ay: if True, ignore Academic Years where archived = 1.
	    start_date / end_date: optional bounded window override.
	    strict_location: if True, missing locations raise.

	Strategy:
	    1) Select Student Groups via a single SQL with optional joins/filters.
	    2) For each group, call rebuild_employee_bookings_for_student_group().
	"""
	conditions: List[str] = []
	params: List[object] = []

	# Join Academic Year to optionally skip archived ones
	join_ay = "left join `tabAcademic Year` ay on ay.name = sg.academic_year"

	if academic_year:
		conditions.append("sg.academic_year = %s")
		params.append(academic_year)

	if only_active:
		conditions.append("sg.status = 'Active'")

	if skip_archived_ay:
		conditions.append("ifnull(ay.archived, 0) = 0")

	where_clause = " where " + " and ".join(conditions) if conditions else ""

	rows = frappe.db.sql(
		f"""
		select sg.name
		from `tabStudent Group` sg
		{join_ay}
		{where_clause}
		""",
		params,
		as_dict=True,
	)

	for r in rows:
		sg_name = r["name"]
		rebuild_employee_bookings_for_student_group(
			sg_name,
			start_date=start_date,
			end_date=end_date,
			strict_location=strict_location,
		)


# ─────────────────────────────────────────────────────────────
# Simple alias for your muscle memory
# ─────────────────────────────────────────────────────────────

def rebuild_employee_bookings_for_group(
	student_group: str,
	*,
	start_date: Optional[date] = None,
	end_date: Optional[date] = None,
	strict_location: bool = True,
) -> None:
	"""
	Alias wrapper so you can call:

	    from ifitwala_ed.schedule.student_group_employee_booking import rebuild_employee_bookings_for_group
	    rebuild_employee_bookings_for_group("11.2_ToK_2526/IIS 2025-2026")

	under the hood this just calls rebuild_employee_bookings_for_student_group().
	"""
	return rebuild_employee_bookings_for_student_group(
		student_group=student_group,
		start_date=start_date,
		end_date=end_date,
		strict_location=strict_location,
	)
