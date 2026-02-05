# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class StudentPatientVisit(Document):
	def validate(self):
		self.set_school()

	def set_school(self):
		if self.school:
			return

		student = frappe.db.get_value("Student Patient", self.student_patient, "student")
		if not student:
			return

	def after_insert(self):
		self.notify_instructor()

	def notify_instructor(self):
		try:
			from ifitwala_ed.schedule.schedule_utils import get_rotation_dates, get_effective_schedule_for_ay
			from ifitwala_ed.schedule.student_group_scheduling import get_school_for_student_group
			from frappe.utils import get_time, getdate
			
			student = frappe.db.get_value("Student Patient", self.student_patient, "student")
			if not student:
				return

			# Get student info for notification
			student_doc = frappe.get_doc("Student", student)
			student_name = student_doc.student_full_name
			student_image = student_doc.student_image
			
			today_date = getdate(self.date) if self.date else getdate()
			current_time = get_time(self.time_of_arrival or frappe.utils.now_time())

			# 1. Get active groups for student
			groups = frappe.db.sql("""
				SELECT parent as name, academic_year, school, school_schedule 
				FROM `tabStudent Group Student`
				WHERE student = %s AND active = 1
			""", (student,), as_dict=True)

			notified_users = set()

			for group in groups:
				# 2. Resolve Schedule
				schedule_name = group.school_schedule
				if not schedule_name:
					school = group.school or get_school_for_student_group(group.name)
					if group.academic_year and school:
						schedule_name = get_effective_schedule_for_ay(group.academic_year, school)
				
				if not schedule_name:

					continue
				# 3. Get Rotation Day
				# We get rotation dates for the whole year, but we only need today. 
				# Optimization: In a real scenario we might cache this or have a specific util.
				# For now, we call the util.
				rot_dates = get_rotation_dates(schedule_name, group.academic_year)
				rotation_day = next((r["rotation_day"] for r in rot_dates if getdate(r["date"]) == today_date), None)

				if not rotation_day:

					continue
				# 4. Check Schedule for this block
				# We check if current time falls within any block for this group
				schedule_rows = frappe.db.get_all("Student Group Schedule", filters={
					"parent": group.name,
					"rotation_day": rotation_day
				}, fields=["from_time", "to_time", "instructor", "location"])

				for row in schedule_rows:
					if not row.from_time or not row.to_time:

						continue					
					# Check time overlap
					if row.from_time <= current_time <= row.to_time:
						if row.instructor:
							# Get User for Instructor
							employee = frappe.db.get_value("Instructor", row.instructor, "employee")
							if employee:
								user_id = frappe.db.get_value("Employee", employee, "user_id")
								if user_id and user_id not in notified_users:
									
									frappe.publish_realtime(
										event='global_notification',
										user=user_id,
										message={
											'title': 'Student Location Update',
											'content': f'{student_name} is currently at the Nurse.',
											'image': student_image,
											'type': 'info'
										}
									)
									notified_users.add(user_id)
		except Exception as e:
			frappe.log_error(f"Error notifying instructor for visit {self.name}: {e}")

@frappe.whitelist()
def get_student_school(student_patient, date=None):
	# date argument is kept for compatibility but not used for anchor_school
	student = frappe.db.get_value("Student Patient", student_patient, "student")
	if not student:
		return None

	return frappe.db.get_value("Student", student, "anchor_school")


