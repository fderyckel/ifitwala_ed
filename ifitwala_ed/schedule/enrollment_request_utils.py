# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/enrollment_request_utils.py

import json
import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime, nowdate


@frappe.whitelist()
def validate_program_enrollment_request(request_name, force=0):
	if not request_name:
		frappe.throw(_("Program Enrollment Request is required."))

	_assert_no_catalog_prereqs()

	doc = frappe.get_doc("Program Enrollment Request", request_name)
	force = int(force or 0)

	# Determinism rule:
	# - Once a request is Approved (or Rejected), we do NOT recompute validation.
	# - Rules changing later must affect future requests only.
	final_statuses = {"Approved", "Rejected"}
	if (doc.status in final_statuses) and doc.validation_payload and not force:
		try:
			return json.loads(doc.validation_payload)
		except Exception:
			return {"validation_payload": doc.validation_payload}

	# Existing fast-path: if already Valid and has payload, reuse unless forced
	if not force and doc.validation_status == "Valid" and doc.validation_payload:
		try:
			return json.loads(doc.validation_payload)
		except Exception:
			return {"validation_payload": doc.validation_payload}

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



@frappe.whitelist()
def materialize_program_enrollment_request(request_name):
	if not request_name:
		frappe.throw(_("Program Enrollment Request is required."))

	req = frappe.get_doc("Program Enrollment Request", request_name)
	if req.status != "Approved":
		frappe.throw(_("Only Approved requests can be materialized."))

	if not req.academic_year:
		frappe.throw(_("Academic Year is required to materialize enrollment."))

	offering = frappe.db.get_value(
		"Program Offering",
		req.program_offering,
		["program", "school"],
		as_dict=True,
	) or {}

	program = req.program or offering.get("program")
	if not program:
		frappe.throw(_("Program is required to materialize enrollment."))

	filters = {
		"student": req.student,
		"program_offering": req.program_offering,
		"academic_year": req.academic_year,
	}
	matches = frappe.get_all("Program Enrollment", filters=filters, fields=["name"], limit=1)

	request_courses = []
	seen = set()
	for row in req.courses or []:
		course = row.course
		if not course or course in seen:
			continue
		seen.add(course)
		request_courses.append(course)
	if not request_courses:
		frappe.throw(_("No courses selected to materialize."))

	if matches:
		enrollment = frappe.get_doc("Program Enrollment", matches[0].name)
		existing_courses = {r.course: r for r in enrollment.courses or []}
		for course in request_courses:
			if course in existing_courses:
				existing_courses[course].status = "Enrolled"
			else:
				enrollment.append("courses", {"course": course, "status": "Enrolled"})
		if (enrollment.enrollment_source or "").strip() == "Request":
			enrollment.program_enrollment_request = req.name
	else:
		enrollment = frappe.get_doc({
			"doctype": "Program Enrollment",
			"student": req.student,
			"program": program,
			"program_offering": req.program_offering,
			"academic_year": req.academic_year,
			"school": req.school or offering.get("school"),
			"enrollment_date": nowdate(),
			"enrollment_source": "Request",
			"program_enrollment_request": req.name,
			"courses": [
				{"course": course, "status": "Enrolled"} for course in request_courses
			],
		})

	frappe.flags.enrollment_from_request = True
	try:
		enrollment.save()
	finally:
		frappe.flags.enrollment_from_request = False
	comment = _("Materialized from Program Enrollment Request {0}.").format(req.name)
	enrollment.add_comment("Comment", comment)
	return enrollment.name


