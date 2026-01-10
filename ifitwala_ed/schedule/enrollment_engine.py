# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/schedule/enrollment_engine.py

import frappe
from frappe import _
from frappe.utils import now_datetime


SUPPORTED_CAPACITY_POLICIES = {
	"committed_only",
	"approved_requests",
	"approved_plus_review",
}


def evaluate_enrollment_request(payload):
	student = (payload or {}).get("student")
	program_offering = (payload or {}).get("program_offering")
	requested_courses = (payload or {}).get("requested_courses") or []
	request_id = (payload or {}).get("request_id")
	capacity_policy = (payload or {}).get("capacity_policy") or "committed_only"

	if not student:
		frappe.throw(_("Student is required."))
	if not program_offering:
		frappe.throw(_("Program Offering is required."))
	if not requested_courses:
		frappe.throw(_("requested_courses is required."))

	_assert_no_catalog_prereqs()

	if capacity_policy not in SUPPORTED_CAPACITY_POLICIES:
		frappe.throw(_("Capacity policy '{0}' is not supported.").format(capacity_policy))

	unique_courses = []
	seen = set()
	for course in requested_courses:
		if not course or course in seen:
			continue
		seen.add(course)
		unique_courses.append(course)

	offering = frappe.db.get_value(
		"Program Offering",
		program_offering,
		["program"],
		as_dict=True,
	) or {}
	program = offering.get("program")

	offering_courses = _get_offering_courses(program_offering)
	program_courses = _get_program_courses(program) if program else {}
	student_history = _get_student_course_history(student)
	student_results = _get_student_results(student)

	capacity_counts, policy_used, policy_unavailable = _get_capacity_counts(
		program_offering,
		capacity_policy,
		request_id=request_id,
	)

	course_results = []
	for course in unique_courses:
		course_row = offering_courses.get(course)
		reasons = []
		evidence = []
		blocked = False
		override_required = False

		if not course_row:
			blocked = True
			reasons.append("Course is not part of the Program Offering.")
			capacity_result = _capacity_unknown(policy_used)
		else:
			prereq_rows = _get_prerequisite_rows(program, course)
			prereq_result = _evaluate_prerequisites(
				course,
				prereq_rows,
				student_history,
				student_results,
				course_level=(program_courses.get(course) or {}).get("level"),
			)
			reasons.extend(prereq_result["reasons"])
			evidence.extend(prereq_result["evidence"])
			if not prereq_result["eligible"]:
				blocked = True
				override_required = True

			repeat_result = _evaluate_repeat_attempts(
				course,
				program_courses.get(course),
				student_history,
				student_results,
				requested_count=requested_courses.count(course),
			)
			reasons.extend(repeat_result["reasons"])
			if not repeat_result["eligible"]:
				blocked = True
				override_required = True

			capacity_result = _evaluate_capacity(
				course,
				course_row,
				capacity_counts,
				requested_count=requested_courses.count(course),
				policy=policy_used,
				policy_unavailable=policy_unavailable,
			)
			if capacity_result["status"] == "full":
				blocked = True
				reasons.append("Capacity full for this course.")

		eligible = not blocked

		course_results.append({
			"course": course,
			"eligible": eligible,
			"blocked": blocked,
			"override_required": override_required,
			"reasons": reasons,
			"evidence": evidence,
			"capacity": capacity_result,
		})

	basket_result = _evaluate_basket(
		unique_courses,
		offering_courses,
		{
			"program_offering": program_offering,
			"program_courses": program_courses,
		},
	)

	return {
		"student": student,
		"program_offering": program_offering,
		"requested_courses": unique_courses,
		"generated_at": now_datetime(),
		"results": {
			"courses": course_results,
			"basket": basket_result,
		},
	}


def _get_student_course_history(student):
	rows = frappe.db.sql(
		"""
		SELECT
			pec.course AS course,
			pec.status AS status,
			pe.academic_year AS academic_year,
			pe.program AS program,
			pe.program_offering AS program_offering
		FROM `tabProgram Enrollment Course` pec
		JOIN `tabProgram Enrollment` pe
			ON pe.name = pec.parent
		WHERE pe.student = %s
			AND IFNULL(pec.course, '') != ''
		""",
		(student,),
		as_dict=True,
	)

	history = {}
	for row in rows:
		course = row.get("course")
		if not course:
			continue
		entry = history.setdefault(course, {"statuses": set(), "rows": []})
		status = (row.get("status") or "").strip()
		if status:
			entry["statuses"].add(status)
		entry["rows"].append({
			"status": status,
			"academic_year": row.get("academic_year"),
			"program": row.get("program"),
			"program_offering": row.get("program_offering"),
		})

	return history


