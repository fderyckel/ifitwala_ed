# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

# import frappe
import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.doctype.program_offering.program_offering import program_course_link_query
from ifitwala_ed.schedule.grade_scale_resolver_utils import resolve_grade_scale


class TestProgramOffering(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_grade_scale_resolver_program_default(self):
        program_scale = _make_grade_scale("Program")
        organization = _make_organization()
        school = _make_school(organization)
        academic_year = _make_academic_year(school)
        course = _make_course("Course")
        program = _make_program(program_scale, [course.name])
        offering = _make_offering(
            program,
            school,
            academic_year,
            [
                {
                    "course": course.name,
                    "course_name": course.course_name,
                }
            ],
        )

        result = resolve_grade_scale(offering.name, course.name)
        self.assertEqual(result["grade_scale"], program_scale.name)

    def test_grade_scale_resolver_offering_override(self):
        program_scale = _make_grade_scale("Program")
        offering_scale = _make_grade_scale("Offering")
        organization = _make_organization()
        school = _make_school(organization)
        academic_year = _make_academic_year(school)
        course = _make_course("Course")
        program = _make_program(program_scale, [course.name])
        offering = _make_offering(
            program,
            school,
            academic_year,
            [
                {"course": course.name, "course_name": course.course_name},
            ],
            grade_scale=offering_scale.name,
        )

        result = resolve_grade_scale(offering.name, course.name)
        self.assertEqual(result["grade_scale"], offering_scale.name)

    def test_grade_scale_resolver_offering_course_override(self):
        program_scale = _make_grade_scale("Program")
        offering_scale = _make_grade_scale("Offering")
        course_scale = _make_grade_scale("OfferingCourse")
        organization = _make_organization()
        school = _make_school(organization)
        academic_year = _make_academic_year(school)
        course = _make_course("Course")
        program = _make_program(program_scale, [course.name])
        offering = _make_offering(
            program,
            school,
            academic_year,
            [
                {
                    "course": course.name,
                    "course_name": course.course_name,
                    "grade_scale": course_scale.name,
                }
            ],
            grade_scale=offering_scale.name,
        )

        result = resolve_grade_scale(offering.name, course.name)
        self.assertEqual(result["grade_scale"], course_scale.name)

    def test_program_course_link_query_scopes_to_program_catalog(self):
        program_scale = _make_grade_scale("Program")
        organization = _make_organization()
        school = _make_school(organization)
        academic_year = _make_academic_year(school)
        course_one = _make_course("Course One")
        course_two = _make_course("Course Two")
        extra_course = _make_course("Extra Course")
        program = _make_program(program_scale, [course_one.name, course_two.name])
        _make_offering(
            program,
            school,
            academic_year,
            [{"course": course_one.name, "course_name": course_one.course_name}],
        )

        rows = program_course_link_query(
            "Course",
            "",
            "name",
            0,
            20,
            {"program": program.name, "exclude_courses": [course_one.name]},
        )

        self.assertEqual(rows, [[course_two.name, course_two.course_name]])
        self.assertNotIn([extra_course.name, extra_course.course_name], rows)


def _make_grade_scale(prefix):
    grade_scale = frappe.get_doc(
        {
            "doctype": "Grade Scale",
            "grade_scale_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "boundaries": [
                {"grade_code": "A", "boundary_interval": 90},
                {"grade_code": "B", "boundary_interval": 80},
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
    doc = frappe.get_doc(
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
    doc.insert()
    return doc


def _make_program(grade_scale, courses=None):
    program = frappe.get_doc(
        {
            "doctype": "Program",
            "program_name": f"Program {frappe.generate_hash(length=6)}",
            "grade_scale": grade_scale.name,
            "courses": [{"course": course_name} for course_name in (courses or [])],
        }
    )
    program.insert()
    return program


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


def _make_offering(program, school, academic_year, offering_courses, grade_scale=None):
    normalized_courses = []
    for row in offering_courses or []:
        row_data = dict(row)
        row_data.setdefault("start_academic_year", academic_year.name)
        row_data.setdefault("end_academic_year", academic_year.name)
        normalized_courses.append(row_data)

    offering = frappe.get_doc(
        {
            "doctype": "Program Offering",
            "program": program.name,
            "school": school.name,
            "offering_title": f"Offering {frappe.generate_hash(length=6)}",
            "grade_scale": grade_scale,
            "offering_academic_years": [{"academic_year": academic_year.name}],
            "offering_courses": normalized_courses,
        }
    )
    offering.insert()
    return offering
