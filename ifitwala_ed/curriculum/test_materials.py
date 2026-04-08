from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _materials_module(*, roles: list[str], instructor_groups: list[str], coordinator_courses: list[str] | None = None):
    student_groups_api = ModuleType("ifitwala_ed.api.student_groups")
    student_groups_api._instructor_group_names = lambda user: instructor_groups

    with stubbed_frappe(extra_modules={"ifitwala_ed.api.student_groups": student_groups_api}) as frappe:
        frappe.session.user = "teacher@example.com"
        frappe.get_roles = lambda user: roles
        frappe.db.escape = lambda value: f"'{value}'"
        frappe.db.exists = lambda doctype, filters=None: False

        def fake_get_all(doctype, filters=None, pluck=None, **kwargs):
            if doctype == "Student Group" and pluck == "course":
                return ["COURSE-1"] if instructor_groups else []
            return []

        def fake_get_value(doctype, filters, fieldname=None, as_dict=False):
            if doctype == "Employee":
                return "EMP-1"
            if doctype == "Student":
                return None
            return None

        def fake_sql(query, params=None, as_dict=False):
            if "FROM `tabProgram Coordinator`" in query:
                rows = [{"course": course} for course in (coordinator_courses or [])]
                return rows if as_dict else rows
            return []

        frappe.get_all = fake_get_all
        frappe.db.get_value = fake_get_value
        frappe.db.sql = fake_sql
        yield import_fresh("ifitwala_ed.curriculum.materials")


class TestMaterialsPermissions(TestCase):
    def test_resolve_material_origin_marks_class_owned_anchors_as_shared_in_class(self):
        with _materials_module(
            roles=["Instructor"],
            instructor_groups=["SG-1"],
        ) as materials:
            self.assertEqual(materials.resolve_material_origin("Class Teaching Plan"), "shared_in_class")
            self.assertEqual(materials.resolve_material_origin("Class Session"), "shared_in_class")
            self.assertEqual(materials.resolve_material_origin("Task"), "task")
            self.assertEqual(materials.resolve_material_origin("Unit Plan"), "curriculum")

    def test_get_material_permission_query_conditions_includes_instructor_and_coordinator_courses(self):
        with _materials_module(
            roles=["Instructor", "Curriculum Coordinator"],
            instructor_groups=["SG-1"],
            coordinator_courses=["COURSE-2"],
        ) as materials:
            sql = materials.get_material_permission_query_conditions(
                user="teacher@example.com",
                table_alias="`tabSupporting Material`",
            )

        self.assertIn("COURSE-1", sql)
        self.assertIn("COURSE-2", sql)

    def test_user_can_manage_course_material_denies_read_only_coordinator(self):
        with _materials_module(
            roles=["Curriculum Coordinator"],
            instructor_groups=[],
            coordinator_courses=["COURSE-2"],
        ) as materials:
            self.assertFalse(materials.user_can_manage_course_material("teacher@example.com", "COURSE-2"))
            self.assertTrue(materials.user_can_read_course_material("teacher@example.com", "COURSE-2"))
