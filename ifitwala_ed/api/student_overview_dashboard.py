# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/student_overview_dashboard.py

from __future__ import annotations

from datetime import date
from typing import Dict, List

import frappe
from frappe.utils import getdate, nowdate

from ifitwala_ed.utilities.school_tree import get_descendant_schools
from ifitwala_ed.api.student_log_dashboard import get_authorized_schools


ALLOWED_STAFF_ROLES = {
	"Academic Admin",
	"Curriculum Coordinator",
	"Counsellor",
	"Attendance",
	"System Manager",
	"Administrator",
	"Academic Staff",
	"Instructor",
}


def _current_user() -> str:
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw("You need to sign in to access Student Overview.", frappe.PermissionError)
	return user


def _user_roles(user: str | None = None) -> set[str]:
	return set(frappe.get_roles(user or frappe.session.user))


def _is_staff(user_roles: set[str]) -> bool:
	return bool(user_roles & ALLOWED_STAFF_ROLES)


def _get_program_subtree(program: str | None) -> list[str] | None:
	if not program:
		return None

	lft, rgt = frappe.db.get_value("Program", program, ["lft", "rgt"])
	if lft is None or rgt is None:
		return [program]

	return frappe.get_all(
		"Program",
		filters={"lft": (">=", lft), "rgt": ("<=", rgt)},
		pluck="name",
	)


def _students_for_guardian(user: str) -> List[str]:
	guardian = frappe.db.get_value("Guardian", {"user": user}, "name")
	if not guardian:
		return []
	return [
		r[0]
		for r in frappe.db.sql(
			"SELECT DISTINCT parent FROM `tabStudent Guardian` WHERE guardian = %s", (guardian,)
		)
	]


def _students_for_student_user(user: str) -> List[str]:
	# Best-effort match: student_email stored on Student is the login username
	stu = frappe.db.get_value("Student", {"student_email": user}, "name")
	return [stu] if stu else []


def _get_student_scope(user: str) -> List[str]:
	roles = _user_roles(user)
	if "Student" in roles:
		return _students_for_student_user(user)
	if "Guardian" in roles:
		return _students_for_guardian(user)
	# Staff → unrestricted (handled later by school filter)
	return []


def _normalize_params(obj):
	if isinstance(obj, str):
		try:
			return frappe.parse_json(obj) or {}
		except Exception:
			return {}
	return obj or {}

@frappe.whitelist()
def get_filter_meta():
	"""
	Schools: default + descendants for the current user (via get_authorized_schools).
	Programs: distinct programs that appear in ACTIVE Program Enrollments
	          under those schools (archived = 0).
	"""
	user = _current_user()
	roles = _user_roles(user)
	student_scope = _get_student_scope(user)

	# Students / Guardians: scope is their Program Enrollments only
	if student_scope:
		pe_rows = frappe.get_all(
			"Program Enrollment",
			filters={
				"student": ["in", student_scope],
				"archived": 0,
			},
			fields=["distinct school", "program"],
		)
		school_names = sorted({r.school for r in pe_rows if r.school})
		program_names = sorted({r.program for r in pe_rows if r.program})

		schools = frappe.get_all(
			"School",
			filters={"name": ["in", school_names]} if school_names else {},
			fields=["name", "school_name as label"],
			order_by="lft",
		)

		programs = []
		if program_names:
			for r in frappe.get_all(
				"Program",
				filters={"name": ["in", program_names]},
				fields=["name", "program_name as label"],
				order_by="program_name",
			):
				programs.append(r)

		default_school = school_names[0] if school_names else None

		return {
			"default_school": default_school,
			"schools": schools,
			"programs": programs,
		}

	# Staff path
	auth_schools = get_authorized_schools(user)
	if not auth_schools:
		return {"default_school": None, "schools": [], "programs": []}

	# Active Program Enrollments in authorized schools
	pe_rows = frappe.db.sql(
		"""
		SELECT DISTINCT pe.school, pe.program, p.program_name
		FROM `tabProgram Enrollment` pe
		LEFT JOIN `tabProgram` p ON p.name = pe.program
		WHERE pe.archived = 0
		  AND pe.school IN %(schools)s
		""",
		{"schools": tuple(auth_schools)},
		as_dict=True,
	)

	# School list (UI options)
	schools = frappe.get_all(
		"School",
		filters={"name": ["in", auth_schools]},
		fields=["name", "school_name as label"],
		order_by="lft",
	)

	# Unique program options
	seen_programs = set()
	programs = []
	for row in pe_rows:
		if not row.program or row.program in seen_programs:
			continue
		seen_programs.add(row.program)
		programs.append(
			{
				"name": row.program,
				"label": row.program_name or row.program,
				# optional, if you want school-aware program filter later
				"school": row.school,
			}
		)

	default_school = auth_schools[0]

	return {
		"default_school": default_school,
		"schools": schools,
		"programs": programs,
	}

