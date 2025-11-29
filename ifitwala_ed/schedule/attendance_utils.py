# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/attendace_utils.py

import frappe
from frappe import _
from frappe.utils import now_datetime, getdate, nowdate
from frappe.utils.caching import redis_cache
from typing import List, Dict
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates
from ifitwala_ed.schedule.student_group_scheduling import get_school_for_student_group
from ifitwala_ed.school_settings.doctype.term.term import get_current_term


ATT_CODE_FIELD   = "attendance_code"
ATT_CODE_DOCTYPE = "Student Attendance Code"
ATT_DOCTYPE      = "Student Attendance"
SG_SCHEDULE_DT   = "Student Group Schedule"
SG_DOCTYPE       = "Student Group"
LIMIT_DEFAULT    = 30           # UI paging only
DEFAULT_PAGE_LEN = 25

MEETING_DATES_TTL = 24 * 60 * 60  # 1 day



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
	students = get_student_group_students(student_group, start, page_length, with_medical=True)

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
def fetch_existing_attendance(student_group: str, attendance_date: str) -> Dict[str, Dict[int, Dict[str, str]]]:
	rows = frappe.db.get_all(
		ATT_DOCTYPE,
		filters={"student_group": student_group, "attendance_date": attendance_date},
		fields=["student", "block_number", "attendance_code", "remark"],
	)
	data: Dict[str, Dict[int, Dict[str, str]]] = {}
	for r in rows:
		data.setdefault(r.student, {})[r.block_number] = {
			"code": r.attendance_code,
			"remark": r.remark or "",
		}
	return data


@frappe.whitelist()
def list_attendance_codes(show_in_attendance_tool: int | None = 1) -> List[Dict[str, str]]:
	"""
	Return attendance codes intended for the attendance tool.
	- When `show_in_attendance_tool` is 1 (default), restrict to codes configured for the UI.
	- Otherwise, return all codes while preserving display order.
	"""
	filters = {}
	if show_in_attendance_tool is not None:
		filters["show_in_attendance_tool"] = int(show_in_attendance_tool)

	records = frappe.db.get_all(
		ATT_CODE_DOCTYPE,
		fields=["name", "attendance_code", "attendance_code_name", "display_order", "color"],
		filters=filters,
		order_by="display_order asc, attendance_code_name asc",
	)

	default_color = "#2563eb"
	for row in records:
		row["color"] = row.get("color") or default_color

	return records


@frappe.whitelist()
def attendance_recorded_dates(student_group: str | None = None) -> List[str]:
	"""
	Return distinct dates where attendance exists for the given student group.
	Used to highlight completed days on the calendar.
	"""
	if not student_group:
		return []

	rows = frappe.db.sql(
		"""
		SELECT DISTINCT attendance_date
		FROM `tabStudent Attendance`
		WHERE student_group = %(student_group)s
		ORDER BY attendance_date ASC
		""",
		{"student_group": student_group},
	)
	return [row[0].isoformat() for row in rows if row and row[0]]


