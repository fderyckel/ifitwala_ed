# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/student_group_employee_booking.py

"""
Student Group -> Employee Booking materialization.

This module is the ONLY place where abstract schedules
are intentionally converted into concrete bookings.

If this module is not called:
- teaching exists only as an abstract timetable
- room and staff availability MUST remain best-effort
"""

from __future__ import annotations

from datetime import date
from typing import Dict, Optional, List

import frappe
from frappe.utils import getdate

from ifitwala_ed.utilities.employee_booking import (
	delete_employee_bookings_for_source,
	upsert_employee_booking,
)
from ifitwala_ed.schedule.schedule_utils import iter_student_group_room_slots


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

BOOKING_SOURCE_DOCTYPE = "Student Group"

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
			employee
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
) -> None:
	"""
	Materialize all teaching slots for a given Student Group into Employee Booking.

	Strategy:
	1. Determine the date window (defaults to full Academic Year of the group).
	2. Delete existing Employee Booking rows for this Student Group.
	3. Preload Student Group Schedule rows (one SQL) and index by (rotation_day, block_number).
	4. Use iter_student_group_room_slots() to expand the timetable to concrete
	   date+time slots within [start_date, end_date].
	5. For each slot, resolve the Instructor → Employee and upsert an Employee Booking row.

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

	if not start_date or not end_date or start_date > end_date:
		# Nothing sensible to do
		return

	# 2) Clear existing bookings for this source
	delete_employee_bookings_for_source(BOOKING_SOURCE_DOCTYPE, student_group)

	# 3) Preload schedule rows and build index
	sched_index = _build_schedule_index(student_group)
	if not sched_index:
		# No schedule → nothing to materialize
		return

	instructor_cache: Dict[str, Optional[str]] = {}

	# Base context for bookings
	# sg.school is Data but should correspond to School.name in your setup.
	school = sg.school or None
	academic_year = sg.academic_year or None

	# 4) Expand timetable into concrete slots
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

		start_dt = slot.get("start")
		end_dt = slot.get("end")
		if not start_dt or not end_dt:
			continue

		# 5) Upsert Employee Booking row
		upsert_employee_booking(
			employee=employee,
			start=start_dt,
			end=end_dt,
			source_doctype=BOOKING_SOURCE_DOCTYPE,
			source_name=student_group,
			booking_type="Teaching",
			blocks_availability=1,
			school=school,
			academic_year=academic_year,
			unique_by_slot=True,
		)


# ─────────────────────────────────────────────────────────────
# Bulk backfill for console use
# ─────────────────────────────────────────────────────────────

def rebuild_employee_bookings_for_all_student_groups(
	*,
	academic_year: Optional[str] = None,
	only_active: bool = True,
	skip_archived_ay: bool = True,
) -> None:
	"""
	Backfill Employee Booking for many Student Groups.

	Designed to be called from bench console, e.g.:

	Args:
	    academic_year: optional filter; if given, restrict to this AY.
	    only_active: if True, restrict to Student Groups with status = "Active".
	    skip_archived_ay: if True, ignore Academic Years where archived = 1.

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
		rebuild_employee_bookings_for_student_group(sg_name)


# ─────────────────────────────────────────────────────────────
# Simple alias for your muscle memory
# ─────────────────────────────────────────────────────────────

def rebuild_employee_bookings_for_group(
	student_group: str,
	*,
	start_date: Optional[date] = None,
	end_date: Optional[date] = None,
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
	)
