# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.doctype.course_enrollment_tool.course_enrollment_tool import (
    fetch_eligible_students,
)
from ifitwala_ed.schedule.doctype.program_enrollment_request.test_program_enrollment_request import (
    _make_course,
    _make_grade_scale,
    _make_organization,
    _make_school,
    _make_student,
)


class TestCourseEnrollmentTool(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_course_tool_filters_students_by_source_course(self):
        context = _build_course_tool_context()

        eligible = fetch_eligible_students(
            "Student",
            "",
            "name",
            0,
            20,
            filters={
                "program_offering": context["target_offering"].name,
                "academic_year": context["target_ay"].name,
                "course": context["target_course"].name,
                "source_program_offering": context["source_offering"].name,
                "source_academic_year": context["source_ay"].name,
                "source_course": context["source_course"].name,
            },
        )
        self.assertEqual([row[0] for row in eligible], [context["matching_student"].name])

        tool = frappe.get_doc("Course Enrollment Tool")
        tool.program_offering = context["target_offering"].name
        tool.program = context["program"].name
        tool.academic_year = context["target_ay"].name
        tool.course = context["target_course"].name
        tool.source_program_offering = context["source_offering"].name
        tool.source_academic_year = context["source_ay"].name
        tool.source_course = context["source_course"].name
        tool.set(
            "students",
            [
                {
                    "student": context["matching_student"].name,
                    "student_name": context["matching_student"].student_full_name,
                }
            ],
        )

        tool.add_course_to_program_enrollment()

        target_enrollment = frappe.get_doc("Program Enrollment", context["matching_target_enrollment"].name)
        self.assertIn(context["target_course"].name, {row.course for row in target_enrollment.courses})

        other_enrollment = frappe.get_doc("Program Enrollment", context["other_target_enrollment"].name)
        self.assertNotIn(context["target_course"].name, {row.course for row in other_enrollment.courses})


def _build_course_tool_context():
    grade_scale = _make_grade_scale()
    organization = _make_organization()
    school = _make_school(organization)
    source_ay = _make_academic_year(school.name, "2025-08-01", "2026-06-30")
    target_ay = _make_academic_year(school.name, "2026-08-01", "2027-06-30")
    _make_term(school.name, source_ay.name, "2025-08-01", "2026-06-30")
    _make_term(school.name, target_ay.name, "2026-08-01", "2027-06-30")

    source_course = _make_course("French 5")
    other_source_course = _make_course("Spanish 5")
    target_course = _make_course("French 6")

    program = frappe.get_doc(
        {
            "doctype": "Program",
            "program_name": f"Program {frappe.generate_hash(length=6)}",
            "program_slug": f"program-{frappe.generate_hash(length=8)}",
            "grade_scale": grade_scale.name,
            "courses": [
                {"course": source_course.name, "level": "None"},
                {"course": other_source_course.name, "level": "None"},
                {"course": target_course.name, "level": "None"},
            ],
        }
    ).insert()

    source_offering = _make_offering(
        program=program.name,
        school=school.name,
        academic_year=source_ay.name,
        courses=[source_course.name, other_source_course.name],
    )
    target_offering = _make_offering(
        program=program.name,
        school=school.name,
        academic_year=target_ay.name,
        courses=[target_course.name],
    )

    matching_student = _make_student("French")
    other_student = _make_student("Spanish")

    matching_source_enrollment = _make_enrollment(
        student=matching_student.name,
        program=program.name,
        program_offering=source_offering.name,
        academic_year=source_ay.name,
        enrollment_date=source_ay.year_start_date,
    )
    matching_source_enrollment.append("courses", {"course": source_course.name, "status": "Completed"})
    matching_source_enrollment.save()
    matching_source_enrollment.db_set("archived", 1, update_modified=False)

    other_source_enrollment = _make_enrollment(
        student=other_student.name,
        program=program.name,
        program_offering=source_offering.name,
        academic_year=source_ay.name,
        enrollment_date=source_ay.year_start_date,
    )
    other_source_enrollment.append("courses", {"course": other_source_course.name, "status": "Completed"})
    other_source_enrollment.save()
    other_source_enrollment.db_set("archived", 1, update_modified=False)

    matching_target_enrollment = _make_enrollment(
        student=matching_student.name,
        program=program.name,
        program_offering=target_offering.name,
        academic_year=target_ay.name,
        enrollment_date=target_ay.year_start_date,
    )
    other_target_enrollment = _make_enrollment(
        student=other_student.name,
        program=program.name,
        program_offering=target_offering.name,
        academic_year=target_ay.name,
        enrollment_date=target_ay.year_start_date,
    )

    return {
        "program": program,
        "source_ay": source_ay,
        "target_ay": target_ay,
        "source_course": source_course,
        "target_course": target_course,
        "source_offering": source_offering,
        "target_offering": target_offering,
        "matching_student": matching_student,
        "matching_target_enrollment": matching_target_enrollment,
        "other_target_enrollment": other_target_enrollment,
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


def _make_term(school, academic_year, start_date, end_date):
    return frappe.get_doc(
        {
            "doctype": "Term",
            "school": school,
            "academic_year": academic_year,
            "term_name": f"Term {frappe.generate_hash(length=6)}",
            "term_type": "Academic",
            "term_start_date": start_date,
            "term_end_date": end_date,
        }
    ).insert()


def _make_offering(program, school, academic_year, courses):
    return frappe.get_doc(
        {
            "doctype": "Program Offering",
            "program": program,
            "school": school,
            "offering_title": f"Offering {frappe.generate_hash(length=6)}",
            "offering_academic_years": [{"academic_year": academic_year}],
            "offering_courses": [
                {
                    "course": course,
                    "required": 0,
                    "start_academic_year": academic_year,
                    "end_academic_year": academic_year,
                }
                for course in courses
            ],
        }
    ).insert()


def _make_enrollment(student, program, program_offering, academic_year, enrollment_date):
    return frappe.get_doc(
        {
            "doctype": "Program Enrollment",
            "student": student,
            "program": program,
            "program_offering": program_offering,
            "academic_year": academic_year,
            "enrollment_date": enrollment_date,
            "enrollment_source": "Migration",
            "enrollment_override_reason": "Course tool test setup",
        }
    ).insert()
