# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today
from typing import List, Dict
from itertools import islice
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates, get_effective_schedule 

ATT_CODE_FIELD 	 = "attendance_code" 
ATT_CODE_DOCTYPE = "Student Attendance Code"
ATT_DOCTYPE      = "Student Attendance"
SG_SCHEDULE_DT   = "Student Group Schedule"
SG_DOCTYPE       = "Student Group"
LIMIT_DEFAULT    = 30          # how many meeting dates to return


# ---------------------------------------------------------------------
# Helpers exposed to the JS page
# ---------------------------------------------------------------------

DEFAULT_PAGE_LEN = 25

def get_student_group_students(
        student_group: str,
        start: int = 0,
        page_length: int = DEFAULT_PAGE_LEN,
        with_medical: bool = False
) -> List[dict]:
    """
    Return a paginated list of students in <student_group>.

    * Always includes  full name, preferred name, image, DOB.
    * When with_medical=True it also fetches `medical_info`
      from Student Patient (collapsed with MAX() so duplicates disappear).
    """
    extra_select = ", MAX(sp.medical_info) AS medical_info" if with_medical else ""
    extra_join   = "LEFT JOIN `tabStudent Patient` sp ON sp.student = s.name" if with_medical else ""

    return frappe.db.sql(
        f"""
        SELECT
            s.name                              AS student,
            s.student_full_name                 AS student_name,      -- alias stays 'student_name' for JS
            s.student_preferred_name            AS preferred_name,
            s.student_image                     AS student_image,
            s.student_date_of_birth             AS birth_date
            {extra_select}
        FROM `tabStudent Group Student` g
        INNER JOIN `tabStudent` s ON s.name = g.student
        {extra_join}
        WHERE g.parent = %(sg)s
        GROUP BY s.name                         -- collapses duplicates from Patient JOIN
        ORDER BY s.student_full_name
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        {"sg": student_group, "limit": page_length, "offset": start},
        as_dict=True,
    )


@frappe.whitelist()
def fetch_students(student_group: str, start: int = 0, page_length: int = 500):
	students = get_student_group_students(student_group, start, page_length)

	total_students = frappe.db.count(
		"Student Group Student", {"parent": student_group}
	)

	sg = frappe.get_doc("Student Group", student_group)
	group_info = {
		"name":    sg.student_group_name or sg.name,
		"program": sg.program,
		"course":  sg.course,
		"cohort":  sg.cohort,
	}

	return {
		"students": students,
		"start":    start + page_length,
		"total":    total_students,
		"group_info": group_info,
	}


@frappe.whitelist()
def get_meeting_dates(student_group: str, limit: int | None = None) -> list[str]:
	"""Return recent scheduled dates for a student-group (holiday-filtered)."""
	limit = int(limit or LIMIT_DEFAULT)
	sg    = frappe.get_cached_doc(SG_DOCTYPE, student_group)

	# ── Resolve the School Schedule name ─────────────────────────
	sched_name   = None
	calendar_name = None
	school_name   = None

	# A. direct link (preferred)
	if getattr(sg, "school_schedule", None):
		sched_name   = sg.school_schedule
		sched_doc    = frappe.get_cached_doc("School Schedule", sched_name)
		calendar_name = sched_doc.school_calendar
		school_name   = sched_doc.school

	# B. infer via Program ➜ School ➜ get_effective_schedule()
	else:
		if sg.program:
			school_name = frappe.db.get_value("Program", sg.program, "school")
		if not school_name:
			# last-ditch: pick “Default School” (if you have one)
			school_name = frappe.defaults.get_global_default("school")

		# try first calendar for that school & SG academic year
		if school_name:
			calendar_name = frappe.db.get_value(
				"School Calendar",
				{
					"school": school_name,
					"academic_year": sg.academic_year
				},
				"name"
			)

		if calendar_name:
			sched_name = get_effective_schedule(calendar_name, school_name)

	# Bail out gracefully when still nothing
	if not sched_name:
		return []

	# ── Build rotation‐date list (unchanged) ─────────────────────
	rot_dates = get_rotation_dates(
		sched_name,
		sg.academic_year,
		include_holidays=False
	)
	rot_map = {}
	for rd in rot_dates:
		rot_map.setdefault(rd["rotation_day"], []).append(rd["date"])

	# rotation-days actually used by the SG
	rows = frappe.db.get_all(
		SG_SCHEDULE_DT,
		filters={"parent": student_group},
		fields=["rotation_day"],
		distinct=True
	)
	valid_days = {r.rotation_day for r in rows}

	meetings = sorted(
		{d for rd, lst in rot_map.items() if rd in valid_days for d in lst},
		reverse=True
	)
	return [d.isoformat() for d in meetings[:limit]]


@frappe.whitelist()
def previous_status_map(student_group: str, attendance_date: str) -> Dict[str, str]:
	"""
	For UI hints: returns {student: last_code} for the meeting just *before*
	<attendance_date> in that group’s calendar.  Empty dict when none found.
	"""
	meetings = get_meeting_dates(student_group, limit=LIMIT_DEFAULT + 1)
	try:
		prev_date = meetings[meetings.index(attendance_date) + 1]
	except (ValueError, IndexError):
		return {}

	rows = frappe.db.get_all(
    ATT_DOCTYPE,
    filters={
        "student_group": student_group,
        "attendance_date": prev_date,
    },
    fields=["student", ATT_CODE_FIELD]
	)
	return {r.student: getattr(r, ATT_CODE_FIELD) for r in rows}


@frappe.whitelist()
def bulk_upsert_attendance(payload: list[dict]) -> dict:
	"""
	Insert or update many Student Attendance rows in one go.
	`payload` must contain:
	  student, student_group, attendance_date, attendance_code
	Returns {"created": n, "updated": m}
	"""
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)

	if not payload:
		return {"created": 0, "updated": 0}

	user      = frappe.session.user
	roles     = set(frappe.get_roles(user))
	is_admin  = "Academic Admin" in roles
	fieldkey  = "attendance_code"

	# ── validate required keys quickly ──────────────────────────────
	required = {"student", "student_group", "attendance_date", fieldkey}
	for row in payload:
		missing = required - row.keys()
		if missing:
			frappe.throw(f"Missing keys {missing} in payload row.")

	# ── gather composite keys & existing rows ───────────────────────
	keys = {(r["student"], r["attendance_date"], r["student_group"]) for r in payload}
	existing = frappe.db.get_all(
		"Student Attendance",
		filters={
			"student":        ["in", {k[0] for k in keys}],
			"attendance_date":["in", {k[1] for k in keys}],
			"student_group":  ["in", {k[2] for k in keys}],
		},
		fields=["name", "student", "attendance_date", "student_group"],
	)
	existing_map = {
		(e.student, e.attendance_date, e.student_group): e.name for e in existing
	}

	to_insert, to_update = [], []

	for row in payload:
		key = (row["student"], row["attendance_date"], row["student_group"])

		# permission ────────────────
		if not is_admin:
			ok = frappe.db.exists(
				"Student Group Instructor",
				{"parent": row["student_group"],
				 "instructor": ["in", _get_instructor_ids(user)]}
			)
			if not ok:
				frappe.throw("You don’t have rights to record attendance for this group.")

		# meeting-day check ─────────
		if row["attendance_date"] not in get_meeting_dates(row["student_group"]):
			frappe.throw(f"{row['attendance_date']} is not a meeting day for the group.")

		# route ─────────────────────
		if key in existing_map:
			row["name"] = existing_map[key]
			to_update.append(row)
		else:
			to_insert.append(row)

	# ── bulk insert (new rows) ──────────────────────────────────────
	if to_insert:
		frappe.db.bulk_insert(
			"Student Attendance",
			fields=list(to_insert[0].keys()),		# includes attendance_code
			values=[tuple(r.values()) for r in to_insert],
			ignore_duplicates=True
		)

	# ── bulk update (existing) ──────────────────────────────────────
	for chunk in _grouper(to_update, 200):
		for r in chunk:
			frappe.db.set_value(
				"Student Attendance",
				r["name"],
				{fieldkey: r[fieldkey]},
				update_modified=False
			)
		frappe.db.commit()

	return {"created": len(to_insert), "updated": len(to_update)}

# ---------------------------------------------------------------------
# Utility internals
# ---------------------------------------------------------------------

def _get_instructor_ids(user) -> List[str]:
	return frappe.db.get_all(
		"Instructor",
		filters={"linked_user_id": user},
		pluck="name"
	)

def _grouper(seq, size):
	for i in range(0, len(seq), size):
		yield seq[i:i + size]
