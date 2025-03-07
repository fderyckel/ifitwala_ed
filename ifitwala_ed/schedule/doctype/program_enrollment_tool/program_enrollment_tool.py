# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today

class ProgramEnrollmentTool(Document):

	# called by the button get_students on the form
	@frappe.whitelist()
	def get_students(self):
		students = []
		if not self.get_students_from:
			frappe.throw(_("Fill first the mandatory field: Get Students From.  Also fill, if not already done, Academic Year and Program."))
		elif not self.academic_year:
			frappe.throw(_("Fill first the mandatory field: Academic Year.  Also fill, if not already done, Program and Get Students From."))

		else:

			if self.get_students_from == "Others":
				frappe.throw(_("Not yet developped. Choose another option")) 
			
			elif self.get_students_from == "Cohort": 
				# New branch for getting students by Cohort 
				if not self.student_cohort: 
					frappe.throw(_("Please specify the Student Cohort."))  
				
				student = frappe.qb.DocType("Student") 
				query = frappe.qb.from_(student).select(
					student.name.as_("student"),
          student.student_full_name.as_("student_name"),
          student.cohort.as_("student_cohort")
          ).where(
          (student.cohort == self.student_cohort)
          & (student.enabled == 1)
          )
				students = query.run(as_dict=1)
				
			elif self.get_students_from == "Program Enrollment":
				if not self.program: 
					frappe.throw(_("Please specify the Program first."))  				
				program_enrollment = frappe.qb.DocType("Program Enrollment")
				query = frappe.qb.from_(program_enrollment).select(
					program_enrollment.student,
					program_enrollment.student_name,
					program_enrollment.cohort.as_("student_cohort"), 
				).where(
					(program_enrollment.program == self.program) 
					& (program_enrollment.academic_year == self.academic_year) 
					& (program_enrollment.docstatus == 1)
				)
				if self.term: 
					query = query.where(program_enrollment.term == self.term)
				if self.student_cohort:
					query = query.where(program_enrollment.cohort == self.student_cohort)

				students = query.run(as_dict = 1)

				student_list = [d.student for d in students]

				if student_list: 
					student = frappe.qb.DocType("Student")
					inactive_students = frappe.qb.from_(student).select(
						student.name.as_("student"),
						student.student_full_name.as_("student_name")
					).where(
						(student.name.is_in(student_list)) 
						& ((student.enabled == 0))
					).run(as_dict = 1) 

					inactive_students_ids = {d.student for d in inactive_students}
					students = [s for s in students if s.student not in inactive_students_ids]

			if students: 
				return students
			else: 
				frappe.throw(_("There isn't any student enrolled for that academic year and program."))

	@frappe.whitelist()
	def enroll_students(self):
		total = len(self.students)	# note how this gives the length (number of row) of a child table
		
		enrdate = getdate(today())
		if self.new_academic_year:
			year_start = frappe.get_doc("Academic Year", self.new_academic_year)
			enrdate = getdate(year_start.year_start_date)
		if self.new_term:
			term_start = frappe.get_doc("Term", self.new_term)
			enrdate = getdate(term_start.term_start_date)

		for i, stud in enumerate(self.students):
			frappe.publish_realtime("program_enrollment_tool", dict(progress = [i+1, total]), user = frappe.session.user)
			if stud.student:
				pe = frappe.new_doc("Program Enrollment")
				pe.student = stud.student
				pe.student_name = stud.student_name
				pe.cohort = stud.student_cohort if stud.student_cohort else self.new_student_cohort
				pe.program = self.new_program
				pe.academic_year = self.new_academic_year
				pe.academic_term = self.new_term if self.new_term else ""
				pe.enrollment_date = enrdate
				pe.save()
		frappe.msgprint(_("{0} students have been enrolled").format(total))