def _validate_request(doc):
	payload = {
		"evaluated_at": now_datetime().isoformat(),
		"program": None,
		"offering": doc.program_offering,
		"grade_scale": None,
		"prerequisites": [],
		"overall_result": "invalid",
	}

	request_rows = [r for r in (doc.courses or []) if r.course]
	if not request_rows:
		return payload, False

	offering = frappe.db.get_value(
		"Program Offering",
		doc.program_offering,
		["program", "seat_policy", "seat_hold_hours"],
		as_dict=True,
	) or {}
	program = doc.program or offering.get("program")
	payload["program"] = program
	if program:
		payload["grade_scale"] = frappe.db.get_value("Program", program, "grade_scale")

	offering_courses = _offering_courses(doc.program_offering)
	offering_map = {r.get("course"): r for r in offering_courses if r.get("course")}

	program_courses = _program_courses(program) if program else []
	program_course_map = {r.get("course"): r for r in program_courses if r.get("course")}

	prereq_rows = _program_prereqs(program)
	status_map = _student_course_statuses(doc.student)
	attempt_map = _student_attempt_counts(doc.student, program) if program else {}
	term_result_cache = {}

	requested_counts = _count_requested_courses(request_rows)
	committed_counts, held_counts = _seat_counts(
		doc.program_offering,
		offering.get("seat_policy") or "Approved Requests Hold Seats",
		int(offering.get("seat_hold_hours") or 24),
		exclude_request=doc.name,
	)

	all_valid = True
	for row in request_rows:
		course = row.course
		offering_row = offering_map.get(course)
		if not offering_row:
			all_valid = False
			payload["prerequisites"].append(_snapshot_entry(
				required_course=course,
				rule="offering_membership",
				required=1,
				achieved=0,
				result="fail",
			))
			continue

		repeat_failures = _repeat_rule_failures(
			course,
			program_course_map.get(course),
			attempt_map.get(course, 0),
			requested_counts.get(course, 0),
		)
		if repeat_failures:
			all_valid = False
			for failure in repeat_failures:
				payload["prerequisites"].append(_snapshot_entry_from_repeat_failure(failure))

		prereq_ok, prereq_groups, _prereq_failures = _evaluate_prereqs(
			course=course,
			apply_to_level=row.apply_to_level,
			prereq_rows=prereq_rows,
			status_map=status_map,
			term_result_cache=term_result_cache,
			student=doc.student,
		)
		for group in prereq_groups:
			for requirement in group.get("requirements") or []:
				payload["prerequisites"].append(_snapshot_entry_from_prereq(requirement))
		if not prereq_ok:
			all_valid = False

		seat_status, seat_failure = _seat_status_for_course(
			offering_row,
			requested_counts.get(course, 0),
			committed_counts.get(course, 0),
			held_counts.get(course, 0),
		)
		if seat_failure:
			all_valid = False
			payload["prerequisites"].append(_snapshot_entry_from_capacity(course, seat_failure))

	basket_valid, _basket_details = evaluate_basket_rules(
		doc.program_offering,
		request_rows,
		program_course_map,
	)
	if not basket_valid:
		all_valid = False
		payload["prerequisites"].append(_snapshot_entry(
			required_course="BASKET",
			rule="basket_valid",
			required=1,
			achieved=0,
			result="fail",
		))

	payload["overall_result"] = "valid" if all_valid else "invalid"
	return payload, all_valid


@frappe.whitelist()
def evaluate_basket_rules(program_offering, request_courses, program_course_map=None):
	rules = frappe.get_all(
		"Program Offering Enrollment Rule",
		filters={"parent": program_offering, "parenttype": "Program Offering"},
		fields=["rule_type", "int_value_1", "int_value_2", "course_group", "level", "notes"],
		order_by="idx asc",
	)

	details = []
	if not rules:
		return True, details

	if program_course_map is None:
		program = frappe.db.get_value("Program Offering", program_offering, "program")
		program_course_map = {r.get("course"): r for r in _program_courses(program)} if program else {}

	courses = []
	for row in request_courses:
		if isinstance(row, str):
			courses.append(row)
			continue
		if isinstance(row, dict):
			course = row.get("course")
		else:
			course = getattr(row, "course", None)
		if course:
			courses.append(course)
	total_courses = len(courses)

	for rule in rules:
		rule_type = rule.get("rule_type")
		passed = True
		actual = None
		expected = None
		message = None

		if rule_type == "MIN_TOTAL_COURSES":
			expected = int(rule.get("int_value_1") or 0)
			actual = total_courses
			passed = actual >= expected
		elif rule_type == "MAX_TOTAL_COURSES":
			expected = int(rule.get("int_value_1") or 0)
			actual = total_courses
			passed = actual <= expected
		elif rule_type == "MIN_LEVEL_COUNT":
			expected = int(rule.get("int_value_1") or 0)
			level = (rule.get("level") or "").strip()
			actual = 0
			if level:
				for course in courses:
					if (program_course_map.get(course, {}) or {}).get("level") == level:
						actual += 1
				passed = actual >= expected
			else:
				passed = False
				message = "Level is required for MIN_LEVEL_COUNT."
		elif rule_type == "REQUIRE_GROUP_COVERAGE":
			group = rule.get("course_group")
			actual = 0
			if group:
				for course in courses:
					if (program_course_map.get(course, {}) or {}).get("category") == group:
						actual += 1
				passed = actual > 0
			else:
				passed = False
				message = "Course Group is required for REQUIRE_GROUP_COVERAGE."
		else:
			passed = False
			message = f"Unknown rule type: {rule_type}."

		details.append({
			"rule_type": rule_type,
			"passed": passed,
			"expected": expected,
			"actual": actual,
			"course_group": rule.get("course_group"),
			"level": rule.get("level"),
			"notes": rule.get("notes"),
			"message": message,
		})

	valid = all(r["passed"] for r in details)
	return valid, details


