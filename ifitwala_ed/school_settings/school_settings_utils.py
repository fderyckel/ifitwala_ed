# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import get_descendants_of


def get_allowed_schools(user=None, selected_school=None):
	"""
	Returns a list of schools the user is allowed to query (their default school and all descendants),
	or only the selected descendant if selected.
	"""
	user = user or frappe.session.user
	default_school = frappe.defaults.get_user_default("school", user)
	if not default_school:
		return []  # No access to any data

	# User's full allowed set (default + descendants)
	all_schools = [default_school] + get_descendants_of("School", default_school)
	all_schools = list(set(all_schools))  # Ensure uniqueness

	if not selected_school or selected_school == default_school:
		return all_schools
	if selected_school in all_schools:
		return [selected_school]
	# If the filter is for a school outside their allowed set, return nothing
	return []

@frappe.whitelist()
def get_user_allowed_schools():
	user = frappe.session.user
	default_school = frappe.defaults.get_user_default("school", user)
	if not default_school:
		return []
	descendants = get_descendants_of("School", default_school)
	return [default_school] + descendants

