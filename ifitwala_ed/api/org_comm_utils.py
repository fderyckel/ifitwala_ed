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

	def _employee_matches_team(team_name: str) -> bool:
		"""
		Audience.team is a Link to Team => value must be Team.name.
		Employee.department might not be a Team.name.
		We only treat it as a match if Employee.department is an actual Team record.
		"""
		if not employee:
			return False

		dept = (employee.get("department") or "").strip()
		if not dept:
			return False

		# If Employee.department is not a Team.name, do NOT use it.
		if not frappe.db.exists("Team", dept):
			return False

		return dept == team_name

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

	# 1) User visibility cone (permission cone):
	#    own school + ancestors + descendants (prevents sibling leakage)
	user_school = None
	valid_target_schools: set[str] = set()

	if employee and employee.get("school"):
		user_school = employee.get("school")

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
		aud_team = aud.get("team")
		aud_school = aud.get("school")
		aud_student_group = aud.get("student_group")
		aud_target_group = aud.get("target_group")

		# ------------------------------------------------------------
		# A) Explicit archive filters (team / student_group / school)
		# ------------------------------------------------------------
		if filter_team:
			# If a team filter is set, audience row must be that team.
			if aud_team != filter_team:
				continue

		if filter_student_group:
			# If a student group filter is set, audience row must be that group.
			if aud_student_group != filter_student_group:
				continue

		# School filter (strict upward only; global rows still allowed)
		if filter_school_scope is not None and aud_school:
			if aud_school not in filter_school_scope:
				continue

		# ------------------------------------------------------------
		# B) Permission cone / sibling leakage prevention
		# ------------------------------------------------------------
		if aud_school:
			# If audience specifies a school, user must have a resolvable school and it must be in their cone.
			if not user_school:
				continue
			if valid_target_schools and aud_school not in valid_target_schools:
				continue

		# ------------------------------------------------------------
		# C) Audience row constraints MUST be respected
		#    (prevents "Whole Staff" bypassing a team-specific row)
		# ------------------------------------------------------------
		if aud_team:
			if not _employee_matches_team(aud_team):
				continue

		if aud_student_group:
			if not is_instructor_for_group(user, aud_student_group):
				continue

		# ------------------------------------------------------------
		# D) Target group rules (role-based)
		# ------------------------------------------------------------
		match_found = False

		# Broad groups
		if aud_target_group in {"Whole Community", "Whole Staff"}:
			match_found = True

		# Staff role grouping
		elif aud_target_group == "Academic Staff":
			if "Academic Staff" in roles or "Instructor" in roles:
				match_found = True

		elif aud_target_group == "Support Staff":
			# Keep your prior meaning: support staff = not academic staff
			if "Academic Staff" not in roles and "Instructor" not in roles:
				match_found = True

		# Student-group rows already enforced above (C), but keep this for clarity
		elif aud_student_group:
			match_found = True

		# If you later want Students/Guardians matching, do it explicitly here
		# elif aud_target_group == "Students": ...
		# elif aud_target_group == "Guardians": ...

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