def _offering_courses(program_offering):
	return frappe.get_all(
		"Program Offering Course",
		filters={"parent": program_offering, "parenttype": "Program Offering"},
		fields=[
			"course",
			"capacity",
			"waitlist_enabled",
			"reserved_seats",
		],
		order_by="idx asc",
	)


def _program_courses(program):
	return frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		fields=["course", "repeatable", "max_attempts", "level", "category"],
		order_by="idx asc",
	)


def _program_prereqs(program):
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
			"grade_scale_used",
		],
		order_by="idx asc",
	)


def _student_course_statuses(student):
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


def _student_attempt_counts(student, program):
	if not student or not program:
		return {}

	rows = frappe.db.sql(
		"""
		SELECT
			pec.course AS course,
			COUNT(pec.name) AS total
		FROM `tabProgram Enrollment Course` pec
		JOIN `tabProgram Enrollment` pe
			ON pe.name = pec.parent
		WHERE pe.student = %s
			AND pe.program = %s
			AND IFNULL(pec.course, '') != ''
			AND IFNULL(pec.status, '') != 'Dropped'
		GROUP BY pec.course
		""",
		(student, program),
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


def _evaluate_prereqs(course, apply_to_level, prereq_rows, status_map, term_result_cache, student):
	relevant = [
		r for r in prereq_rows
		if r.get("apply_to_course") == course and _level_matches(r.get("apply_to_level"), apply_to_level)
	]
	if not relevant:
		return True, [], []

	grouped = {}
	for row in relevant:
		group = int(row.get("prereq_group") or 1)
		grouped.setdefault(group, []).append(row)

	group_results = []
	failures = []
	any_pass = False

	for group, rows in sorted(grouped.items(), key=lambda item: item[0]):
		requirements = []
		group_pass = True
		for row in rows:
			passed, detail = _evaluate_prereq_row(row, status_map, term_result_cache, student)
			requirements.append(detail)
			if not passed:
				group_pass = False
				failures.append(detail)
		group_results.append({
			"group": group,
			"passed": group_pass,
			"requirements": requirements,
		})
		if group_pass:
			any_pass = True

	if any_pass:
		return True, group_results, []
	return False, group_results, failures


def _evaluate_prereq_row(row, status_map, term_result_cache, student):
	# Option B: concurrency enforcement deferred; ignore concurrency_ok for now.
	required_course = row.get("required_course")
	min_numeric_score = row.get("min_numeric_score")
	if min_numeric_score is not None:
		min_numeric_score = float(min_numeric_score)

	result = {
		"type": "prerequisite",
		"required_course": required_course,
		"min_numeric_score": min_numeric_score,
		"grade_scale_used": row.get("grade_scale_used"),
		"course_status": None,
		"numeric_score": None,
		"term": None,
		"reporting_cycle": None,
		"passed": False,
		"note": None,
	}

	if not required_course:
		result["note"] = "Missing required course configuration."
		return False, result

	statuses = status_map.get(required_course, set())
	result["course_status"] = sorted(statuses)

	if min_numeric_score is None:
		eligible_statuses = {"Completed"}
		if not statuses.intersection(eligible_statuses):
			result["note"] = "No eligible enrollment found for required course."
			return False, result
		result["passed"] = True
		return True, result

	term_result = _best_course_term_result(student, required_course, term_result_cache)
	if not term_result or term_result.get("numeric_score") is None:
		result["note"] = "No term result / numeric score found"
		return False, result

	numeric_score = float(term_result.get("numeric_score"))
	result["numeric_score"] = numeric_score
	result["term"] = term_result.get("term")
	result["reporting_cycle"] = term_result.get("reporting_cycle")

	if numeric_score >= min_numeric_score:
		result["passed"] = True
		return True, result

	result["note"] = "Numeric score below prerequisite threshold."
	return False, result


def _best_course_term_result(student, required_course, term_result_cache):
	cache_key = (student, required_course)
	if cache_key in term_result_cache:
		return term_result_cache[cache_key]

	# Temporary Phase 2 rule: prefer override results, else most recent by term end date / modified.
	rows = frappe.db.sql(
		"""
		SELECT
			ctr.name,
			ctr.numeric_score,
			ctr.is_override,
			ctr.term,
			ctr.reporting_cycle,
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


def _repeat_rule_failures(course, program_course, attempts, requested_count):
	if not program_course:
		return []

	repeatable = int(program_course.get("repeatable") or 0) == 1
	max_attempts = program_course.get("max_attempts")
	failures = []

	if not repeatable and attempts > 0:
		failures.append({
			"type": "repeat_rule",
			"course": course,
			"repeatable": False,
			"attempts": attempts,
			"message": "Course is not repeatable.",
		})
		return failures

	if not repeatable and requested_count > 1:
		failures.append({
			"type": "repeat_rule",
			"course": course,
			"repeatable": False,
			"attempts": attempts,
			"message": "Course is not repeatable.",
		})
		return failures

	if max_attempts:
		max_attempts = int(max_attempts)
		if attempts + requested_count > max_attempts:
			failures.append({
				"type": "repeat_rule",
				"course": course,
				"repeatable": repeatable,
				"attempts": attempts,
				"max_attempts": max_attempts,
				"message": "Maximum attempts exceeded.",
			})

	return failures


def _seat_counts(program_offering, seat_policy, seat_hold_hours, exclude_request=None):
	committed = _committed_seats(program_offering)
	if seat_policy == "Committed Only":
		return committed, {}

	if seat_policy == "Approved Requests Hold Seats":
		held = _request_seats(
			program_offering,
			statuses=("Approved",),
			exclude_request=exclude_request,
		)
		return committed, held

	if seat_policy == "Submitted Holds Seats":
		since = add_to_date(now_datetime(), hours=-int(seat_hold_hours or 0))
		held = _request_seats(
			program_offering,
			statuses=("Submitted", "Under Review", "Approved"),
			exclude_request=exclude_request,
			since=since,
		)
		return committed, held

	return committed, {}


def _committed_seats(program_offering):
	rows = frappe.db.sql(
		"""
		SELECT
			pec.course AS course,
			COUNT(pec.name) AS total
		FROM `tabProgram Enrollment Course` pec
		JOIN `tabProgram Enrollment` pe
			ON pe.name = pec.parent
		WHERE pe.program_offering = %s
			AND IFNULL(pec.course, '') != ''
			AND IFNULL(pec.status, '') != 'Dropped'
		GROUP BY pec.course
		""",
		(program_offering,),
		as_dict=True,
	)

	counts = {}
	for row in rows:
		course = row.get("course")
		if not course:
			continue
		counts[course] = int(row.get("total") or 0)
	return counts


def _request_seats(program_offering, statuses, exclude_request=None, since=None):
	conditions = ["per.program_offering = %(program_offering)s", "per.status in %(statuses)s"]
	params = {"program_offering": program_offering, "statuses": statuses}

	if exclude_request:
		conditions.append("per.name != %(exclude_request)s")
		params["exclude_request"] = exclude_request

	if since:
		conditions.append("COALESCE(per.submitted_on, per.modified, per.creation) >= %(since)s")
		params["since"] = since

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
			AND IFNULL(perc.course, '') != ''
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


def _seat_status_for_course(offering_row, requested_count, committed, held):
	capacity = offering_row.get("capacity")
	if capacity is None:
		return "available", None

	capacity = int(capacity or 0)
	used = committed + held
	needed = used + int(requested_count or 0)

	if needed <= capacity:
		return "available", None

	waitlist_enabled = int(offering_row.get("waitlist_enabled") or 0) == 1
	seat_status = "waitlist" if waitlist_enabled else "full"

	failure = {
		"type": "capacity",
		"capacity": capacity,
		"committed": committed,
		"held": held,
		"requested": int(requested_count or 0),
		"message": "Capacity exceeded.",
	}
	return seat_status, failure


def _snapshot_entry(required_course, rule, required, achieved, result):
	return {
		"required_course": required_course,
		"rule": rule,
		"required": required,
		"achieved": achieved,
		"result": result,
	}


def _snapshot_entry_from_prereq(requirement):
	required_course = requirement.get("required_course")
	required = requirement.get("min_numeric_score")
	achieved = requirement.get("numeric_score")
	rule = ">= min_numeric_score"
	if required is None:
		rule = "completion_required"
	result = "pass" if requirement.get("passed") else "fail"
	return _snapshot_entry(required_course, rule, required, achieved, result)


def _snapshot_entry_from_repeat_failure(failure):
	course = failure.get("course")
	attempts = failure.get("attempts")
	max_attempts = failure.get("max_attempts")
	if max_attempts:
		return _snapshot_entry(
			course,
			"attempts <= max_attempts",
			max_attempts,
			attempts,
			"fail",
		)

	repeatable = int(failure.get("repeatable") or 0)
	return _snapshot_entry(course, "repeatable", 1, repeatable, "fail")


def _snapshot_entry_from_capacity(course, seat_failure):
	required = seat_failure.get("capacity")
	achieved = (
		int(seat_failure.get("committed") or 0)
		+ int(seat_failure.get("held") or 0)
		+ int(seat_failure.get("requested") or 0)
	)
	return _snapshot_entry(course, "capacity_available", required, achieved, "fail")


def _assert_no_catalog_prereqs():
	meta = frappe.get_meta("Course")
	if not meta:
		return
	if meta.has_field("prerequisites"):
		frappe.throw(_("Catalog-level prerequisites are not supported. Use program-scoped prerequisites."))
	assert not meta.has_field("prerequisites")
