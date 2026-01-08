# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import nowdate

from ifitwala_ed.schedule.doctype.program_enrollment_request.program_enrollment_request import (
	validate_enrollment_request,
)


class TestProgramEnrollmentRequest(FrappeTestCase):
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
		self.assertTrue(payload["courses"][context["target_course"].name]["prereq_ok"])

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
		self.assertFalse(payload["courses"][context["target_course"].name]["prereq_ok"])

	def test_validate_request_capacity_exceeded(self):
		context = _setup_enrollment_context(score=85, capacity=1)
		student_two = _make_student("Capacity")

		first_request = _make_enrollment_request(
			context,
			student=context["student"],
			course=context["target_course"],
			status="Submitted",
		)
		second_request = _make_enrollment_request(
			context,
			student=student_two,
			course=context["target_course"],
		)

		payload = validate_enrollment_request(second_request.name)
		second_request.reload()

		self.assertEqual(second_request.validation_status, "Invalid")
		self.assertFalse(payload["courses"][context["target_course"].name]["capacity_ok"])


def _setup_enrollment_context(score, capacity=None):
	grade_scale = _make_grade_scale()
	organization = _make_organization()
	school = _make_school(organization)
	academic_year = _make_academic_year(school)
	term = _make_term(academic_year)
	student = _make_student("Prereq")
	required_course = _make_course("Required")
	target_course = _make_course("Target")

	program = frappe.get_doc({
		"doctype": "Program",
		"program_name": f"Program {frappe.generate_hash(length=6)}",
		"grade_scale": grade_scale.name,
		"prerequisites": [
			{
				"apply_to_course": target_course.name,
				"required_course": required_course.name,
				"min_grade": "B-",
			}
		],
	}).insert()

	offering_course = {
		"course": target_course.name,
		"course_name": target_course.course_name,
		"capacity": capacity,
	}
	offering = frappe.get_doc({
		"doctype": "Program Offering",
		"program": program.name,
		"school": school.name,
		"offering_title": f"Offering {frappe.generate_hash(length=6)}",
		"offering_courses": [offering_course],
	}).insert()

	enrollment = frappe.get_doc({
		"doctype": "Program Enrollment",
		"student": student.name,
		"program": program.name,
		"program_offering": offering.name,
		"academic_year": academic_year.name,
		"enrollment_date": nowdate(),
	}).insert()
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
	request = frappe.get_doc({
		"doctype": "Program Enrollment Request",
		"student": student.name,
		"program_offering": context["offering"].name,
		"status": status,
		"courses": [
			{
				"course": course.name,
				"apply_to_level": "None",
			}
		],
	})
	request.insert()
	return request


def _make_grade_scale():
	grade_scale = frappe.get_doc({
		"doctype": "Grade Scale",
		"grade_scale_name": f"Scale {frappe.generate_hash(length=6)}",
		"boundaries": [
			{"grade_code": "B-", "boundary_interval": 70},
			{"grade_code": "C", "boundary_interval": 60},
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


def _make_academic_year(school):
	academic_year = frappe.get_doc({
		"doctype": "Academic Year",
		"academic_year_name": f"AY {frappe.generate_hash(length=6)}",
		"school": school.name,
	})
	academic_year.insert()
	return academic_year


def _make_term(academic_year):
	term = frappe.get_doc({
		"doctype": "Term",
		"academic_year": academic_year.name,
		"term_name": f"Term {frappe.generate_hash(length=6)}",
		"term_type": "Academic",
		"term_start_date": nowdate(),
		"term_end_date": nowdate(),
	})
	term.insert()
	return term


def _make_student(prefix):
	student = frappe.get_doc({
		"doctype": "Student",
		"student_first_name": prefix,
		"student_last_name": f"Test {frappe.generate_hash(length=6)}",
		"student_email": f"{frappe.generate_hash(length=8)}@example.com",
	})
	student.insert()
	return student


def _make_course(label):
	course = frappe.get_doc({
		"doctype": "Course",
		"course_name": f"{label} {frappe.generate_hash(length=6)}",
		"status": "Active",
	})
	course.insert()
	return course


def _make_course_term_result(student, course, program, academic_year, term, grade_scale, score):
	result = frappe.get_doc({
		"doctype": "Course Term Result",
		"student": student.name,
		"course": course.name,
		"program": program.name,
		"academic_year": academic_year.name,
		"term": term.name,
		"grade_scale": grade_scale.name,
		"numeric_score": score,
	})
	result.insert()
	return result