def _get_student_results(student):
	rows = frappe.db.get_all(
		"Course Term Result",
		filters={"student": student},
		fields=[
			"course",
			"numeric_score",
			"grade_value",
			"term",
			"reporting_cycle",
			"grade_scale",
			"is_override",
			"modified",
		],
	)

	results = {}
	for row in rows:
		course = row.get("course")
		if not course:
			continue
		results.setdefault(course, []).append(row)

	return results


def _get_offering_courses(program_offering):
	rows = frappe.get_all(
		"Program Offering Course",
		filters={"parent": program_offering, "parenttype": "Program Offering"},
		fields=[
			"course",
			"required",
			"elective_group",
			"start_academic_year",
			"start_academic_term",
			"from_date",
			"end_academic_year",
			"end_academic_term",
			"to_date",
			"capacity",
			"waitlist_enabled",
			"reserved_seats",
		],
	)

	return {row.get("course"): row for row in rows if row.get("course")}


def _get_prerequisite_rows(program, course):
	if not program or not course:
		return []

	rows = frappe.get_all(
		"Program Course Prerequisite",
		filters={
			"parent": program,
			"parenttype": "Program",
			"apply_to_course": course,
		},
		fields=[
			"required_course",
			"min_numeric_score",
			"prereq_group",
			"apply_to_level",
		],
		order_by="idx asc",
	)
	return rows


def _evaluate_prerequisites(course, prereq_rows, student_history, student_results, course_level=None):
	if not prereq_rows:
		return {"eligible": True, "reasons": [], "evidence": []}

	grouped = {}
	for row in prereq_rows:
		if row.get("apply_to_level") and course_level and row.get("apply_to_level") != course_level:
			continue
		group = int(row.get("prereq_group") or 1)
		grouped.setdefault(group, []).append(row)

	if not grouped:
		return {
			"eligible": False,
			"reasons": ["Rule not supported by current schema."],
			"evidence": [],
		}

	any_group_passed = False
	all_reasons = []
	evidence = []

	for group, rows in sorted(grouped.items(), key=lambda item: item[0]):
		group_passed = True
		group_reasons = []
		for row in rows:
			passed, reason, row_evidence = _evaluate_prereq_row(
				row,
				student_history,
				student_results,
			)
			if row_evidence:
				evidence.append(row_evidence)
			if not passed:
				group_passed = False
				group_reasons.append(reason)
		if group_passed:
			any_group_passed = True
			break
		all_reasons.extend(group_reasons)

	if any_group_passed:
		return {"eligible": True, "reasons": [], "evidence": evidence}

	reasons = ["Prerequisite requirements not met."]
	reasons.extend([r for r in all_reasons if r])
	return {"eligible": False, "reasons": reasons, "evidence": evidence}


def _evaluate_prereq_row(row, student_history, student_results):
	# Option B: concurrency enforcement deferred; ignore concurrency_ok for now.
	required_course = row.get("required_course")
	min_numeric_score = row.get("min_numeric_score")

	if not required_course:
		return False, "Rule not supported by current schema.", None

	history = student_history.get(required_course) or {}
	statuses = history.get("statuses") or set()

	if min_numeric_score is None:
		if "Completed" in statuses:
			return True, None, None
		return False, f"Required course {required_course} not completed.", None

	best_attempt = _select_best_attempt(student_results.get(required_course, []))
	if not best_attempt or best_attempt.get("numeric_score") is None:
		return False, f"No numeric score evidence for {required_course}.", None

	threshold = float(min_numeric_score)
	numeric_score = float(best_attempt.get("numeric_score"))
	passed = numeric_score >= threshold
	reason = None
	if not passed:
		reason = f"Required {required_course} score {threshold} or higher; got {numeric_score}."

	evidence = {
		"course": required_course,
		"best_numeric_score": numeric_score,
		"grade_value": best_attempt.get("grade_value"),
		"term": best_attempt.get("term"),
		"reporting_cycle": best_attempt.get("reporting_cycle"),
		"retake_policy_applied": "highest_default_unlocked",
	}

	return passed, reason, evidence


def _evaluate_repeat_attempts(course, program_course_config, student_history, student_results, requested_count):
	if not program_course_config:
		return {"eligible": True, "reasons": []}

	repeatable = int(program_course_config.get("repeatable") or 0) == 1
	max_attempts = program_course_config.get("max_attempts")

	attempts = len(student_results.get(course, []))
	completed = "Completed" in (student_history.get(course, {}).get("statuses") or set())

	reasons = []
	if completed and not repeatable:
		reasons.append("Course already completed and not repeatable.")
		return {"eligible": False, "reasons": reasons}

	if max_attempts:
		max_attempts = int(max_attempts)
		if attempts + int(requested_count or 0) > max_attempts:
			reasons.append("Maximum attempts exceeded.")
			return {"eligible": False, "reasons": reasons}

	return {"eligible": True, "reasons": []}


