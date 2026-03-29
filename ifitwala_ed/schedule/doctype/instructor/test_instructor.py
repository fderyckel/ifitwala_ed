# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.doctype.instructor.instructor import (
    instructor_employee_query,
    sync_instructor_logs,
)


class TestInstructor(FrappeTestCase):
    @patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.get_doc")
    @patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.exists")
    def test_sync_instructor_logs_rebuilds_each_existing_instructor(self, mock_exists, mock_get_doc):
        doc_one = type("InstructorDoc", (), {"flags": type("Flags", (), {})()})()
        doc_one.rebuild_instructor_log = lambda: None
        doc_one.save = lambda **kwargs: kwargs

        doc_two = type("InstructorDoc", (), {"flags": type("Flags", (), {})()})()
        doc_two.rebuild_instructor_log = lambda: None
        doc_two.save = lambda **kwargs: kwargs

        mock_exists.side_effect = lambda doctype, name=None: {
            ("Instructor", "Cedric Villani"): True,
            ("Instructor", "Andreas Vesalius"): True,
        }.get((doctype, name), False)
        mock_get_doc.side_effect = [doc_two, doc_one]

        with (
            patch.object(doc_one, "rebuild_instructor_log") as rebuild_one,
            patch.object(doc_one, "save") as save_one,
            patch.object(doc_two, "rebuild_instructor_log") as rebuild_two,
            patch.object(doc_two, "save") as save_two,
        ):
            sync_instructor_logs(["Cedric Villani", "Cedric Villani", "", "Andreas Vesalius"])

        self.assertEqual(mock_get_doc.call_count, 2)
        rebuild_one.assert_called_once_with()
        rebuild_two.assert_called_once_with()
        save_one.assert_called_once_with(ignore_permissions=True)
        save_two.assert_called_once_with(ignore_permissions=True)
        self.assertTrue(doc_one.flags.ignore_version)
        self.assertTrue(doc_two.flags.ignore_version)

    def test_instructor_employee_query_requires_instructor_access(self):
        with (
            patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.session.user", "aa@example.com"),
            patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.has_permission", return_value=False),
        ):
            rows = instructor_employee_query("Employee", "", "name", 0, 20, {})

        self.assertEqual(rows, [])

    def test_instructor_employee_query_is_school_scoped_and_keeps_current_employee(self):
        captured = {}

        def fake_sql(query, params):
            captured["query"] = query
            captured["params"] = params
            return [["EMP-0001", "Ada Lovelace"]]

        with (
            patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.session.user", "aa@example.com"),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor.frappe.has_permission",
                side_effect=lambda doctype, ptype=None, user=None: ptype in {"create", "write"},
            ),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor.frappe.get_roles",
                return_value=["Academic Assistant"],
            ),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor._user_allowed_schools", return_value=["SCH-ROOT"]
            ),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.escape",
                side_effect=lambda value, percent=False: f"'{value}'",
            ),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor.get_filters_cond",
                return_value="`tabEmployee`.`school` = 'SCH-ROOT'",
            ),
            patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.sql", side_effect=fake_sql),
        ):
            rows = instructor_employee_query(
                "Employee",
                "Ada",
                "name",
                0,
                20,
                {"current_instructor": "INST-0001", "current_employee": "EMP-0001", "school": "SCH-ROOT"},
            )

        self.assertEqual(rows, [["EMP-0001", "Ada Lovelace"]])
        self.assertIn("`tabEmployee`.`school` IN ('SCH-ROOT')", captured["query"])
        self.assertIn("`tabEmployee`.`name` = %(current_employee)s", captured["query"])
        self.assertIn("instructor.name != %(current_instructor)s", captured["query"])
        self.assertEqual(captured["params"]["current_employee"], "EMP-0001")
        self.assertEqual(captured["params"]["current_instructor"], "INST-0001")

    def test_instructor_employee_query_without_current_employee_excludes_linked_employees(self):
        captured = {}

        def fake_sql(query, params):
            captured["query"] = query
            captured["params"] = params
            return []

        with (
            patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.session.user", "aa@example.com"),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor.frappe.has_permission",
                side_effect=lambda doctype, ptype=None, user=None: ptype in {"create", "write"},
            ),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor.frappe.get_roles",
                return_value=["Academic Assistant"],
            ),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor._user_allowed_schools", return_value=["SCH-ROOT"]
            ),
            patch(
                "ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.escape",
                side_effect=lambda value, percent=False: f"'{value}'",
            ),
            patch("ifitwala_ed.schedule.doctype.instructor.instructor.get_filters_cond", return_value=""),
            patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.sql", side_effect=fake_sql),
        ):
            instructor_employee_query("Employee", "", "name", 0, 20, {})

        self.assertIn("NOT EXISTS", captured["query"])
        self.assertNotIn("`tabEmployee`.`name` = %(current_employee)s", captured["query"])
