# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import get_link_to_form, cint
from frappe.model.document import Document
from frappe.query_builder import DocType
from ifitwala_ed.schedule.schedule_utils import get_school_term_bounds

class CourseEnrollmentTool(Document):
	@frappe.whitelist()
	def add_course_to_program_enrollment(self):
		if self.program:
			# Validate course belongs to the program
			program_doc = frappe.get_doc("Program", self.program)
			valid_courses = {pc.course for pc in program_doc.courses}
			if self.course not in valid_courses:
				frappe.throw(_("Course {0} is not part of Program {1}. Please correct your selection.").format(
					get_link_to_form("Course", self.course), 
					get_link_to_form("Program", self.program)
				))

		# Caching for performance
		term_bounds_cache = {}

		term_long = frappe.db.get_value("Course", self.course, "term_long")

		for row in self.students:
			if not row.program_enrollment:
				continue

			pe_doc = frappe.get_doc("Program Enrollment", row.program_enrollment)

			# Check if course already exists
			if any(c.course == self.course for c in pe_doc.courses):
				frappe.msgprint(_("Course {0} already exists in Program Enrollment {1}.").format(
					get_link_to_form("Course", self.course),
					get_link_to_form("Program Enrollment", pe_doc.name)
				))
				continue

			# Prepare child row
			new_course_row = {
				"course": self.course,
				"status": "Enrolled"
			}

			if term_long:
				# If course is term-long, use selected tool term
				if self.term:
					new_course_row["term_start"] = self.term
					new_course_row["term_end"] = self.term
			else:
				# Not term-long: fetch bounds once per (school, year)
				cache_key = (pe_doc.school, pe_doc.academic_year)
				if cache_key not in term_bounds_cache:
					bounds = get_school_term_bounds(pe_doc.school, pe_doc.academic_year)
					term_bounds_cache[cache_key] = bounds or {}
				bounds = term_bounds_cache[cache_key]

				# 🔐 Validate presence of term bounds
				if not bounds.get("term_start") or not bounds.get("term_end"):
					frappe.throw(_("Cannot determine term boundaries for School {0}, Academic Year {1}. Please configure terms.").format(
						pe_doc.school, pe_doc.academic_year
					))

				new_course_row["term_start"] = bounds.get("term_start")
				new_course_row["term_end"] = bounds.get("term_end")

			# Append to PE
			pe_doc.append("courses", new_course_row)
			pe_doc.save()
			frappe.msgprint(_("Course {0} successfully added to Program Enrollment {1}.").format(
				get_link_to_form("Course", self.course),
				get_link_to_form("Program Enrollment", pe_doc.name)
			))

		self.save()
		frappe.msgprint(_("Done updating Program Enrollments."))


@frappe.whitelist()
def fetch_eligible_students(doctype, txt, searchfield, start, page_len, filters=None):
	"""
	This method is designed for Link field queries in Frappe.

	Args:
		doctype (str): The DocType we are linking to (likely "Student").
		txt (str): The partial text typed by the user to filter.
		searchfield (str): Usually "name" or the field being searched in the link.
		start (int): For pagination, the starting row.
		page_len (int): Number of rows to return in one go.
		filters (dict): Additional filters from set_query().

	Returns:
		list: Each element is [value, label] for the Link field search results.
	"""
	# 1) Convert start/page_len to integers
	start = cint(start)
	page_len = cint(page_len)	

	if not filters:
		filters = {}

	# 2) Extract custom filters
	academic_year = filters.get("academic_year")
	program = filters.get("program")
	course = filters.get("course")
	term = filters.get("term")  # optional

	if not academic_year:
		frappe.throw(_("Academic Year is required to fetch students."))
	if not program: 
		frappe.throw(_("Program is required to fetch students."))
	if not course: 
		frappe.throw(_("Course is required to fetch students."))
		
	# 3) Build conditions and parameter list
	conditions = [
		"s.enabled = 1", 
		"pe.academic_year = %s",
		"pe.program = %s"
	]
	values = [academic_year, program]

	# Filter by txt, matching either student ID or student_name
	if txt:
		conditions.append("(s.name LIKE %s OR s.student_full_name LIKE %s)")
		values.append(f"%{txt}%")
		values.append(f"%{txt}%")

	# Exclude students who are already enrolled in this course (regardless of PE)
	exclusion_clause = """
		s.name NOT IN (
		SELECT pec.student
		FROM `tabProgram Enrollment Course` pec
		WHERE pec.course = %s
		)
	"""		

	conditions.append(exclusion_clause)
	values.append(course)
	where_clause = " AND ".join(conditions)

	# 5) Transform results into the format [[value, label], ...]
	results = frappe.db.sql(f"""
		SELECT s.name, s.student_full_name
		FROM `tabStudent` s
		WHERE s.name IN (
			SELECT pe.student
			FROM `tabProgram Enrollment` pe
			WHERE pe.program = %s AND pe.academic_year = %s AND pe.docstatus = 0
		)
		AND s.enabled = 1
		AND s.name NOT IN (
			SELECT pec.student
			FROM `tabProgram Enrollment Course` pec
			WHERE pec.course = %s
		)
		{f"AND (s.name LIKE %s OR s.student_full_name LIKE %s)" if txt else ""}
		ORDER BY s.name
		LIMIT {start}, {page_len}
	""", (
		[program, academic_year, course] +
		([f"%{txt}%", f"%{txt}%"] if txt else [])
	), as_dict=True)

	return [
		[row["name"], f"{row['name']} - {row['student_full_name']}".strip(" -")]
		for row in results
	]


@frappe.whitelist()
def get_courses_for_program(doctype, txt, searchfield, start, page_len, filters=None):
	"""
	Return a list of [value, label] for the "course" Link field,
	showing only courses that are in Program's child table "Program Course".
	
	- doctype: "Course" (the link doctype)
	- txt: user-typed text for partial matching
	- searchfield, start, page_len: for pagination
	- filters: dict with {'program': <program_name>}
	
	Steps:
		1) Check if 'program' is in filters.
		2) Query 'Program Course' joined to 'Course' if needed.
		3) Return [[course_name, "COURSE123 - Some Course Title"], ...].
	"""

	start = cint(start)
	page_len = cint(page_len)

	if not filters:
		filters = {}

	program = filters.get("program")
	if not program:
		# No program chosen => No results or you might show all courses
		return []

	# We'll match partial text on the Course name or Course's course_name
	conditions = ["pc.parent = %s"]
	values = [program]

	if txt:
		conditions.append("(c.name LIKE %s OR c.course_name LIKE %s)")
		values.append(f"%{txt}%")
		values.append(f"%{txt}%")

	where_clause = " AND ".join(conditions)

	results = frappe.db.sql(f"""
		SELECT c.name, c.course_name
		FROM `tabProgram Course` pc
		JOIN `tabCourse` c ON c.name = pc.course
		WHERE {where_clause}
		ORDER BY c.name
		LIMIT {start}, {page_len}
	""", values, as_dict=True)

	final = []
	for row in results:
		course_id = row["name"]
		course_label = row["course_name"] or ""
		label = f"{course_id} - {course_label}".strip(" -")
		final.append([course_id, label])

	return final

@frappe.whitelist()
def list_academic_years_desc(doctype, txt, searchfield, start, page_len, filters):
	# Use pluck for efficient flat list retrieval
	results = frappe.db.sql("""
		SELECT name 
		FROM `tabAcademic Year`
		WHERE year_end_date IS NOT NULL
		ORDER BY year_end_date DESC
	""", as_list=True)

	# Return the results directly, already in the correct format
	return results