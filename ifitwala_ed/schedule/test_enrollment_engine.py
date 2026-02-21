# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.schedule.enrollment_engine import evaluate_enrollment_request


class TestEnrollmentEngine(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_meets_prereq_numeric_score(self):
        context = _setup_context(score=75)

        result = evaluate_enrollment_request(
            {
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "requested_courses": [context["target_course"].name],
            }
        )

        course_result = _find_course(result, context["target_course"].name)
        self.assertTrue(course_result["eligible"])

    def test_fails_prereq_override(self):
        context = _setup_context(score=60)

        result = evaluate_enrollment_request(
            {
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "requested_courses": [context["target_course"].name],
            }
        )

        course_result = _find_course(result, context["target_course"].name)
        self.assertFalse(course_result["eligible"])
        self.assertTrue(course_result["override_required"])

    def test_repeat_blocked_not_repeatable(self):
        context = _setup_context(score=85, repeatable=0)
        _make_enrollment(
            context["student"],
            context["program"],
            context["offering"],
            context["academic_year"],
            [{"course": context["target_course"].name, "status": "Completed"}],
        )

        result = evaluate_enrollment_request(
            {
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "requested_courses": [context["target_course"].name],
            }
        )

        course_result = _find_course(result, context["target_course"].name)
        self.assertFalse(course_result["eligible"])
        self.assertTrue(course_result["override_required"])

    def test_capacity_full_committed(self):
        context = _setup_context(score=85, capacity=1)
        other_student = _make_student("Capacity")
        _make_enrollment(
            other_student,
            context["program"],
            context["offering"],
            context["academic_year"],
            [{"course": context["target_course"].name, "status": "Enrolled"}],
        )

        result = evaluate_enrollment_request(
            {
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "requested_courses": [context["target_course"].name],
                "capacity_policy": "committed_only",
            }
        )

        course_result = _find_course(result, context["target_course"].name)
        self.assertEqual(course_result["capacity"]["status"], "full")
        self.assertFalse(course_result["eligible"])

    def test_concurrency_ignored(self):
        context = _setup_context(score=None, concurrency_ok=1, include_result=False, include_history=False)

        result = evaluate_enrollment_request(
            {
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "requested_courses": [
                    context["target_course"].name,
                    context["required_course"].name,
                ],
            }
        )

        course_result = _find_course(result, context["target_course"].name)
        self.assertFalse(course_result["eligible"])
        self.assertTrue(course_result["override_required"])

    def test_request_source_requires_flag(self):
        context = _setup_context(score=80, include_history=False)
        request = _make_enrollment_request(context, status="Approved")

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Program Enrollment",
                    "student": context["student"].name,
                    "program": context["program"].name,
                    "program_offering": context["offering"].name,
                    "academic_year": context["academic_year"].name,
                    "enrollment_date": nowdate(),
                    "enrollment_source": "Request",
                    "program_enrollment_request": request.name,
                }
            ).insert()

        frappe.flags.enrollment_from_request = True
        try:
            frappe.get_doc(
                {
                    "doctype": "Program Enrollment",
                    "student": context["student"].name,
                    "program": context["program"].name,
                    "program_offering": context["offering"].name,
                    "academic_year": context["academic_year"].name,
                    "enrollment_date": nowdate(),
                    "enrollment_source": "Request",
                    "program_enrollment_request": request.name,
                }
            ).insert()
        finally:
            frappe.flags.enrollment_from_request = False

    def test_enrollment_source_immutable(self):
        context = _setup_context(score=80, include_history=False)
        enrollment = _make_enrollment(
            context["student"],
            context["program"],
            context["offering"],
            context["academic_year"],
            [{"course": context["target_course"].name, "status": "Enrolled"}],
        )

        enrollment.enrollment_source = "Admin"
        enrollment.enrollment_override_reason = "Override for test"
        with self.assertRaises(frappe.ValidationError):
            enrollment.save()


