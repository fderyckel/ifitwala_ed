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
			return

		# Skip all validation for "Other"
		if self.group_based_on == "Other":
			return

		student_names = [s.student for s in self.students if s.student]
		if not student_names:
			return

		# Fetch enabled status for all listed students
		enabled_records = frappe.db.get_values(
			"Student",
			{"name": ["in", student_names]},
			["name", "enabled"],
			as_dict=True
		)
		enabled_dict = {rec.name: rec.enabled for rec in enabled_records}

		for student in self.students:
			if not student.student:
				continue

			is_enabled = enabled_dict.get(student.student)
			if is_enabled is None:
				frappe.throw(_("Student data not found for {0}").format(student.student))

			if not is_enabled and student.active:
				frappe.throw(_("{0} - {1} is an inactive student").format(
					student.group_roll_number, student.student_name
				))

			# Check program enrollment (optional)
			if self.program:
				if not frappe.db.exists("Program Enrollment", {
					"student": student.student,
					"program": self.program,
					"academic_year": self.academic_year,
					"docstatus": 1
				}):
					frappe.throw(_("Student {0} ({1}) is not enrolled in the program {2} for academic year {3}.").format(
						student.student_name,
						student.student,
						get_link_to_form("Program", self.program),
						self.academic_year
					))

			# Check cohort (optional)
			if self.cohort:
				if not frappe.db.exists("Program Enrollment", {
					"student": student.student,
					"cohort": self.cohort,
					"academic_year": self.academic_year,
					"docstatus": 1
				}):
					frappe.throw(_("Student {0} ({1}) is not in cohort {2} for academic year {3}.").format(
						student.student_name,
						student.student,
						get_link_to_form("Student Cohort", self.cohort),
						self.academic_year
					))

			# 🔁 Soft validation for duplicate assignment to same course & term (Course-based groups only)
			if self.group_based_on == "Course" and self.course:
				conflict_term = self.term

				# Attempt to infer term if not explicitly set
				if not conflict_term:
					conflict_term = frappe.db.get_value("Program Enrollment", {
						"student": student.student,
						"course": self.course,
						"academic_year": self.academic_year,
						"docstatus": 1
					}, "term", order_by="modified desc")

				# Only proceed if term is available (either from group or enrollment)
				if conflict_term:
					conflict = frappe.db.sql("""
						SELECT sg.name
						FROM `tabStudent Group` sg
						INNER JOIN `tabStudent Group Student` sgs ON sgs.parent = sg.name
						WHERE
							sg.name != %(current_group)s
							AND sgs.student = %(student)s
							AND sg.group_based_on = 'Course'
							AND sg.academic_year = %(academic_year)s
							AND sg.course = %(course)s
							AND sg.term = %(term)s
						LIMIT 1
					""", {
						"student": student.student,
						"current_group": self.name,
						"academic_year": self.academic_year,
						"course": self.course,
						"term": conflict_term
					})

					if conflict:
						# 🔔 Warn user but do not block
						frappe.msgprint(
							_("<span style='color: orange; font-weight: bold;'>Heads up:</span> Student <b>{0} ({1})</b> is already assigned to another Course-based group <b>{2}</b> for the same course and term.")
							.format(student.student_name, student.student, conflict[0][0]),
							title=_("Possible Duplicate Assignment"),
							indicator="orange"
						)

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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def fetch_students(doctype, txt, searchfield, start, page_len, filters):
	group_based_on = filters.get("group_based_on")

	if group_based_on == "Other":
		return frappe.db.sql(f"""
			SELECT name, student_full_name 
			FROM `tabStudent`
			WHERE enabled = 1
				AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
			ORDER BY idx DESC, name
			LIMIT %s, %s
		""", (f"%{txt}%", f"%{txt}%", start, page_len))

	elif group_based_on == "Course":
		enrolled_students = get_program_enrollment(
			academic_year=filters.get('academic_year'),
			term=filters.get('term'),
			program=filters.get('program'),
			cohort=filters.get('cohort'),
			course=filters.get('course')
		)

		existing_students = frappe.db.sql_list('''
			SELECT student 
			FROM `tabStudent Group Student` 
			WHERE parent = %s
		''', (filters.get('student_group'),))

		student_ids = [
			d.student for d in enrolled_students 
			if d.student not in existing_students
		] if enrolled_students else []

		if not student_ids:
			return []

		return frappe.db.sql(f"""
			SELECT name, student_full_name 
			FROM `tabStudent`
			WHERE name IN ({', '.join(['%s'] * len(student_ids))})
				AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
			ORDER BY idx DESC, name
			LIMIT %s, %s
		""", tuple(student_ids + [f"%{txt}%", f"%{txt}%", start, page_len]))

	# Activity: placeholder for future refinement
	elif group_based_on == "Activity":
		return frappe.db.sql(f"""
			SELECT name, student_full_name 
			FROM `tabStudent`
			WHERE enabled = 1
				AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
			ORDER BY idx DESC, name
			LIMIT %s, %s
		""", (f"%{txt}%", f"%{txt}%", start, page_len))

	# Fallback: Assume Cohort group
	else:
		enrolled_students = get_program_enrollment(
			academic_year=filters.get('academic_year'),
			term=filters.get('term'),
			program=filters.get('program'),
			cohort=filters.get('cohort'),
			course=None  # Not relevant in this case
		)

		existing_students = frappe.db.sql_list('''
			SELECT student 
			FROM `tabStudent Group Student` 
			WHERE parent = %s
		''', (filters.get('student_group'),))

		student_ids = [
			d.student for d in enrolled_students 
			if d.student not in existing_students
		] if enrolled_students else []

		if not student_ids:
			return []

		return frappe.db.sql(f"""
			SELECT name, student_full_name 
			FROM `tabStudent`
			WHERE name IN ({', '.join(['%s'] * len(student_ids))})
				AND (`{searchfield}` LIKE %s OR student_full_name LIKE %s)
			ORDER BY idx DESC, name
			LIMIT %s, %s
		""", tuple(student_ids + [f"%{txt}%", f"%{txt}%", start, page_len]))



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



########################## Permissions ##########################
##### Used in other parts

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