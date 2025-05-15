# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_link_to_form
from ifitwala_ed.schedule.schedule_utils import get_school_term_bounds
from ifitwala_ed.utilities.school_tree import get_effective_record, ParentRuleViolation
from frappe.utils.nestedset import get_ancestors_of

class ProgramEnrollment(Document):

	def validate(self):
		self._resolve_academic_year()
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

		# Ensure the academic year and program belong to the same school
		if self.program and not self.school: 
			self.school = frappe.db.get_value("Program", self.program, "school")			

	def before_submit(self):
		self.validate_only_one_active_enrollment()

	def on_submit(self):
		self.update_student_joining_date()


	def _resolve_academic_year(self):
		allowed_schools = [self.school] + get_ancestors_of("School", self.school)

		# 1 ▸ AUTOFILL when field left blank
		if not self.academic_year:
			ay = get_effective_record(
				"Academic Year",
				self.school,
				extra_filters={"archived": 0},
			)
			if not ay:
				raise ParentRuleViolation(
					_("No Academic Year found for {0} or its ancestors.").format(self.school)
				)
			self.academic_year = ay
			return

		# 2 ▸ VALIDATE a manually-picked AY
		ay_school = frappe.db.get_value("Academic Year", self.academic_year, "school")
		if ay_school not in allowed_schools:
			raise ParentRuleViolation(
				_("Academic Year {0} belongs to {1}, which is outside the allowed hierarchy.")
				.format(self.academic_year, ay_school)
			)

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

	# you cannot enrolled twice for a same program, same year, same term.
	def validate_duplication(self): 
		existing_enrollment_name = frappe.db.exists("Program Enrollment", { 
			"student": self.student, 
			"academic_year": self.academic_year, 
			"program": self.program, 
			"name": ("!=", self.name)
		})
		if existing_enrollment_name: 
			student_name = frappe.db.get_value("student", self.student, "student_name")
			link_to_existing_enrollment = get_link_to_form("Program Enrollment", existing_enrollment_name)
			frappe.throw(_("Student {0} is already enrolled in this program for this term. See existing enrollment {1}").format(student_name, link_to_existing_enrollment)) 
			
	def validate_only_one_active_enrollment(self): 
		"""
    Checks if there's another active (archived=0) Program Enrollment for the same student.
    Raises an error if another active enrollment is found.
    """ 
		if self.archived: 
			return # if archived is not checked. 
		
		existing_enrollment = frappe.db.get_value( 
			"Program Enrollment", 
			{ 
				"student": self.student, 
				"archived": 0,  # Check for active enrollments 
				"name": ("!=", self.name)  # Exclude the current document 
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
		rows = frappe.db.sql("""
			SELECT course
			FROM `tabProgram Course`
			WHERE parent = %s AND required = 1
			ORDER BY idx
			""", (self.program), as_dict=1)
		
		# Get bounds once per call
		bounds = None
		if self.school:
			bounds = get_school_term_bounds(self.school, self.academic_year)
			
		for row in rows:
			row["status"] = "Enrolled"

			term_long = frappe.db.get_value("Course", row["course"], "term_long")
			if not term_long and bounds:
				row["term_start"] = bounds.get("term_start")
				row["term_end"] = bounds.get("term_end")

		return rows


	# This will update the joining date on the student doctype in function of the joining date of the program.
	def update_student_joining_date(self):
		date = frappe.db.sql("""select min(enrollment_date) from `tabProgram Enrollment` where student= %s""", self.student)
		if date and date[0] and date[0][0]:
			frappe.db.set_value("Student", self.student, "student_joining_date", date[0][0])


		
# from JS. to filter out course that are only present in the program list of courses.
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_program_courses(doctype, txt, searchfield, start, page_len, filters):

	return frappe.db.sql(f"""select course, course_name 
		FROM `tabProgram Course`
		WHERE parent = %(program)s AND course LIKE %(txt)s
		ORDER BY
			IF(LOCATE(%(_txt)s, course), LOCATE(%(_txt)s, course), 99999),
			idx DESC,
			`tabProgram Course`.course ASC
		LIMIT {start}, {page_len}""", 
		{
			"txt": f"%{txt}%",
			"_txt": txt.replace('%', ''),
			"program": filters["program"],
			"start": start,
			"page_len": page_len
			}
	)

# from JS to filter out students that have already been enrolled for a given year and/or term
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_students(doctype, txt, searchfield, start, page_len, filters):
	page_len = 50

	if not filters.get("academic_year"):
		return []

	enrolled_students = frappe.db.get_values(
    "Program Enrollment",
    filters={
        "academic_year": filters.get("academic_year")
    },
    fieldname="student"
	) or []

	# Efficient and clean conversion to list of dicts (if you want it)
	excluded_students = [d[0] for d in enrolled_students] or [""]

	# Build SQL
	sql = f"""
		SELECT name, student_full_name 
		FROM tabStudent
		WHERE 
			enabled = 1
			AND name NOT IN ({', '.join(['%s'] * len(excluded_students))})
			AND (
			  name LIKE %s
        OR student_full_name LIKE %s
			)
		ORDER BY idx DESC, name
		LIMIT %s, %s
	"""

	# Params: excluded list + search text + pagination
	#params = excluded_students + [f"%{txt}%", start, page_len]
	params = excluded_students + [f"%{txt}%", f"%{txt}%", start, page_len]

	return frappe.db.sql(sql, params)

# from JS to display AY in descending order 
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_academic_years(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else filters or {}

    conditions = []
    values = {}

    if txt:
        conditions.append("name LIKE %(txt)s")
        values["txt"] = f"%{txt}%"

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

    return frappe.db.sql(f"""
        SELECT name
        FROM `tabAcademic Year`
        {where_clause}
        ORDER BY year_start_date DESC
        LIMIT %(start)s, %(page_len)s
    """, {
        **values,
        "start": start,
        "page_len": page_len
    })

@frappe.whitelist()
def get_program_courses_for_enrollment(program):
	courses = frappe.db.get_values(
		"Program Course",
		{"parent": program},
		"course",
		order_by="idx"
	)

	# Flatten to list of course names
	return [c[0] for c in courses if c[0]]

