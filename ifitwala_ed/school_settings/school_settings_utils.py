# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/school_settings_utils.py

import frappe
from frappe.utils.nestedset import get_descendants_of

def get_allowed_schools(user=None, selected_school=None):
	"""
	Visibility helper ONLY.

	Returns schools the user can SEE.
	Does NOT imply calendar inheritance or resolution.
	"""
	user = user or frappe.session.user
	root_school = frappe.defaults.get_user_default("school", user)

	if not root_school:
		return []

	visible = [root_school] + get_descendants_of("School", root_school)

	if selected_school:
		return [selected_school] if selected_school in visible else []

	return visible


@frappe.whitelist()
def get_user_allowed_schools():
	user = frappe.session.user
	root_school = frappe.defaults.get_user_default("school", user)
	if not root_school:
		return []

	return [root_school] + get_descendants_of("School", root_school)


# ---------------------------------------------------------------------
# Option B helper (NEW, additive)
# ---------------------------------------------------------------------

def resolve_terms_for_school_calendar(school: str, academic_year: str):
	"""
	Pattern B — Canonical term resolver.

	IMPORTANT:
	- This function does NOT decide inheritance.
	- It ONLY returns candidate terms that a School Calendar may use.
	- Final authority remains the School Calendar record.

	Resolution order:
	1. School-scoped terms for this school
	2. Ancestor-school terms (explicit, via school_tree)
	3. Global template terms (school IS NULL)

	No mutation. No silent inheritance.
	"""

	if not school or not academic_year:
		return []

	from ifitwala_ed.utilities.school_tree import get_ancestor_schools

	candidates = []

	# 1 ▸ Exact school terms
	candidates += frappe.get_all(
		"Term",
		filters={
			"academic_year": academic_year,
			"school": school,
		},
		pluck="name",
		order_by="term_start_date",
	)

	# 2 ▸ Ancestor-scoped terms (explicit reuse, not inheritance)
	if not candidates:
		for ancestor in get_ancestor_schools(school):
			candidates += frappe.get_all(
				"Term",
				filters={
					"academic_year": academic_year,
					"school": ancestor,
				},
				pluck="name",
				order_by="term_start_date",
			)
			if candidates:
				break

	# 3 ▸ Global templates (opt-in via calendar only)
	if not candidates:
		candidates += frappe.get_all(
			"Term",
			filters={
				"academic_year": academic_year,
				"school": ["is", "not set"],
			},
			pluck="name",
			order_by="term_start_date",
		)

	return candidates