@frappe.whitelist()
def search_students(search_text: str = "", school: str | None = None, program: str | None = None):
	"""
	Typeahead for the Student Overview filter.

	Staff:
	  - universe is ACTIVE Program Enrollments (archived = 0)
	  - filtered by authorized school scope (+descendants) and optional program subtree.

	Student / Guardian:
	  - universe is their own active Program Enrollments.

	Blank search: up to 20 students in scope (no name filter).
	"""
	user = _current_user()
	roles = _user_roles(user)
	visible_students = _get_student_scope(user)

	# ----- Helper: program subtree (NestedSet) -----
	def _get_program_subtree(program_name: str | None) -> list[str] | None:
		if not program_name:
			return None
		lft, rgt = frappe.db.get_value("Program", program_name, ["lft", "rgt"])
		if lft is None or rgt is None:
			return [program_name]
		return frappe.get_all(
			"Program",
			filters={"lft": (">=", lft), "rgt": ("<=", rgt)},
			pluck="name",
		)

	# ----- Student / Guardian path -----
	if visible_students:
		params: dict = {"students": tuple(visible_students)}
		conditions = ["pe.archived = 0", "pe.student IN %(students)s"]

		# school filter: selected school's descendants
		if school:
			school_scope = get_descendant_schools(school)
			if school_scope:
				conditions.append("pe.school IN %(schools)s")
				params["schools"] = tuple(school_scope)

		# program filter: nested subtree
		if program:
			program_scope = _get_program_subtree(program) or [program]
			conditions.append("pe.program IN %(programs)s")
			params["programs"] = tuple(program_scope)

		search_text = (search_text or "").strip()
		if search_text:
			conditions.append(
				"(s.name LIKE %(txt)s OR s.student_full_name LIKE %(txt)s)"
			)
			params["txt"] = f"%{search_text}%"

		sql = f"""
			SELECT DISTINCT s.name AS student, s.student_full_name
			FROM `tabProgram Enrollment` pe
			JOIN `tabStudent` s ON s.name = pe.student
			WHERE {' AND '.join(conditions)}
			ORDER BY s.student_full_name
			LIMIT 20
		"""
		rows = frappe.db.sql(sql, params, as_dict=True)
		return [{"student": r.student, "student_full_name": r.student_full_name} for r in rows]

	# ----- Staff path -----
	auth_schools = get_authorized_schools(user) if _is_staff(roles) else []
	if not auth_schools:
		return []

	# School scope = selected school's descendants ∩ authorized
	if school:
		school_scope = get_descendant_schools(school)
		if auth_schools:
			school_scope = [s for s in school_scope if s in auth_schools]
	else:
		school_scope = auth_schools

	program_scope = None
	if program:
		program_scope = _get_program_subtree(program) or [program]

	params: dict = {}
	conditions = ["pe.archived = 0"]

	if school_scope:
		conditions.append("pe.school IN %(schools)s")
		params["schools"] = tuple(school_scope)

	if program_scope:
		conditions.append("pe.program IN %(programs)s")
		params["programs"] = tuple(program_scope)

	search_text = (search_text or "").strip()
	if search_text:
		conditions.append(
			"(s.name LIKE %(txt)s OR s.student_full_name LIKE %(txt)s)"
		)
		params["txt"] = f"%{search_text}%"

	sql = f"""
		SELECT DISTINCT s.name AS student, s.student_full_name
		FROM `tabProgram Enrollment` pe
		JOIN `tabStudent` s ON s.name = pe.student
		WHERE {' AND '.join(conditions)}
		ORDER BY s.student_full_name
		LIMIT 20
	"""

	rows = frappe.db.sql(sql, params, as_dict=True)
	return [{"student": r.student, "student_full_name": r.student_full_name} for r in rows]


