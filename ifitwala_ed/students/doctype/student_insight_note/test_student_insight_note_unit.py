from __future__ import annotations
import __future__

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import stubbed_frappe


@contextmanager
def _student_insight_note_module():
    student_module = ModuleType("ifitwala_ed.students.doctype.student.student")
    student_module.STUDENT_INSTRUCTOR_SCOPE_OVERRIDE_ROLES = {
        "Academic Admin",
        "Academic Assistant",
        "Admission Manager",
        "Admission Officer",
        "Counselor",
        "Curriculum Coordinator",
        "Accreditation Visitor",
    }
    student_module.STUDENT_INSTRUCTOR_SCOPE_ROLES = {"Instructor"}
    student_module.STUDENT_SCHOOL_SCOPED_ROLES = {
        "Academic Admin",
        "Academic Assistant",
        "Academic Staff",
        "Admission Manager",
        "Admission Officer",
        "Counselor",
        "Curriculum Coordinator",
        "Accreditation Visitor",
    }
    student_module.get_instructor_student_scope_condition = lambda user: (
        f"sgs.student = `tabStudent`.`name` AND sgi.user_id = '{user}'"
    )
    student_module.get_permission_query_conditions = lambda user: "1=0"

    employee_utils = ModuleType("ifitwala_ed.utilities.employee_utils")
    employee_utils.get_user_visible_schools = lambda user=None: []

    with stubbed_frappe(
        extra_modules={
            "ifitwala_ed.students.doctype.student.student": student_module,
            "ifitwala_ed.utilities.employee_utils": employee_utils,
        }
    ) as frappe:
        frappe_utils = sys.modules["frappe.utils"]
        frappe_utils.add_days = lambda value, days: value
        frappe_utils.getdate = lambda value=None: value
        frappe_utils.nowdate = lambda: "2026-05-29"

        frappe.flags = SimpleNamespace(in_migration=False, in_patch=False)
        frappe.db.escape = lambda value, percent=True: f"'{value}'"
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.sql = lambda *args, **kwargs: []

        module = ModuleType("ifitwala_ed.students.doctype.student_insight_note.student_insight_note")
        module.__file__ = str(Path(__file__).with_name("student_insight_note.py"))
        module.__package__ = "ifitwala_ed.students.doctype.student_insight_note"

        source = Path(module.__file__).read_text(encoding="utf-8")
        code = compile(
            source,
            module.__file__,
            "exec",
            flags=__future__.annotations.compiler_flag,
            dont_inherit=True,
        )
        exec(code, module.__dict__)

        yield module, frappe


class TestStudentInsightNoteUnit(TestCase):
    def test_metadata_uses_student_name_title_without_link_field_list_join(self):
        payload = json.loads(Path(__file__).with_name("student_insight_note.json").read_text(encoding="utf-8"))
        fields = {field["fieldname"]: field for field in payload["fields"] if field.get("fieldname")}

        self.assertEqual(payload["title_field"], "student_name")
        self.assertNotIn("in_list_view", fields["student"])
        self.assertEqual(fields["student_name"].get("in_list_view"), 1)

    def test_hooks_register_permission_query_and_document_permission(self):
        hooks_text = Path(__file__).parents[3].joinpath("hooks.py").read_text(encoding="utf-8")

        self.assertIn(
            '"Student Insight Note": '
            '"ifitwala_ed.students.doctype.student_insight_note.student_insight_note.get_permission_query_conditions"',
            hooks_text,
        )
        self.assertIn(
            '"Student Insight Note": '
            '"ifitwala_ed.students.doctype.student_insight_note.student_insight_note.has_permission"',
            hooks_text,
        )

    def test_school_scoped_predicate_uses_note_school_not_student_anchor_school(self):
        with _student_insight_note_module() as (module, frappe):
            with (
                patch.object(frappe, "get_roles", return_value=["Academic Assistant"]),
                patch.object(module, "get_user_visible_schools", return_value=["SCH-ROOT", "SCH-CHILD"]),
            ):
                sql, params = module.get_student_insight_visibility_predicate("assistant@example.com")

        self.assertIn("`tabStudent Insight Note`.school IN %(schools)s", sql)
        self.assertNotIn("anchor_school", sql)
        self.assertEqual(params["schools"], ("SCH-ROOT", "SCH-CHILD"))

    def test_permission_query_interpolates_note_school_scope_for_desk_list(self):
        with _student_insight_note_module() as (module, frappe):
            with (
                patch.object(frappe, "get_roles", return_value=["Academic Staff"]),
                patch.object(module, "get_user_visible_schools", return_value=["SCH-CHILD"]),
            ):
                condition = module.get_permission_query_conditions("staff@example.com")

        self.assertIn("`tabStudent Insight Note`.visibility IN ('Teachers')", condition)
        self.assertIn("`tabStudent Insight Note`.school IN ('SCH-CHILD')", condition)
        self.assertNotIn("%(schools)s", condition)
        self.assertNotIn("anchor_school", condition)

    def test_instructor_scope_still_uses_assignment_subquery(self):
        with _student_insight_note_module() as (module, frappe):
            with patch.object(frappe, "get_roles", return_value=["Instructor", "Academic Staff"]):
                sql, params = module.get_student_insight_visibility_predicate("teacher@example.com")

        self.assertIn("FROM `tabStudent`", sql)
        self.assertIn("sgs.student = `tabStudent`.`name`", sql)
        self.assertIn("`tabStudent Insight Note`.student", sql)
        self.assertNotIn("anchor_school", sql)
        self.assertEqual(params["visibilities"], ("Teachers",))
