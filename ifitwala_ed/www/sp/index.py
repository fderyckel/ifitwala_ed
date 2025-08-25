import frappe
from frappe import _
from frappe.utils import now_datetime

def _get_student_name_for_user(user: str) -> str | None:
	"""Return Student name linked to this user (by Student.student_email)."""
	return frappe.db.get_value("Student", {"student_email": user}, "name")

def _get_academic_years(student_name: str) -> list[str]:
	"""Distinct academic years from Program Enrollment for this student, newest first."""
	rows = frappe.db.sql(
		"""
		select distinct academic_year
		from `tabProgram Enrollment`
		where student = %s
		order by academic_year desc
		""",
		(student_name,),
		as_dict=False,
	)
	return [r[0] for r in rows if r and r[0]]

def _get_courses_for_year(student_name: str, academic_year: str) -> list[dict]:
	"""
	Courses for the student's Program Enrollment in a given academic year.
	Skips rows explicitly marked Dropped.
	"""
	rows = frappe.db.sql(
		"""
		select pec.course, pec.course_name
		from `tabProgram Enrollment Course` pec
		join `tabProgram Enrollment` pe on pec.parent = pe.name
		where pe.student = %s
		  and pe.academic_year = %s
		  and coalesce(pec.status, 'Enrolled') <> 'Dropped'
		order by coalesce(pec.course_name, pec.course)
		""",
		(student_name, academic_year),
		as_dict=True,
	)
	# Shape for cards
	return [
		{
			"course": r.get("course"),
			"course_name": r.get("course_name") or r.get("course"),
			"href": f"/sp/course/{r.get('course')}",
		}
		for r in rows
		if r.get("course")
	]

def get_context(context):
	# Guests → main website
	if frappe.session.user == "Guest":
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/"
		return

	context.no_cache = 1
	context.portal_root = "/sp"
	context.page_title = "Dashboard"
	context.breadcrumbs = []

	# Year for footer (avoid calling functions in Jinja)
	context.current_year = now_datetime().year

	# Students: load courses; Guardians: to be handled later (multi-child selection)
	roles = set(frappe.get_roles(frappe.session.user))
	student_name = _get_student_name_for_user(frappe.session.user) if "Student" in roles else None

	# Default empty context (so template never breaks)
	context.academic_years = []
	context.selected_year = None
	context.courses = []
	context.courses_empty_reason = None

	if not student_name:
		# Leave cards empty for now (guardian flow will populate later)
		context.courses_empty_reason = "No student profile linked to this login yet."
		return

	# Academic year options
	years = _get_academic_years(student_name)
	context.academic_years = years

	# Selected year from query string (?year=YYYY-YY), default to newest
	selected = frappe.form_dict.get("year") if hasattr(frappe, "form_dict") else None
	if not selected or selected not in years:
		selected = years[0] if years else None
	context.selected_year = selected

	# Courses for selected year
	if selected:
		context.courses = _get_courses_for_year(student_name, selected)
		if not context.courses:
			context.courses_empty_reason = "No courses found for the selected academic year."
	else:
		context.courses_empty_reason = "No academic years found for this student."

