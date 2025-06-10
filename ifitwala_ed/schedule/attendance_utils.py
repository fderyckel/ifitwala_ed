# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now_datetime, getdate, nowdate
from typing import List, Dict
from itertools import islice
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates
from ifitwala_ed.school_settings.doctype.term.term import get_current_term

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

	sched_name = sg.school_schedule
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
def fetch_existing_attendance(student_group: str, attendance_date: str) -> Dict[str, Dict[int, str]]:
	"""Return {student: {block: attendance_code}} for existing entries."""
	rows = frappe.db.get_all(
		"Student Attendance",
		filters={
			"student_group": student_group,
			"attendance_date": attendance_date,
		},
		fields=["student", "block_number", "attendance_code"]
	)
	data = {} 
	for r in rows: 
		data.setdefault(r.student, {})[r.block_number] = r.attendance_code 
	return data


@frappe.whitelist()
def previous_status_map(student_group: str, attendance_date: str) -> Dict[str, str]:
	"""
	For UI hints: returns {student: last_code} for the meeting just *before*
	<attendance_date> in that group's calendar.  Empty dict when none found.
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
def fetch_blocks_for_day(student_group: str, attendance_date: str) -> List[int]:
    """
    Given a student group and a specific attendance date,
    return the list of block numbers scheduled for that group on that day.
    """
    sg = frappe.get_cached_doc("Student Group", student_group)
    if not sg.school_schedule:
        return []

    from ifitwala_ed.schedule.schedule_utils import get_rotation_dates

    # 1. Find the rotation_day for that date
    rot_dates = get_rotation_dates(sg.school_schedule, sg.academic_year, include_holidays=False)
    rotation_map = {rd["date"].isoformat(): rd["rotation_day"] for rd in rot_dates}
    rotation_day = rotation_map.get(attendance_date)
    if not rotation_day:
        return []

    # 2. Return all blocks for that rotation_day in the Student Group Schedule
    rows = frappe.get_all(
        "Student Group Schedule",
        filters={"parent": student_group, "rotation_day": rotation_day},
        fields=["block_number"],
        order_by="block_number ASC"
    )
    return [r.block_number for r in rows if r.block_number is not None]


@frappe.whitelist()
def bulk_upsert_attendance(payload=None):
	"""Insert or update many Student Attendance rows in one go."""
	if isinstance(payload, str):
		try:
			payload = frappe.parse_json(payload)
		except Exception as e:
			frappe.throw(f"Invalid payload JSON: {e}")

	if not isinstance(payload, list):
		frappe.throw("Payload must be a list of records.")
	if not payload:
		return {"created": 0, "updated": 0}

	fieldkey = "attendance_code"
	required = {"student", "student_group", "attendance_date", fieldkey, "block_number"}

	for row in payload:
		missing = required - row.keys()
		if missing:
			frappe.throw(f"Missing keys {missing} in payload row.")

	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	is_admin = "Academic Admin" in roles

	# Preload Student Group metadata
	sample_group = payload[0]["student_group"]
	sg = frappe.get_cached_doc("Student Group", sample_group)
	program_school = (
		frappe.db.get_value("Program", sg.program, "school")
		if sg.program else None
	)

	today = getdate()

	current_term = get_current_term(sg.academic_year)
	if current_term:
		if today < getdate(current_term.term_start_date) or today > getdate(current_term.term_end_date):
			frappe.throw(_("You cannot edit attendance outside the current term."))
	else:
		# fallback: no term defined
		if row["attendance_date"] < nowdate():
			frappe.throw(_("You cannot modify attendance for past academic years."))	

	# Preload Student Group Schedule map: (rotation_day, block_number) → row
	schedule_rows = frappe.get_all(
		"Student Group Schedule", 
		filters={"parent": sample_group}, 
		fields=["rotation_day", "block_number", "instructor", "location"]
		)
	sched_map = {
		(row.rotation_day, row.block_number): row for row in schedule_rows
	}

	# Build date → rotation_day map
	from ifitwala_ed.schedule.schedule_utils import get_rotation_dates
	rot_dates = get_rotation_dates(sg.school_schedule, sg.academic_year, include_holidays=False)
	rotation_map = {rd["date"].isoformat(): rd["rotation_day"] for rd in rot_dates}

	keys = {(r["student"], r["attendance_date"], r["student_group"], r["block_number"]) for r in payload}
	existing = frappe.db.get_all(
		"Student Attendance", 
		filters={
			"student": ["in", list({k[0] for k in keys})], 
			"attendance_date": ["in", list({k[1] for k in keys})], 
			"student_group": ["in", list({k[2] for k in keys})], 
			"block_number": ["in", list({k[3] for k in keys})],
		},
		fields=["name", "student", "attendance_date", "student_group", "block_number", "attendance_code"] 
	)
	existing_map = { 
		(e.student, e.attendance_date, e.student_group, e.block_number): (e.name, e.attendance_code) 
		for e in existing
	}

	to_insert, to_update = [], []
	for row in payload:
		key = (row["student"], row["attendance_date"], row["student_group"], row["block_number"])

		if not is_admin:
			ok = frappe.db.exists(
				"Student Group Instructor",
				{"parent": row["student_group"], "instructor": ["in", _get_instructor_ids(user)]}
			)
			if not ok:
				frappe.throw("You don't have rights to record attendance for this group.")

		if row["attendance_date"] not in get_meeting_dates(row["student_group"]):
			frappe.throw(f"{row['attendance_date']} is not a meeting day for the group.")

		rotation_day = rotation_map.get(row["attendance_date"])
		block_row = next(
			(r for (rot, blk), r in sched_map.items() if rot == rotation_day),
			None
		) 
		
		enriched = {
			"name": f"ATT-{row['student']}-{row['attendance_date']}T{now_datetime().strftime('%H:%M')}",
			"student": row["student"],
			"student_group": row["student_group"],
			"attendance_date": row["attendance_date"],
			"attendance_code": row["attendance_code"],
			"attendance_time": now_datetime().time(),
			"attendance_method": "Manual",
			"academic_year": sg.academic_year,
			"term": sg.term,
			"program": sg.program,
			"course": sg.course,
			"school": program_school,
			"rotation_day": rotation_day,
			"block_number": block_row.block_number if block_row else None,
			"instructor": block_row.instructor if block_row else None,
			"location": block_row.location if block_row else None
		}
		
		if key in existing_map: 
			existing_name, existing_code = existing_map[key] 
			if row["attendance_code"] != existing_code: 
				to_update.append((existing_name, row["attendance_code"])) 
		else: 
			to_insert.append(enriched)

	if to_insert: 
		frappe.db.bulk_insert( 
			doctype="Student Attendance",
			fields=list(to_insert[0].keys()), 
			values=[list(r.values()) for r in to_insert], 
			ignore_duplicates=True 
		)
		frappe.db.commit()

	for name, new_code in to_update: 
		frappe.db.set_value( 
			"Student Attendance", name, {fieldkey: new_code}, update_modified=True)
	
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
