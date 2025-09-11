# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import now_datetime

def _get_student_name_for_user(user: str) -> str | None:
	# Map portal user → Student by email (lightweight, indexed)
	return frappe.db.get_value("Student", {"student_email": user}, "name")

def _get_academic_years(student_name: str) -> list[str]:
	# Distinct years from Program Enrollment for this student, newest first (single indexed scan)
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
	# Lean join across PE/PEC/Course; avoid heavy get_doc calls
	rows = frappe.db.sql(
		"""
		select
			pec.course,
			coalesce(pec.course_name, c.course_name) as course_name,
			c.course_group,
			c.course_image
		from `tabProgram Enrollment Course` pec
		join `tabProgram Enrollment` pe on pec.parent = pe.name
		left join `tabCourse` c on c.name = pec.course
		where pe.student = %s
		  and pe.academic_year = %s
		  and coalesce(pec.status, 'Enrolled') <> 'Dropped'
		order by coalesce(pec.course_name, pec.course)
		""",
		(student_name, academic_year),
		as_dict=True,
	)

	placeholder = "/assets/ifitwala_ed/images/course_placeholder.png"
	courses = []
	for r in rows:
		course = r.get("course")
		if not course:
			continue
		courses.append({
			"course": course,
			"course_name": r.get("course_name") or course,
			"course_group": r.get("course_group"),
			"course_image": r.get("course_image") or placeholder,
			"href": f"/sp/course/{course}",
		})
	return courses

def get_context(context):
	# Redirect guests to public site
	if frappe.session.user == "Guest":
		frappe.local.response["type"] = "redirect"
		frappe.local.response["location"] = "/"
		return

	context.no_cache = 1
	context.portal_root = "/sp"
	context.page_title = _("Courses")
	context.breadcrumbs = [{"label": _("Dashboard"), "route": "/sp"}, {"label": _("Courses")}]
	context.current_year = now_datetime().year

	# Defaults to keep template safe
	context.academic_years = []
	context.selected_year = None
	context.courses = []
	context.courses_empty_reason = None

	roles = set(frappe.get_roles(frappe.session.user))
	student_name = _get_student_name_for_user(frappe.session.user) if "Student" in roles else None
	if not student_name:
		context.courses_empty_reason = _("No student profile linked to this login yet.")
		return

	years = _get_academic_years(student_name)
	context.academic_years = years

	selected = frappe.form_dict.get("year") if hasattr(frappe, "form_dict") else None
	if not selected or selected not in years:
		selected = years[0] if years else None
	context.selected_year = selected

	if selected:
		context.courses = _get_courses_for_year(student_name, selected)
		if not context.courses:
			context.courses_empty_reason = _("No courses found for the selected academic year.")
	else:
		context.courses_empty_reason = _("No academic years found for this student.")

