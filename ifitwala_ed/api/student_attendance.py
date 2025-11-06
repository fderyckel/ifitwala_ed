import frappe
from frappe import _

from ifitwala_ed.api.student_groups import (
	TRIAGE_ROLES,
	_user_roles,
	_instructor_group_names,
)

PORTAL_GROUP_FIELDS = [
	"name",
	"student_group_name",
	"program",
	"course",
	"cohort",
	"academic_year",
	"status",
]


@frappe.whitelist()
def fetch_portal_student_groups():
	"""
	Return active student groups visible to the logged-in staff member.
	* Academic Admin / Counselor / Instructor / Admin roles see all active groups.
	* Other instructors only see the groups they are assigned to through Student Group Instructor.
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please sign in to view student groups."))

	filters: dict[str, object] = {"status": "Active"}
	roles = _user_roles(user)

	if roles & TRIAGE_ROLES:
		return _query_groups(filters)

	# Restrict to instructor-linked groups
	group_names = _instructor_group_names(user)
	if not group_names:
		return []

	filters["name"] = ["in", list(group_names)]
	return _query_groups(filters)


def _query_groups(filters: dict[str, object]):
	return frappe.get_all(
		"Student Group",
		fields=PORTAL_GROUP_FIELDS,
		filters=filters,
		order_by="student_group_name asc",
	)
