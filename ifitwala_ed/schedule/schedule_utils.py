# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/schedule_utils.py

"""
Core schedule utilities for Ifitwala_Ed.

Responsibilities:
- Calendar / term helpers
    • get_calendar_holiday_set
    • get_school_term_bounds
    • current_academic_year

- Rotation engine
    • get_rotation_dates: map an Academic Year + School Schedule to
      (date, rotation_day) pairs, honoring weekends and holidays.

- Schedule resolution
    • get_effective_schedule: find the closest School Schedule for a
      given School Calendar + School (walking up the school tree).
    • get_effective_schedule_for_ay: find the closest School Schedule
      whose School Calendar belongs to a given Academic Year.

- Student Group expansion (generic)
    • iter_student_group_room_slots: expand a Student Group timetable
      into absolute room slots (location + start/end datetimes) for
      downstream systems:
          - central location_conflicts engine
          - employee bookings / staff calendar

- Cache invalidation helpers
    • invalidate_for_student_group
    • invalidate_all_for_calendar
    • _delete_staff_calendar_cache

- Visual helpers
    • get_block_colour / get_course_block_colour for timetable colours.

What is *not* here:
- Student Group validation, conflict rules, or SG-specific queries:
  see student_group.py and student_group_scheduling.py.
- Attendance-specific logic: see attendance_utils.py.
"""

import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, get_datetime
from frappe.utils.caching import redis_cache
from collections import defaultdict
from datetime import date
from ifitwala_ed.utilities.school_tree import get_ancestor_schools
from ifitwala_ed.schedule.student_group_scheduling import get_school_for_student_group
from typing import Optional


def get_calendar_holiday_set(calendar_name: str) -> set:
	"""
	Return the set of non-weekend holiday/break dates for a School Calendar.

	We deliberately mirror the semantics used in get_rotation_dates():
	- weekly_off = 1  → weekend (handled elsewhere, never instructional)
	- weekly_off = 0  → real holiday/break
	"""
	if not calendar_name:
		return set()

	rows = frappe.get_all(
		"School Calendar Holidays",
		filters={"parent": calendar_name, "weekly_off": 0},
		pluck="holiday_date",
	)

	return {getdate(d) for d in rows if d}

@redis_cache(ttl=86400)
def get_weekend_days_for_calendar(calendar_name: str | None) -> list[int]:
	"""
	Return weekend weekday numbers (JS 0-6) for a School Calendar.

	- Uses School Calendar Holidays.weekly_off = 1 when holidays are generated.
	- Falls back to School Calendar.weekly_off (single-select) when no child rows.
	- Final fallback: [6, 0] → Saturday, Sunday in JS getDay() convention.
	"""
	# No calendar → default Sat/Sun
	if not calendar_name:
		return [6, 0]

	try:
		cal = frappe.get_cached_doc("School Calendar", calendar_name)
	except Exception:
		return [6, 0]

	days: set[int] = set()

	# 1) Holidays child table with weekly_off = 1
	for h in getattr(cal, "holidays", []) or []:
		try:
			if int(getattr(h, "weekly_off", 0)) != 1:
				continue
			if not getattr(h, "holiday_date", None):
				continue

			d = getdate(h.holiday_date)           # Python date
			py_weekday = d.weekday()              # Monday=0 .. Sunday=6
			fc_day = (py_weekday + 1) % 7         # FullCalendar: Sunday=0 .. Saturday=6
			days.add(fc_day)
		except Exception:
			continue

	# 2) Fallback: parent.weekly_off single-select
	if not days:
		label_map = {
			"Sunday": 0,
			"Monday": 1,
			"Tuesday": 2,
			"Wednesday": 3,
			"Thursday": 4,
			"Friday": 5,
			"Saturday": 6,
		}
		weekday_label = getattr(cal, "weekly_off", None)
		if weekday_label:
			js = label_map.get(weekday_label)
			if js is not None:
				days.add(js)

	# 3) Final fallback: Sat–Sun
	if not days:
		return [6, 0]

	return sorted(days)


