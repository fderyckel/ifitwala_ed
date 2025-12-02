# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_demographics_dashboard.py

from __future__ import annotations

import frappe

ALLOWED_ANALYTICS_ROLES = {
	"Academic Admin",
	"Grade Level Lead",
	"Counsellor",
	"Curriculum Coordinator",
	"Admissions Officer",
	"Marketing Manager",
	"System Manager",
	"Administrator",
}


def _ensure_demographics_access(user: str | None = None) -> str:
	"""Gate analytics to authorized staff roles."""
	user = user or frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You need to sign in to access Student Demographic Analytics.", frappe.PermissionError)

	roles = set(frappe.get_roles(user))
	if roles & ALLOWED_ANALYTICS_ROLES:
		return user

	frappe.throw("You do not have permission to access Student Demographic Analytics.", frappe.PermissionError)
	return user


def _empty_dashboard():
	return {
		"kpis": {
			"total_students": 0,
			"cohorts_represented": 0,
			"unique_nationalities": 0,
			"unique_home_languages": 0,
			"residency_split_pct": {"local": 0, "expat": 0, "boarder": 0, "other": 0},
			"pct_with_siblings": 0,
			"guardian_diversity_score": 0,
		},
		"nationality_distribution": [],
		"nationality_by_cohort": [],
		"gender_by_cohort": [],
		"residency_status": [],
		"age_distribution": [],
		"home_language": [],
		"multilingual_profile": [],
		"family_kpis": {
			"family_count": 0,
			"avg_children_per_family": 0,
			"pct_families_with_2_plus": 0,
		},
		"sibling_distribution": [],
		"family_size_histogram": [],
		"guardian_nationality": [],
		"guardian_comm_language": [],
		"guardian_residence_country": [],
		"guardian_residence_city": [],
		"guardian_sector": [],
		"financial_guardian": [],
		"slices": {},
	}


@frappe.whitelist()
def get_filter_meta():
	"""
	Return filter metadata used by the demographics dashboard.
	This is intentionally lightweight; extend with cohorts/programs if needed.
	"""
	_ensure_demographics_access()

	schools = frappe.get_all(
		"School",
		fields=["name as name", "school_name as label"],
		order_by="name asc",
	)
	cohorts = frappe.get_all(
		"Cohort",
		fields=["name as name", "cohort_name as label"],
		order_by="name asc",
	) if frappe.db.table_exists("Cohort") else []

	return {
		"default_school": frappe.defaults.get_user_default("school"),
		"schools": schools,
		"cohorts": cohorts,
	}


@frappe.whitelist()
def get_dashboard(filters=None):
	"""
	Placeholder implementation: returns empty aggregates so the UI can render.
	Replace with real aggregation logic scoped to active students only.
	"""
	_ensure_demographics_access()
	# Accept both JSON string and dict for filters
	if isinstance(filters, str):
		try:
			filters = frappe.parse_json(filters) or {}
		except Exception:
			filters = {}
	else:
		filters = filters or {}

	return _empty_dashboard()


@frappe.whitelist()
def get_slice_entities(slice_key: str | None = None, filters=None, start: int = 0, page_length: int = 50):
	"""
	Placeholder drill-down: returns an empty list.
	Implement real lookup by slice_key (student or guardian) when data is ready.
	"""
	_ensure_demographics_access()
	return []
