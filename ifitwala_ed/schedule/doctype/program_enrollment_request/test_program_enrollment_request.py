# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.schedule.doctype.program_enrollment_request.program_enrollment_request import (
    validate_enrollment_request,
)
from ifitwala_ed.schedule.enrollment_request_utils import materialize_program_enrollment_request


class TestProgramEnrollmentRequest(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_validate_request_prereq_pass(self):
        context = _setup_enrollment_context(score=75)
        request = _make_enrollment_request(
            context,
            student=context["student"],
            course=context["target_course"],
        )

        payload = validate_enrollment_request(request.name)
        request.reload()

        self.assertEqual(request.validation_status, "Valid")
        self.assertTrue(bool((payload.get("summary") or {}).get("valid")))
        self.assertTrue(_has_prereq_result(payload, context["required_course"].name, "pass"))

    def test_validate_request_prereq_fail(self):
        context = _setup_enrollment_context(score=60)
        request = _make_enrollment_request(
            context,
            student=context["student"],
            course=context["target_course"],
        )

        payload = validate_enrollment_request(request.name)
        request.reload()

        self.assertEqual(request.validation_status, "Invalid")
        self.assertFalse(bool((payload.get("summary") or {}).get("valid")))
        self.assertTrue(_has_prereq_result(payload, context["required_course"].name, "fail"))

    def test_validate_request_capacity_exceeded(self):
        context = _setup_enrollment_context(
            score=85,
            capacity=1,
            seat_policy="Approved Requests Hold Seats",
        )
        student_two = _make_student("Capacity")

        _make_enrollment_request(
            context,
            student=context["student"],
            course=context["target_course"],
            status="Approved",
        )
        second_request = _make_enrollment_request(
            context,
            student=student_two,
            course=context["target_course"],
        )

        payload = validate_enrollment_request(second_request.name)
        second_request.reload()

        self.assertEqual(second_request.validation_status, "Invalid")
        self.assertFalse(bool((payload.get("summary") or {}).get("valid")))
        self.assertTrue(_has_rule_result(payload, context["target_course"].name, "capacity_available", "fail"))

    def test_validate_request_basket_rules(self):
        rules = [
            {"rule_type": "MIN_TOTAL_COURSES", "int_value_1": 2},
            {"rule_type": "MIN_LEVEL_COUNT", "int_value_1": 1, "level": "Higher Level"},
        ]
        context = _setup_enrollment_context(
            score=80,
            enrollment_rules=rules,
            program_course_level="Higher Level",
        )
        request = _make_enrollment_request(
            context,
            student=context["student"],
            course=context["target_course"],
        )

        payload = validate_enrollment_request(request.name)
        request.reload()

        self.assertEqual(request.validation_status, "Invalid")
        self.assertFalse(bool((payload.get("summary") or {}).get("valid")))
        self.assertTrue(_has_rule_result(payload, "BASKET", "basket_valid", "fail"))

    def test_materialize_request_updates_enrollment(self):
        context = _setup_enrollment_context(score=85)
        request = _make_enrollment_request(
            context,
            student=context["student"],
            course=context["target_course"],
            status="Approved",
        )

        enrollment_name = materialize_program_enrollment_request(request.name)
        materialize_program_enrollment_request(request.name)

        count = frappe.db.count(
            "Program Enrollment",
            {
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "academic_year": context["academic_year"].name,
            },
        )
        self.assertEqual(count, 1)

        enrollment = frappe.get_doc("Program Enrollment", enrollment_name)
        courses = {row.course: row.status for row in enrollment.courses}
        self.assertIn(context["target_course"].name, courses)
        self.assertEqual(courses[context["target_course"].name], "Enrolled")


def _has_prereq_result(payload, required_course, result):
    course_rows = (payload.get("results") or {}).get("courses") or []
    if result == "fail":
        for entry in course_rows:
            reasons = entry.get("reasons") or []
            if any(required_course in str(reason or "") for reason in reasons):
                return True
        return False
    if result == "pass":
        for entry in course_rows:
            reasons = entry.get("reasons") or []
            if any(required_course in str(reason or "") for reason in reasons):
                return False
        return True
    return False


def _has_rule_result(payload, required_course, rule, result):
    if rule == "capacity_available":
        for entry in (payload.get("results") or {}).get("courses") or []:
            if entry.get("course") != required_course:
                continue
            status = ((entry.get("capacity") or {}).get("status") or "").strip()
            if result == "fail" and status == "full":
                return True
            if result == "pass" and status != "full":
                return True
    if rule == "basket_valid":
        basket_status = (((payload.get("results") or {}).get("basket") or {}).get("status") or "").strip()
        if result == "fail" and basket_status == "invalid":
            return True
        if result == "pass" and basket_status in {"ok", "valid"}:
            return True
    return False


def _setup_enrollment_context(
    score,
    capacity=None,
    seat_policy=None,
    enrollment_rules=None,
    program_course_level=None,
    program_course_category=None,
):
    grade_scale = _make_grade_scale()
    organization = _make_organization()
    school = _make_school(organization)
    academic_year = _make_academic_year(school)
    term = _make_term(academic_year)
    student = _make_student("Prereq")
    required_course = _make_course("Required")
    target_course = _make_course("Target")

    program = frappe.get_doc(
        {
            "doctype": "Program",
            "program_name": f"Program {frappe.generate_hash(length=6)}",
            "grade_scale": grade_scale.name,
            "courses": [
                {
                    "course": target_course.name,
                    "level": program_course_level or "None",
                    "category": program_course_category,
                },
                {
                    "course": required_course.name,
                    "level": "None",
                },
            ],
            "prerequisites": [
                {
                    "apply_to_course": target_course.name,
                    "required_course": required_course.name,
                    "min_grade": "B-",
                }
            ],
        }
    ).insert()

    offering_course = {
        "course": target_course.name,
        "course_name": target_course.course_name,
        "start_academic_year": academic_year.name,
        "end_academic_year": academic_year.name,
        "capacity": capacity,
    }
    data = {
        "doctype": "Program Offering",
        "program": program.name,
        "school": school.name,
        "offering_title": f"Offering {frappe.generate_hash(length=6)}",
        "offering_academic_years": [{"academic_year": academic_year.name}],
        "offering_courses": [
            offering_course,
            {
                "course": required_course.name,
                "course_name": required_course.course_name,
                "start_academic_year": academic_year.name,
                "end_academic_year": academic_year.name,
            },
        ],
    }
    if seat_policy:
        data["seat_policy"] = seat_policy
    if enrollment_rules:
        data["enrollment_rules"] = enrollment_rules
    else:
        data["enrollment_rules"] = [{"rule_type": "MIN_TOTAL_COURSES", "int_value_1": 1}]
    offering = frappe.get_doc(data).insert()

    enrollment = frappe.get_doc(
        {
            "doctype": "Program Enrollment",
            "student": student.name,
            "program": program.name,
            "program_offering": offering.name,
            "academic_year": academic_year.name,
            "enrollment_date": nowdate(),
            "enrollment_source": "Migration",
            "enrollment_override_reason": "Test setup",
        }
    ).insert()
    enrollment.append("courses", {"course": required_course.name, "status": "Completed"})
    enrollment.save()

    _make_course_term_result(
        student=student,
        course=required_course,
        program=program,
        academic_year=academic_year,
        term=term,
        grade_scale=grade_scale,
        score=score,
    )

    return {
        "grade_scale": grade_scale,
        "organization": organization,
        "school": school,
        "academic_year": academic_year,
        "term": term,
        "student": student,
        "required_course": required_course,
        "target_course": target_course,
        "program": program,
        "offering": offering,
    }


def _make_enrollment_request(context, student, course, status="Draft"):
    request = frappe.get_doc(
        {
            "doctype": "Program Enrollment Request",
            "student": student.name,
            "program_offering": context["offering"].name,
            "academic_year": context["academic_year"].name,
            "status": "Draft",
            "courses": [
                {
                    "course": course.name,
                    "apply_to_level": "None",
                }
            ],
        }
    )
    request.insert()
    if status != "Draft":
        validate_enrollment_request(request.name)
        request.db_set("status", status, update_modified=False)
        request.reload()
    return request


def _make_grade_scale():
    grade_scale = frappe.get_doc(
        {
            "doctype": "Grade Scale",
            "grade_scale_name": f"Scale {frappe.generate_hash(length=6)}",
            "boundaries": [
                {"grade_code": "B-", "boundary_interval": 70},
                {"grade_code": "C", "boundary_interval": 60},
            ],
        }
    )
    grade_scale.insert()
    return grade_scale


def _make_organization():
    organization = frappe.get_doc(
        {
            "doctype": "Organization",
            "organization_name": f"Org {frappe.generate_hash(length=6)}",
            "abbr": f"ORG{frappe.generate_hash(length=4)}",
        }
    )
    organization.insert()
    return organization


def _make_school(organization):
    school = frappe.get_doc(
        {
            "doctype": "School",
            "school_name": f"School {frappe.generate_hash(length=6)}",
            "abbr": f"S{frappe.generate_hash(length=4)}",
            "organization": organization.name,
        }
    )
    school.insert()
    return school


def _make_academic_year(school):
    academic_year = frappe.get_doc(
        {
            "doctype": "Academic Year",
            "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
            "school": school.name,
            "year_start_date": "2025-08-01",
            "year_end_date": "2026-06-30",
            "archived": 0,
            "visible_to_admission": 1,
        }
    )
    academic_year.insert()
    return academic_year


def _make_term(academic_year):
    term = frappe.get_doc(
        {
            "doctype": "Term",
            "academic_year": academic_year.name,
            "term_name": f"Term {frappe.generate_hash(length=6)}",
            "term_type": "Academic",
            "term_start_date": nowdate(),
            "term_end_date": nowdate(),
        }
    )
    term.insert()
    return term


def _make_student(prefix):
    student = frappe.get_doc(
        {
            "doctype": "Student",
            "student_first_name": prefix,
            "student_last_name": f"Test {frappe.generate_hash(length=6)}",
            "student_email": f"{frappe.generate_hash(length=8)}@example.com",
        }
    )
    previous_in_migration = bool(getattr(frappe.flags, "in_migration", False))
    frappe.flags.in_migration = True
    try:
        student.insert()
    finally:
        frappe.flags.in_migration = previous_in_migration
    return student


def _make_course(label):
    course = frappe.get_doc(
        {
            "doctype": "Course",
            "course_name": f"{label} {frappe.generate_hash(length=6)}",
            "status": "Active",
        }
    )
    course.insert()
    return course


def _make_course_term_result(student, course, program, academic_year, term, grade_scale, score):
    result = frappe.get_doc(
        {
            "doctype": "Course Term Result",
            "student": student.name,
            "course": course.name,
            "program": program.name,
            "academic_year": academic_year.name,
            "term": term.name,
            "grade_scale": grade_scale.name,
            "numeric_score": score,
        }
    )
    result.insert()
    return result
