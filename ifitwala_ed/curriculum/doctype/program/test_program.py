# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.curriculum.doctype.program import program as program_module


class TestProgram(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

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
        ).insert(ignore_permissions=True)

        program.reload()
        row = program.prerequisites[0]
        self.assertFalse(bool(row.grade_scale_used))
        self.assertFalse(bool(row.min_numeric_score))

    def test_prereq_missing_grade_scale_accepted(self):
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

        program.insert(ignore_permissions=True)
        self.assertEqual(program.prerequisites[0].min_grade, "B-")

    def test_prereq_grade_not_found_accepted(self):
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

        program.insert(ignore_permissions=True)
        self.assertEqual(program.prerequisites[0].min_grade, "Z")

    def test_effective_assessment_categories_fall_back_to_parent_when_child_empty(self):
        parent = frappe._dict(
            {
                "name": "PROG-PARENT",
                "parent_program": "",
                "assessment_categories": [
                    frappe._dict(
                        {
                            "assessment_category": "CAT-1",
                            "default_weight": 40,
                            "color_override": "#123456",
                            "active": 1,
                            "idx": 1,
                        }
                    )
                ],
            }
        )
        child = frappe._dict(
            {
                "name": "PROG-CHILD",
                "parent_program": "PROG-PARENT",
                "assessment_categories": [],
            }
        )

        with patch.object(program_module.frappe, "get_doc", return_value=parent):
            source_program, rows = program_module._resolve_effective_assessment_category_source(child)

        self.assertEqual(source_program, "PROG-PARENT")
        self.assertEqual(rows[0].assessment_category, "CAT-1")

    def test_effective_assessment_categories_prefer_local_rows(self):
        child = frappe._dict(
            {
                "name": "PROG-CHILD",
                "parent_program": "PROG-PARENT",
                "assessment_categories": [
                    frappe._dict(
                        {
                            "assessment_category": "CAT-LOCAL",
                            "default_weight": 50,
                            "color_override": "#abcdef",
                            "active": 1,
                            "idx": 1,
                        }
                    )
                ],
            }
        )

        source_program, rows = program_module._resolve_effective_assessment_category_source(child)

        self.assertEqual(source_program, "PROG-CHILD")
        self.assertEqual(rows[0].assessment_category, "CAT-LOCAL")


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
    grade_scale.insert(ignore_permissions=True)
    return grade_scale


def _make_course(label):
    course = frappe.get_doc(
        {
            "doctype": "Course",
            "course_name": f"{label} {frappe.generate_hash(length=6)}",
            "status": "Active",
        }
    )
    course.insert(ignore_permissions=True)
    return course