@frappe.whitelist()
def previous_status_map(student_group: str, attendance_date: str) -> Dict[str, str]:
	"""
	UI hint: {student -> last_code} for the meeting *before* <attendance_date>.
	"""
	meetings = get_meeting_dates(student_group)
	try:
		idx = meetings.index(attendance_date)
	except ValueError:
		return {}
	if idx == 0:
		return {}

	prev_date = meetings[idx - 1]
	rows = frappe.db.get_all(
		ATT_DOCTYPE,
		filters={"student_group": student_group, "attendance_date": prev_date},
		fields=["student", ATT_CODE_FIELD],
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
	"""Insert or update many Student Attendance rows in one go (multi-group safe)."""
	# ── 1) Parse & validate payload ─────────────────────────────────────
	if isinstance(payload, str):
		try:
			payload = frappe.parse_json(payload)
		except Exception as e:
			frappe.throw(f"Invalid payload JSON: {e}")

	if not isinstance(payload, list):
		frappe.throw("Payload must be a list of records.")
	if not payload:
		return {"created": 0, "updated": 0}

	required = {"student", "student_group", "attendance_date", "attendance_code", "block_number", "remark"}
	for row in payload:
		missing = required - set(row.keys())
		if missing:
			frappe.throw(f"Missing keys {missing} in payload row.")

	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	is_admin = "Academic Admin" in roles

	# ── 2) Precompute per-group context ─────────────────────────────────
	from ifitwala_ed.schedule.attendance_utils import get_meeting_dates
	from ifitwala_ed.schedule.attendance_utils import _get_instructor_ids
	from ifitwala_ed.schedule.attendance_utils import MEETING_DATES_TTL  # not required, but documents intent

	def _norm_block(b):
		return None if b in (None, "", "null") else int(b)

	group_names = sorted({r["student_group"] for r in payload})
	instructor_ids = set(_get_instructor_ids(user)) if not is_admin else set()

	group_ctx = {}
	for g in group_names:
		sg = frappe.get_cached_doc("Student Group", g)
		group_school = get_school_for_student_group(sg)

		# Term window (today must be within current term if one exists)
		today = getdate()
		current_term = get_current_term(sg.academic_year)
		term_guard = None
		if current_term:
			term_guard = (getdate(current_term.term_start_date), getdate(current_term.term_end_date))

		# Student Group Schedule → (rotation_day, block_number) → row
		schedule_rows = frappe.get_all(
			"Student Group Schedule",
			filters={"parent": g},
			fields=["rotation_day", "block_number", "instructor", "location"]
		)
		sched_map = {(int(r.rotation_day), int(r.block_number)): r for r in schedule_rows if r.block_number is not None}

		# Rotation map: date ISO -> rotation_day
		rot_dates = get_rotation_dates(sg.school_schedule, sg.academic_year, include_holidays=False)
		rotation_map = {rd["date"].isoformat(): int(rd["rotation_day"]) for rd in rot_dates}

		# Valid meeting dates (ISO strings) from cached helper
		valid_meetings = set(get_meeting_dates(g))

		# Permission: instructors of this SG (once per group)
		if is_admin:
			allowed = True
		else:
			allowed = bool(instructor_ids) and bool(
				frappe.db.exists("Student Group Instructor", {"parent": g, "instructor": ["in", list(instructor_ids)]})
			)

		group_ctx[g] = dict(
			sg=sg,
			program_school=group_school,
			term_guard=term_guard,
			rotation_map=rotation_map,
			sched_map=sched_map,
			valid_meetings=valid_meetings,
			allowed=allowed,
		)

	# ── 3) Load existing rows with one composite key query (chunked) ────
	# Use COALESCE for NULL block numbers; sentinel only for lookup, never stored.
	SENTINEL = -1
	def _norm_for_key(b):
		return SENTINEL if b in (None, "", "null") else int(b)

	keys = list({
		(r["student"], r["attendance_date"], r["student_group"], _norm_for_key(r.get("block_number")))
		for r in payload
	})

	existing_map = {}  # (student, date, group, block_norm) -> (name, code, remark)
	if keys:
		CHUNK = 1000
		for i in range(0, len(keys), CHUNK):
			chunk = keys[i:i+CHUNK]
			placeholders = ",".join(["(%s,%s,%s,%s)"] * len(chunk))
			params = [v for tup in chunk for v in tup]
			rows = frappe.db.sql(
				f"""
				SELECT
					name,
					student,
					attendance_date,
					student_group,
					COALESCE(block_number, {SENTINEL}) AS block_number,
					attendance_code,
					IFNULL(remark, '') AS remark
				FROM `tabStudent Attendance`
				WHERE (student, attendance_date, student_group, COALESCE(block_number, {SENTINEL}))
				      IN ({placeholders})
				""",
				params,
				as_dict=True,
			)
			for r in rows:
				existing_map[(r.student, r.attendance_date.isoformat(), r.student_group, int(r.block_number))] = (
					r.name, r.attendance_code, r.remark or ""
				)

	# ── 4) Build inserts / updates (with validation) ────────────────────
	to_insert, to_update = [], []

	for row in payload:
		stu = row["student"]
		grp = row["student_group"]
		att_date = row["attendance_date"]
		code = row["attendance_code"]
		remark_txt = (row.get("remark") or "").strip()[:255]
		block_norm = _norm_for_key(row.get("block_number"))

		# Permissions
		ctx = group_ctx.get(grp)
		if not ctx:
			frappe.throw(f"Unknown student group: {grp}")
		if not is_admin and not ctx["allowed"]:
			frappe.throw("You don't have rights to record attendance for this group.")

		# Term guard
		if ctx["term_guard"]:
			start_d, end_d = ctx["term_guard"]
			if not (start_d <= getdate() <= end_d):
				frappe.throw(_("You cannot edit attendance outside the current term."))
		else:
			# fallback when no term is defined
			if att_date < nowdate():
				frappe.throw(_("You cannot modify attendance for past academic years."))

		# Meeting date validation
		if att_date not in ctx["valid_meetings"]:
			frappe.throw(f"{att_date} is not a meeting day for the group.")

		# Rotation / schedule lookups
		rotation_day = ctx["rotation_map"].get(att_date)
		block_row = None
		if rotation_day is not None and block_norm != SENTINEL:
			block_row = ctx["sched_map"].get((rotation_day, int(block_norm)))

		# Composite key for existence test
		key = (stu, att_date, grp, block_norm)

		if key in existing_map:
			existing_name, existing_code, existing_note = existing_map[key]
			if code != existing_code or remark_txt != (existing_note or ""):
				to_update.append({
					"name": existing_name,
					"code": code,
					"remark": remark_txt,
				})
		else:
			# Insert row (provide full analytics enrichment; keep block_number NULL if unknown)
			sg = ctx["sg"]
			group_school = ctx["program_school"]
			block_number_value = None if block_norm == SENTINEL else int(block_norm)

			# generate a mostly-unique name (bulk_insert bypasses doc events)
			stamp = now_datetime().strftime('%H%M%S%f')
			name_val = f"ATT-{stu}-{att_date}-B{block_number_value or 'NA'}-T{stamp}"

			to_insert.append({
				"name": name_val,
				"student": stu,
				"student_group": grp,
				"attendance_date": att_date,
				"attendance_code": code,
				"attendance_time": now_datetime().time(),
				"attendance_method": "Manual",
				"academic_year": sg.academic_year,
				"term": sg.term,
				"program": sg.program,
				"course": sg.course,
				"school": group_school,
				"rotation_day": rotation_day,
				"block_number": block_number_value,
				"instructor": (block_row.instructor if block_row else None),
				"location": (block_row.location if block_row else None),
				"remark": remark_txt,
			})

	# ── 5) Write changes (one commit) ───────────────────────────────────
	if to_insert:
		frappe.db.bulk_insert(
			doctype="Student Attendance",
			fields=list(to_insert[0].keys()),
			values=[list(r.values()) for r in to_insert],
			ignore_duplicates=True,
		)  # bulk_insert bypasses events; fine here since we enrich fields ourselves. :contentReference[oaicite:1]{index=1}

	for upd in to_update:
		frappe.db.set_value(  # updates modified/modified_by automatically. :contentReference[oaicite:2]{index=2}
			"Student Attendance",
			upd["name"],
			{"attendance_code": upd["code"], "remark": upd["remark"]},
			update_modified=True,
		)

	frappe.db.commit()

	return {"created": len(to_insert), "updated": len(to_update)}


# --- Caching helpers for meeting dates --------------------------------

def _meeting_dates_key(student_group: str) -> str:
	return f"ifw:meeting_dates:{student_group}"

@frappe.whitelist()
@redis_cache(ttl=MEETING_DATES_TTL)
def get_meeting_dates(student_group: str | None = None, *, limit: int | None = None) -> List[str]:
	if not student_group:
		return []

	key = f"ifw:meeting_dates:{student_group}"

	sg = frappe.get_doc("Student Group", student_group)

	schedule_name = sg.school_schedule
	if not schedule_name:
		from ifitwala_ed.schedule.schedule_utils import get_effective_schedule_for_ay
		from ifitwala_ed.schedule.student_group_scheduling import get_school_for_student_group
		schedule_name = get_effective_schedule_for_ay(sg.academic_year, get_school_for_student_group(sg))

	if not schedule_name:
		frappe.cache().set_value(key, [], expires_in_sec=MEETING_DATES_TTL)
		return []

	# Get rotation days that the group actually uses
	used_rot_days = frappe.db.get_all(
		"Student Group Schedule",
		filters={"parent": student_group},
		fields=["rotation_day"],
		distinct=True,
	)
	rot_days_set = {int(r["rotation_day"]) for r in used_rot_days if r.get("rotation_day") is not None}
	if not rot_days_set:
		frappe.cache().set_value(key, [], expires_in_sec=MEETING_DATES_TTL)
		return []

	# Build the full rotation
	rot = get_rotation_dates(schedule_name, sg.academic_year, include_holidays=False)
	# Filter
	meeting = [rd["date"].isoformat() for rd in rot if rd["rotation_day"] in rot_days_set]

	# Cache + return
	frappe.cache().set_value(key, meeting, expires_in_sec=MEETING_DATES_TTL)

	return meeting if limit is None else meeting[:limit]



def invalidate_meeting_dates(student_group: str | None = None) -> None:
	rc = frappe.cache()
	if student_group:
		rc.delete_value(_meeting_dates_key(student_group))
		return
	for k in rc.get_keys("ifw:meeting_dates:*"):
		rc.delete_value(k)


# ---------------------------------------------------------------------
# Utility internals
# ---------------------------------------------------------------------

def _get_instructor_ids(user) -> List[str]:
	return frappe.db.get_all(
		"Instructor",
		filters={"linked_user_id": user},
		pluck="name"
	)
