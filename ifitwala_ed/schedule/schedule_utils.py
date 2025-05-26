# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_days, today
from frappe import _
from datetime import timedelta, date

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

def get_rotation_dates(school_schedule_name, academic_year, include_holidays=False):
    # Fetch necessary documents
    school_schedule = frappe.get_cached_doc("School Schedule", school_schedule_name)
    academic_year_doc = frappe.get_cached_doc("Academic Year", academic_year)
    school_calendar = frappe.get_cached_doc("School Calendar", school_schedule.school_calendar)

    start_date = academic_year_doc.year_start_date
    end_date = academic_year_doc.year_end_date
    rotation_days = school_schedule.rotation_days

    # Collect holidays if not included in rotations
    holidays = set()
    if not include_holidays:
        holidays = {
            getdate(h.holiday_date)
            for h in school_calendar.holidays
        }

    rotation_dates = []
    current_date = getdate(start_date)
    rotation_index = 1

    while current_date <= getdate(end_date):
        if current_date not in holidays:
            rotation_dates.append({
                "date": current_date,
                "rotation_day": rotation_index
            })
            # Increment and reset rotation index as needed
            rotation_index = (rotation_index % rotation_days) + 1
        elif include_holidays:
            # Holidays included in rotation increment rotation day
            rotation_dates.append({
                "date": current_date,
                "rotation_day": rotation_index
            })
            rotation_index = (rotation_index % rotation_days) + 1
        # Else, skip holidays without incrementing rotation

        current_date += add_days(current_date, 1)

    return rotation_dates


def validate_duplicate_student(students):
	unique_students = []
	for stud in students:
		if stud.student in unique_students:
			frappe.throw(_("Student {0} - {1} appears Multiple times in row {2} & {3}")
				.format(stud.student, stud.student_name, unique_students.index(stud.student)+1, stud.idx))
		else:
			unique_students.append(stud.student)

	return None

"""Fast overlap detection for Student Group scheduling (v2025‑05‑09)."""
from collections import defaultdict

# ──────────────────────────────────────────────────────────────────────────────
# Utility
# ──────────────────────────────────────────────────────────────────────────────

# ── Custom error for hard‑rule conflicts ────────────────────────────────────
class OverlapError(frappe.ValidationError):
    """Raised when a scheduling conflict violates the hard rule."""
    pass

def get_conflict_rule():
    """Return 'Hard' or 'Soft' based on School Settings (defaults to Hard)."""
    try:
        return frappe.db.get_single_value("School", "schedule_conflict_rule") or "Hard"
    except Exception:
        # If School Settings not installed yet (e.g. tests)
        return "Hard"

@frappe.whitelist()
def check_slot_conflicts(group_doc):
    """Scan existing Student Group schedules for clashes.

    Returns a dict keyed by category (room / instructor / student) with a list of
    tuples (entity, rotation_day, block_number).
    """
    conflicts = defaultdict(list)

    # Pre‑collect instructors & students once (avoid per‑slot sub‑queries)
    instructor_ids = tuple(i.instructor for i in group_doc.get("instructors") or [])
    student_ids = tuple(s.student for s in group_doc.get("students") or [])

    for slot in group_doc.get("schedule") or []:
        rot, block = slot.rotation_day, slot.block_number

        # ── Room clash ───────────────────────────────────────────────────────
        if slot.room and frappe.db.exists(
            "Student Group Schedule",
            {
                "rotation_day": rot,
                "block_number": block,
                "room": slot.room,
                "parent": ("!=", group_doc.name),
                "docstatus": ("<", 2),
            },
        ):
            conflicts["room"].append((slot.room, rot, block))

        # ── Instructor clash ────────────────────────────────────────────────
        if instructor_ids:
            sql = """
                SELECT 1 FROM `tabStudent Group Instructor` gi
                JOIN `tabStudent Group Schedule` gs ON gs.parent = gi.parent
                WHERE gi.instructor IN %(instructors)s
                  AND gs.rotation_day = %(rot)s
                  AND gs.block_number = %(block)s
                  AND gs.parent != %(group)s
                  AND gs.docstatus < 2
                LIMIT 1
            """
            if frappe.db.sql(sql, {
                "instructors": instructor_ids, "rot": rot, "block": block, "group": group_doc.name
            }):
                conflicts["instructor"].append((instructor_ids, rot, block))

        # ── Student clash ───────────────────────────────────────────────────
        if student_ids:
            sql = """
                SELECT 1 FROM `tabStudent Group Student` st
                JOIN `tabStudent Group Schedule` gs ON gs.parent = st.parent
                WHERE st.student IN %(students)s
                  AND gs.rotation_day = %(rot)s
                  AND gs.block_number = %(block)s
                  AND gs.parent != %(group)s
                  AND gs.docstatus < 2
                LIMIT 1
            """
            if frappe.db.sql(sql, {
                "students": student_ids, "rot": rot, "block": block, "group": group_doc.name
            }):
                conflicts["student"].append((student_ids, rot, block))

    return dict(conflicts)


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

	chain = [school] + get_ancestors_of("School", school)
	for sch in chain:
		sched = frappe.db.get_value(
			"School Schedule",
			{"school_calendar": school_calendar, "school": sch},
			"name",
		)
		if sched:
			frappe.cache().set_value(cache_key, sched, expires_in=300)
			return sched

	frappe.cache().set_value(cache_key, "__none__", expires_in=300)
	return None