def _evaluate_capacity(course, offering_course_row, capacity_counts, requested_count, policy, policy_unavailable=False):
	capacity = offering_course_row.get("capacity")
	if capacity is None:
		return _capacity_unknown(policy)

	capacity = int(capacity or 0)
	counted = int(capacity_counts.get(course, 0))
	remaining = capacity - counted
	prospective_total = counted + int(requested_count or 0)

	if prospective_total > capacity:
		status = "full"
	elif remaining <= 2:
		status = "at_risk"
	else:
		status = "ok"

	result = {
		"capacity": capacity,
		"counted": counted,
		"remaining": remaining,
		"status": status,
		"policy": policy,
	}
	if policy_unavailable:
		result["policy_unavailable"] = True
	return result


def _evaluate_basket(requested_courses, offering_course_rows, basket_policy):
	required_courses = []
	group_summary = {}
	for course, row in offering_course_rows.items():
		if int(row.get("required") or 0) == 1:
			required_courses.append(course)
		group = row.get("elective_group")
		if group:
			group_summary[group] = group_summary.get(group, 0) + (1 if course in requested_courses else 0)

	missing_required = [c for c in required_courses if c not in requested_courses]
	reasons = []
	status = "ok"

	if missing_required:
		status = "invalid"
		reasons.append("Missing required courses in basket.")

	program_offering = (basket_policy or {}).get("program_offering")
	rule_rows = []
	if program_offering and frappe.db.table_exists("Program Offering Enrollment Rule"):
		rule_rows = frappe.get_all(
			"Program Offering Enrollment Rule",
			filters={"parent": program_offering, "parenttype": "Program Offering"},
			fields=["rule_type", "int_value_1"],
			order_by="idx asc",
		)

	for rule in rule_rows:
		rule_type = rule.get("rule_type")
		if rule_type == "MIN_TOTAL_COURSES":
			min_total = int(rule.get("int_value_1") or 0)
			if len(requested_courses) < min_total:
				status = "invalid"
				reasons.append(f"Minimum total courses is {min_total}.")
		elif rule_type == "MAX_TOTAL_COURSES":
			max_total = int(rule.get("int_value_1") or 0)
			if len(requested_courses) > max_total:
				status = "invalid"
				reasons.append(f"Maximum total courses is {max_total}.")
		else:
			status = "invalid"
			reasons.append("Rule not supported by current schema.")

	if not rule_rows:
		status = "not_configured" if status == "ok" else status
		reasons.append("TODO: Basket rules not configured beyond required/elective metadata.")

	return {
		"status": status,
		"reasons": reasons,
		"missing_required_courses": missing_required,
		"group_summary": group_summary,
	}


def _get_program_courses(program):
	rows = frappe.get_all(
		"Program Course",
		filters={"parent": program, "parenttype": "Program"},
		fields=["course", "repeatable", "max_attempts", "level", "category"],
	)
	return {row.get("course"): row for row in rows if row.get("course")}


def _select_best_attempt(attempts):
	best = None
	for attempt in attempts:
		score = attempt.get("numeric_score")
		if score is None:
			continue
		if best is None or float(score) > float(best.get("numeric_score")):
			best = attempt
	return best


def _get_capacity_counts(program_offering, policy, request_id=None):
	committed = _count_committed_seats(program_offering)

	if policy == "committed_only":
		return committed, policy, False

	statuses = []
	if policy == "approved_requests":
		statuses = ["Approved"]
	elif policy == "approved_plus_review":
		statuses = ["Approved", "Under Review"]

	if not _request_status_supported(statuses):
		return committed, "committed_only", True

	request_counts = _count_request_seats(program_offering, statuses, request_id=request_id)
	combined = committed.copy()
	for course, count in request_counts.items():
		combined[course] = combined.get(course, 0) + count
	return combined, policy, False


def _request_status_supported(statuses):
	if not statuses:
		return False
	if not frappe.db.table_exists("Program Enrollment Request"):
		return False

	meta = frappe.get_meta("Program Enrollment Request")
	field = meta.get_field("status") if meta else None
	if not field:
		return False

	options = {(opt or "").strip() for opt in (field.options or "").split("\n")}
	return all(status in options for status in statuses)


def _count_committed_seats(program_offering):
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


def _count_request_seats(program_offering, statuses, request_id=None):
	conditions = ["per.program_offering = %(program_offering)s", "per.status in %(statuses)s"]
	params = {"program_offering": program_offering, "statuses": tuple(statuses)}

	if request_id:
		conditions.append("per.name != %(request_id)s")
		params["request_id"] = request_id

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


def _capacity_unknown(policy):
	return {
		"capacity": None,
		"counted": None,
		"remaining": None,
		"status": "unknown",
		"policy": policy,
	}


def _assert_no_catalog_prereqs():
	meta = frappe.get_meta("Course")
	if not meta:
		return
	if meta.has_field("prerequisites"):
		frappe.throw(_("Catalog-level prerequisites are not supported. Use program-scoped prerequisites."))
	assert not meta.has_field("prerequisites")
