# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_link_to_form
from ifitwala_ed.schedule.utils import validate_duplicate_student

class StudentGroup(Document):
	def autoname(self):
		if self.group_based_on == "Course" or self.group_based_on == "Activity": 
			if self.term: 
				self.name = self.student_group_abbreviation + "/" + self.term
			else: 
				self.name = self.student_group_abbreviation + "/" + self.academic_year
		elif self.group_based_on == "Cohort":
			self.name = self.student_group_abbreviation + "/" + self.cohort
		else:
			self.name = self.student_group_abbreviation
		

	def validate(self):
		if self.term: 
			self.validate_term()
		self.validate_program_and_course()
		self.validate_mandatory_fields()
		self.validate_size()
		self.validate_students()
		self.validate_and_set_child_table_fields()
		validate_duplicate_student(self.students)
		if self.group_based_on in ["Course", "Activity"]:
			if self.term: 
				self.title = self.student_group_abbreviation + "/" + self.term
			else: 
				self.title = self.student_group_abbreviation + "/" + self.academic_year
		elif self.group_based_on == "Cohort":
			self.title = self.student_group_abbreviation + "/" + self.cohort
		else:
			self.title = self.student_group_abbreviation

	def validate_term(self) -> None:
		term_year = frappe.get_doc("Term", self.term)
		if self.academic_year != term_year.academic_year:
			frappe.throw(_("The term {0} does not belong to the academic year {1}.").format(self.term, self.academic_year))

	def validate_program_and_course(self) -> None:
		"""Validates the course against the program if group_based_on is 'Course'."""
		# Added: Condition to check group_based_on and program before validating.
		if self.group_based_on == "Course" and self.program:
			if not self.course:
				frappe.throw(_("Course is required when Group Based On is Course and a Program is selected."))

			# Changed: Use frappe.db.exists for efficient existence check.
			if not frappe.db.exists("Program Course", {"parent": self.program, "course": self.course}):
				frappe.throw(_("{0} is not a valid course for the {1} program. Please select a different course or the appropriate program."
							).format(get_link_to_form("Course", self.course), get_link_to_form("Program", self.program))
				)

	def validate_mandatory_fields(self) -> None:
		if self.group_based_on == "Course" and not self.course:
			frappe.throw(_("Please select a course."))
		if self.group_based_on == "Cohort" and not self.cohort:
			frappe.throw(_("Please select a cohort."))

	# Throwing message if more students than maximum size in the group
	def validate_size(self):
		if cint(self.maximum_size) < 0:
			frappe.throw(_("Max number of student in this group cannot be negative."))
		if self.maximum_size and len(self.students) > cint(self.maximum_size):
			frappe.throw(_("You can only enroll {0} students in this group.").format(self.maximum_size))

	# you should not be able to make a group that include inactive students.
	# this is to ensure students are still active students (aka not graduated or not transferred, etc.)
	def validate_students(self):
		if not self.students: 
			return	# Nothing to validate if the child table is empty
		
		student_names = [s.student for s in self.students if s.student]
		if not student_names:
			return	# Nothing to validate if student names are not present
		
		enabled_map = frappe.db.get_value(
			"Student", 
			{"name": ("in", student_names)}, 
			"enabled",
			as_dict=True
		)

		# Convert to a dictionary for easy lookup: {student_name: enabled_status}
		enabled_dict = {student: enabled for student, enabled in enabled_map}  
		
		for student in self.students: 
			if not student.student:
				continue

      # Check if the student is enabled using the retrieved values 
			is_enabled = enabled_dict.get(student.student) 
			if is_enabled is None: 
				frappe.throw(_("Student data not found for {0}").format(student.student))  
				
			if not is_enabled and student.active: 
				frappe.throw(_("{0} - {1} is an inactive student").format(student.group_roll_number, student.student_name)) 
				
			# Program Enrollment Check (if applicable) 
			if self.program: 
				if not frappe.db.exists("Program Enrollment", {"student": student.student, "program": self.program, "academic_year": self.academic_year, "docstatus": 1}): 
					frappe.throw(_("Student {0} ({1}) is not enrolled in the program {2} for academic year {3}."
                    ).format(student.student_name, student.student, get_link_to_form("Program", self.program), self.academic_year)
          )
		
			# Cohort check
			if self.cohort: 
				if not frappe.db.exists("Program Enrollment", {"student": student.student, "cohort": self.cohort, "academic_year": self.academic_year, "docstatus":1}): 
					frappe.throw(_("Student {0} ({1}) is not in  cohort {2} for academic year {3}.").format(student.student_name,
                        student.student, get_link_to_form("Student Cohort", self.cohort), self.academic_year))		

	# to input the roll number field in child table
	def validate_and_set_child_table_fields(self):
		roll_numbers = [d.group_roll_number for d in self.students if d.group_roll_number]
		max_roll_no = max(roll_numbers) if roll_numbers else 0
		roll_no_list = []
		for d in self.students:
			if not d.student_name:
				d.student_name = frappe.db.get_value("Student", d.student, "student_full_name")
			if not d.group_roll_number:
				max_roll_no += 1
				d.group_roll_number = max_roll_no
			if d.group_roll_number in roll_no_list:
				frappe.throw(_("Duplicate roll number for student {0}").format(d.student_name))
			else:
				roll_no_list.append(d.group_roll_number)

