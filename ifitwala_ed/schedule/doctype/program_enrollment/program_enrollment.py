# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe 
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, get_link_to_form
from ifitwala_ed.schedule.schedule_utils import get_school_term_bounds
from ifitwala_ed.utilities.school_tree import get_effective_record, ParentRuleViolation
from frappe.utils.nestedset import get_ancestors_of
from ifitwala_ed.utilities.school_tree import get_descendant_schools

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
		self._validate_course_terms()

		# Ensure the academic year and program belong to the same school
		if self.program and not self.school: 
			self.school = frappe.db.get_value("Program", self.program, "school")			

	def before_submit(self):
		self.validate_only_one_active_enrollment()

	def on_submit(self):
		self.update_student_joining_date()


	def _resolve_academic_year(self):
		allowed_schools = [self.school] + get_ancestors_of("School", self.school)

		# 1 ▸ autofill if left blank
		if not self.academic_year:
			self.academic_year = get_effective_record(
				"Academic Year",
				self.school,
				extra_filters={"archived": 0},	
			)
			if not self.academic_year:
				raise ParentRuleViolation(
					_("No active Academic Year found for {0} or its ancestors.")
					.format(self.school)
				)
			return

		# 2 ▸ validate manual pick
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
			return # if archived is checked. 
		
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

	# Ensure all courses use terms from one valid source: either the school or the fallback ancestor, and term_start <= term_end.
	def _validate_course_terms(self):
		valid_terms, source_school = get_terms_for_ay_with_fallback(self.school, self.academic_year)
		if not valid_terms:
			return  # No terms anywhere—let other validations handle this situation

		for row in self.courses:
			# Check valid terms
			if row.term_start and row.term_start not in valid_terms:
				frappe.throw(
					_("Term Start '{0}' must be from {1} for Academic Year '{2}'.").format(
						row.term_start, source_school, self.academic_year
					),
					title=_("Invalid Term Start")
				)
			if row.term_end and row.term_end not in valid_terms:
				frappe.throw(
					_("Term End '{0}' must be from {1} for Academic Year '{2}'.").format(
						row.term_end, source_school, self.academic_year
					),
					title=_("Invalid Term End")
				)

			# Check order: term_start <= term_end
			if row.term_start and row.term_end:
				if row.term_start == row.term_end:
					continue  # ok if same
				term_start_doc = frappe.get_doc("Term", row.term_start)
				term_end_doc = frappe.get_doc("Term", row.term_end)
				if getdate(term_start_doc.term_start_date) > getdate(term_end_doc.term_start_date):
					frappe.throw(
						_("For course <b>{0}</b>: The start term <b>{1}</b> ({2}) must not be after the end term <b>{3}</b> ({4}).")
						.format(
							row.course or "",
							row.term_start, term_start_doc.term_start_date,
							row.term_end, term_end_doc.term_start_date
						),
						title=_("Invalid Term Sequence")
					)
		
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

	school = filters.get("school")
	if not school:
		return []

	def find_school_with_ay(school):
		# Search for AYs for this school, else walk up to parent
		while school:
			ay_exists = frappe.db.exists("Academic Year", {"school": school})
			if ay_exists:
				return school
			# Standard NestedSet parent
			parent = frappe.db.get_value("School", school, "parent_school")
			if not parent or parent == school:
				break
			school = parent
		return None

	target_school = find_school_with_ay(school)
	if not target_school:
		return []

	conditions = ["school = %(school)s"]
	values = {"school": target_school}

	if txt:
		conditions.append("name LIKE %(txt)s")
		values["txt"] = f"%{txt}%"

	where_clause = "WHERE " + " AND ".join(conditions)

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


def get_terms_for_ay_with_fallback(school, academic_year):
    """Returns (terms, source_school) for the best available school: leaf, else nearest ancestor with terms for AY."""
    if not (school and academic_year):
        return [], None
    # 1. Try direct school first
    terms = frappe.db.get_values(
        "Term",
        {"school": school, "academic_year": academic_year},
        "name"
    )
    if terms:
        return [t[0] for t in terms], school
    # 2. Fallback to ancestors in order
    current_school = frappe.get_doc("School", school)
    ancestors = frappe.get_all("School", filters={
        "lft": ["<", current_school.lft],
        "rgt": [">", current_school.rgt]
    }, fields=["name"], order_by="lft desc")
    for ancestor in ancestors:
        ancestor_terms = frappe.db.get_values(
            "Term",
            {"school": ancestor.name, "academic_year": academic_year},
            "name"
        )
        if ancestor_terms:
            return [t[0] for t in ancestor_terms], ancestor.name
    return [], None

@frappe.whitelist()
def get_valid_terms_with_fallback(school, academic_year):
    terms, source_school = get_terms_for_ay_with_fallback(school, academic_year)
    return {
        "valid_terms": terms,
        "source_school": source_school
    }


def get_permission_query_conditions(user):
    # Allow full access to Administrator or System Manager
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return None

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return "1=0"  # No access if no default school

    descendant_schools = get_descendant_schools(user_school)
    if not descendant_schools:
        return "1=0"
    schools_list = "', '".join(descendant_schools)
    return f"`tabProgram Enrollment`.`school` IN ('{schools_list}')"

def has_permission(doc, user=None):
    if not user:
        user = frappe.session.user

    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True

    user_school = frappe.defaults.get_user_default("school", user)
    if not user_school:
        return False

    descendant_schools = get_descendant_schools(user_school)
    return doc.school in descendant_schools

def on_doctype_update():
	# idempotent: adds only if missing
	frappe.db.add_index("Program Enrollment", ["student"])
	# useful for AY-scoped lookups
	frappe.db.add_index("Program Enrollment", ["student", "academic_year"])
	# Program Enrollment: speed up lookups from Student Referral flow
	frappe.db.add_index("Program Enrollment", ["student", "archived"])	