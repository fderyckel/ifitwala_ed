# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate
from datetime import timedelta
from frappe.utils import today
from frappe import _

## function to get the start and end dates of the current academic year
## used in program enrollment, course enrollment too. 
@frappe.whitelist()
def get_school_term_bounds(school, academic_year):
	if not school or not academic_year:
		return {}

	terms = frappe.db.sql("""
		SELECT name, term_start_date, term_end_date
		FROM `tabTerm`
    WHERE term_type = `Academic` AND
		WHERE school = %s AND academic_year = %s
	    """, (school,academic_year), as_dict=True)

	if not terms:
		return {}

	# Sort in memory
	term_start = min(terms, key=lambda t: t["term_start_date"])
	term_end = max(terms, key=lambda t: t["term_end_date"])

	return {
		"term_start": term_start["name"],
		"term_end": term_end["name"]
	}

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

        current_date += timedelta(days=1)

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