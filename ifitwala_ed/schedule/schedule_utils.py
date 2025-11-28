# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/schedule_utils.py

import json
import frappe
from frappe import _
from frappe.utils import getdate, add_days, today, get_datetime
from collections import defaultdict
from datetime import timedelta, date
from ifitwala_ed.utilities.school_tree import get_ancestor_schools
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
    academic_year = frappe.db.get_value("Academic Year",
        {"year_start_date": ["<=", today_date], "year_end_date": [">=", today_date],
         "status": "Active"
        },"name"
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
	end_date   = acad_year.year_end_date
	rot_days   = sched.rotation_days
	next_rot   = sched.first_day_rotation_day or 1

	# pre-collect holiday + weekend flags
	holiday_flag = {
		getdate(h.holiday_date): bool(h.weekly_off)     # True  → weekend
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


def validate_duplicate_student(students):
	unique_students = []
	for stud in students:
		if stud.student in unique_students:
			frappe.throw(_("Student {0} - {1} appears Multiple times in row {2} & {3}")
				.format(stud.student, stud.student_name, unique_students.index(stud.student)+1, stud.idx))
		else:
			unique_students.append(stud.student)

	return None

"""Fast overlap detection for Student Group scheduling"""
from collections import defaultdict

# ──────────────────────────────────────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────────────────────────────────────

# ── Custom error for hard‑rule conflicts ────────────────────────────────────
class OverlapError(frappe.ValidationError):
    """Raised when a scheduling conflict violates the hard rule."""
    pass

# ──────────────────────────────────────────────────────────────────────────────
# Student Group helpers used by scheduling / conflict engines
# ──────────────────────────────────────────────────────────────────────────────


def get_school_for_student_group(sg_doc_or_name) -> Optional[str]:
	"""
	Return the best school for a Student Group in priority order:
	1) Student Group.school (if present)
	2) Program Offering.school (if SG has program_offering)
	3) Program.school (legacy fallback)
	"""
	sg = frappe.get_doc("Student Group", sg_doc_or_name) if isinstance(sg_doc_or_name, str) else sg_doc_or_name

	# 1) SG-level school wins
	if getattr(sg, "school", None):
		return sg.school

	# 2) Then the Program Offering's school (if linked)
	if getattr(sg, "program_offering", None):
		sch = frappe.db.get_value("Program Offering", sg.program_offering, "school")
		if sch:
			return sch

	# 3) Legacy fallback: Program's school
	if getattr(sg, "program", None):
		return frappe.db.get_value("Program", sg.program, "school")

	return None


def get_conflict_rule():
	"""Return 'Hard' or 'Soft' based on School Settings (defaults to Hard)."""
	try:
		return frappe.db.get_single_value("School", "schedule_conflict_rule") or "Hard"
	except Exception:
		# If School Settings not installed yet (e.g. tests)
		return "Hard"


def _extract(obj, attr):
	"""Return obj[attr] or obj.attr, whichever exists (None if missing)."""
	if isinstance(obj, dict):
		return obj.get(attr)
	return getattr(obj, attr, None)


def _uniq(seq):
	"""Return list of unique, truthy items preserving order."""
	seen = set()
	out = []
	for item in seq:
		if not item or item in seen:
			continue
		seen.add(item)
		out.append(item)
	return out


def _get_display_map(doctype: str, label_field: str, ids: tuple[str, ...]) -> dict[str, str]:
	"""Return {id: display_label} for the given ids."""
	if not ids:
		return {}

	unique_ids = list(dict.fromkeys([i for i in ids if i]))
	if not unique_ids:
		return {}

	rows = frappe.db.get_all(
		doctype,
		filters={"name": ["in", unique_ids]},
		fields=["name", label_field],
	)
	return {
		row["name"]: row.get(label_field) or row["name"]
		for row in rows
	}


def _build_slot_conditions(slots: list[tuple[int, int]]) -> tuple[str, dict]:
	"""Return SQL snippet + params for (rotation_day, block_number) pairs."""
	conds = []
	params = {}
	for idx, (rot, blk) in enumerate(slots):
		conds.append(f"(gs.rotation_day = %(rot_{idx})s AND gs.block_number = %(blk_{idx})s)")
		params[f"rot_{idx}"] = rot
		params[f"blk_{idx}"] = blk
	return " OR ".join(conds), params


def _aggregate_conflicts(rows, label_map):
	"""Group rows by (rotation_day, block_number) with deduped ids & groups."""
	slots = {}
	for row in rows:
		rot = row.get("rotation_day")
		blk = row.get("block_number")
		entity = row.get("entity")
		group = row.get("student_group")

		if rot is None or blk is None or not entity:
			continue
		try:
			rot = int(rot)
			blk = int(blk)
		except Exception:
			continue

		key = (rot, blk)
		entry = slots.setdefault(
			key,
			{"rotation_day": rot, "block_number": blk, "ids": [], "groups": []},
		)
		entry["ids"].append(entity)
		entry["groups"].append(group)

	out = []
	for entry in slots.values():
		ids = tuple(_uniq(entry["ids"]))
		out.append({
			"rotation_day": entry["rotation_day"],
			"block_number": entry["block_number"],
			"ids": ids,
			"labels": tuple(label_map.get(i, i) for i in ids),
			"groups": tuple(_uniq(entry["groups"])),
		})
	return out

@frappe.whitelist()
def check_slot_conflicts(group_doc):
	"""Scan existing Student Group schedules for clashes.

	Returns a dict keyed by category (instructor / student) with a list of
	payload dicts:
		{
			"rotation_day": <int>,
			"block_number": <int>,
			"ids": (<entity ids>, ...),
			"labels": (<readable names>, ...),
		}

	Room/location clashes are handled by the central location_conflicts engine.
	"""
	# Normalize input: client calls send JSON string, server calls may send a dict/doc
	if isinstance(group_doc, str):
		group_doc = frappe._dict(json.loads(group_doc))

	# Ensure .name is never NULL for the SQL filter (gs.parent != %(grp)s)
	group_name = group_doc.get("name") or "__new__"

	conflicts = defaultdict(list)

	# Pre-collect instructors & students once (avoid per-slot sub-queries)
	instructors = group_doc.get("instructors") or []
	students    = group_doc.get("students") or []
	slots       = group_doc.get("student_group_schedule") or []

	instructor_entities = [
		_extract(i, "employee") or _extract(i, "instructor")
		for i in instructors
		if _extract(i, "employee") or _extract(i, "instructor")
	]
	instructor_ids = tuple(_uniq(instructor_entities))
	student_ids = tuple(
		_extract(s, "student") for s in students if _extract(s, "student")
	)

	normalized_slots: list[tuple[int, int]] = []
	for slot in slots:
		rot = _extract(slot, "rotation_day")
		blk = _extract(slot, "block_number")
		if rot is None or blk is None:
			continue
		try:
			rot = int(rot)
			blk = int(blk)
		except Exception:
			continue
		normalized_slots.append((rot, blk))

	if not normalized_slots:
		return {}

	slot_clause, slot_params = _build_slot_conditions(normalized_slots)
	if not slot_clause:
		return {}

	def _instructor_label_map(entities) -> dict[str, str]:
		"""
		Map Employee IDs → human-readable labels.

		We try, in order of preference:
		- employee_full_name (your new field)
		- employee_name      (legacy ERPNext field, if present)
		- first_name + last_name
		- fallback to the Employee ID itself
		"""
		if not entities:
			return {}

		ids = list({e for e in entities if e})
		if not ids:
			return {}

		# Build a safe field list that matches your Employee schema
		fields = ["name"]

		# New schema (your current Employee)
		if frappe.db.has_column("Employee", "employee_full_name"):
			fields.append("employee_full_name")

		# Legacy ERPNext-style field – keep for compatibility on other sites
		if frappe.db.has_column("Employee", "employee_name"):
			fields.append("employee_name")

		# Extra safety: if you ever rely on first/last names
		if frappe.db.has_column("Employee", "employee_first_name"):
			fields.append("employee_first_name")
		if frappe.db.has_column("Employee", "employee_last_name"):
			fields.append("employee_last_name")

		emp_rows = frappe.get_all(
			"Employee",
			filters={"name": ["in", ids]},
			fields=fields,
			ignore_permissions=True,
		)

		label_map: dict[str, str] = {}

		for row in emp_rows:
			# frappe.get_all → dict rows
			name = row.get("name")

			label = (
				row.get("employee_full_name")
				or row.get("employee_name")
				or " ".join(
					[
						(row.get("employee_first_name") or "").strip(),
						(row.get("employee_last_name") or "").strip(),
					]
				).strip()
				or name
			)

			if name:
				label_map[name] = label

		return label_map

	instructor_labels = _instructor_label_map(instructor_ids)
	student_labels = _get_display_map("Student", "student_full_name", student_ids)

	if instructor_ids:
		params = {"grp": group_name, "ids": instructor_ids}
		params.update(slot_params)
		rows = frappe.db.sql(
			f"""
			SELECT coalesce(gi.employee, gi.instructor) AS entity,
				   gs.rotation_day,
				   gs.block_number,
				   gs.parent AS student_group
			FROM `tabStudent Group Instructor` gi
			JOIN `tabStudent Group Schedule`  gs ON gs.parent = gi.parent
			WHERE coalesce(gi.employee, gi.instructor) IN %(ids)s
				AND gs.parent != %(grp)s
				AND gs.docstatus < 2
				AND ({slot_clause})
			""",
			params,
			as_dict=True,
		)
		conflicts["instructor"] = _aggregate_conflicts(rows, instructor_labels)

	if student_ids:
		params = {"grp": group_name, "ids": student_ids}
		params.update(slot_params)
		rows = frappe.db.sql(
			f"""
			SELECT st.student AS entity,
				   gs.rotation_day,
				   gs.block_number,
				   gs.parent AS student_group
			FROM `tabStudent Group Student` st
			JOIN `tabStudent Group Schedule` gs ON gs.parent = st.parent
			WHERE st.student IN %(ids)s
				AND gs.parent != %(grp)s
				AND gs.docstatus < 2
				AND ({slot_clause})
			""",
			params,
			as_dict=True,
		)
		conflicts["student"] = _aggregate_conflicts(rows, student_labels)

	return dict(conflicts)




@frappe.whitelist()
def fetch_block_grid(schedule_name: str | None = None, sg: str | None = None) -> dict:
	"""Return rotation-day metadata to build the quick-add matrix.
		Args:
			schedule_name: explicit School Schedule name (may be None)
			sg: Student Group name - used to infer schedule & instructors
	"""

	# Resolve schedule when not supplied
	if not schedule_name:
		sg = sg or frappe.form_dict.get("sg")         # fallback for older calls
		if not sg:
			frappe.throw(_("Either schedule_name or sg is required."))
		sg_doc = frappe.get_doc("Student Group", sg)
		schedule_name = sg_doc._get_school_schedule().name

	doc = frappe.get_cached_doc("School Schedule", schedule_name)
	grid = {}
	for blk in doc.school_schedule_block:		# variable blocks per day
		grid.setdefault(blk.rotation_day, []).append({
			"block": blk.block_number,
			"label": f"B{blk.block_number}",
			"from":  blk.from_time,
			"to":    blk.to_time
		})
	# sort blocks inside each day
	for day in grid:
		grid[day].sort(key=lambda b: b["block"])
	return {
		"schedule_name": schedule_name,
		"days": sorted(grid.keys()),
		"grid": grid,				# {day: [blocks…]}
		"instructors": [
			{"value": i.instructor, "label": i.instructor_name or i.instructor}
			for i in frappe.get_doc("Student Group", frappe.form_dict.sg).instructors
		]
	}

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

			slots.append({
				"location":      loc,
				"start":         start_dt,
				"end":           end_dt,
				"rotation_day":  rd,
				"block_number":  blk,
				"student_group": sg_name,
			})

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
	_delete_keys(prefix)		# brute-force; run during low load
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
	"Course":   "#6074ff",
	"Activity": "#ff9f40",
	"Recess":   "#2ecc71",
	"Assembly": "#b455f5",
	"Other":    "#95a5a6",
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
