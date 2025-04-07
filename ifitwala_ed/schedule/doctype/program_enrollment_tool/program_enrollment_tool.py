# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

class ProgramEnrollmentTool(Document):

	@frappe.whitelist()
	def get_students(self):
		students = []

		if not self.get_students_from:
			frappe.throw(_("Please select an option for 'Get Students From'."))

		# --- COHORT PATH ---
		if self.get_students_from == "Cohort":
			if not self.student_cohort: 
				frappe.throw(_("Please specify the Student Cohort."))

			student = frappe.qb.DocType("Student")
			query = (
				frappe.qb.from_(student)
				.select(
					student.name.as_("student"),
					student.student_full_name.as_("student_name"),
					student.cohort.as_("student_cohort")
				)
				.where(
					(student.cohort == self.student_cohort) & 
					(student.enabled == 1)
				)
			)
			students = query.run(as_dict=True)

		# --- PROGRAM ENROLLMENT PATH ---
		elif self.get_students_from == "Program Enrollment":
			if not self.academic_year or not self.program:
				frappe.throw(_("Please specify both Program and Academic Year."))

			program_enrollment = frappe.qb.DocType("Program Enrollment")
			query = (
				frappe.qb.from_(program_enrollment)
				.select(
					program_enrollment.student,
					program_enrollment.student_name,
					program_enrollment.cohort.as_("student_cohort")
				)
				.where(
					(program_enrollment.program == self.program) &
					(program_enrollment.academic_year == self.academic_year) &
					(program_enrollment.docstatus == 1)
				)
			)

			if self.student_cohort:
				query = query.where(program_enrollment.cohort == self.student_cohort)

			students = query.run(as_dict=True)

			# Remove inactive students
			student_list = [s.student for s in students]

			if student_list:
				student = frappe.qb.DocType("Student")
				inactive = (
					frappe.qb.from_(student)
					.select(student.name)
					.where((student.name.isin(student_list)) & (student.enabled == 0))
				).run(as_dict=True)
				inactive_ids = {s.name for s in inactive}
				students = [s for s in students if s["student"] not in inactive_ids]

		else:
			frappe.throw(_("Unsupported 'Get Students From' value."))

		if students:
			return students
		else:
			frappe.throw(_("No students found with the given criteria."))

	@frappe.whitelist()
	def enroll_students(self):
		total = len(self.students)
		if not self.new_program or not self.new_academic_year:
			frappe.throw(_("New Program and New Academic Year are required."))

		enrdate = self.new_enrollment_date
		if not enrdate:
			year = frappe.get_doc("Academic Year", self.new_academic_year)
			enrdate = getdate(year.year_start_date)

		for i, stud in enumerate(self.students):
			frappe.publish_realtime("program_enrollment_tool", dict(progress=[i+1, total]), user=frappe.session.user)

			if stud.student:
				pe = frappe.new_doc("Program Enrollment")
				pe.student = stud.student
				pe.student_name = stud.student_name
				pe.cohort = stud.student_cohort or self.new_student_cohort
				pe.program = self.new_program
				pe.academic_year = self.new_academic_year
				pe.enrollment_date = enrdate
				pe.save()

		frappe.msgprint(_("{0} students have been enrolled.").format(total))
