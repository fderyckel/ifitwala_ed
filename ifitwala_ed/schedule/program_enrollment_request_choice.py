# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import re
from collections import defaultdict

import frappe
from frappe import _

from ifitwala_ed.schedule.basket_group_utils import get_offering_course_semantics
from ifitwala_ed.schedule.enrollment_engine import (
    _evaluate_basket,
    _evaluate_capacity,
    _evaluate_prerequisites,
    _evaluate_repeat_attempts,
    _get_capacity_counts,
    _get_prerequisite_rows,
    _get_program_courses,
    _get_student_course_history,
    _get_student_results,
    evaluate_basket_selection,
)
from ifitwala_ed.schedule.enrollment_request_utils import (
    _assert_no_catalog_prereqs,
    _map_offering_seat_policy_to_capacity_policy,
    build_program_enrollment_request_validation,
)

GROUP_NAME_PATTERN = re.compile(r"'([^']+)'")


def _normalize_choice_rank(value) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    try:
        rank = int(text)
    except (TypeError, ValueError):
        frappe.throw(_("Choice Rank must be a positive whole number."))

    if rank == 0:
        return None
    if rank < 0:
        frappe.throw(_("Choice Rank must be a positive whole number."))
    return rank


def _normalize_rows(rows) -> list[dict]:
    normalized = []
    seen = set()

    for row in rows or []:
        course = (getattr(row, "course", None) or (row or {}).get("course") or "").strip()
        if not course or course in seen:
            continue
        seen.add(course)
        normalized.append(
            {
                "course": course,
                "required": 1 if int(getattr(row, "required", None) or (row or {}).get("required") or 0) == 1 else 0,
                "applied_basket_group": (
                    getattr(row, "applied_basket_group", None) or (row or {}).get("applied_basket_group") or ""
                ).strip(),
                "choice_rank": _normalize_choice_rank(
                    getattr(row, "choice_rank", None) if hasattr(row, "choice_rank") else (row or {}).get("choice_rank")
                ),
            }
        )

    return normalized


def _required_offering_basket_groups(program_offering: str) -> list[str]:
    if not program_offering:
        return []

    rows = frappe.get_all(
        "Program Offering Enrollment Rule",
        filters={
            "parent": program_offering,
            "parenttype": "Program Offering",
            "rule_type": "REQUIRE_GROUP_COVERAGE",
        },
        fields=["basket_group"],
        order_by="idx asc",
    )

    output = []
    seen = set()
    for row in rows or []:
        basket_group = (row.get("basket_group") or "").strip()
        if not basket_group or basket_group in seen:
            continue
        seen.add(basket_group)
        output.append(basket_group)
    return output


def _extract_group_name(message: str | None) -> str | None:
    text = str(message or "").strip()
    if not text:
        return None
    match = GROUP_NAME_PATTERN.search(text)
    if not match:
        return None
    return (match.group(1) or "").strip() or None


def _format_choice_validation_message(message: str | None) -> str | None:
    text = str(message or "").strip()
    if not text:
        return None

    if text == "Missing required courses in basket.":
        return _("Add every required course before you submit.")

    if text == "One or more selected courses must be assigned to a basket group before validation can pass.":
        return _("Choose which section each selected course should count toward before you submit.")

    if text.startswith("Basket must include at least one course from group"):
        group_name = _extract_group_name(text)
        if group_name:
            return _("Choose at least one course in {group}.").format(group=group_name)
        return _("Choose at least one course in this section.")

    return text


def _format_choice_validation_violation(violation) -> str | None:
    if isinstance(violation, str):
        return _format_choice_validation_message(violation)

    payload = violation or {}
    code = (payload.get("code") or "").strip()
    message = payload.get("message")

    if code == "missing_required":
        return _("Add every required course before you submit.")

    if code == "ambiguous_basket_group":
        return _("Choose which section each selected course should count toward before you submit.")

    if code == "require_group_coverage":
        group_name = _extract_group_name(message)
        if group_name:
            return _("Choose at least one course in {group}.").format(group=group_name)
        return _("Choose at least one course in this section.")

    return _format_choice_validation_message(message)


