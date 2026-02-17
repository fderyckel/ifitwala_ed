# Copyright (c) 2024, fdR and Contributors
# See license.txt

# import frappe
import frappe
from frappe.tests.utils import FrappeTestCase


class TestProgram(FrappeTestCase):
    def test_prereq_resolves_min_numeric_score(self):
        grade_scale = _make_grade_scale()
        required_course = _make_course("Required")
        target_course = _make_course("Target")

        program = frappe.get_doc(
            {
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
            }
        ).insert()

        program.reload()
        row = program.prerequisites[0]
        self.assertEqual(row.grade_scale_used, grade_scale.name)
        self.assertEqual(float(row.min_numeric_score), 70.0)

    def test_prereq_missing_grade_scale_raises(self):
        required_course = _make_course("NoScale")
        target_course = _make_course("TargetMissingScale")

        program = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Program {frappe.generate_hash(length=6)}",
                "prerequisites": [
                    {
                        "apply_to_course": target_course.name,
                        "required_course": required_course.name,
                        "min_grade": "B-",
                    }
                ],
            }
        )

        with self.assertRaises(frappe.ValidationError):
            program.insert()

    def test_prereq_grade_not_found_raises(self):
        grade_scale = _make_grade_scale()
        required_course = _make_course("MissingGrade")
        target_course = _make_course("TargetMissingGrade")

        program = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Program {frappe.generate_hash(length=6)}",
                "grade_scale": grade_scale.name,
                "prerequisites": [
                    {
                        "apply_to_course": target_course.name,
                        "required_course": required_course.name,
                        "min_grade": "Z",
                    }
                ],
            }
        )

        with self.assertRaises(frappe.ValidationError):
            program.insert()


def _make_grade_scale():
    grade_scale = frappe.get_doc(
        {
            "doctype": "Grade Scale",
            "grade_scale_name": f"Scale {frappe.generate_hash(length=6)}",
            "boundaries": [
                {"grade_code": "A", "boundary_interval": 90},
                {"grade_code": "B-", "boundary_interval": 70},
            ],
        }
    )
    grade_scale.insert()
    return grade_scale


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