def _ensure_can_view_student(student: str, school: str | None, program: str | None):
	user = _current_user()
	roles = _user_roles(user)

	# Students/Guardians: only within their scope
	scope = _get_student_scope(user)
	if scope and student not in scope:
		frappe.throw("You are not allowed to access this student.", frappe.PermissionError)

	if _is_staff(roles):
		authorized = set(get_authorized_schools(user))
		if school and authorized and school not in authorized:
			frappe.throw("You are not allowed to access this school.", frappe.PermissionError)
		# program is best-effort; skip hard enforcement to avoid false negatives
		return

	# If not staff and no explicit scope match, deny
	if not scope:
		frappe.throw("You are not allowed to access this student.", frappe.PermissionError)


def _compute_age(dob: date | str | None) -> int | None:
	if not dob:
		return None
	try:
		d = getdate(dob)
	except Exception:
		return None
	today = getdate(nowdate())
	years = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
	return max(years, 0)


def _identity_block(student: str, program: str | None, school: str | None):
	student_doc = frappe.db.get_value(
		"Student",
		student,
		[
			"name",
			"student_full_name",
			"student_image",
			"cohort",
			"student_gender",
			"student_date_of_birth",
			"anchor_school",
		],
		as_dict=True,
	) or {}

	pe_filters = {"student": student}
	if program:
		pe_filters["program"] = program
	if school:
		pe_filters["school"] = school

	program_enrollment = frappe.db.get_value(
		"Program Enrollment",
		pe_filters,
		[
			"name",
			"program",
			"program_offering",
			"academic_year",
			"enrollment_date",
			"archived",
			"school",
		],
		as_dict=True,
		order_by="enrollment_date desc",
	)

	student_groups = frappe.db.sql(
		"""
		SELECT sg.name,
		       sg.student_group_name AS label,
		       sg.student_group_abbreviation AS abbreviation,
		       sg.group_based_on,
		       sg.course,
		       sg.attendance_scope
		FROM `tabStudent Group Student` sgs
		LEFT JOIN `tabStudent Group` sg ON sg.name = sgs.parent
		WHERE sgs.student = %s
		ORDER BY sg.student_group_name
		""",
		(student,),
		as_dict=True,
	)

	return {
		"student": student,
		"full_name": student_doc.get("student_full_name"),
		"photo": student_doc.get("student_image"),
		"cohort": student_doc.get("cohort"),
		"gender": student_doc.get("student_gender"),
		"age": _compute_age(student_doc.get("student_date_of_birth")),
		"date_of_birth": student_doc.get("student_date_of_birth"),
		"school": {
			"name": student_doc.get("anchor_school") or (program_enrollment or {}).get("school") or school,
			"label": frappe.db.get_value(
				"School",
				(student_doc.get("anchor_school") or school),
				"school_name",
			),
		},
		"program_enrollment": program_enrollment or {},
		"student_groups": student_groups,
	}


def _attendance_map():
	rows = frappe.get_all(
		"Student Attendance Code",
		fields=["name", "attendance_code", "attendance_code_name", "count_as_present", "color"],
	)
	return {r.name: r for r in rows}