def _choice_validation_messages(basket_result: dict) -> list[str]:
    messages: list[str] = []
    seen: set[str] = set()

    for raw_violation in list(basket_result.get("violations") or []):
        message = _format_choice_validation_violation(raw_violation)
        if not message or message in seen:
            continue
        seen.add(message)
        messages.append(message)

    for raw_reason in list(basket_result.get("reasons") or []):
        message = _format_choice_validation_message(raw_reason)
        if not message or message in seen:
            continue
        seen.add(message)
        messages.append(message)

    if not messages and list(basket_result.get("missing_required_courses") or []):
        messages.append(_("Add every required course before you submit."))

    if not messages and (basket_result.get("status") or "").strip() == "invalid":
        messages.append(_("Please review the course choices above before you submit."))

    return messages


def _format_course_validation_message(*, course_label: str, message: str | None) -> str | None:
    text = str(message or "").strip()
    if not text:
        return None

    if text == "Course is not part of the Program Offering.":
        return _(
            "{course} is no longer part of this selection window. Please refresh and review the choices again."
        ).format(course=course_label)

    if text == "Prerequisite requirements not met.":
        return _(
            "The school needs to review whether {course} can be selected based on previous course requirements."
        ).format(course=course_label)

    if text == "Rule not supported by current schema.":
        return _("The school needs to review whether {course} can be selected.").format(course=course_label)

    if text.startswith("Required course ") and text.endswith(" not completed."):
        return _(
            "The school needs to review whether {course} can be selected based on previous course requirements."
        ).format(course=course_label)

    if text.startswith("No numeric score evidence for "):
        return _(
            "The school needs to review whether {course} can be selected based on previous course requirements."
        ).format(course=course_label)

    if text.startswith("Required ") and " score " in text and "; got " in text:
        return _(
            "The school needs to review whether {course} can be selected based on previous course requirements."
        ).format(course=course_label)

    if text == "Course already completed and not repeatable.":
        return _("{course} has already been completed and cannot be selected again.").format(course=course_label)

    if text == "Maximum attempts exceeded.":
        return _(
            "{course} cannot be selected again because the maximum number of attempts has already been used."
        ).format(course=course_label)

    return text


def _course_validation_messages(engine_payload: dict, offering_semantics: dict[str, dict]) -> list[str]:
    messages: list[str] = []
    seen: set[str] = set()
    capacity_full_courses: list[str] = []

    for row in list(((engine_payload.get("results") or {}).get("courses") or [])):
        if not row.get("blocked"):
            continue

        course = (row.get("course") or "").strip()
        semantics = offering_semantics.get(course) or {}
        course_label = (semantics.get("course_name") or "").strip() or course
        raw_reasons = [
            str(reason or "").strip() for reason in list(row.get("reasons") or []) if str(reason or "").strip()
        ]

        if any(reason == "Capacity full for this course." for reason in raw_reasons):
            if course_label and course_label not in capacity_full_courses:
                capacity_full_courses.append(course_label)

        for raw_reason in raw_reasons:
            if raw_reason == "Capacity full for this course.":
                continue
            message = _format_course_validation_message(course_label=course_label, message=raw_reason)
            if not message or message in seen:
                continue
            seen.add(message)
            messages.append(message)

    if capacity_full_courses:
        if len(capacity_full_courses) == 1:
            message = _(
                "No places are available in {course} right now. Please contact the school if this selection still needs review."
            ).format(course=capacity_full_courses[0])
        else:
            message = _(
                "Some selected courses are not available right now because no places are available in this offering. Please contact the school if this selection still needs review."
            )
        if message not in seen:
            seen.add(message)
            messages.insert(0, message)

    return messages


