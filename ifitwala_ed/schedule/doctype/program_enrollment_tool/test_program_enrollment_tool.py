# Copyright (c) 2024, François de Ryckel and Contributors
# See license.txt

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


class TestProgramEnrollmentTool(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_program_tool_prepares_and_materializes_requests(self):
        context = _build_program_tool_context()

        tool = frappe.get_doc("Program Enrollment Tool")
        tool.get_students_from = "Program Enrollment"
        tool.program_offering = context["source_offering"].name
        tool.target_academic_year = context["source_ay"].name
        tool.new_program_offering = context["target_offering"].name
        tool.new_target_academic_year = context["target_ay"].name
        tool.new_enrollment_date = context["target_ay"].year_start_date

        tool.set("students", tool.get_students())

        prepare_summary = tool.prepare_requests()
        self.assertEqual(prepare_summary["counts"]["created_requests"], 1)
        self.assertEqual(prepare_summary["counts"]["failed"], 0)

        request_name = frappe.db.get_value(
            "Program Enrollment Request",
            {
                "student": context["student"].name,
                "program_offering": context["target_offering"].name,
                "academic_year": context["target_ay"].name,
            },
        )
        request = frappe.get_doc("Program Enrollment Request", request_name)
        self.assertEqual(request.status, "Draft")
        self.assertEqual(
            {row.course for row in request.courses},
            {context["required_course"].name, context["optional_course"].name},
        )

        validate_summary = tool.validate_requests()
        self.assertEqual(validate_summary["counts"]["validated"], 1)
        request.reload()
        self.assertEqual(request.status, "Submitted")
        self.assertEqual(request.validation_status, "Valid")

        approve_summary = tool.approve_requests()
        self.assertEqual(approve_summary["counts"]["approved"], 1)
        request.reload()
        self.assertEqual(request.status, "Approved")

        materialize_summary = tool.materialize_requests()
        self.assertEqual(materialize_summary["counts"]["materialized"], 1)

        enrollment_name = frappe.db.get_value(
            "Program Enrollment",
            {
                "student": context["student"].name,
                "program_offering": context["target_offering"].name,
                "academic_year": context["target_ay"].name,
            },
        )
        enrollment = frappe.get_doc("Program Enrollment", enrollment_name)
        self.assertEqual(enrollment.enrollment_source, "Request")
        self.assertEqual(enrollment.program_enrollment_request, request.name)
        self.assertEqual(
            {row.course for row in enrollment.courses},
            {context["required_course"].name, context["optional_course"].name},
        )


def _build_program_tool_context():
    grade_scale = _make_grade_scale()
    organization = _make_organization()
    school = _make_school(organization)
    source_ay = _make_academic_year(school.name, "2025-08-01", "2026-06-30")
    target_ay = _make_academic_year(school.name, "2026-08-01", "2027-06-30")
    _make_term(source_ay.name, "2025-08-01", "2026-06-30")
    _make_term(target_ay.name, "2026-08-01", "2027-06-30")
    student = _make_student("Rollover")
    basket_group = _make_basket_group("French")
    required_course = _make_course("Core")
    optional_course = _make_course("French")

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
    )
    target_offering = _make_offering(
        program=program.name,
        school=school.name,
        academic_year=target_ay.name,
        required_course=required_course.name,
        optional_course=optional_course.name,
        basket_group=basket_group.name,
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
            "enrollment_override_reason": "Program tool test setup",
        }
    ).insert()
    source_enrollment.append(
        "courses",
        {
            "course": optional_course.name,
            "status": "Enrolled",
            "credited_basket_group": basket_group.name,
        },
    )
    source_enrollment.save()
    source_enrollment.db_set("archived", 1, update_modified=False)

    return {
        "student": student,
        "source_ay": source_ay,
        "target_ay": target_ay,
        "required_course": required_course,
        "optional_course": optional_course,
        "source_offering": source_offering,
        "target_offering": target_offering,
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


def _make_offering(program, school, academic_year, required_course, optional_course, basket_group):
    return frappe.get_doc(
        {
            "doctype": "Program Offering",
            "program": program,
            "school": school,
            "offering_title": f"Offering {frappe.generate_hash(length=6)}",
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
            "enrollment_rules": [{"rule_type": "MIN_TOTAL_COURSES", "int_value_1": 1}],
        }
    ).insert()
