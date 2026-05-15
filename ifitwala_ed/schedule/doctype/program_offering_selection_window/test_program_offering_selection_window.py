# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.doctype.program_enrollment_request.test_program_enrollment_request import (
    _make_basket_group,
    _make_course,
    _make_grade_scale,
    _make_organization,
    _make_school,
    _make_student,
)


class TestProgramOfferingSelectionWindow(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_window_prepares_and_links_requests(self):
        context = _build_self_enrollment_context()
        window = context["window"]

        window.load_students()
        summary = window.prepare_requests()
        window.reload()

        self.assertEqual(summary["counts"]["created_requests"], 1)
        self.assertEqual(len(window.students), 1)
        self.assertTrue(window.students[0].program_enrollment_request)

        request = frappe.get_doc("Program Enrollment Request", window.students[0].program_enrollment_request)
        self.assertEqual(request.selection_window, window.name)
        self.assertEqual(request.status, "Draft")
        self.assertEqual(
            {row.course for row in request.courses},
            {context["required_course"].name, context["optional_course"].name},
        )

        response = window.open_window()
        window.reload()
        self.assertEqual(response["status"], "Open")
        self.assertEqual(window.status, "Open")
        self.assertTrue(bool(window.open_from))

    def test_prepare_requests_skips_students_already_enrolled_in_target(self):
        context = _build_self_enrollment_context()
        window = context["window"]
        source_enrollment = context["source_enrollment"]
        source_enrollment.archived = 1
        source_enrollment.save()

        frappe.get_doc(
            {
                "doctype": "Program Enrollment",
                "student": context["student"].name,
                "program": context["target_offering"].program,
                "program_offering": context["target_offering"].name,
                "academic_year": context["target_ay"].name,
                "enrollment_date": context["target_ay"].year_start_date,
                "enrollment_source": "Migration",
                "enrollment_override_reason": "Already enrolled target setup",
            }
        ).insert()

        window.load_students()
        summary = window.prepare_requests()
        window.reload()

        self.assertEqual(summary["counts"]["already_enrolled"], 1)
        self.assertEqual(len(window.students), 0)


def _build_self_enrollment_context(*, carry_forward_optional: bool = True, audience: str = "Guardian") -> dict:
    grade_scale = _make_grade_scale()
    organization = _make_organization()
    school = _make_school(organization)
    source_ay = _make_academic_year(school.name, "2025-08-01", "2026-06-30")
    target_ay = _make_academic_year(school.name, "2026-08-01", "2027-06-30")
    _make_term(source_ay.name, "2025-08-01", "2026-06-30")
    _make_term(target_ay.name, "2026-08-01", "2027-06-30")
    student = _make_student("Selection")
    basket_group = _make_basket_group("Language Group")
    required_course = _make_course("Core")
    optional_course = _make_course("Language")

    program = frappe.get_doc(
        {
            "doctype": "Program",
            "program_name": f"Program {frappe.generate_hash(length=6)}",
            "program_slug": f"program-{frappe.generate_hash(length=8)}",
            "grade_scale": grade_scale.name,
            "courses": [
                {"course": required_course.name, "level": "None", "required": 1},
                {"course": optional_course.name, "level": "None", "required": 0},
            ],
        }
    ).insert()

    source_offering = _make_offering(
        program=program.name,
        school=school.name,
        academic_year=source_ay.name,
        required_course=required_course.name,
        optional_course=optional_course.name,
        basket_group=basket_group.name,
        allow_self_enroll=1,
    )
    target_offering = _make_offering(
        program=program.name,
        school=school.name,
        academic_year=target_ay.name,
        required_course=required_course.name,
        optional_course=optional_course.name,
        basket_group=basket_group.name,
        allow_self_enroll=1,
    )

    source_enrollment = frappe.get_doc(
        {
            "doctype": "Program Enrollment",
            "student": student.name,
            "program": program.name,
            "program_offering": source_offering.name,
            "academic_year": source_ay.name,
            "enrollment_date": source_ay.year_start_date,
            "enrollment_source": "Migration",
            "enrollment_override_reason": "Selection window test setup",
        }
    ).insert()
    if carry_forward_optional:
        source_enrollment.append(
            "courses",
            {
                "course": optional_course.name,
                "status": "Enrolled",
                "credited_basket_group": basket_group.name,
            },
        )
        source_enrollment.save()

    window = frappe.get_doc(
        {
            "doctype": "Program Offering Selection Window",
            "program_offering": target_offering.name,
            "academic_year": target_ay.name,
            "audience": audience,
            "status": "Draft",
            "source_mode": "Program Enrollment",
            "source_program_offering": source_offering.name,
            "source_academic_year": source_ay.name,
        }
    ).insert()

    return {
        "student": student,
        "school": school,
        "source_ay": source_ay,
        "target_ay": target_ay,
        "required_course": required_course,
        "optional_course": optional_course,
        "basket_group": basket_group,
        "source_offering": source_offering,
        "target_offering": target_offering,
        "window": window,
        "source_enrollment": source_enrollment,
    }


def _make_academic_year(school, start_date, end_date):
    return frappe.get_doc(
        {
            "doctype": "Academic Year",
            "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
            "school": school,
            "year_start_date": start_date,
            "year_end_date": end_date,
            "archived": 0,
            "visible_to_admission": 1,
        }
    ).insert()


def _make_term(academic_year, start_date, end_date):
    return frappe.get_doc(
        {
            "doctype": "Term",
            "academic_year": academic_year,
            "term_name": f"Term {frappe.generate_hash(length=6)}",
            "term_type": "Academic",
            "term_start_date": start_date,
            "term_end_date": end_date,
        }
    ).insert()


def _make_offering(program, school, academic_year, required_course, optional_course, basket_group, allow_self_enroll):
    return frappe.get_doc(
        {
            "doctype": "Program Offering",
            "program": program,
            "school": school,
            "offering_title": f"Offering {frappe.generate_hash(length=6)}",
            "allow_self_enroll": allow_self_enroll,
            "offering_academic_years": [{"academic_year": academic_year}],
            "offering_courses": [
                {
                    "course": required_course,
                    "required": 1,
                    "start_academic_year": academic_year,
                    "end_academic_year": academic_year,
                    "capacity": 30,
                },
                {
                    "course": optional_course,
                    "required": 0,
                    "start_academic_year": academic_year,
                    "end_academic_year": academic_year,
                    "capacity": 30,
                },
            ],
            "offering_course_basket_groups": [{"course": optional_course, "basket_group": basket_group}],
            "enrollment_rules": [
                {"rule_type": "MIN_TOTAL_COURSES", "int_value_1": 1},
                # Portal choice-state tests rely on this fixture requiring one optional
                # selection from the configured basket group.
                {"rule_type": "REQUIRE_GROUP_COVERAGE", "basket_group": basket_group},
            ],
        }
    ).insert()
