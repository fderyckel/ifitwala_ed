# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.curriculum.doctype.program import program as program_module


class TestProgram(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_all_programs_root_cannot_have_parent(self):
        root = _get_or_create_program_root()
        other_parent = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Other Parent {frappe.generate_hash(length=6)}",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)

        root.reload()
        root.parent_program = other_parent.name

        with self.assertRaisesRegex(frappe.ValidationError, "cannot have a Parent Program"):
            root.save(ignore_permissions=True)

    def test_all_programs_root_cannot_be_archived(self):
        root = _get_or_create_program_root()
        root.reload()
        root.archive = 1

        with self.assertRaisesRegex(frappe.ValidationError, "cannot be archived"):
            root.save(ignore_permissions=True)

    def test_all_programs_root_must_remain_group(self):
        root = _get_or_create_program_root()
        root.reload()
        root.is_group = 0

        with self.assertRaisesRegex(frappe.ValidationError, "must remain marked as Group"):
            root.save(ignore_permissions=True)

    def test_parent_program_must_be_group(self):
        parent = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Parent Program {frappe.generate_hash(length=6)}",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)

        child = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Child Program {frappe.generate_hash(length=6)}",
                "parent_program": parent.name,
            }
        )

        with self.assertRaisesRegex(frappe.ValidationError, "Parent Program .* must be marked as Group"):
            child.insert(ignore_permissions=True)

    def test_make_program_group_promotes_parent(self):
        parent = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Parent Program {frappe.generate_hash(length=6)}",
                "is_group": 0,
            }
        ).insert(ignore_permissions=True)

        result = program_module.make_program_group(parent.name)

        self.assertTrue(result["changed"])
        self.assertEqual(frappe.db.get_value("Program", parent.name, "is_group"), 1)

    def test_program_with_children_must_remain_group(self):
        parent = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Parent Program {frappe.generate_hash(length=6)}",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Child Program {frappe.generate_hash(length=6)}",
                "parent_program": parent.name,
            }
        ).insert(ignore_permissions=True)

        parent.reload()
        parent.is_group = 0

        with self.assertRaisesRegex(frappe.ValidationError, "must remain marked as Group"):
            parent.save(ignore_permissions=True)

    def test_program_parent_query_excludes_current_subtree(self):
        parent = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Query Parent {frappe.generate_hash(length=6)}",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)
        child = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Query Child {frappe.generate_hash(length=6)}",
                "parent_program": parent.name,
            }
        ).insert(ignore_permissions=True)
        unrelated = frappe.get_doc(
            {
                "doctype": "Program",
                "program_name": f"Query Unrelated {frappe.generate_hash(length=6)}",
                "is_group": 1,
            }
        ).insert(ignore_permissions=True)

        rows = program_module.program_parent_query("Program", "", "name", 0, 50, {"current_program": parent.name})
        names = {row[0] for row in rows}

        self.assertNotIn(parent.name, names)
        self.assertNotIn(child.name, names)
        self.assertIn(unrelated.name, names)

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


def _get_or_create_program_root():
    if frappe.db.exists("Program", "All Programs"):
        return frappe.get_doc("Program", "All Programs")

    return frappe.get_doc(
        {
            "doctype": "Program",
            "name": "All Programs",
            "program_name": "All Programs",
            "is_group": 1,
        }
    ).insert(ignore_permissions=True)
