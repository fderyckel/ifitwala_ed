# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt


import json
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.query_builder import DocType
from ifitwala_ed.schedule.schedule_utils import (
	get_rotation_dates,
	current_academic_year,
	get_block_colour, get_course_block_colour
)
from ifitwala_ed.utilities.school_tree import get_descendant_schools

# ─────────────────────────────────────────────────────────────────────
def _coerce_filters(raw):
	if not raw:
		return {}
	if isinstance(raw, str):
		try:
			raw = json.loads(raw)
		except Exception:
			return {}
	if isinstance(raw, list):
		return {f["fieldname"]: f.get("value") or f.get("default")
		        for f in raw if f.get("value") or f.get("default")}
	if isinstance(raw, dict):
		return raw
	return {}

# ─────────────────────────────────────────────────────────────────────
def _get_default_instructor(user):
	return frappe.db.get_value("Instructor", {"linked_user_id": user}, "name")

@frappe.whitelist()
def get_default_instructor():
	return _get_default_instructor(frappe.session.user)

@frappe.whitelist()
def get_default_academic_year():
	user = frappe.session.user
	today = frappe.utils.today()

	# 1) Resolve user's school (Employee → School; else Instructor → School)
	school = (
		frappe.db.get_value("Employee",  {"user_id": user}, "school")
		or frappe.db.get_value("Instructor", {"linked_user_id": user}, "school")
	)

	# 2) School-configured current AY wins
	if school:
		cfg_year = frappe.db.get_value("School", school, "current_academic_year")
		if cfg_year:
			return cfg_year

	# 3) Otherwise, pick a non-archived AY containing today, scoped to the school
	if school:
		year = frappe.db.get_value(
			"Academic Year",
			{
				"school": school,
				"archived": 0,
				"year_start_date": ["<=", today],
				"year_end_date":   [">=", today],
			},
			"name",
		)
		if year:
			return year

	# 4) Last fallback: any non-archived AY that contains today (helps initial setup)
	year = frappe.db.get_value(
		"Academic Year",
		{
			"archived": 0,
			"year_start_date": ["<=", today],
			"year_end_date":   [">=", today],
		},
		"name",
	)

	return year or ""


# ─────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def fetch_instructor_options(
		doctype=None,
		txt="",
		searchfield=None,
		start=0,
		page_len=20,
		filters=None):

	user   = frappe.session.user
	roles  = set(frappe.get_roles(user))

	Instr  = DocType("Instructor")
	qb     = frappe.qb
	query  = qb.from_(Instr).select(Instr.name, Instr.instructor_name)

	# ---------- scope by school --------------------------------------
	if "Academic Admin" in roles:
		user_school = frappe.db.get_value("Employee",  {"user_id": user}, "school") \
		           or frappe.db.get_value("Instructor", {"linked_user_id": user}, "school")
		if user_school:
			schools = [user_school] + get_descendant_schools(user_school)
			query = query.where(Instr.school.isin(schools))
	elif "Instructor" in roles:
		instr = _get_default_instructor(user)
		if not instr:
			return []
		query = query.where(Instr.name == instr)

	# ---------- name search ------------------------------------------
	if txt:
		query = query.where(Instr.instructor_name.like(f"%{txt}%"))

	rows = query.limit(page_len).offset(start).run()
	return [[r[0], r[1]] for r in rows]		# search_link format

