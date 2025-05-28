# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates, current_academic_year
from frappe import _
from frappe.utils import getdate

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

class Schedule(Document):
	
	def db_insert(self, *args, **kwargs):
		pass

	def load_from_db(self):
		pass

	def db_update(self):
		pass

	@staticmethod
	def get_list(args):
		pass

	@staticmethod
	def get_count(args):
		pass

	@staticmethod
	def get_stats(args):
		pass 
  
@frappe.whitelist() 
def get_events(self, start, end, filters=None):
	user = frappe.session.user
	roles = frappe.get_roles(user)
	academic_year = filters.get("academic_year") if filters else current_academic_year()

	instructor = None

	if "Academic Admin" in roles:
		instructor = filters.get("instructor")
		if not instructor:
			frappe.throw(_("Please select an instructor."))
	elif "Instructor" in roles:
		instructor = frappe.db.get_value("Instructor", {"user_id": user}, "name")
		if not instructor:
			frappe.throw(_("Instructor profile not found."))
	else:
		frappe.throw(_("Insufficient permissions."))

	schedule_entries = []

	# Parse incoming strings → date objects
	start_date = getdate(start)
	end_date   = getdate(end)

	# De-dup helpers
	processed_calendars = set()   # calendars we’ve already scanned
	banner_dates        = set() 

	StudentGroup = DocType("Student Group")
	StudentGroupInstructor = DocType("Student Group Instructor")
	StudentGroupSchedule = DocType("Student Group Schedule") 
		
	groups = ( 
		frappe.qb.from_(StudentGroup) 
		.inner_join(StudentGroupInstructor).on(StudentGroupInstructor.parent == StudentGroup.name)
		.select(
			StudentGroup.name, StudentGroup.student_group_name,
			StudentGroup.course, StudentGroup.school
		)
		.where(
			(StudentGroupInstructor.instructor == instructor) &
			(StudentGroup.academic_year == academic_year) &
			(StudentGroup.status == 'Active')
		)
	).run(as_dict=True) 
		
	for group in groups: 
		school_schedule_name = frappe.db.get_value("School Schedule", {"school": group.school}, "name")
		if not school_schedule_name:
			continue

		school_schedule = frappe.get_cached_doc("School Schedule", school_schedule_name)
		rotation_dates = get_rotation_dates(school_schedule_name, academic_year, school_schedule.include_holidays_in_rotation)

		# ── Get / cache holidays for this calendar ─────────────────────────────
		cal_name = school_schedule.school_calendar
		if cal_name not in processed_calendars:
			processed_calendars.add(cal_name)

			cal_doc = frappe.get_cached_doc("School Calendar", cal_name)
			hol_colour  = cal_doc.break_color   or "#e74c3c"  
			wend_colour = cal_doc.weekend_color or "#bdc3c7"  

			for hol in cal_doc.holidays:               # child table rows
				h_date = getdate(hol.holiday_date)
				if h_date < start_date or h_date > end_date:
					continue

				key = h_date.isoformat()
				if key in banner_dates:                # avoid duplicates across calendars
					continue
				banner_dates.add(key)

				schedule_entries.append({
					"name":  f"hol-{key}",
					"title": hol.description or ("Weekend" if hol.is_weekend else "School Holiday"),
					"start": h_date,
					"end":   h_date,
					"allDay": 1,
					"color":  wend_colour if hol.is_weekend else hol_colour
				})

		schedules = (
			frappe.qb.from_(StudentGroupSchedule)
			.select(
				StudentGroupSchedule.rotation_day,
				StudentGroupSchedule.block_number,
				StudentGroupSchedule.from_time,
				StudentGroupSchedule.to_time,
				StudentGroupSchedule.location, 
				StudentGroupSchedule.instructor,
			)
			.where(StudentGroupSchedule.parent == group.name)
		).run(as_dict=True)
			
		rotation_map = {}
		for rd in rotation_dates:
			rotation_map.setdefault(rd["rotation_day"], []).append(rd["date"])

		for s in schedules:
			# look up block metadata once per (rotation_day, block)
			blk_meta = frappe.db.get_value(
				"School Schedule Block",
					{
						"parent": school_schedule_name,
						"rotation_day": s.rotation_day,
						"block_number": s.block_number,						},
				["block_type", "from_time", "to_time"],
				as_dict=True,
			)
			if not blk_meta:
				continue

			colour = get_block_colour(blk_meta.block_type)

			for dt in rotation_map.get(s.rotation_day, []):
				schedule_entries.append({
					"name": f"{group.student_group_name}-{s.rotation_day}-{s.block_number}",
					"title": f"{group.course} ({group.student_group_name})",
					"start": frappe.utils.get_datetime(f"{dt} {blk_meta.from_time}"),
					"end":   frappe.utils.get_datetime(f"{dt} {blk_meta.to_time}"),
					"allDay": 0,
					"color": colour,
					"extendedProps": {
						"block_type": blk_meta.block_type,
						"location":   s.location,
						"instructor": s.instructor,
						"student_group": group.name
					}
				})

	return schedule_entries

