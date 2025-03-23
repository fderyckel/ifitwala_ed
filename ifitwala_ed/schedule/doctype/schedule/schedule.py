# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.query_builder import DocType
from ifitwala_ed.schedule.schedule_utils import get_rotation_dates, current_academic_year
from frappe import _

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

			schedules = (
				frappe.qb.from_(StudentGroupSchedule)
				.select(
					StudentGroupSchedule.rotation_day,
					StudentGroupSchedule.block_number,
					StudentGroupSchedule.from_time,
					StudentGroupSchedule.to_time,
					StudentGroupSchedule.room
				)
				.where(StudentGroupSchedule.parent == group.name)
			).run(as_dict=True)
			
			rotation_map = {}
			for rd in rotation_dates:
				rotation_map.setdefault(rd["rotation_day"], []).append(rd["date"])

			for s in schedules:
				dates = rotation_map.get(s.rotation_day, [])
				for date in dates:
					schedule_entries.append({
						"name": f"{group.student_group_name}-{s.rotation_day}-{s.block_number}",
						"title": f"{group.course} ({group.student_group_name})",
						"start": frappe.utils.get_datetime(f"{date} {s.from_time}"),
						"end": frappe.utils.get_datetime(f"{date} {s.to_time}"),
						"allDay": 0,
						"color": "#74b9ff"
					})

		return schedule_entries