# ─────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def get_instructor_events(start, end, filters=None):
	filters       = _coerce_filters(filters)
	school_calendar = filters.get("school_calendar")
	academic_year = filters.get("academic_year") or current_academic_year()
	user          = frappe.session.user
	roles         = set(frappe.get_roles(user))
	start_date    = getdate(start)
	end_date      = getdate(end)
	events               = []
	processed_calendars  = set()
	banner_dates         = set()

	def _fmt(t):
			"""Return HH:MM:SS with zero-padded hour."""
			if isinstance(t, (bytes, bytearray)):             # MariaDB can deliver bytes
					t = t.decode()
			s = str(t)                                        # fallback for datetime.time
			return s.zfill(8) if len(s) == 7 else s           # '9:10:00' → '09:10:00'

	# ---------- resolve instructor -----------------------------------
	if "Academic Admin" in roles:
		instructor = filters.get("instructor")
		if not instructor:
			return []
	else:
		instructor = _get_default_instructor(user)
		if not instructor:
			frappe.throw(_("Your User is not linked to an Instructor record."))
		filters["instructor"] = instructor		# tamper-proof

	# ---------- SG query ---------------------------------------------
	SG       = DocType("Student Group")
	SGSchedule = DocType("Student Group Schedule")

	groups = (
		frappe.qb.from_(SG)
		.inner_join(SGSchedule).on(SGSchedule.parent == SG.name)
		.select(
			SG.name,
			SG.student_group_name,
			SG.course,
			SG.program
		)
		.where(
			(SGSchedule.instructor == instructor) &
			(SG.status == "Active") &
			(
				(SG.academic_year == academic_year)
				if academic_year else
				frappe.qb.true()        # no filter when year blank
			)
		)
		.groupby(SG.name)     # distinct groups
	).run(as_dict=True)


	for grp in groups:
		# ----- school resolution --------------------------------------
		school  = None
		sched_name = None

		if grp.program:
			school = frappe.db.get_value("Program", grp.program, "school")

		if school:
			sched_name = frappe.db.get_value("School Schedule", {"school": school}, "name")
		else:
			# fallback: first schedule that starts with SG-name (activities)
			sched_name = frappe.db.get_value("School Schedule", {"name": ["like", f"{grp.name}%"]}, "name")
			if sched_name:
				school = frappe.db.get_value("School Schedule", sched_name, "school")

		if not sched_name or not school:
			continue

		sched_doc      = frappe.get_cached_doc("School Schedule", sched_name)
		rotation_dates = get_rotation_dates(
			sched_name,
			academic_year or sched_doc.academic_year,
			sched_doc.include_holidays_in_rotation
		)

		if not academic_year:
			academic_year = sched_doc.academic_year

		# ----- holiday / weekend banners (once per calendar) ----------
		cal_name = sched_doc.school_calendar
		if cal_name not in processed_calendars:
			processed_calendars.add(cal_name)
			cal_doc  = frappe.get_cached_doc("School Calendar", cal_name)
			hol_col  = cal_doc.break_color   or "#e74c3c"
			wen_col  = cal_doc.weekend_color or "#bdc3c7"

			for hol in cal_doc.holidays:
				h_date = getdate(hol.holiday_date)
				if h_date < start_date or h_date > end_date:
					continue
				key = h_date.isoformat()
				if key in banner_dates:
					continue
				banner_dates.add(key)

				is_weekend = bool(hol.weekly_off)        # ← NEW

				events.append({
					"id":    f"hol-{key}",
					"title": hol.description or ("Weekend" if is_weekend else "Holiday"),
					"start": h_date,
					"end":   h_date,
					"allDay": True,
					"color": wen_col if is_weekend else hol_col
				})

		# ----- SG-Schedule rows ---------------------------------------
		slots = (
			frappe.qb.from_(SGSchedule)
			.select(
				SGSchedule.rotation_day,
				SGSchedule.block_number,
				SGSchedule.location,
				SGSchedule.instructor
			)
			.where(SGSchedule.parent == grp.name)
		).run(as_dict=True)

		for s in slots:
			if not s.instructor:
				frappe.logger().warning(f"SG {grp.name} row {s.rotation_day}/{s.block_number} has no instructor")


		rot_map = {}
		for rd in rotation_dates:
			rot_map.setdefault(rd["rotation_day"], []).append(rd["date"])

		for sl in slots:
			block_meta = frappe.db.get_value(
				"School Schedule Block",
				{
					"parent": sched_name,
					"rotation_day": sl.rotation_day,
					"block_number": sl.block_number
				},
				["block_type", "from_time", "to_time"],
				as_dict=True
			)
			if not block_meta:
				continue

			color = (get_course_block_colour(school) if block_meta.block_type == "Course" else get_block_colour(block_meta.block_type))

			for dt in rot_map.get(sl.rotation_day, []):
				events.append({
					"id": f"{grp.name}-{sl.rotation_day}-{sl.block_number}-{dt}",
					"title": f"{grp.course} ({grp.student_group_name})",
					"start": f"{dt}T{_fmt(block_meta.from_time)}",
					"end":   f"{dt}T{_fmt(block_meta.to_time)}",
					"allDay": False,
					"color": color,
					"extendedProps": {
						"location":   sl.location,
						"block_type": block_meta.block_type,
						"student_group": grp.name
					}
				})

	return events
