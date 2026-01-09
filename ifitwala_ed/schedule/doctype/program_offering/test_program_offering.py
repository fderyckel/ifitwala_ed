# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

# import frappe
import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.grade_scale_resolver_utils import resolve_grade_scale


class TestProgramOffering(FrappeTestCase):
	def test_grade_scale_resolver_program_default(self):
		program_scale = _make_grade_scale("Program")
		organization = _make_organization()
		school = _make_school(organization)
		program = _make_program(program_scale)
		course = _make_course("Course")
		offering = _make_offering(program, school, [{
			"course": course.name,
			"course_name": course.course_name,
		}])

		result = resolve_grade_scale(offering.name, course.name)
		self.assertEqual(result["grade_scale"], program_scale.name)

	def test_grade_scale_resolver_offering_override(self):
		program_scale = _make_grade_scale("Program")
		offering_scale = _make_grade_scale("Offering")
		organization = _make_organization()
		school = _make_school(organization)
		program = _make_program(program_scale)
		course = _make_course("Course")
		offering = _make_offering(
			program,
			school,
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
		program = _make_program(program_scale)
		course = _make_course("Course")
		offering = _make_offering(
			program,
			school,
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


def _make_grade_scale(prefix):
	grade_scale = frappe.get_doc({
		"doctype": "Grade Scale",
		"grade_scale_name": f"{prefix} {frappe.generate_hash(length=6)}",
		"boundaries": [
			{"grade_code": "A", "boundary_interval": 90},
			{"grade_code": "B", "boundary_interval": 80},
		],
	})
	grade_scale.insert()
	return grade_scale


def _make_organization():
	organization = frappe.get_doc({
		"doctype": "Organization",
		"organization_name": f"Org {frappe.generate_hash(length=6)}",
		"abbr": f"ORG{frappe.generate_hash(length=4)}",
	})
	organization.insert()
	return organization


def _make_school(organization):
	school = frappe.get_doc({
		"doctype": "School",
		"school_name": f"School {frappe.generate_hash(length=6)}",
		"abbr": f"SCH{frappe.generate_hash(length=4)}",
		"organization": organization.name,
	})
	school.insert()
	return school


def _make_program(grade_scale):
	program = frappe.get_doc({
		"doctype": "Program",
		"program_name": f"Program {frappe.generate_hash(length=6)}",
		"grade_scale": grade_scale.name,
	})
	program.insert()
	return program


def _make_course(label):
	course = frappe.get_doc({
		"doctype": "Course",
		"course_name": f"{label} {frappe.generate_hash(length=6)}",
		"status": "Active",
	})
	course.insert()
	return course


def _make_offering(program, school, offering_courses, grade_scale=None):
	offering = frappe.get_doc({
		"doctype": "Program Offering",
		"program": program.name,
		"school": school.name,
		"offering_title": f"Offering {frappe.generate_hash(length=6)}",
		"grade_scale": grade_scale,
		"offering_courses": offering_courses,
	})
	offering.insert()
	return offering
