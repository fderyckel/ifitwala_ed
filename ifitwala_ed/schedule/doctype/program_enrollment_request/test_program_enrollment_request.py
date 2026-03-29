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

    def test_request_autofills_single_offering_academic_year(self):
        context = _setup_enrollment_context(score=95)

        request = frappe.get_doc(
            {
                "doctype": "Program Enrollment Request",
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "courses": [{"course": context["target_course"].name}],
            }
        ).insert()

        self.assertEqual(request.academic_year, context["academic_year"].name)
        self.assertEqual(request.program, context["program"].name)
        self.assertEqual(request.school, context["school"].name)

    def test_request_rejects_academic_year_outside_offering(self):
        context = _setup_enrollment_context(score=95)
        outside_ay = _make_academic_year(
            context["school"],
            start_date="2027-08-01",
            end_date="2028-06-30",
        )

        request = frappe.get_doc(
            {
                "doctype": "Program Enrollment Request",
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "academic_year": outside_ay.name,
                "courses": [{"course": context["target_course"].name}],
            }
        )

        with self.assertRaises(frappe.ValidationError):
            request.insert()

    def test_request_requires_explicit_academic_year_for_multi_year_offering(self):
        context = _setup_enrollment_context(score=95)
        second_ay = _make_academic_year(
            context["school"],
            start_date="2026-08-01",
            end_date="2027-06-30",
        )
        context["offering"].append("offering_academic_years", {"academic_year": second_ay.name})
        context["offering"].save()

        request = frappe.get_doc(
            {
                "doctype": "Program Enrollment Request",
                "student": context["student"].name,
                "program_offering": context["offering"].name,
                "courses": [{"course": context["target_course"].name}],
            }
        )

        with self.assertRaises(frappe.ValidationError):
            request.insert()

    def test_validate_request_prereq_pass(self):
        context = _setup_enrollment_context(score=95)
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

    def test_submitted_request_requires_explicit_basket_group_for_multi_group_course(self):
        humanities_group = _make_basket_group("Group 3 Humanities")
        sciences_group = _make_basket_group("Group 4 Sciences")
        context = _setup_enrollment_context(
            score=95,
            target_basket_groups=[humanities_group.name, sciences_group.name],
            offering_basket_groups=[humanities_group.name, sciences_group.name],
        )
        request = _make_enrollment_request(
            context,
            student=context["student"],
            course=context["target_course"],
        )

        request.status = "Submitted"
        with self.assertRaises(frappe.ValidationError):
            request.save()

        request.reload()
        request.status = "Submitted"
        request.courses[0].applied_basket_group = humanities_group.name
        request.save()
        request.reload()

        self.assertEqual(request.validation_status, "Valid")
        self.assertEqual(request.courses[0].applied_basket_group, humanities_group.name)

    def test_materialize_request_updates_enrollment(self):
        basket_group = _make_basket_group("Sciences")
        context = _setup_enrollment_context(
            score=95,
            create_existing_enrollment=False,
            target_basket_groups=[basket_group.name],
            offering_basket_groups=[basket_group.name],
        )
        for row in context["offering"].offering_courses:
            if row.course == context["target_course"].name:
                row.start_academic_term = context["term"].name
                row.end_academic_term = context["term"].name
        context["offering"].save()
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
        courses = {row.course: row for row in enrollment.courses}
        self.assertIn(context["target_course"].name, courses)
        self.assertEqual(courses[context["target_course"].name].status, "Enrolled")
        self.assertEqual(courses[context["target_course"].name].credited_basket_group, basket_group.name)
        self.assertEqual(int(courses[context["target_course"].name].required or 0), 0)
        self.assertEqual(courses[context["target_course"].name].term_start, context["term"].name)
        self.assertEqual(courses[context["target_course"].name].term_end, context["term"].name)


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
    capacity=30,
    seat_policy=None,
    enrollment_rules=None,
    program_course_level=None,
    target_basket_groups=None,
    offering_basket_groups=None,
    create_existing_enrollment=True,
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
            "program_slug": f"program-{frappe.generate_hash(length=8)}",
            "grade_scale": grade_scale.name,
            "courses": [
                {
                    "course": target_course.name,
                    "level": program_course_level or "None",
                },
                {
                    "course": required_course.name,
                    "level": "None",
                },
            ],
            "course_basket_groups": [
                {"course": target_course.name, "basket_group": basket_group}
                for basket_group in (target_basket_groups or [])
            ],
            "prerequisites": [
                {
                    "apply_to_course": target_course.name,
                    "apply_to_level": program_course_level or "None",
                    "required_course": required_course.name,
                    "min_grade": "B-",
                    "grade_scale_used": grade_scale.name,
                    "min_numeric_score": 70,
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
                "required": 0,
                "start_academic_year": academic_year.name,
                "end_academic_year": academic_year.name,
            },
        ],
        "offering_course_basket_groups": [
            {"course": target_course.name, "basket_group": basket_group}
            for basket_group in (offering_basket_groups or target_basket_groups or [])
        ],
    }
    if seat_policy:
        data["seat_policy"] = seat_policy
    if enrollment_rules:
        data["enrollment_rules"] = enrollment_rules
    else:
        data["enrollment_rules"] = [{"rule_type": "MIN_TOTAL_COURSES", "int_value_1": 1}]
    offering = frappe.get_doc(data).insert()

    if create_existing_enrollment:
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


def _make_enrollment_request(context, student, course, status="Draft", applied_basket_group=None):
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
                    "applied_basket_group": applied_basket_group,
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


def _make_academic_year(school, start_date="2025-08-01", end_date="2026-06-30"):
    academic_year = frappe.get_doc(
        {
            "doctype": "Academic Year",
            "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
            "school": school.name,
            "year_start_date": start_date,
            "year_end_date": end_date,
            "archived": 0,
            "visible_to_admission": 1,
        }
    )
    academic_year.insert()
    return academic_year


def _make_term(academic_year):
    school = academic_year.school or frappe.db.get_value("Academic Year", academic_year.name, "school")
    term = frappe.get_doc(
        {
            "doctype": "Term",
            "academic_year": academic_year.name,
            "school": school,
            "term_name": f"Term {frappe.generate_hash(length=6)}",
            "term_type": "Academic",
            "term_start_date": nowdate(),
            "term_end_date": nowdate(),
        }
    )
    term.insert()
    if school:
        frappe.db.set_value("Term", term.name, "school", school, update_modified=False)
        term.reload()
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


def _make_basket_group(label):
    basket_group = frappe.get_doc(
        {
            "doctype": "Basket Group",
            "basket_group_name": f"{label} {frappe.generate_hash(length=6)}",
        }
    )
    basket_group.insert()
    return basket_group


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
