# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, today
from typing import List, Dict
from itertools import islice
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates, get_effective_schedule 


ATT_CODE_DOCTYPE = "Student Attendance Code"
ATT_DOCTYPE      = "Student Attendance"
SG_SCHEDULE_DT   = "Student Group Schedule"
SG_DOCTYPE       = "Student Group"
LIMIT_DEFAULT    = 30          # how many meeting dates to return


# ---------------------------------------------------------------------
# Helpers exposed to the JS page
# ---------------------------------------------------------------------

@frappe.whitelist()
def get_meeting_dates(student_group: str, limit: int | None = None) -> List[str]:
	"""
	Return the last <limit> dates (ISO strings) on which <student_group> meets.
	Holidays / weekends are excluded according to the School Schedule flags.
	"""
	limit = int(limit or LIMIT_DEFAULT)
	sg    = frappe.get_cached_doc(SG_DOCTYPE, student_group)

	# ❶ Resolve effective School Schedule for this SG
	sched_name = get_effective_schedule(sg.school_calendar, sg.school)
	if not sched_name:
		return []

	# ❷ Build map rotation_day → list[date]  (utility already respects holidays)
	rot_dates = get_rotation_dates(
		sched_name,
		sg.academic_year,
		include_holidays=False       # holidays never need an attendance row
	)
	rot_map = {}
	for rd in rot_dates:
		rot_map.setdefault(rd["rotation_day"], []).append(rd["date"])

	# ❸ Fetch the rotation-days the SG is actually scheduled
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
	return [d.isoformat() for d in islice(meetings, limit)]


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
			"attendance_date": prev_date
		},
		fields=["student", "code"]
	)
	return {r.student: r.code for r in rows}


@frappe.whitelist()
def bulk_upsert_attendance(payload: List[dict]) -> dict:
	"""
	Insert or update many Student Attendance rows in one go.
	`payload` must be a list of plain dicts with at least:
	  student, student_group, attendance_date, code
	Returns {"created": n, "updated": m}
	Permissions: Instructor can only act on own groups; enforced here.
	"""
	if isinstance(payload, str):
		payload = frappe.parse_json(payload)   # for JS XHR

	if not payload:
		return {"created": 0, "updated": 0}

	user    = frappe.session.user
	roles   = set(frappe.get_roles(user))
	is_admin = "Academic Admin" in roles

	# ------- split new vs existing -----------------------------------
	keys = {(d["student"], d["attendance_date"], d["student_group"]) for d in payload}
	existing = frappe.db.get_all(
		ATT_DOCTYPE,
		filters={
			"student_group": ["in", {k[2] for k in keys}],
			"attendance_date": ["in", {k[1] for k in keys}],
			"student": ["in", {k[0] for k in keys}],
		},
		fields=["name", "student", "attendance_date", "student_group"],
	)
	existing_map = {
		(e.student, e.attendance_date, e.student_group): e.name for e in existing
	}

	to_insert, to_update = [], []
	for row in payload:
		key = (row["student"], row["attendance_date"], row["student_group"])

		# --- permission check ----------------------------------------
		if not is_admin:
			_ok = frappe.db.exists(
				"Student Group Instructor",
				{
					"parent": row["student_group"],
					"instructor": ["in", _get_instructor_ids(user)],
				}
			)
			if not _ok:
				frappe.throw("You don’t have rights to record attendance for this group.")

		# --- validate the date --------------------------------------
		if row["attendance_date"] not in get_meeting_dates(row["student_group"]):
			frappe.throw(f"{row['attendance_date']} is not a meeting day for the group.")

		# --- route ---------------------------------------------------
		if key in existing_map:
			row["name"] = existing_map[key]
			to_update.append(row)
		else:
			to_insert.append(row)

	# ------- bulk_insert (new rows) ----------------------------------
	if to_insert:
		frappe.db.bulk_insert(
			ATT_DOCTYPE,
			fields=list(to_insert[0].keys()),
			values=[tuple(r.values()) for r in to_insert],
			ignore_duplicates=True
		)

	# ------- bulk update (existing rows) -----------------------------
	for chunk in _grouper(to_update, 200):
		if not chunk:
			continue
		for r in chunk:
			frappe.db.set_value(
				ATT_DOCTYPE,
				r["name"],
				{"code": r["code"]},
				update_modified=False,
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
