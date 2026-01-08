# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


_ACTIVE_REQUEST_STATUSES = ("Submitted", "Under Review", "Approved")


class ProgramEnrollmentRequest(Document):
	pass


@frappe.whitelist()
def get_offering_catalog(program_offering):
	if not program_offering:
		frappe.throw(_("Program Offering is required."))

	rows = frappe.get_all(
		"Program Offering Course",
		filters={
			"parent": program_offering,
			"parenttype": "Program Offering",
		},
		fields=[
			"course",
			"course_name",
			"required",
			"elective_group",
			"capacity",
			"waitlist_enabled",
			"reserved_seats",
		],
		order_by="idx asc",
	)

	return rows


@frappe.whitelist()
def validate_enrollment_request(request_name):
	if not request_name:
		frappe.throw(_("Program Enrollment Request is required."))

	doc = frappe.get_doc("Program Enrollment Request", request_name)
	payload, is_valid = _validate_request(doc)

	status = "Valid" if is_valid else "Invalid"
	updates = {
		"validation_status": status,
		"validation_payload": json.dumps(payload, sort_keys=True),
		"validated_on": now_datetime(),
		"validated_by": frappe.session.user,
	}

	doc.db_set(updates, update_modified=True)
	return payload


def _validate_request(doc):
	payload = {
		"request": doc.name,
		"program_offering": doc.program_offering,
		"student": doc.student,
		"courses": {},
		"errors": [],
	}

	requested_courses = [r for r in (doc.courses or []) if r.course]
	if not requested_courses:
		payload["errors"].append("No courses selected.")
		return payload, False

	offering_rows = get_offering_catalog(doc.program_offering)
	offering_map = {r.get("course"): r for r in offering_rows if r.get("course")}

	existing_counts = _existing_request_counts(doc.program_offering, exclude_request=doc.name)
	request_counts = _count_requested_courses(requested_courses)

	prereq_rows = _program_prereqs(doc)
	enrollment_status_map = _student_enrollment_statuses(doc.student)
	term_result_cache = {}

	all_valid = True
	for row in requested_courses:
		course = row.course
		course_payload = {
			"offering_ok": True,
			"capacity_ok": True,
			"prereq_ok": True,
			"prereq_groups": [],
		}

		offering_row = offering_map.get(course)
		if not offering_row:
			course_payload["offering_ok"] = False
			course_payload["prereq_ok"] = False
			all_valid = False
			payload["errors"].append(f"Course {course} is not in the offering.")
			payload["courses"][course] = course_payload
			continue

		capacity = offering_row.get("capacity")
		if capacity is not None:
			current = existing_counts.get(course, 0)
			requested = request_counts.get(course, 0)
			if current + requested > int(capacity or 0):
				course_payload["capacity_ok"] = False
				all_valid = False
				payload["errors"].append(
					f"Capacity exceeded for course {course} ({current + requested}/{capacity})."
				)

		prereq_ok, prereq_groups = _evaluate_prereqs(
			course=course,
			apply_to_level=row.apply_to_level,
			prereq_rows=prereq_rows,
			enrollment_status_map=enrollment_status_map,
			term_result_cache=term_result_cache,
			student=doc.student,
		)
		course_payload["prereq_ok"] = prereq_ok
		course_payload["prereq_groups"] = prereq_groups
		if not prereq_ok:
			all_valid = False
			payload["errors"].append(f"Prerequisite check failed for course {course}.")

		payload["courses"][course] = course_payload

	return payload, all_valid


def _existing_request_counts(program_offering, exclude_request=None):
	conditions = ["per.program_offering = %(program_offering)s"]
	params = {"program_offering": program_offering}
	if exclude_request:
		conditions.append("per.name != %(exclude_request)s")
		params["exclude_request"] = exclude_request
	if _ACTIVE_REQUEST_STATUSES:
		conditions.append("per.status in %(statuses)s")
		params["statuses"] = _ACTIVE_REQUEST_STATUSES

	where_clause = " and ".join(conditions)
	rows = frappe.db.sql(
		f"""
		SELECT
			perc.course AS course,
			COUNT(perc.name) AS total
		FROM `tabProgram Enrollment Request Course` perc
		JOIN `tabProgram Enrollment Request` per
			ON per.name = perc.parent
		WHERE {where_clause}
		GROUP BY perc.course
		""",
		params,
		as_dict=True,
	)

	counts = {}
	for row in rows:
		course = row.get("course")
		if not course:
			continue
		counts[course] = int(row.get("total") or 0)
	return counts


def _count_requested_courses(rows):
	counts = {}
	for row in rows:
		if not row.course:
			continue
		counts[row.course] = counts.get(row.course, 0) + 1
	return counts