ROT_CACHE_TTL = 24 * 60 * 60		# one day

def build_rotation_map(calendar_name: str) -> dict[int, list[tuple]]:
	"""
	Returns a dict keyed by rotation_day (1-N) → list of dates.
	Respects:
	  • calendar.include_holidays_in_rotation
	  • holiday.is_weekend  (weekly-off days pause rotation)
	"""
	key = f"rotmap::{calendar_name}"
	if cached := frappe.cache().get_value(key):
		return cached

	cal = frappe.get_doc("School Calendar", calendar_name)
	rot_count = cal.rotation_days
	include_holidays = cal.include_holidays_in_rotation

	holiday_flag = {
		getdate(h.holiday_date): h.is_weekend for h in cal.holidays
	}
	out = {i: [] for i in range(1, rot_count + 1)}
	instr_index = 0

	for term in cal.terms:
		cur = getdate(term.start)
		while cur <= getdate(term.end):
			is_holiday = cur in holiday_flag
			is_weekend = holiday_flag.get(cur, 0)

			if is_holiday and not include_holidays:
				# skip rotation increment
				cur = add_days(cur, 1)
				continue

			rotation = 1 + (instr_index % rot_count)
			out[rotation].append(cur)
			instr_index += 1

			if is_weekend and not include_holidays:
				# weekend doesn’t advance rotation_index
				instr_index -= 1

			cur = add_days(cur, 1)

	frappe.cache().set_value(key, out, expires_in=ROT_CACHE_TTL)
	return out

CACHE_TTL = 6 * 60 * 60		# 6 hours

def build_user_calendar(user: str, start_date: date, days: int = 7) -> list[dict]:
	"""
	Returns a list of event dicts for <user> in [start_date, +days).
	Caches each day separately: key  calendar::<user>::YYYY-MM-DD
	"""
	out = []
	for i in range(days):
		d = start_date + timedelta(days=i)
		key = f"calendar::{user}::{d.isoformat()}"

		if cached := frappe.cache().get_value(key):
			out.extend(json.loads(cached))
			continue

		# build for that single day
		event_list = _build_events_for_day(user, d)
		frappe.cache().set_value(key, json.dumps(event_list), expires_in=CACHE_TTL)
		out.extend(event_list)
	return out

# ----------------------------------------------------------------
def _build_events_for_day(user, cur_date):
	"""
	Compute events for a user on a single date.
	Students → match student_groups
	Instructors → match instructor links
	"""
	events = []
	sg_filters = {
		"academic_year": ["!=", ""],		# only active groups
		"docstatus": 1
	}
	sgs = frappe.db.get_list("Student Group", filters=sg_filters, fields=["name", "school_calendar", "school"])

	for sg in sgs:
		rot_map = build_rotation_map(sg.school_calendar)
		# find rotation of cur_date (may be holiday)
		for rd, date_list in rot_map.items():
			if cur_date in date_list:
				events.extend(_expand_sg_rotation(sg.name, rd, cur_date))
				break

	return events

def _expand_sg_rotation(sg_name, rotation_day, cur_date):
	"""
	Read SG-Schedule rows for that rotation_day, fetch block times,
	return concrete events list
	"""
	rows = frappe.db.get_all(
		"Student Group Schedule",
		filters={"parent": sg_name, "rotation_day": rotation_day},
		fields=["block_number", "location", "instructor"]
	)
	if not rows:
		return []

	# get effective schedule
	sg = frappe.get_doc("Student Group", sg_name)
	sched = get_effective_schedule(sg.school_calendar, sg.school)
	block_times = frappe.db.get_all(
		"School Schedule Block",
		filters={"parent": sched},
		fields=["block_number", "from_time", "to_time"]
	)

	bt_map = {b.block_number: (b.from_time, b.to_time) for b in block_times}
	out = []
	for r in rows:
		if r.block_number not in bt_map:
			continue
		start, end = bt_map[r.block_number]
		out.append({
			"title": sg_name,
			"start": f"{cur_date} {start}",
			"end":   f"{cur_date} {end}",
			"location": r.location,
			"instructor": r.instructor,
			"student_group": sg_name
		})
	return out


def invalidate_for_student_group(doc, _):
	for s in doc.students:
		prefix = f"calendar::{s.student}::"
		_delete_keys(prefix)
	for instr in doc.instructors:
		prefix = f"calendar::{instr.instructor}::"
		_delete_keys(prefix)

def invalidate_all_for_calendar(doc, _):
	prefix = "calendar::"
	_delete_keys(prefix)		# brute-force; run during low load

def _delete_keys(prefix):
	rc = frappe.cache()
	for k in rc.get_keys(f"{prefix}*"):
		rc.delete_value(k)