def get_permission_query_conditions(user):
	if not user:
		user = frappe.session.user
	current_user = frappe.get_doc("User", frappe.session.user)
	roles = [role.role for role in current_user.roles]

	if "Student" in roles:
		return """(name in (select parent from `tabStudent Group Student` where user_id=%(user)s))""" % {
			"user": frappe.db.escape(user),
			}

	if "Instructor" in roles:
		return """(name in (select parent from `tabStudent Group Instructor` where user_id=%(user)s))""" % {
				"user": frappe.db.escape(user),
				}
	super_viewer = ["Administrator", "System Manager", "Academic Admin", "Schedule Maker"]
	for role in roles:
		if role in super_viewer:
			return ""


def group_has_permission(user, doc):
	current_user = frappe.get_doc("User", user)
	roles = [role.role for role in current_user.roles]
	super_viewer = ["Administrator", "System Manager", "Academic Admin", "Schedule Maker", "Admission Officer"]
	for role in roles:
		if role in super_viewer:
			return True

	if current_user.name in [i.user_id.lower() for i in doc.instructors]:
		return True

	if current_user.name in [i.user_id.lower() for i in doc.students]:
		return True

	return False

@frappe.whitelist()
def get_students(academic_year, group_based_on, term=None, program=None, cohort=None, course=None):
	enrolled_students = get_program_enrollment(academic_year, term, program, cohort, course)

	if enrolled_students:
		student_list = []
		for s in enrolled_students:
			if frappe.db.get_value("Student", s.student, "enabled"):
				s.update({"active": 1})
			else:
				s.update({"active": 0})
			student_list.append(s)
		return student_list
	else:
		frappe.msgprint(_("No students found"))
		return []



def get_program_enrollment(academic_year, term=None, program=None, cohort=None, course=None):

	condition1 = " "
	condition2 = " "
	if term:
		condition1 += " and pe.term = %(term)s"
	if program:
		condition1 += " and pe.program = %(program)s"
	if cohort:
		condition1 += " and pe.cohort = %(cohort)s"
	if course:
		condition1 += " and pe.name = pec.parent and pec.course = %(course)s"
		condition2 = ", `tabProgram Enrollment Course` pec"

	return frappe.db.sql('''
		select
			pe.student, pe.student_name
		from
			`tabProgram Enrollment` pe {condition2}
		where
			pe.academic_year = %(academic_year)s  {condition1} and pe.docstatus=1
		order by
			pe.student_name asc
		'''.format(condition1=condition1, condition2=condition2),
		({"academic_year": academic_year, "term":term, "program": program, "cohort": cohort, "course": course}), as_dict=1)

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fetch_students(doctype, txt, searchfield, start, page_len, filters):
	if filters.get("group_based_on") != "Activity":
		enrolled_students = get_program_enrollment(filters.get('academic_year'), filters.get('term'),
			filters.get('program'), filters.get('cohort'))
		student_group_student = frappe.db.sql_list('''select student from `tabStudent Group Student` where parent=%s''',
			(filters.get('student_group')))
		students = ([d.student for d in enrolled_students if d.student not in student_group_student]
			if enrolled_students else [""]) or [""]
		return frappe.db.sql("""select name, student_full_name from tabStudent
			where name in ({0}) and (`{1}` LIKE %s or student_full_name LIKE %s)
			order by idx desc, name
			limit %s, %s""".format(", ".join(['%s']*len(students)), searchfield),
			tuple(students + ["%%%s%%" % txt, "%%%s%%" % txt, start, page_len]))
	else:
		return frappe.db.sql("""select name, student_full_name from tabStudent
			where `{0}` LIKE %s or student_full_name LIKE %s
			order by idx desc, name
			limit %s, %s""".format(searchfield),
			tuple(["%%%s%%" % txt, "%%%s%%" % txt, start, page_len]))