def _summarize_live_validation(
    engine_payload: dict, *, offering_semantics: dict[str, dict]
) -> tuple[str | None, bool, list[str]]:
    summary = engine_payload.get("summary") or {}
    basket_result = (engine_payload.get("results") or {}).get("basket") or {}
    basket_status = (summary.get("basket_status") or basket_result.get("status") or "").strip() or None
    course_blocked = any(
        bool(row.get("blocked")) for row in list(((engine_payload.get("results") or {}).get("courses") or []))
    )

    ready_for_submit = not course_blocked and basket_status in {"ok", "valid", "not_configured"}
    live_status = basket_status
    if course_blocked or basket_status == "invalid":
        live_status = "invalid"

    messages = _choice_validation_messages(basket_result)
    messages.extend(_course_validation_messages(engine_payload, offering_semantics))

    deduped_messages: list[str] = []
    seen: set[str] = set()
    for message in messages:
        normalized = str(message or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped_messages.append(normalized)

    return live_status, ready_for_submit, deduped_messages


def _live_validation_state(request, *, offering_semantics: dict[str, dict]) -> tuple[dict, str | None, bool, list[str]]:
    engine_payload, _updates = build_program_enrollment_request_validation(request, force=1)
    live_status, ready_for_submit, deduped_messages = _summarize_live_validation(
        engine_payload,
        offering_semantics=offering_semantics,
    )
    return engine_payload, live_status, ready_for_submit, deduped_messages


def _live_validation_batch_context(requests, offering_semantics_by_offering: dict[str, dict]) -> dict:
    draft_requests = [
        request
        for request in requests or []
        if (request.get("request_status") or "").strip() == "Draft"
        and (request.get("name") or "").strip()
        and (request.get("student") or "").strip()
        and (request.get("program_offering") or "").strip()
    ]
    if not draft_requests:
        return {
            "offering_meta": {},
            "offering_rules": {},
            "program_courses": {},
            "capacity_context": {},
            "student_history": {},
            "student_results": {},
            "prerequisite_rows": {},
        }

    offering_names = sorted({(request.get("program_offering") or "").strip() for request in draft_requests})
    offering_rows = frappe.get_all(
        "Program Offering",
        filters={"name": ("in", offering_names)},
        fields=["name", "program", "seat_policy"],
    )
    offering_meta = {row.get("name"): row for row in offering_rows if row.get("name")}

    rule_rows = frappe.get_all(
        "Program Offering Enrollment Rule",
        filters={"parent": ("in", offering_names), "parenttype": "Program Offering"},
        fields=["parent", "idx", "rule_type", "int_value_1", "int_value_2", "basket_group", "level", "notes"],
        order_by="parent asc, idx asc",
    )
    offering_rules = defaultdict(list)
    for row in rule_rows or []:
        parent = (row.get("parent") or "").strip()
        if not parent:
            continue
        offering_rules[parent].append(row)

    student_names = sorted({(request.get("student") or "").strip() for request in draft_requests})
    student_history = {student: _get_student_course_history(student) for student in student_names}
    student_results = {student: _get_student_results(student) for student in student_names}

    program_names = sorted(
        {(meta.get("program") or "").strip() for meta in offering_meta.values() if (meta.get("program") or "").strip()}
    )
    program_courses = {program: _get_program_courses(program) for program in program_names}

    prerequisite_keys = set()
    for request in draft_requests:
        offering_name = (request.get("program_offering") or "").strip()
        program = (offering_meta.get(offering_name) or {}).get("program")
        if not program:
            continue

        offering_semantics = offering_semantics_by_offering.setdefault(
            offering_name,
            get_offering_course_semantics(offering_name),
        )
        for row in _normalize_rows(request.get("courses") or []):
            course = row.get("course")
            if course and course in offering_semantics:
                prerequisite_keys.add((program, course))

    prerequisite_rows = {
        key: _get_prerequisite_rows(key[0], key[1]) for key in sorted(prerequisite_keys, key=lambda item: item)
    }

    capacity_context = {}
    for offering_name in offering_names:
        offering_semantics_by_offering.setdefault(
            offering_name,
            get_offering_course_semantics(offering_name),
        )
        seat_policy = (offering_meta.get(offering_name) or {}).get("seat_policy")
        capacity_policy = _map_offering_seat_policy_to_capacity_policy(seat_policy)
        counts, policy_used, policy_unavailable = _get_capacity_counts(offering_name, capacity_policy)
        capacity_context[offering_name] = {
            "counts": counts,
            "policy": policy_used,
            "policy_unavailable": policy_unavailable,
        }

    return {
        "offering_meta": offering_meta,
        "offering_rules": dict(offering_rules),
        "program_courses": program_courses,
        "capacity_context": capacity_context,
        "student_history": student_history,
        "student_results": student_results,
        "prerequisite_rows": prerequisite_rows,
    }


def _build_live_validation_engine_payload(
    request,
    *,
    offering_semantics: dict[str, dict],
    batch_context: dict,
) -> dict:
    explicit_rows = _normalize_rows(request.get("courses") or [])
    if not explicit_rows:
        frappe.throw(_("No courses selected to validate."))

    offering_name = (request.get("program_offering") or "").strip()
    student = (request.get("student") or "").strip()
    if not offering_name or not student:
        frappe.throw(_("Program Offering and Student are required to validate live course choices."))

    offering_meta = batch_context["offering_meta"].get(offering_name) or {}
    program = (offering_meta.get("program") or "").strip()
    requested_courses = [row["course"] for row in explicit_rows if row.get("course")]
    requested_row_map = {row["course"]: row for row in explicit_rows if row.get("course")}
    student_history = batch_context["student_history"].get(student) or {}
    student_results = batch_context["student_results"].get(student) or {}
    program_courses = batch_context["program_courses"].get(program) or {}
    capacity_context = batch_context["capacity_context"].get(offering_name) or {}
    capacity_counts = capacity_context.get("counts") or {}
    policy_used = capacity_context.get("policy") or "committed_only"
    policy_unavailable = bool(capacity_context.get("policy_unavailable"))

    course_results = []
    any_course_blocked = False
    any_course_override_required = False

    for course in requested_courses:
        course_row = offering_semantics.get(course)
        requested_row = requested_row_map.get(course) or {}
        reasons = []
        evidence = []
        blocked = False
        override_required = False

        if not course_row:
            blocked = True
            reasons.append("Course is not part of the Program Offering.")
            capacity_result = {
                "capacity": None,
                "counted": None,
                "remaining": None,
                "status": "unknown",
                "policy": policy_used,
            }
            if policy_unavailable:
                capacity_result["policy_unavailable"] = True
        else:
            prereq_rows = batch_context["prerequisite_rows"].get((program, course), [])
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
                requested_count=1,
            )
            reasons.extend(repeat_result.get("reasons") or [])
            if not repeat_result.get("eligible"):
                blocked = True
                override_required = True

            capacity_result = _evaluate_capacity(
                course,
                course_row,
                capacity_counts,
                requested_count=1,
                policy=policy_used,
                policy_unavailable=policy_unavailable,
            )
            if capacity_result.get("status") == "full":
                blocked = True
                override_required = True
                reasons.append("Capacity full for this course.")

        if blocked:
            any_course_blocked = True
        if override_required:
            any_course_override_required = True

        course_results.append(
            {
                "course": course,
                "applied_basket_group": requested_row.get("applied_basket_group") or "",
                "basket_groups": list((course_row or {}).get("basket_groups") or []),
                "eligible": not blocked,
                "blocked": blocked,
                "override_required": override_required,
                "reasons": reasons,
                "evidence": evidence,
                "capacity": capacity_result,
                "requested_count": 1,
            }
        )

    basket_result = _evaluate_basket(
        explicit_rows,
        offering_semantics,
        {
            "program_offering": offering_name,
            "program_courses": program_courses,
        },
        rule_rows=batch_context["offering_rules"].get(offering_name, []),
    )

    basket_status = (basket_result.get("status") or "").strip()
    basket_override_required = bool(basket_result.get("override_required"))
    basket_invalid = basket_status == "invalid"
    basket_pass = basket_status in {"ok", "valid"}
    basket_not_configured = basket_status == "not_configured"

    overall_blocked = bool(any_course_blocked or basket_invalid)
    overall_valid = bool((not any_course_blocked) and basket_pass)
    overall_override_required = bool(any_course_override_required or basket_override_required)

    return {
        "student": student,
        "program_offering": offering_name,
        "requested_courses": requested_courses,
        "requested_rows": explicit_rows,
        "requested_counts": {course: 1 for course in requested_courses},
        "summary": {
            "valid": bool(overall_valid),
            "blocked": bool(overall_blocked),
            "override_required": bool(overall_override_required),
            "basket_status": basket_status,
            "basket_not_configured": bool(basket_not_configured),
        },
        "results": {
            "courses": course_results,
            "basket": basket_result,
        },
    }


