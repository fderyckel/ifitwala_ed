import frappe
from frappe import _

from ifitwala_ed.schedule.page.student_group_cards.student_group_cards import (
	get_student_group_students,
)

TRIAGE_ROLES = {"Academic Admin", "Academic Staff", "Instructor", "Academic Assistant", "Counselor", "System Manager", "Administrator"}


def _user_roles(user: str) -> set[str]:
	return set(frappe.get_roles(user))


def _instructor_group_names(user: str) -> set[str]:
	names: set[str] = set()
	# Linked directly via user id
	for row in frappe.get_all(
		"Student Group Instructor",
		filters={"user_id": user},
		pluck="parent",
	):
		names.add(row)

	# Linked via Instructor document
	instructor_ids = frappe.get_all(
		"Instructor", filters={"linked_user_id": user}, pluck="name"
	)
	if instructor_ids:
		for row in frappe.get_all(
			"Student Group Instructor",
			filters={"instructor": ["in", instructor_ids]},
			pluck="parent",
		):
			names.add(row)

	# Linked via Employee mapping
	employee = frappe.db.get_value(
		"Employee", {"user_id": user, "status": "Active"}, "name"
	)
	if employee:
		for row in frappe.get_all(
			"Student Group Instructor",
			filters={"employee": employee},
			pluck="parent",
		):
			names.add(row)

	return names


def _base_group_filters(program=None, course=None, cohort=None) -> dict:
	filters: dict = {}
	if program:
		filters["program"] = program
	if course:
		filters["course"] = course
	if cohort:
		filters["cohort"] = cohort
	return filters


@frappe.whitelist()
def fetch_groups(program=None, course=None, cohort=None):
	"""
	Return student groups visible to the current user.
	* Admin / Academic Admin / Counselor / System Manager see all groups.
	* Instructors (or mapped employees) see only groups they are attached to.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You need to sign in to view student groups."))

	filters = _base_group_filters(program, course, cohort)
	roles = _user_roles(user)

	if roles & TRIAGE_ROLES:
		return frappe.get_all("Student Group", filters=filters, fields=["name", "student_group_name"])

	# Restrict to instructor-linked groups
	group_names = _instructor_group_names(user)
	if not group_names:
		return []

	filters["name"] = ["in", list(group_names)]
	return frappe.get_all("Student Group", filters=filters, fields=["name", "student_group_name"])


@frappe.whitelist()
def fetch_group_students(student_group: str, start: int = 0, page_length: int = 25):
	"""
	Return roster for a specific student group. Applies the same instructor/triage permissions.
	"""
	if not student_group:
		frappe.throw(_("Student Group is required."))

	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("You need to sign in to view student groups."))

	roles = _user_roles(user)
	if roles & TRIAGE_ROLES:
		allowed = True
	else:
		group_names = _instructor_group_names(user)
		allowed = student_group in group_names

	if not allowed:
		frappe.throw(_("You do not have access to this student group."))

	students = get_student_group_students(student_group, start, page_length)
	total = frappe.db.count("Student Group Student", {"parent": student_group})

	group = frappe.get_doc("Student Group", student_group)
	group_info = {
		"name": group.name,
		"program": group.program,
		"course": group.course,
		"cohort": group.cohort,
	}

	return {
		"students": students,
		"start": start + page_length,
		"total": total,
		"group_info": group_info,
	}