def _program_prereqs(doc):
	program = doc.program
	if not program and doc.program_offering:
		program = frappe.db.get_value("Program Offering", doc.program_offering, "program")
	if not program:
		return []

	return frappe.get_all(
		"Program Course Prerequisite",
		filters={"parent": program, "parenttype": "Program"},
		fields=[
			"apply_to_course",
			"apply_to_level",
			"prereq_group",
			"required_course",
			"min_numeric_score",
			"min_grade",
			"grade_scale_used",
			"concurrency_ok",
		],
		order_by="idx asc",
	)


def _student_enrollment_statuses(student):
	if not student:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT
			pec.course AS course,
			pec.status AS status
		FROM `tabProgram Enrollment Course` pec
		JOIN `tabProgram Enrollment` pe
			ON pe.name = pec.parent
		WHERE pe.student = %s
			AND IFNULL(pec.course, '') != ''
		""",
		(student,),
		as_dict=True,
	)

	status_map = {}
	for row in rows:
		course = row.get("course")
		status = row.get("status") or ""
		if not course:
			continue
		status_map.setdefault(course, set()).add(status)
	return status_map


def _evaluate_prereqs(course, apply_to_level, prereq_rows, enrollment_status_map, term_result_cache, student):
	relevant = [
		r for r in prereq_rows
		if r.get("apply_to_course") == course and _level_matches(r.get("apply_to_level"), apply_to_level)
	]
	if not relevant:
		return True, []

	grouped = {}
	for row in relevant:
		group = int(row.get("prereq_group") or 1)
		grouped.setdefault(group, []).append(row)

	group_results = []
	any_pass = False

	for group, rows in sorted(grouped.items(), key=lambda item: item[0]):
		requirements = []
		group_pass = True
		for row in rows:
			passed, detail = _evaluate_requirement(row, enrollment_status_map, term_result_cache, student)
			requirements.append(detail)
			if not passed:
				group_pass = False
		group_results.append({
			"group": group,
			"passed": group_pass,
			"requirements": requirements,
		})
		if group_pass:
			any_pass = True

	return any_pass, group_results


def _evaluate_requirement(row, enrollment_status_map, term_result_cache, student):
	required_course = row.get("required_course")
	min_numeric_score = row.get("min_numeric_score")
	if min_numeric_score is not None:
		min_numeric_score = float(min_numeric_score)
	concurrency_ok = int(row.get("concurrency_ok") or 0) == 1

	result = {
		"required_course": required_course,
		"min_numeric_score": min_numeric_score,
		"grade_scale_used": row.get("grade_scale_used"),
		"course_status": None,
		"numeric_score": None,
		"passed": False,
		"note": None,
	}

	if not required_course:
		result["note"] = "Missing required course configuration."
		return False, result

	statuses = enrollment_status_map.get(required_course, set())
	if concurrency_ok:
		eligible_statuses = {"Completed", "Enrolled"}
	else:
		eligible_statuses = {"Completed"}

	if not statuses.intersection(eligible_statuses):
		result["note"] = "No eligible enrollment found for required course."
		return False, result

	result["course_status"] = sorted(statuses)

	if min_numeric_score is None:
		result["passed"] = True
		return True, result

	term_result = _best_course_term_result(student, required_course, term_result_cache)
	if not term_result or term_result.get("numeric_score") is None:
		result["note"] = "No numeric score evidence found."
		return False, result

	numeric_score = float(term_result.get("numeric_score"))
	result["numeric_score"] = numeric_score
	if numeric_score >= min_numeric_score:
		result["passed"] = True
		return True, result

	result["note"] = "Numeric score below prerequisite threshold."
	return False, result


def _best_course_term_result(student, required_course, term_result_cache):
	cache_key = (student, required_course)
	if cache_key in term_result_cache:
		return term_result_cache[cache_key]

	# Temporary Phase 1 rule: prefer override results, else most recent by term end date / modified.
	rows = frappe.db.sql(
		"""
		SELECT
			ctr.name,
			ctr.numeric_score,
			ctr.is_override,
			ctr.term,
			ctr.modified,
			term.term_end_date
		FROM `tabCourse Term Result` ctr
		LEFT JOIN `tabTerm` term
			ON term.name = ctr.term
		WHERE ctr.student = %s
			AND ctr.course = %s
		ORDER BY
			ctr.is_override DESC,
			term.term_end_date DESC,
			ctr.modified DESC
		LIMIT 1
		""",
		(student, required_course),
		as_dict=True,
	)

	result = rows[0] if rows else None
	term_result_cache[cache_key] = result
	return result


def _level_matches(prereq_level, request_level):
	level = (prereq_level or "").strip()
	if not level or level == "None":
		return True
	return level == (request_level or "").strip()
