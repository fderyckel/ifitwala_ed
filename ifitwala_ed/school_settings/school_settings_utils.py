# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/school_settings_utils.py

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


# ---------------------------------------------------------------------
# Option B helper (NEW, additive)
# ---------------------------------------------------------------------

def resolve_terms_for_school_calendar(school: str, academic_year: str):
	"""
	Canonical resolver for Option B.

	Returns the list of Term names that apply to a given (school, academic_year),
	as resolved by School Calendar — NOT by implicit inheritance.

	Resolution order:
	1. School-scoped terms explicitly defined for (school, academic_year)
	2. Global (template) terms (school IS NULL) for the same academic_year

	This function performs NO mutation.
	It is intended for:
	- School Calendar population
	- Enrollment logic
	- Attendance / analytics resolution
	"""

	if not school or not academic_year:
		return []

	# 1. School-scoped terms
	school_terms = frappe.get_all(
		"Term",
		filters={
			"academic_year": academic_year,
			"school": school,
		},
		pluck="name",
		order_by="term_start_date",
	)

	if school_terms:
		return school_terms

	# 2. Global (template) terms
	global_terms = frappe.get_all(
		"Term",
		filters={
			"academic_year": academic_year,
			"school": ["is", "not set"],
		},
		pluck="name",
		order_by="term_start_date",
	)

	return global_terms