## function to get the start and end dates of the current academic year
## used in program enrollment, course enrollment tool.
@frappe.whitelist()
def get_school_term_bounds(school, academic_year):
	if not school or not academic_year:
		return {}

	checked_schools = set()
	current_school = school

	while current_school and current_school not in checked_schools:
		# Get terms for this school & academic year
		terms = frappe.db.sql("""
			SELECT name, term_start_date, term_end_date
			FROM `tabTerm`
			WHERE term_type = 'Academic'
				AND school = %s
				AND academic_year = %s
		""", (current_school, academic_year), as_dict=True)

		if terms:
			term_start = min(terms, key=lambda t: t["term_start_date"])
			term_end = max(terms, key=lambda t: t["term_end_date"])
			return {
				"term_start": term_start["name"],
				"term_end": term_end["name"]
			}

		checked_schools.add(current_school)

		# Get parent school using NestedSet
		school_doc = frappe.get_doc("School", current_school)
		ancestors = frappe.get_all(
			"School",
			filters={"lft": ["<", school_doc.lft], "rgt": [">", school_doc.rgt]},
			fields=["name", "lft"],
			order_by="lft desc"
		)
		if ancestors:
			current_school = ancestors[0]["name"]
		else:
			current_school = None

	return {}


## used in schedule.py (our virtual doctype for showing the schedules)
def current_academic_year():
	today_date = today()
	academic_year = frappe.db.get_value(
		"Academic Year",
		{
			"year_start_date": ["<=", today_date],
			"year_end_date": [">=", today_date],
			"status": "Active",
		},
		"name",
	)

	if not academic_year:
		frappe.throw(_("No active academic year found for today's date."))

	return academic_year


@frappe.whitelist()
def get_rotation_dates(school_schedule_name, academic_year, include_holidays=None):
	sched = frappe.get_cached_doc("School Schedule", school_schedule_name)
	calendar = frappe.get_cached_doc("School Calendar", sched.school_calendar)
	acad_year = frappe.get_cached_doc("Academic Year", academic_year)

	# explicit arg overrides checkbox (used by old callers)
	if include_holidays is None:
		include_holidays = bool(sched.include_holidays_in_rotation)

	# ──── first instructional day = Schedule.first_day_of_academic_year ────
	start_date = sched.first_day_of_academic_year or acad_year.year_start_date
	end_date = acad_year.year_end_date
	rot_days = sched.rotation_days
	next_rot = sched.first_day_rotation_day or 1

	# pre-collect holiday + weekend flags
	holiday_flag = {
		getdate(h.holiday_date): bool(h.weekly_off)  # True  → weekend
		for h in calendar.holidays
	}

	out = []
	cur = getdate(start_date)

	while cur <= getdate(end_date):
		is_weekend = holiday_flag.get(cur, False)
		is_holiday = cur in holiday_flag and not is_weekend

		# weekends never advance rotation & never yield events
		if is_weekend:
			cur = add_days(cur, 1)
			continue

		# break / holiday handling
		if is_holiday and not include_holidays:
			# skip rotation increment
			cur = add_days(cur, 1)
			continue

		out.append({"date": cur, "rotation_day": next_rot})
		next_rot = 1 + (next_rot % rot_days)
		cur = add_days(cur, 1)

	return out

# ──────────────────────────────────────────────────────────────────────────────
# Student Group helpers used by scheduling / conflict engines
# ──────────────────────────────────────────────────────────────────────────────

def get_conflict_rule():
	"""Return 'Hard' or 'Soft' based on School Settings (defaults to Hard)."""
	try:
		return frappe.db.get_single_value("School", "schedule_conflict_rule") or "Hard"
	except Exception:
		# If School Settings not installed yet (e.g. tests)
		return "Hard"

# ─────────────────────────────────────────────────────────────────────
# Utility called by Timetable builder (elsewhere in your app)
# ─────────────────────────────────────────────────────────────────────
def get_effective_schedule(school_calendar: str, school: str) -> str | None:
	"""
	Return closest School Schedule for <school> within the Calendar tree.
	Used by timetable generation code.  Cached in Redis for 5 min.
	"""
	cache_key = f"effective_schedule::{school_calendar}::{school}"
	sched = frappe.cache().get_value(cache_key)
	if sched:
		return None if sched == "__none__" else sched

	chain = get_ancestor_schools(school)
	for sch in chain:
		sched = frappe.db.get_value(
			"School Schedule",
			{"school_calendar": school_calendar, "school": sch},
			"name",
		)
		if sched:
			frappe.cache().set_value(cache_key, sched, expires_in_sec=300)
			return sched

	frappe.cache().set_value(cache_key, "__none__", expires_in_sec=300)
	return None


