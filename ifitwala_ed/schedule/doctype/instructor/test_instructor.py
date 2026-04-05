# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest import TestCase
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.schedule.doctype.instructor.instructor import (
    Instructor,
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
            patch.object(doc_one, "rebuild_instructor_log", return_value=True) as rebuild_one,
            patch.object(doc_one, "save") as save_one,
            patch.object(doc_two, "rebuild_instructor_log", return_value=False) as rebuild_two,
            patch.object(doc_two, "save") as save_two,
        ):
            sync_instructor_logs(["Cedric Villani", "Cedric Villani", "", "Andreas Vesalius"])

        self.assertEqual(mock_get_doc.call_count, 2)
        rebuild_one.assert_called_once_with()
        rebuild_two.assert_called_once_with()
        save_one.assert_called_once_with(ignore_permissions=True)
        save_two.assert_not_called()
        self.assertTrue(doc_one.flags.ignore_version)
        self.assertFalse(hasattr(doc_two.flags, "ignore_version"))

    def test_instructor_employee_query_requires_instructor_access(self):
        with (
            patch.object(frappe, "session", frappe._dict(user="aa@example.com")),
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
            patch.object(frappe, "session", frappe._dict(user="aa@example.com")),
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
            patch.object(frappe, "session", frappe._dict(user="aa@example.com")),
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


class FakeInstructorDoc:
    def __init__(self, name, instructor_log=None):
        self.name = name
        self._instructor_log = []
        self.set("instructor_log", instructor_log or [])

    def get(self, fieldname, default=None):
        if fieldname == "instructor_log":
            return self._instructor_log
        return default

    def set(self, fieldname, value):
        if fieldname == "instructor_log":
            self._instructor_log = [frappe._dict(row) for row in (value or [])]

    def append(self, fieldname, value):
        if fieldname == "instructor_log":
            self._instructor_log.append(frappe._dict(value))


class TestInstructorLogHistory(TestCase):
    @patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.get_all")
    def test_rebuild_instructor_log_upgrades_current_legacy_snapshot_rows(self, mock_get_all):
        mock_get_all.side_effect = [
            [
                {
                    "student_group": "MATH-HL/T1",
                    "designation": "Teacher",
                    "creation": "2025-08-01 09:00:00",
                }
            ],
            [
                {
                    "student_group": "MATH-HL/T1",
                    "school": "IIS Secondary",
                    "program_offering": "IB DP 2027",
                    "program": "Diploma Programme",
                    "academic_year": "IIS 2025-2026",
                    "term": "Term 1",
                    "course": "Mathematics HL",
                    "group_based_on": "Course",
                }
            ],
        ]
        doc = FakeInstructorDoc(
            "Ada Lovelace",
            instructor_log=[
                {
                    "student_group": "MATH-HL/T1",
                    "designation": "Teacher",
                    "program": "Diploma Programme",
                    "academic_year": "IIS 2025-2026",
                    "term": "Term 1",
                    "course": "Mathematics HL",
                    "other_details": "School: IIS Secondary",
                }
            ],
        )

        changed = Instructor.rebuild_instructor_log(doc)

        self.assertTrue(changed)
        self.assertEqual(len(doc.get("instructor_log")), 1)
        row = doc.get("instructor_log")[0]
        self.assertEqual(str(row.from_date), "2025-08-01")
        self.assertFalse(row.to_date)
        self.assertIn("Group Type: Course", row.other_details)

    @patch("ifitwala_ed.schedule.doctype.instructor.instructor.nowdate", return_value="2026-04-02")
    @patch("ifitwala_ed.schedule.doctype.instructor.instructor.frappe.db.get_all")
    def test_rebuild_instructor_log_closes_removed_rows_and_adds_new_current_rows(self, mock_get_all, _mock_nowdate):
        mock_get_all.side_effect = [
            [
                {
                    "student_group": "PASTORAL-2025",
                    "designation": "Advisor",
                    "creation": "2026-01-10 08:30:00",
                }
            ],
            [
                {
                    "student_group": "PASTORAL-2025",
                    "school": "IIS Secondary",
                    "program_offering": "",
                    "program": "",
                    "academic_year": "IIS 2025-2026",
                    "term": "",
                    "course": "",
                    "group_based_on": "Pastoral",
                }
            ],
        ]
        doc = FakeInstructorDoc(
            "Ada Lovelace",
            instructor_log=[
                {
                    "student_group": "MATH-HL/T1",
                    "designation": "Teacher",
                    "program": "Diploma Programme",
                    "academic_year": "IIS 2025-2026",
                    "term": "Term 1",
                    "course": "Mathematics HL",
                    "from_date": "2025-08-01",
                    "other_details": "Group Type: Course\nSchool: IIS Secondary",
                },
                {
                    "student_group": "OLD-SNAPSHOT",
                    "designation": "Teacher",
                    "program": "Diploma Programme",
                    "academic_year": "IIS 2025-2026",
                    "term": "Term 2",
                    "course": "Biology",
                },
            ],
        )

        changed = Instructor.rebuild_instructor_log(doc)

        self.assertTrue(changed)
        rows = doc.get("instructor_log")
        self.assertEqual(len(rows), 2)

        current_row = next(row for row in rows if row.student_group == "PASTORAL-2025")
        closed_row = next(row for row in rows if row.student_group == "MATH-HL/T1")

        self.assertEqual(str(current_row.from_date), "2026-01-10")
        self.assertFalse(current_row.to_date)
        self.assertIn("Group Type: Pastoral", current_row.other_details)
        self.assertEqual(str(closed_row.to_date), "2026-04-02")