def get_program_enrollment_request_live_choice_states(requests) -> dict[str, dict]:
    draft_requests = [
        request
        for request in requests or []
        if (request.get("name") or "").strip() and (request.get("request_status") or "").strip() == "Draft"
    ]
    if not draft_requests:
        return {}

    _assert_no_catalog_prereqs()

    offering_semantics_by_offering: dict[str, dict] = {}
    batch_context = _live_validation_batch_context(draft_requests, offering_semantics_by_offering)
    live_choice_states: dict[str, dict] = {}

    for request in draft_requests:
        request_name = (request.get("name") or "").strip()
        offering_name = (request.get("program_offering") or "").strip()
        offering_semantics = offering_semantics_by_offering.get(offering_name) or {}

        try:
            engine_payload = _build_live_validation_engine_payload(
                request,
                offering_semantics=offering_semantics,
                batch_context=batch_context,
            )
            _live_status, ready_for_submit, reasons = _summarize_live_validation(
                engine_payload,
                offering_semantics=offering_semantics,
            )
        except Exception as exc:
            message = str(exc or "").strip() or _(
                "The current course choices still need attention before this request can be submitted."
            )
            live_choice_states[request_name] = {
                "ready_for_submit": False,
                "reasons": [message],
            }
            continue

        live_choice_states[request_name] = {
            "ready_for_submit": bool(ready_for_submit),
            "reasons": list(reasons or []),
        }

    return live_choice_states