def get_effective_schedule_for_ay(academic_year: str, school: str | None) -> str | None:
	"""
	Find the nearest School Schedule (walking up the school tree) whose
	School Calendar belongs to <academic_year>. Cache for 5 minutes.
	"""
	if not (academic_year and school):
		return None

	rc = frappe.cache()
	key = f"ifw:eff_sched_ay:{academic_year}:{school}"

	if (cached := rc.get_value(key)) is not None:
		return None if cached == "__none__" else cached

	allowed = tuple(get_ancestor_schools(school))
	if not allowed:
		rc.set_value(key, "__none__", expires_in_sec=300)
		return None

	# calendars for AY within allowed schools
	cals = frappe.db.get_all(
		"School Calendar",
		filters={"academic_year": academic_year, "school": ["in", allowed]},
		pluck="name",
	)

	if cals:
		for sch in allowed:  # prefer closest
			sched = frappe.db.get_value(
				"School Schedule",
				{"school_calendar": ["in", cals], "school": sch},
				"name",
			)
			if sched:
				rc.set_value(key, sched, expires_in_sec=300)
				return sched

	rc.set_value(key, "__none__", expires_in_sec=300)
	return None


def iter_student_group_room_slots(
	sg_name: str,
	start_date: date | None = None,
	end_date: date | None = None,
) -> list[dict]:
	"""
	Expand a Student Group's schedule into concrete room slots with absolute datetimes.

	Returns a list of dicts like:
	{
		"location":       <Location name>,
		"start":          <datetime in site timezone>,
		"end":            <datetime in site timezone>,
		"rotation_day":   <int>,
		"block_number":   <int>,
		"student_group":  <Student Group name>,
	}

	This is the raw material for:
	  • central location-conflict checker (vs Meetings / School Events / etc.)
	  • Employee Booking materialization (teaching slots)

	Important: teaching slots are *not* generated on School Calendar holidays/breaks
	(non-weekend days where weekly_off = 0).
	"""

	sg = frappe.get_doc("Student Group", sg_name)

	# Guard rails: we need an Academic Year.
	if not getattr(sg, "academic_year", None):
		return []

	# Resolve school with a safe helper.
	school = getattr(sg, "school", None) or get_school_for_student_group(sg)
	if not school:
		return []

	# Resolve School Schedule:
	#   1) prefer explicit sg.school_schedule
	#   2) fall back to effective schedule for (AY, school) spine
	schedule_name = getattr(sg, "school_schedule", None)
	if not schedule_name:
		schedule_name = get_effective_schedule_for_ay(sg.academic_year, school)

	if not schedule_name:
		return []

	# Derive holiday (non-weekend) dates from the linked School Calendar.
	# We treat these as non-instructional for Employee Booking, even if the
	# rotation logic includes them.
	calendar_name = frappe.db.get_value("School Schedule", schedule_name, "school_calendar")
	holiday_dates = get_calendar_holiday_set(calendar_name)

	# 1) Rotation → list[dates] map for this schedule + AY
	rot_rows = get_rotation_dates(schedule_name, sg.academic_year)
	if not rot_rows:
		return []

	rotation_dates: dict[int, list[date]] = defaultdict(list)
	for row in rot_rows:
		d = getdate(row.get("date"))
		rd = row.get("rotation_day")
		if not d or rd is None:
			continue
		try:
			rd = int(rd)
		except Exception:
			continue
		rotation_dates[rd].append(d)

	if not rotation_dates:
		return []

	# 2) Block times per (rotation_day, block_number) from School Schedule Block
	block_rows = frappe.db.get_all(
		"School Schedule Block",
		filters={"parent": schedule_name},
		fields=["rotation_day", "block_number", "from_time", "to_time"],
	)
	if not block_rows:
		return []

	block_map: dict[tuple[int, int], tuple[str, str]] = {}
	for b in block_rows:
		if b.get("rotation_day") is None or b.get("block_number") is None:
			continue
		try:
			rd = int(b["rotation_day"])
			blk = int(b["block_number"])
		except Exception:
			continue
		block_map[(rd, blk)] = (b.get("from_time"), b.get("to_time"))

	if not block_map:
		return []

	# 3) SG schedule rows for that group
	sg_rows = frappe.db.get_all(
		"Student Group Schedule",
		filters={"parent": sg_name},
		fields=["rotation_day", "block_number", "location"],
	)

	if not sg_rows:
		return []

	# 4) Normalize boundaries
	start_bound = getdate(start_date) if start_date else None
	end_bound = getdate(end_date) if end_date else None

	slots: list[dict] = []

	for row in sg_rows:
		loc = row.get("location")
		if not loc:
			# no room → irrelevant for room conflicts
			continue

		rd = row.get("rotation_day")
		blk = row.get("block_number")
		if rd is None or blk is None:
			continue

		try:
			rd = int(rd)
			blk = int(blk)
		except Exception:
			continue

		bt = block_map.get((rd, blk))
		if not bt:
			# schedule validation should normally prevent this; fail-safe skip
			continue

		from_t, to_t = bt
		if not (from_t and to_t):
			continue

		dates_for_rotation = rotation_dates.get(rd, [])
		if not dates_for_rotation:
			continue

		for d in dates_for_rotation:
			# Window bounds
			if start_bound and d < start_bound:
				continue
			if end_bound and d > end_bound:
				continue

			# Never materialise teaching slots on School Calendar holidays/breaks
			# (non-weekend days where weekly_off = 0 in School Calendar Holidays).
			if d in holiday_dates:
				continue

			start_dt = get_datetime(f"{d} {from_t}")
			end_dt = get_datetime(f"{d} {to_t}")
			if not (start_dt and end_dt) or end_dt <= start_dt:
				continue

			slots.append(
				{
					"location": loc,
					"start": start_dt,
					"end": end_dt,
					"rotation_day": rd,
					"block_number": blk,
					"student_group": sg_name,
				}
			)

	return slots