def _find_course(result, course):
    for row in result["results"]["courses"]:
        if row["course"] == course:
            return row
    return None


def _setup_context(
    score,
    capacity=None,
    repeatable=1,
    concurrency_ok=0,
    include_result=True,
    include_history=True,
):
    grade_scale = _make_grade_scale()
    organization = _make_organization()
    school = _make_school(organization)
    academic_year = _make_academic_year(school)
    term = _make_term(academic_year)
    student = _make_student("Student")
    required_course = _make_course("Required")
    target_course = _make_course("Target")

    program = _make_program(
        grade_scale,
        target_course,
        required_course,
        repeatable=repeatable,
        concurrency_ok=concurrency_ok,
    )
    offering = _make_offering(program, school, academic_year, target_course, required_course, capacity=capacity)

    if include_history:
        _make_enrollment(
            student,
            program,
            offering,
            academic_year,
            [{"course": required_course.name, "status": "Completed"}],
        )

    if include_result and score is not None:
        _make_course_term_result(
            student,
            required_course,
            program,
            academic_year,
            term,
            grade_scale,
            score,
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


def _make_program(grade_scale, target_course, required_course, repeatable=1, concurrency_ok=0):
    program = frappe.get_doc(
        {
            "doctype": "Program",
            "program_name": f"Program {frappe.generate_hash(length=6)}",
            "grade_scale": grade_scale.name,
            "courses": [
                {
                    "course": target_course.name,
                    "level": "None",
                    "repeatable": repeatable,
                },
                {
                    "course": required_course.name,
                    "level": "None",
                    "repeatable": 1,
                },
            ],
            "prerequisites": [
                {
                    "apply_to_course": target_course.name,
                    "required_course": required_course.name,
                    "min_grade": "B-",
                    "concurrency_ok": concurrency_ok,
                }
            ],
        }
    ).insert()
    return program


def _make_offering(program, school, academic_year, target_course, required_course, capacity=None):
    offering = frappe.get_doc(
        {
            "doctype": "Program Offering",
            "program": program.name,
            "school": school.name,
            "offering_title": f"Offering {frappe.generate_hash(length=6)}",
            "offering_academic_years": [{"academic_year": academic_year.name}],
            "enrollment_rules": [{"rule_type": "MIN_TOTAL_COURSES", "int_value_1": 1}],
            "offering_courses": [
                {
                    "course": target_course.name,
                    "course_name": target_course.course_name,
                    "start_academic_year": academic_year.name,
                    "end_academic_year": academic_year.name,
                    "capacity": capacity,
                },
                {
                    "course": required_course.name,
                    "course_name": required_course.course_name,
                    "start_academic_year": academic_year.name,
                    "end_academic_year": academic_year.name,
                },
            ],
        }
    ).insert()
    return offering


def _make_enrollment(student, program, offering, academic_year, course_rows):
    enrollment_name = frappe.db.get_value(
        "Program Enrollment",
        {
            "student": student.name,
            "program_offering": offering.name,
            "academic_year": academic_year.name,
        },
    )
    if enrollment_name:
        enrollment = frappe.get_doc("Program Enrollment", enrollment_name)
    else:
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
    for row in course_rows:
        enrollment.append("courses", row)
    enrollment.save()
    return enrollment


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


def _make_enrollment_request(context, status="Approved"):
    request = frappe.get_doc(
        {
            "doctype": "Program Enrollment Request",
            "student": context["student"].name,
            "program_offering": context["offering"].name,
            "academic_year": context["academic_year"].name,
            "status": "Draft",
            "courses": [{"course": context["target_course"].name}],
        }
    )
    request.insert()
    if status != "Draft":
        from ifitwala_ed.schedule.doctype.program_enrollment_request.program_enrollment_request import (
            validate_enrollment_request,
        )

        validate_enrollment_request(request.name)
        request.db_set("status", status, update_modified=False)
        request.reload()
    return request
