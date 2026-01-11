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

	# Normalize + count requested courses once (prevents duplicate row inflation)
	# - requested_counts is the only source of "requested_count"
	# - unique_courses is stable order (first occurrence wins)
	requested_counts = {}
	unique_courses = []
	seen = set()

	for course in requested_courses:
		c = (course or "").strip()
		if not c:
			continue
		requested_counts[c] = requested_counts.get(c, 0) + 1
		if c in seen:
			continue
		seen.add(c)
		unique_courses.append(c)

	if not unique_courses:
		frappe.throw(_("requested_courses is required."))

	offering = frappe.db.get_value(
		"Program Offering",
		program_offering,
		["program"],
		as_dict=True,
	) or {}
	program = offering.get("program")

	# Core data fetches (keep DB calls minimal + once)
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
	any_course_blocked = False
	any_course_override_required = False

	for course in unique_courses:
		course_row = offering_courses.get(course)
		reasons = []
		evidence = []
		blocked = False
		override_required = False

		# Stable requested count from normalized input.
		# Important: duplicates must NEVER inflate seat-hold math beyond requested_count,
		# and requested_count must NEVER be derived from list.count() inside loops.
		req_count = int(requested_counts.get(course, 0) or 0)

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
			reasons.extend(prereq_result.get("reasons") or [])
			evidence.extend(prereq_result.get("evidence") or [])
			if not prereq_result.get("eligible"):
				blocked = True
				override_required = True

			repeat_result = _evaluate_repeat_attempts(
				course,
				program_courses.get(course),
				student_history,
				student_results,
				requested_count=req_count,
			)
			reasons.extend(repeat_result.get("reasons") or [])
			if not repeat_result.get("eligible"):
				blocked = True
				override_required = True

			capacity_result = _evaluate_capacity(
				course,
				course_row,
				capacity_counts,
				requested_count=req_count,
				policy=policy_used,
				policy_unavailable=policy_unavailable,
			)
			if capacity_result.get("status") == "full":
				blocked = True
				# Capacity full is a *constraint* failure; override may be allowed later by policy,
				# but for now we treat it as requiring explicit override.
				override_required = True
				reasons.append("Capacity full for this course.")

		eligible = not blocked
		if blocked:
			any_course_blocked = True
		if override_required:
			any_course_override_required = True

		course_results.append({
			"course": course,
			"eligible": eligible,
			"blocked": blocked,
			"override_required": override_required,
			"reasons": reasons,
			"evidence": evidence,
			"capacity": capacity_result,
			# Preserve raw duplication info without changing the canonical requested_courses contract.
			"requested_count": req_count,
		})

	# Basket rules are offering-scoped and can invalidate the entire request.
	basket_result = _evaluate_basket(
		unique_courses,
		offering_courses,
		{
			"program_offering": program_offering,
			"program_courses": program_courses,
		},
	)

	basket_status = (basket_result or {}).get("status")
	basket_invalid = basket_status == "invalid"
	basket_not_configured = basket_status == "not_configured"

	# Locking decision for now:
	# - If basket rules are invalid -> request is blocked and requires override.
	# - If basket rules are not_configured -> do not block; surface as informational.
	any_blocked = any_course_blocked or basket_invalid
	requires_override = any_course_override_required or basket_invalid

	return {
		"student": student,
		"program_offering": program_offering,
		# Canonical output: unique + stable order (first occurrence wins).
		"requested_courses": unique_courses,
		# Optional: preserve raw duplication counts for audit/debug without reintroducing O(n^2).
		"requested_counts": requested_counts,
		"generated_at": now_datetime(),
		"summary": {
			"blocked": bool(any_blocked),
			"override_required": bool(requires_override),
			"basket_not_configured": bool(basket_not_configured),
		},
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
	"""
	Basket rules (Option B - structured child table) evaluation.

	Invariants:
	- Offering-scoped (Program Offering Enrollment Rule child table).
	- Evaluated on Enrollment Requests (basket), independent of per-course prerequisites.
	- Deterministic: given the same inputs + same rule rows, returns the same output.
	- Efficient: 1 DB call for rule rows, no per-rule DB calls.

	Inputs:
	- requested_courses: list of unique course names (engine already de-dupes upstream).
	- offering_course_rows: dict[course] -> Program Offering Course row (required/elective_group metadata).
	- basket_policy: dict with "program_offering" and optionally "program_courses" (future).
	"""

	program_offering = (basket_policy or {}).get("program_offering")
	requested_courses = requested_courses or []
	requested_set = set(requested_courses)

	# 0) Pre-compute required courses + elective group coverage from offering metadata.
	# Keep this deterministic: sort derived lists and never rely on dict iteration order.
	required_courses = []
	group_summary = {}

	for course, row in (offering_course_rows or {}).items():
		c = (course or "").strip()
		if not c:
			continue

		if int((row or {}).get("required") or 0) == 1:
			required_courses.append(c)

		group = ((row or {}).get("elective_group") or "").strip()
		if group:
			group_summary[group] = group_summary.get(group, 0) + (1 if c in requested_set else 0)

	required_courses = sorted(set(required_courses))
	missing_required = [c for c in required_courses if c not in requested_set]

	# 1) Load structured rules (Option B). If none exist, that's a valid configuration state.
	rule_rows = []
	if program_offering:
		rule_rows = frappe.get_all(
			"Program Offering Enrollment Rule",
			filters={"parent": program_offering, "parenttype": "Program Offering"},
			fields=["idx", "rule_type", "int_value_1", "int_value_2", "course_group", "level", "notes"],
			order_by="idx asc",
		)

	# 2) Deterministic accumulators.
	status = "ok"
	reasons = []
	violations = []

	def _violate(code, msg, rule=None):
		nonlocal status
		status = "invalid"
		reasons.append(msg)
		violations.append({
			"code": code,
			"message": msg,
			"rule_type": (rule or {}).get("rule_type"),
			"rule_idx": (rule or {}).get("idx"),
		})

	# 3) Always enforce offering-level required courses first (basket-level constraint).
	if missing_required:
		_violate("missing_required", "Missing required courses in basket.")

	# 4) Evaluate rules (pure, one pass, stable order by idx asc).
	total_courses = len(requested_courses)

	for rule in (rule_rows or []):
		rule_type = ((rule.get("rule_type") or "").strip() or "").upper()

		if rule_type == "MIN_TOTAL_COURSES":
			min_total = int(rule.get("int_value_1") or 0)
			if min_total > 0 and total_courses < min_total:
				_violate("min_total_courses", f"Minimum total courses is {min_total}.", rule)

		elif rule_type == "MAX_TOTAL_COURSES":
			max_total = int(rule.get("int_value_1") or 0)
			if max_total > 0 and total_courses > max_total:
				_violate("max_total_courses", f"Maximum total courses is {max_total}.", rule)

		elif rule_type == "REQUIRE_GROUP_COVERAGE":
			# Uses offering elective_group summary as the lightweight group signal.
			group = ((rule.get("course_group") or "").strip() or "")
			if not group:
				_violate("misconfigured_rule", "Basket rule REQUIRE_GROUP_COVERAGE is misconfigured (course_group is required).", rule)
			else:
				if int(group_summary.get(group, 0) or 0) <= 0:
					_violate("require_group_coverage", f"Basket must include at least one course from group '{group}'.", rule)

		elif rule_type == "MIN_LEVEL_COUNT":
			# Structured-rule-only engine: rule exists but inputs aren't wired yet.
			# Treat as invalid + explicit so staff notice config drift immediately.
			_violate("unsupported_rule", "Basket rule MIN_LEVEL_COUNT is not supported yet (level mapping not provided to engine).", rule)

		elif not rule_type:
			_violate("misconfigured_rule", "Basket rule has an empty rule_type.", rule)

		else:
			_violate("unknown_rule_type", f"Unknown basket rule type: {rule_type}.", rule)

	# 5) If no structured rules exist and we’re otherwise OK, mark explicitly.
	if not rule_rows and status == "ok":
		status = "not_configured"

	# 6) Basket-level override truth (engine may tighten policy later, but PER needs a flag now).
	override_required = (status == "invalid")

	return {
		"status": status,
		"override_required": bool(override_required),
		"reasons": reasons,
		"violations": violations,
		"missing_required_courses": missing_required,
		"group_summary": group_summary,
		"meta": {
			"total_courses": total_courses,
			"rules_evaluated": len(rule_rows or []),
		},
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
	# Count seats held by requests in given statuses, per course.
	# IMPORTANT: do not let duplicate rows in the child table inflate capacity.
	conditions = ["per.program_offering = %(program_offering)s", "per.status in %(statuses)s"]
	params = {"program_offering": program_offering, "statuses": tuple(statuses)}

	if request_id:
		conditions.append("per.name != %(request_id)s")
		params["request_id"] = request_id

	where_clause = " and ".join(conditions)

	# DISTINCT on (request, course) to avoid duplicates inflating capacity.
	rows = frappe.db.sql(
		f"""
		SELECT
			x.course AS course,
			COUNT(*) AS total
		FROM (
			SELECT DISTINCT
				per.name AS request_name,
				perc.course AS course
			FROM `tabProgram Enrollment Request Course` perc
			JOIN `tabProgram Enrollment Request` per
				ON per.name = perc.parent
			WHERE {where_clause}
				AND IFNULL(perc.course, '') != ''
		) x
		GROUP BY x.course
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