def get_effective_program_enrollment_request_rows(
    request,
    *,
    offering_semantics: dict[str, dict] | None = None,
) -> list[dict]:
    explicit_rows = _normalize_rows(request.get("courses") or [])
    if offering_semantics is None:
        offering_semantics = get_offering_course_semantics((request.program_offering or "").strip())
    effective_rows = []
    seen = set()

    for row in explicit_rows:
        course = row.get("course")
        if not course or course in seen:
            continue
        if offering_semantics and course not in offering_semantics:
            continue
        seen.add(course)

        semantics = offering_semantics.get(course) or {}
        effective_rows.append(
            {
                "course": course,
                "required": 1 if semantics.get("required") else 0,
                "applied_basket_group": (row.get("applied_basket_group") or "").strip(),
                "choice_rank": _normalize_choice_rank(row.get("choice_rank")),
            }
        )

    for course, semantics in offering_semantics.items():
        if not semantics.get("required") or course in seen:
            continue
        effective_rows.append(
            {
                "course": course,
                "required": 1,
                "applied_basket_group": "",
                "choice_rank": None,
            }
        )

    return effective_rows


def get_program_enrollment_request_choice_state(
    request,
    *,
    can_edit: bool,
    offering_semantics: dict[str, dict] | None = None,
    required_basket_groups: list[str] | None = None,
) -> dict:
    offering_name = (request.program_offering or "").strip()
    if offering_semantics is None:
        offering_semantics = get_offering_course_semantics(offering_name) if offering_name else {}
    explicit_rows = _normalize_rows(request.get("courses") or [])
    explicit_by_course = {row["course"]: row for row in explicit_rows}
    effective_rows = get_effective_program_enrollment_request_rows(request, offering_semantics=offering_semantics)
    effective_by_course = {row["course"]: row for row in effective_rows}
    if required_basket_groups is None:
        required_basket_groups = _required_offering_basket_groups(offering_name)
    basket_result = (
        evaluate_basket_selection(program_offering=offering_name, requested_courses=effective_rows)
        if offering_name
        else {
            "status": None,
            "override_required": False,
            "reasons": [],
            "violations": [],
            "missing_required_courses": [],
            "ambiguous_courses": [],
            "group_summary": {},
        }
    )
    engine_payload = {"summary": {}, "results": {"courses": [], "basket": basket_result}}
    live_status = (basket_result.get("status") or "").strip() or None
    ready_for_submit = live_status in {"ok", "not_configured"}
    validation_messages = _choice_validation_messages(basket_result)

    if offering_name and request.get("student"):
        engine_payload, live_status, ready_for_submit, validation_messages = _live_validation_state(
            request,
            offering_semantics=offering_semantics,
        )
        basket_result = ((engine_payload.get("results") or {}).get("basket") or {}) or basket_result

    courses = []
    required_count = 0
    optional_count = 0
    selected_optional_count = 0

    for course, semantics in offering_semantics.items():
        effective_row = effective_by_course.get(course) or {}
        basket_groups = list(semantics.get("basket_groups") or [])
        required = bool(semantics.get("required"))
        is_selected = required or course in explicit_by_course
        applied_basket_group = (effective_row.get("applied_basket_group") or "").strip()
        choice_rank = effective_row.get("choice_rank")

        if required:
            required_count += 1
        else:
            optional_count += 1
            if course in explicit_by_course:
                selected_optional_count += 1

        courses.append(
            {
                "course": course,
                "course_name": (semantics.get("course_name") or "").strip() or course,
                "required": required,
                "basket_groups": basket_groups,
                "applied_basket_group": applied_basket_group or None,
                "choice_rank": choice_rank,
                "is_selected": bool(is_selected),
                "requires_basket_group_selection": bool(
                    is_selected and len(basket_groups) > 1 and not applied_basket_group
                ),
                "is_explicit_choice": bool(course in explicit_by_course),
                "has_choice_rank": choice_rank is not None,
            }
        )

    request_status = (request.status or "").strip() or "Draft"

    return {
        "request": {
            "name": request.name,
            "status": request_status,
            "academic_year": (request.academic_year or "").strip(),
            "program": (request.program or "").strip(),
            "program_offering": offering_name,
            "validation_status": (request.validation_status or "").strip() or "Not Validated",
            "submitted_on": request.submitted_on,
            "submitted_by": (request.submitted_by or "").strip() or None,
            "can_edit_choices": bool(can_edit),
            "can_submit_choices": bool(can_edit),
        },
        "summary": {
            "has_request": True,
            "has_courses": bool(courses),
            "has_selectable_courses": any(not bool(row.get("required")) for row in courses),
            "can_edit_choices": bool(can_edit),
            "ready_for_submit": ready_for_submit,
            "required_course_count": required_count,
            "optional_course_count": optional_count,
            "selected_optional_count": selected_optional_count,
        },
        "validation": {
            "status": live_status,
            "ready_for_submit": ready_for_submit,
            "reasons": validation_messages,
            "violations": [],
            "missing_required_courses": list(basket_result.get("missing_required_courses") or []),
            "ambiguous_courses": list(basket_result.get("ambiguous_courses") or []),
            "group_summary": dict(basket_result.get("group_summary") or {}),
        },
        "required_basket_groups": required_basket_groups,
        "courses": courses,
    }


