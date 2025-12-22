# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_comm_utils

import frappe
from ifitwala_ed.utilities.school_tree import get_ancestor_schools, get_descendant_schools
from frappe import _

def check_audience_match(comm_name, user, roles, employee, filter_team=None, filter_student_group=None, filter_school=None):
	"""
	Checks if the current user matches the audience criteria for a given Org Communication.

	Strict filter behavior:
	- If filter_student_group is set:
		Only include communications that have an audience row with that exact student_group.
		The match MUST happen on that student_group row (no leakage via Whole Staff / Team).
		Eligibility:
			- Academic Admin: allowed
			- Others: must be instructor for that group
	- Else if filter_team is set:
		Only include communications that have an audience row with that exact team.
		The match MUST happen on that team row (no leakage via Whole Staff).
		Eligibility:
			- Academic Admin: allowed
			- Others: must be member of that Team via Team Member child table

	Strict school filter behaviour:
	- If filter_school = X, show only audiences where audience.school is in {X} ∪ Anc(X).
	- Never include descendants of X.
	- Global (aud.school is None) is still allowed by the school filter.

	User visibility:
	- Audience school must lie within user's cone: {user_school} ∪ Anc(user_school) ∪ Desc(user_school)
	  (prevents sibling leakage).
	"""

	# Normalize "All"/empty
	if filter_team in ("All", "", None):
		filter_team = None
	if filter_student_group in ("All", "", None):
		filter_student_group = None
	if filter_school in ("All", "", None):
		filter_school = None

	# Defensive: student_group and team filters are mutually exclusive.
	# If both are present, student_group wins (narrower).
	if filter_student_group:
		filter_team = None

	is_academic_admin = "Academic Admin" in roles

	# System Manager baseline:
	# - If no extra filters: see everything without checking audiences.
	# - If filters are present, still respect them.
	if "System Manager" in roles and not filter_team and not filter_student_group and not filter_school:
		return True

	audiences = frappe.get_all(
		"Org Communication Audience",
		filters={"parent": comm_name},
		fields=["target_group", "school", "team", "program", "student_group"],
	)

	if not audiences:
		return False

	# ──────────────────────────────────────────────
	# 1) User visibility cone: own school + ancestors + descendants (prevents sibling leakage)
	# ──────────────────────────────────────────────
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

	# ──────────────────────────────────────────────
	# 2) Strict filter scope: selected school + ancestors only (NO descendants)
	# ──────────────────────────────────────────────
	filter_school_scope: set[str] | None = None
	if filter_school:
		try:
			up_f = get_ancestor_schools(filter_school) or []
		except Exception:
			up_f = []
		filter_school_scope = set(up_f + [filter_school])

	# ──────────────────────────────────────────────
	# 3) Team membership resolution (NO Employee.department usage)
	#    Team Member is a child table of Team:
	#      - parent = Team.name
	#      - member = User (may be empty)
	#      - employee = Employee (required)
	# ──────────────────────────────────────────────
	employee_name = employee.get("name") if employee else None

	# Collect all team names we might need to evaluate (including filter_team)
	team_names = {a.team for a in audiences if a.team}
	if filter_team:
		team_names.add(filter_team)

	user_teams: set[str] = set()

	if team_names and (user or employee_name):
		# We treat membership as:
		# - Team Member.member == user  OR
		# - Team Member.employee == employee_name
		#
		# NOTE: Team Member is a child table, so its "parent" is the Team name.
		conds = []
		params = {"teams": tuple(team_names)}

		if user and user != "Guest":
			conds.append("tm.member = %(user)s")
			params["user"] = user

		if employee_name:
			conds.append("tm.employee = %(employee)s")
			params["employee"] = employee_name

		# If we have no valid condition, skip query
		if conds:
			rows = frappe.db.sql(
				f"""
				SELECT DISTINCT tm.parent
				FROM `tabTeam Member` tm
				WHERE tm.parent IN %(teams)s
				  AND ({' OR '.join(conds)})
				""",
				params,
				as_dict=True,
			)
			user_teams = {r.get("parent") for r in rows if r.get("parent")}

	for aud in audiences:
		# --- SCHOOL FILTER CHECK (strict upward only) ---
		# Global audience rows (aud.school is None) are NOT excluded by the school filter.
		if filter_school_scope is not None and aud.school:
			if aud.school not in filter_school_scope:
				continue

		# --- USER VISIBILITY CHECK (permission cone) ---
		# If the audience row is school-scoped, it must lie inside the user's cone.
		if aud.school:
			if not user_school:
				continue
			if valid_target_schools and aud.school not in valid_target_schools:
				continue

		# ──────────────────────────────────────────────
		# FILTER MODE 1: student_group strict
		# ──────────────────────────────────────────────
		if filter_student_group:
			# Must match ONLY on an audience row that has that exact student_group
			if aud.student_group != filter_student_group:
				continue

			# Eligibility for student group row
			if is_academic_admin:
				return True

			if is_instructor_for_group(user, aud.student_group):
				return True

			continue

		# ──────────────────────────────────────────────
		# FILTER MODE 2: team strict
		# ──────────────────────────────────────────────
		if filter_team:
			# Must match ONLY on an audience row that has that exact team
			if aud.team != filter_team:
				continue

			# Eligibility for team row
			if is_academic_admin:
				return True

			if aud.team and aud.team in user_teams:
				return True

			continue

		# ──────────────────────────────────────────────
		# NO team/student_group filters:
		# normal audience matching rules
		# ──────────────────────────────────────────────

		# TARGET GROUP CHECK
		if aud.target_group in {"Whole Community", "Whole Staff"}:
			return True

		if aud.target_group == "Academic Staff" and ("Academic Staff" in roles or "Instructor" in roles):
			return True

		if aud.target_group == "Support Staff" and "Academic Staff" not in roles:
			return True

		# Team audience row (membership via Team Member)
		if aud.team and aud.team in user_teams:
			return True

		# Student group audience row (instructor membership)
		if aud.student_group:
			if is_instructor_for_group(user, aud.student_group):
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
