# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.utils import getdate
from frappe.query_builder import DocType
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates, current_academic_year, get_block_colour
from ifitwala_ed.utilities.school_tree import get_descendant_schools

# -------------------------------------------------------------------------
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

# -------------------------------------------------------------------------
def _get_default_instructor(user):
	"""Return Instructor name linked to <user> or None."""
	return frappe.db.get_value("Instructor", {"linked_user_id": user}, "name")

@frappe.whitelist()
def get_default_instructor():
	"""JS helper → default the dropdown for Instructor-role users."""
	return _get_default_instructor(frappe.session.user)

# -------------------------------------------------------------------------
@frappe.whitelist()
def fetch_instructor_options(txt="", page_len=20, start=0, filters=None):
	"""
	Return list of {value,label} for the instructor filter, limited to the
	user’s default/descendant schools (Academic Admin) or their own record.
	Used by JS to populate the dropdown.
	"""
	user = frappe.session.user
	roles = set(frappe.get_roles(user))

	user_school = frappe.db.get_value(
	    "Employee", {"user_id": user}, "school"
	) or frappe.db.get_value(
	    "Instructor", {"linked_user_id": user}, "school"
	)

	if not user_school:
		return []

	query = frappe.qb.from_("Instructor").select("name", "instructor_name")

	if "Academic Admin" in roles:
		schools = get_descendant_schools(user_school) + [user_school]
		query = query.where(("school").isin(schools))
	else:
		# ordinary Instructor → only themselves
		instr = _get_default_instructor(user)
		if not instr:
			return []
		query = query.where(("name") == instr)

	if txt:
		query = query.where(("instructor_name").like(f"%{txt}%"))

	query = query.limit(page_len).offset(start)

	return [{"value": r[0], "label": r[1]} for r in query.run()]

# -------------------------------------------------------------------------
@frappe.whitelist()
def get_instructor_events(start, end, filters=None):
	"""
	FullCalendar feed. Parameters arrive as ISO strings.
	Returns list[dict] → FullCalendar Event objects.
	"""
	filters = _coerce_filters(filters)
	user     = frappe.session.user
	roles    = set(frappe.get_roles(user))

	# ---- work out ≡ instructor ------------------------------------------------
	if "Academic Admin" in roles:
		instructor = filters.get("instructor")
		if not instructor:
			frappe.throw(_("Please pick an Instructor."), title=_("Missing Filter"))
	else:
		instructor = _get_default_instructor(user)
		if not instructor:
			frappe.throw(_("Your User is not linked to an Instructor record."))
		# protect against tampering
		filters["instructor"] = instructor

	academic_year = (
	    filters.get("academic_year") or current_academic_year()
	)

	# ---- query Student Groups -------------------------------------------------
	SG           = DocType("Student Group")
	SGInstr      = DocType("Student Group Instructor")
	SGSchedule   = DocType("Student Group Schedule")

	start_date = getdate(start)
	end_date   = getdate(end)

	groups = (
		frappe.qb.from_(SG)
		.inner_join(SGInstr).on(SGInstr.parent == SG.name)
		.select(
			SG.name, SG.student_group_name, SG.course, SG.school
		)
		.where(
			(SGInstr.instructor == instructor) &
			(SG.academic_year == academic_year) &
			(SG.status == "Active")
		)
	).run(as_dict=True)

	events              = []
	processed_calenders = set()
	banner_dates        = set()

	for grp in groups:
		# ---------- school schedule & rotation dates --------------------------
		sched_name = frappe.db.get_value(
		    "School Schedule", {"school": grp.school}, "name"
		)
		if not sched_name:
			continue

		sched_doc      = frappe.get_cached_doc("School Schedule", sched_name)
		rotation_dates = get_rotation_dates(
		    sched_name, academic_year, sched_doc.include_holidays_in_rotation
		)

		# ---------- weekend / holiday banners (once per calendar) ------------
		cal_name = sched_doc.school_calendar
		if cal_name not in processed_calenders:
			processed_calenders.add(cal_name)
			cal_doc = frappe.get_cached_doc("School Calendar", cal_name)
			hol_col = cal_doc.break_color   or "#e74c3c"
			wen_col = cal_doc.weekend_color or "#bdc3c7"

			for hol in cal_doc.holidays:
				h_date = getdate(hol.holiday_date)
				if h_date < start_date or h_date > end_date:
					continue
				key = h_date.isoformat()
				if key in banner_dates:
					continue
				banner_dates.add(key)
				events.append({
					"id":    f"hol-{key}",
					"title": hol.description or ("Weekend" if hol.is_weekend else "Holiday"),
					"start": h_date,
					"end":   h_date,
					"allDay": True,
					"color": wen_col if hol.is_weekend else hol_col
				})

		# ---------- SG-Schedule rows -----------------------------------------
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

			colour = get_block_colour(block_meta.block_type)

			for dt in rot_map.get(sl.rotation_day, []):
				events.append({
					"id":   f"{grp.name}-{sl.rotation_day}-{sl.block_number}-{dt}",
					"title": f"{grp.course} ({grp.student_group_name})",
					"start": f"{dt} {block_meta.from_time}",
					"end":   f"{dt} {block_meta.to_time}",
					"allDay": False,
					"color": colour,
					"extendedProps": {
						"location":   sl.location,
						"block_type": block_meta.block_type,
						"student_group": grp.name
					}
				})

	return events