def store_program_enrollment_request_choices(request, *, courses: list[dict] | None = None) -> None:
    if not request.program_offering:
        frappe.throw(_("Program Offering is required before course choices can be updated."))

    submitted_rows = _normalize_rows(courses or [])
    submitted_by_course = {row["course"]: row for row in submitted_rows}
    offering_semantics = get_offering_course_semantics(request.program_offering)
    allowed_courses = set(offering_semantics.keys())
    unknown_courses = sorted(course for course in submitted_by_course if course not in allowed_courses)
    if unknown_courses:
        frappe.throw(
            _("One or more selected courses are not part of this Program Offering: {courses}.").format(
                courses=", ".join(unknown_courses)
            )
        )

    current_rows = _normalize_rows(request.get("courses") or [])
    current_by_course = {row["course"]: row for row in current_rows}
    rows_to_store = []

    for course, semantics in offering_semantics.items():
        current = current_by_course.get(course) or {}
        submitted = submitted_by_course.get(course) or {}
        if semantics.get("required"):
            rows_to_store.append(
                {
                    "course": course,
                    "required": 1,
                    "applied_basket_group": (
                        submitted.get("applied_basket_group") or current.get("applied_basket_group") or ""
                    ),
                    "choice_rank": submitted.get("choice_rank")
                    if "choice_rank" in submitted
                    else current.get("choice_rank"),
                }
            )
            continue

        if not submitted:
            continue

        rows_to_store.append(
            {
                "course": course,
                "required": 0,
                "applied_basket_group": submitted.get("applied_basket_group") or "",
                "choice_rank": submitted.get("choice_rank"),
            }
        )

    request.set("courses", rows_to_store)
    request.validation_status = "Not Validated"
    request.validation_payload = None
    request.validated_on = None
    request.validated_by = None
    request.requires_override = 0