def _attendance_block(student: str, academic_year: str | None):
	code_map = _attendance_map()
	filters = {"student": student}
	if academic_year:
		filters["academic_year"] = academic_year

	rows = frappe.get_all(
		"Student Attendance",
		filters=filters,
		fields=[
			"attendance_date",
			"attendance_code",
			"course",
			"student_group",
			"program",
			"school",
		],
		order_by="attendance_date asc",
	)

	total = len(rows)
	present = sum(1 for r in rows if code_map.get(r.attendance_code, {}).get("count_as_present"))

	all_day_heatmap = []
	for r in rows:
		code = code_map.get(r.attendance_code, {})
		all_day_heatmap.append(
			{
				"date": r.attendance_date,
				"attendance_code": r.attendance_code,
				"attendance_code_name": code.get("attendance_code_name"),
				"count_as_present": code.get("count_as_present"),
				"color": code.get("color") or "#cbd5e1",
				"academic_year": academic_year,
			}
		)

	# Course/activity heatmap uses ISO week label for grouping
	by_course_heatmap = []
	for r in rows:
		week_label = ""
		if r.attendance_date:
			try:
				week_label = getdate(r.attendance_date).strftime("%G-W%V")
			except Exception:  # noqa: E722 (guard against unexpected date formats)
				week_label = ""
		entry = {
			"course": r.course or "General",
			"course_name": frappe.db.get_value("Course", r.course, "course_name") if r.course else "General",
			"week_label": week_label,
			"present_sessions": 1 if code_map.get(r.attendance_code, {}).get("count_as_present") else 0,
			"absent_sessions": 1 if not code_map.get(r.attendance_code, {}).get("count_as_present") else 0,
			"unexcused_sessions": 0,
			"academic_year": academic_year,
		}
		by_course_heatmap.append(entry)

	breakdown_map: Dict[str, Dict[str, int]] = {}
	for r in rows:
		course_key = r.course or "General"
		entry = breakdown_map.setdefault(
			course_key,
			{
				"course": course_key,
				"course_name": frappe.db.get_value("Course", r.course, "course_name") if r.course else "General",
				"present_sessions": 0,
				"excused_absent_sessions": 0,
				"unexcused_absent_sessions": 0,
				"late_sessions": 0,
				"academic_year": academic_year,
			},
		)
		if code_map.get(r.attendance_code, {}).get("count_as_present"):
			entry["present_sessions"] += 1
		else:
			entry["unexcused_absent_sessions"] += 1

	by_course_breakdown = list(breakdown_map.values())

	return {
		"summary": {
			"present_percentage": present / total if total else 0,
			"total_days": total,
			"present_days": present,
			"excused_absences": 0,
			"unexcused_absences": total - present,
			"late_count": 0,
			"most_impacted_course": None,
		},
		"view_mode": "all_day",
		"all_day_heatmap": all_day_heatmap,
		"by_course_heatmap": by_course_heatmap,
		"by_course_breakdown": by_course_breakdown,
	}


def _task_rows(student: str, program: str | None):
	sql = """
		SELECT
			t.name as task,
			t.title,
			t.course,
			c.course_name,
			t.student_group,
			t.delivery_type,
			t.due_date,
			t.status as task_status,
			t.program,
			t.academic_year,
			ts.status,
			ts.complete,
			ts.mark_awarded,
			ts.total_mark,
			ts.visible_to_student,
			ts.visible_to_guardian,
			ts.updated_on
		FROM `tabTask Student` ts
		INNER JOIN `tabTask` t ON t.name = ts.parent
		LEFT JOIN `tabCourse` c ON c.name = t.course
		WHERE ts.student = %(student)s
	"""
	params = {"student": student}
	if program:
		sql += " AND (t.program = %(program)s OR t.program IS NULL)"
		params["program"] = program
	return frappe.db.sql(sql, params, as_dict=True)


