# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_comm_utils

import frappe
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools
from frappe import _

def check_audience_match(comm_name, user, roles, employee, filter_team=None, filter_student_group=None, filter_school=None):
	"""
	Checks if the current user (employee) matches the audience criteria
	for a given Org Communication.

	Strict school filter behaviour:
	- If filter_school = X, show only audiences where audience.school is in {X} ∪ Anc(X).
	- Never include descendants of X.
	- Global (aud.school is None) is still allowed by the school filter.
	"""

	# System Manager baseline:
	# - If no extra filters: see everything without checking audiences.
	# - If filters are present, still respect them (school / team / SG).
	if "System Manager" in roles and not filter_team and not filter_student_group and not filter_school:
		return True

	audiences = frappe.get_all(
		"Org Communication Audience",
		filters={"parent": comm_name},
		fields=["target_group", "school", "team", "program", "student_group"],
	)

	if not audiences:
		return False

	# 1) User visibility cone: own school + ancestors + descendants (prevents sibling leakage)
	user_school = None
	valid_target_schools: set[str] = set()

	if employee and employee.school:
		user_school = employee.school
		try:
			up = get_ancestor_schools(user_school) or []
		except Exception:
			up = []
		try:
			down = get_descendant_schools(user_school) or []
		except Exception:
			down = []
		valid_target_schools = set(up + down + [user_school])

	# 2) Strict filter scope: selected school + ancestors only (NO descendants)
	filter_school_scope: set[str] | None = None
	if filter_school and filter_school != "All":
		try:
			up_f = get_ancestor_schools(filter_school) or []
		except Exception:
			up_f = []
		filter_school_scope = set(up_f + [filter_school])

	for aud in audiences:
		# --- FILTER CHECKS (team / student group) ---
		if filter_team and aud.team != filter_team:
			continue

		if filter_student_group and aud.student_group != filter_student_group:
			continue

		# --- SCHOOL FILTER CHECK (strict upward only) ---
		# If filter_school is set, keep only audience rows whose school is in {filter} ∪ Anc(filter).
		# Global audience rows (aud.school is None) are NOT excluded by the school filter.
		if filter_school_scope is not None and aud.school:
			if aud.school not in filter_school_scope:
				continue

		# --- USER VISIBILITY CHECK (permission cone) ---
		if aud.school:
			if not user_school:
				continue
			if valid_target_schools and aud.school not in valid_target_schools:
				continue

		# --- TARGET GROUP CHECK ---
		match_found = False

		if aud.target_group in {"Whole Community", "Whole Staff"}:
			match_found = True

		elif aud.target_group == "Academic Staff" and ("Academic Staff" in roles or "Instructor" in roles):
			match_found = True
		elif aud.target_group == "Support Staff" and "Academic Staff" not in roles:
			match_found = True

		elif aud.team and employee and employee.department == aud.team:
			match_found = True

		elif aud.student_group:
			if is_instructor_for_group(user, aud.student_group):
				match_found = True

		if match_found:
			return True

	return False



def is_instructor_for_group(user, student_group):
	"""Determine if user is an instructor for this group."""
	employee_name = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee_name:
		return False

	# If you have a dedicated Instructor doctype linked from Employee, resolve it here.
	instructor_name = frappe.db.get_value("Instructor", {"employee": employee_name}, "name")
	if not instructor_name:
		return False

	return frappe.db.exists(
		"Student Group Instructor",
		{"parent": student_group, "instructor": instructor_name},
	)