def invalidate_for_student_group(doc, _):
	for s in doc.students:
		prefix = f"calendar::{s.student}::"
		_delete_keys(prefix)
	for instr in doc.instructors:
		prefix = f"calendar::{instr.instructor}::"
		_delete_keys(prefix)

	for emp in _collect_staff_calendar_employees(doc):
		_delete_staff_calendar_cache(emp)


def invalidate_all_for_calendar(doc, _):
	prefix = "calendar::"
	_delete_keys(prefix)  # brute-force; run during low load
	_delete_staff_calendar_cache()


def _delete_keys(prefix):
	rc = frappe.cache()
	for k in rc.get_keys(f"{prefix}*"):
		rc.delete_value(k)


def _collect_staff_calendar_employees(doc) -> set[str]:
	employees: set[str] = set()

	def _from_user(user_id: str | None) -> Optional[str]:
		if not user_id:
			return None
		return frappe.db.get_value("Employee", {"user_id": user_id}, "name")

	def _from_instructor(instr_name: str | None) -> Optional[str]:
		if not instr_name:
			return None
		return frappe.db.get_value("Instructor", instr_name, "employee")

	for row in getattr(doc, "instructors", []) or []:
		emp = (getattr(row, "employee", None) or "").strip()
		if emp:
			employees.add(emp)
			continue
		user_emp = _from_user((getattr(row, "user_id", None) or "").strip())
		if user_emp:
			employees.add(user_emp)
			continue
		instr_emp = _from_instructor(getattr(row, "instructor", None))
		if instr_emp:
			employees.add(instr_emp)

	for row in getattr(doc, "student_group_schedule", []) or []:
		emp = (getattr(row, "employee", None) or "").strip()
		if emp:
			employees.add(emp)
			continue
		instr_emp = _from_instructor(getattr(row, "instructor", None))
		if instr_emp:
			employees.add(instr_emp)

	return employees


def _delete_staff_calendar_cache(employee: Optional[str] = None):
	rc = frappe.cache()
	if employee:
		pattern = f"ifw:staff-cal:{employee}:*"
	else:
		pattern = "ifw:staff-cal:*"
	for key in rc.get_keys(pattern):
		rc.delete_value(key)


# ─── Block-type → colour (fallback hex) ────────────────────────────────
BLOCK_COLOURS = {
	"Course": "#6074ff",
	"Activity": "#ff9f40",
	"Recess": "#2ecc71",
	"Assembly": "#b455f5",
	"Other": "#95a5a6",
}


def get_block_colour(block_type: str | None) -> str:
	"""Return hex colour for a block type, with safe fallback."""
	return BLOCK_COLOURS.get((block_type or "").title(), "#74b9ff")


def get_course_block_colour(school: str | None) -> str:
	"""Return the course color set at the school level, or fallback to default course color."""
	if not school:
		return get_block_colour("Course")
	return (
		frappe.db.get_value("School", school, "course_color")
		or get_block_colour("Course")
	)