def _learning_block(student: str, program: str | None, academic_year: str | None):
	task_rows = _task_rows(student, program)

	# Status distribution
	status_distribution = []
	if task_rows:
		counter: Dict[str, int] = {}
		for row in task_rows:
			if academic_year and row.academic_year and row.academic_year != academic_year:
				continue
			key = row.status or "Assigned"
			counter[key] = counter.get(key, 0) + 1
		status_distribution = [{"status": k, "count": v, "year_scope": "current"} for k, v in counter.items()]

	# By course completion
	course_map: Dict[str, Dict[str, int]] = {}
	for row in task_rows:
		if academic_year and row.academic_year and row.academic_year != academic_year:
			continue
		key = row.course or "General"
		entry = course_map.setdefault(
			key,
			{
				"course": key,
				"course_name": row.course_name or key,
				"completion_rate": 0,
				"total_tasks": 0,
				"completed_tasks": 0,
				"missed_tasks": 0,
				"academic_year": row.academic_year,
			},
		)
		entry["total_tasks"] += 1
		if row.status in {"Graded", "Returned"} or row.complete:
			entry["completed_tasks"] += 1
		if row.status == "Missed":
			entry["missed_tasks"] += 1

	for entry in course_map.values():
		total = entry["total_tasks"]
		entry["completion_rate"] = (entry["completed_tasks"] / total) if total else 0

	# Recent tasks (latest 10 by due_date)
	recent_tasks = sorted(
		task_rows,
		key=lambda r: r.get("due_date") or r.get("updated_on") or "",
		reverse=True,
	)[:10]

	# Current courses from Program Enrollment Course
	pec_rows = frappe.db.sql(
		"""
		SELECT pec.course, pec.course_name, pec.status, pec.term_start, pec.term_end
		FROM `tabProgram Enrollment` pe
		LEFT JOIN `tabProgram Enrollment Course` pec ON pec.parent = pe.name
		WHERE pe.student = %(student)s {program_filter}
		ORDER BY pec.course_name
		""".format(
			program_filter="AND pe.program = %(program)s" if program else ""
		),
		{"student": student, "program": program} if program else {"student": student},
		as_dict=True,
	)

	current_courses = [
		{
			"course": r.course,
			"course_name": r.course_name or r.course,
			"status": r.status or "current",
			"completion_rate": next(
				(e["completion_rate"] for e in course_map.values() if e["course"] == r.course), 0
			),
			"academic_summary": {},
		}
		for r in pec_rows
	]

	return {
		"current_courses": current_courses,
		"task_progress": {
			"status_distribution": status_distribution,
			"by_course_completion": list(course_map.values()),
		},
		"recent_tasks": recent_tasks,
	}


def _wellbeing_block(student: str, academic_year: str | None):
	# Student Logs
	logs = frappe.db.get_all(
		"Student Log",
		filters={"student": student},
		fields=["name", "date", "log_type", "follow_up_status", "log", "requires_follow_up"],
		order_by="date desc",
		limit=20,
	)

	# Referrals
	referrals = frappe.db.get_all(
		"Student Referral",
		filters={"student": student},
		fields=["name", "referral_date as date", "referral_type", "reason"],
		order_by="referral_date desc",
		limit=10,
	)

	# Nurse visits
	nurse = frappe.db.get_all(
		"Student Patient Visit",
		filters={"student": student},
		fields=["name", "date", "reason"],
		order_by="date desc",
		limit=10,
	)

	timeline = []
	for r in logs:
		timeline.append(
			{
				"type": "student_log",
				"doctype": "Student Log",
				"name": r.name,
				"date": r.date,
				"title": r.log_type or "Log",
				"summary": (r.log or "")[:140],
				"status": r.follow_up_status,
				"is_sensitive": False,
			}
		)
	for r in referrals:
		timeline.append(
			{
				"type": "referral",
				"doctype": "Student Referral",
				"name": r.name,
				"date": r.date,
				"title": r.referral_type or "Referral",
				"summary": (r.reason or "")[:140],
				"status": None,
				"is_sensitive": True,
			}
		)
	for r in nurse:
		timeline.append(
			{
				"type": "nurse_visit",
				"doctype": "Student Patient Visit",
				"name": r.name,
				"date": r.date,
				"title": "Nurse visit",
				"summary": r.reason,
				"status": None,
				"is_sensitive": True,
			}
		)

	timeline = sorted(timeline, key=lambda r: r.get("date") or "", reverse=True)[:30]

	metrics = {
		"student_logs": {"total": len(logs), "open_followups": sum(1 for r in logs if r.requires_follow_up)},
		"referrals": {"total": len(referrals), "active": sum(1 for r in referrals if (r.status or "").lower() != "closed")},
		"nurse_visits": {"total": len(nurse)},
		"time_series": [],
	}

	return {"timeline": timeline, "metrics": metrics}


