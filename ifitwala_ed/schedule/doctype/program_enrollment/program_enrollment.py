# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import msgprint, _
from frappe.model.document import Document
from frappe.desk.reportview import get_match_cond
from frappe.utils import getdate, get_link_to_form

class ProgramEnrollment(Document):

	def validate(self):
		self.validate_duplicate_course()
		self.validate_duplication()
		if not self.student_name:
			self.student_name = frappe.db.get_value("Student", self.student, "student_full_name")
		if not self.courses:
			self.extend("courses", self.get_courses()) 

		if self.academic_year: 
			year_dates = frappe.get_doc("Academic Year", self.academic_year)
			if self.enrollment_date: 
				if getdate(self.enrollment_date) < getdate(year_dates.year_start_date): 
					frappe.throw(_("The enrollment date for this program is before the start of the academic year {0}. The academic year starts on {1}.  Please revise the date.").format(
						get_link_to_form("Academic Year", self.academic_year), 
						year_dates.year_start_date
					))
				if getdate(self.enrollment_date) > getdate(year_dates.year_end_date): 
					frappe.throw(_("The enrollment date for this program is after the start of the academic year {0}. The academic year ends on {1}.  Please revise the date.").format(
						get_link_to_form("Academic Year", self.academic_year), 
						year_dates.year_end_date
					))

		if self.term:
			term_dates = frappe.get_doc("Term", self.term)
			if term_dates.academic_year != self.academic_year:
				frappe.throw(_("The term does not belong to that academic year."))
			if self.enrollment_date and getdate(term_dates.term_start_date) and getdate(self.enrollment_date) < getdate(term_dates.term_start_date):
				frappe.throw(_("The enrollment date for this program is before the start of the term.  Please revise the date or change the term {0}.").format(get_link_to_form("Term", self.term)))
			if self.enrollment_date and getdate(term_dates.term_end_date) and getdate(self.enrollment_date) > getdate(term_dates.term_end_date):
				frappe.throw(_("The enrollment date for this program is after the end the term.  Pease revise the joining date or change the term {0}.").format(get_link_to_form("Term", self.term)))

	def on_submit(self):
		self.update_student_joining_date()
		self.create_course_enrollment()

	# you cannot enrolled twice for a same program, same year, same term.
	def validate_duplication(self): 
		existing_enrollment_name = frappe.db.exists("Program Enrollment", { 
			"student": self.student, 
			"academic_year": self.academic_year, 
			"term": self.term, 
			"program": self.program, 
			"docstatus": ("<", 2), 
			"name": ("!=", self.name)
		})
		if existing_enrollment_name: 
			student_name = frappe.db.get_value("student", self.student, "student_name")
			link_to_existing_enrollment = get_link_to_form("Program Enrollment", existing_enrollment_name)
			frappe.throw(_("Student {0} is already enrolled in this program for this term. See existing enrollment {1}").format(student_name, link_to_existing_enrollment)) 
			
	def validate_only_one_active_enrollment(self): 
		"""
    Checks if there's another active (status=1) Program Enrollment for the same student.
    Raises an error if another active enrollment is found.
    """ 
		if not self.status: 
			return # if status is not checked. 
		
		existing_enrollment = frappe.db.get_value( 
			"Program Enrollment", 
			{ 
				"student": self.student, 
				"status": 1,  # Check for active enrollments 
				"name": ("!=", self.name),  # Exclude the current document 
				"docstatus": ("<", 2) # not cancelled or draft 
			}, 
			["name", "program", "academic_year"],  # Retrieve name, program and year for the error message 
			as_dict=True
		) 
		
		if existing_enrollment: 
			frappe.throw(_( 
				"Student {0} already has an active Program Enrollment for program {1} in academic year {2}.  See {3}."
			).format( 
					self.student_name, 
					get_link_to_form("Program", existing_enrollment.program), 
					existing_enrollment.academic_year, 
					get_link_to_form("Program Enrollment", existing_enrollment.name)
					),title=_("Active Enrollment Exists") # added for better UI message.
      )



	# If a student is in a program and that program has required courses (non elective), then these courses are loaded automatically.
	@frappe.whitelist()
	def get_courses(self):
		return frappe.db.sql("""SELECT course
								FROM `tabProgram Course`
								WHERE parent = %s AND required = 1
								ORDER BY idx""", (self.program), as_dict=1)

	def validate_duplicate_course(self):
		seen_courses = []
		program_courses = {row[0] for row in frappe.db.get_values("Program Course", filters = {"parent": self.program}, fieldname = "course")}
		for course_entry in self.courses:
			if course_entry.course in seen_courses:
				frappe.throw(_("Course {0} entered twice.").format(
					get_link_to_form("Course",course_entry.course))
				)
			else:
				seen_courses.append(course_entry.course)
			
			if course_entry.course not in program_courses:
				frappe.throw(_("Course {0} is not part of program {1}").format(
					get_link_to_form("Course", course_entry.course),
					get_link_to_form("Program", self.program))
				)

	# This will update the joining date on the student doctype in function of the joining date of the program.
	def update_student_joining_date(self):
		date = frappe.db.sql("""select min(enrollment_date) from `tabProgram Enrollment` where student= %s""", self.student)
		if date and date[0] and date[0][0]:
			frappe.db.set_value("Student", self.student, "student_joining_date", date[0][0])

	def create_course_enrollment(self):
		program = frappe.get_doc("Program", self.program)
		student = frappe.get_doc("Student", self.student)
		course_list = [course.course for course in self.courses]
		for course_name in course_list:
			student.enroll_in_course(course_name=course_name, program_enrollment=self.name, enrollment_date = self.enrollment_date)

	# used (later) below with quiz and assessment
	def get_all_course_enrollments(self):
		course_enrollment_names = frappe.get_list("Course Enrollment", filters={'program_enrollment': self.name})
		return [frappe.get_doc('Course Enrollment', course_enrollment.name) for course_enrollment in course_enrollment_names]



# from JS. to filter out course that are only present in the program list of courses.
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_program_courses(doctype, txt, searchfield, start, page_len, filters):

	return frappe.db.sql("""select course, course_name from `tabProgram Course`
		where  parent = %(program)s and course like %(txt)s {match_cond}
		order by
			if(locate(%(_txt)s, course), locate(%(_txt)s, course), 99999),
			idx desc,
			`tabProgram Course`.course asc
		limit {start}, {page_len}""".format(
			match_cond=get_match_cond(doctype),
			start=start,
			page_len=page_len), {
				"txt": "%{0}%".format(txt),
				"_txt": txt.replace('%', ''),
				"program": filters['program']
			})

# from JS to filter out students that have already been enrolled for a given year and/or term
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_students(doctype, txt, searchfield, start, page_len, filters):
	if not filters.get("term"):
		filters["term"] = frappe.defaults.get_defaults().term

	if not filters.get("academic_year"):
		filters["academic_year"] = frappe.defaults.get_defaults().academic_year

	enrolled_students = frappe.get_list("Program Enrollment", filters={
		"term": filters.get('term'),
		"academic_year": filters.get('academic_year')
	}, fields=["student"])

	students = [d.student for d in enrolled_students] if enrolled_students else [""]

	return frappe.db.sql("""select
			name, student_full_name from tabStudent
		where
			name not in (%s)
		and
			`%s` LIKE %s
		order by
			idx desc, name
		limit %s, %s"""%(
			", ".join(['%s']*len(students)), searchfield, "%s", "%s", "%s"),
			tuple(students + ["%%%s%%" % txt, start, page_len]
		)
	)