def _history_block(student: str, program: str | None):
	# Use Program Enrollment academic years as a backbone
	years = frappe.get_all(
		"Program Enrollment",
		filters={"student": student},
		fields=["academic_year"],
		distinct=True,
		order_by="academic_year desc",
	)
	year_options = []
	for idx, y in enumerate(years):
		if idx == 0:
			year_options.append({"key": "current", "label": "This year", "academic_year": y.academic_year})
		elif idx == 1:
			year_options.append({"key": "previous", "label": "Last year", "academic_year": y.academic_year})
	year_options.append({"key": "all", "label": "All years", "academic_years": [y.academic_year for y in years]})

	academic_trend = []
	attendance_trend = []

	# Task completion per AY
	task_rows = _task_rows(student, program)
	for ay in {r.academic_year for r in task_rows if r.academic_year}:
		yr_rows = [r for r in task_rows if r.academic_year == ay]
		total = len(yr_rows)
		completed = sum(1 for r in yr_rows if r.status in {"Graded", "Returned"} or r.complete)
		academic_trend.append(
			{
				"academic_year": ay,
				"label": ay,
				"overall_grade_label": None,
				"overall_grade_value": None,
				"task_completion_rate": (completed / total) if total else 0,
			}
		)

	# Attendance per AY
	att_years = frappe.get_all(
		"Student Attendance",
		filters={"student": student},
		fields=["distinct academic_year as ay"],
	)
	for row in att_years:
		ay = row.ay
		stats = _attendance_block(student, ay)["summary"]
		attendance_trend.append(
			{
				"academic_year": ay,
				"label": ay,
				"present_percentage": stats["present_percentage"],
				"unexcused_absences": stats["unexcused_absences"],
			}
		)

	return {
		"year_options": year_options,
		"selected_year_scope": "all",
		"academic_trend": sorted(academic_trend, key=lambda r: r["academic_year"]),
		"attendance_trend": sorted(attendance_trend, key=lambda r: r["academic_year"]),
		"reflection_flags": [],
	}


def _kpi_block(student: str, academic_year: str | None):
	attendance_summary = _attendance_block(student, academic_year)["summary"]
	task_rows = _task_rows(student, None)
	if academic_year:
		task_rows = [r for r in task_rows if not r.academic_year or r.academic_year == academic_year]

	total_tasks = len(task_rows)
	completed_tasks = sum(1 for r in task_rows if r.status in {"Graded", "Returned"} or r.complete)
	overdue_tasks = sum(
		1
		for r in task_rows
		if r.due_date and getdate(r.due_date) < getdate(nowdate()) and r.status not in {"Graded", "Returned"}
	)
	missed_tasks = sum(1 for r in task_rows if r.status == "Missed")

	return {
		"attendance": attendance_summary,
		"tasks": {
			"completion_rate": (completed_tasks / total_tasks) if total_tasks else 0,
			"total_tasks": total_tasks,
			"completed_tasks": completed_tasks,
			"overdue_tasks": overdue_tasks,
			"missed_tasks": missed_tasks,
		},
		"academic": {"latest_overall_label": None, "latest_overall_value": None, "trend": None},
		"support": {
			"student_logs_total": frappe.db.count("Student Log", {"student": student}),
			"student_logs_open_followups": frappe.db.count(
				"Student Log", {"student": student, "requires_follow_up": 1}
			),
			# Student Referral has no status field in your schema; count all for now.
			"active_referrals": frappe.db.count("Student Referral", {"student": student}),
			# Student Patient Visit links via student_patient, not student
			"nurse_visits_this_term": frappe.db.count("Student Patient Visit", {"student_patient": student}),
		},
	}


def _permissions_for_view(view_mode: str) -> Dict[str, bool]:
	is_student_view = view_mode in {"student", "guardian"}
	return {
		"can_view_tasks": True,
		"can_view_task_marks": not is_student_view,
		"can_view_logs": not is_student_view,
		"can_view_referrals": not is_student_view,
		"can_view_nurse_details": not is_student_view,
		"can_view_attendance_details": True,
	}


@frappe.whitelist()
def get_student_center_snapshot(student: str, school: str, program: str, view_mode: str = "staff"):
	student = student or ""
	program = program or ""
	school = school or ""
	_ensure_can_view_student(student, school, program)

	identity = _identity_block(student, program, school)
	current_ay = identity.get("program_enrollment", {}).get("academic_year")

	return {
		"meta": {
			"student": student,
			"student_name": identity.get("full_name"),
			"school": school,
			"program": program,
			"current_academic_year": current_ay,
			"view_mode": view_mode,
			"permissions": _permissions_for_view(view_mode),
		},
		"identity": identity,
		"kpis": _kpi_block(student, current_ay),
		"learning": _learning_block(student, program, current_ay),
		"attendance": _attendance_block(student, current_ay),
		"wellbeing": _wellbeing_block(student, current_ay),
		"history": _history_block(student, program),
	}
