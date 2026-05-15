from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentGroupStudentActiveFlags(TestCase):
    def test_execute_backfills_only_null_active_flags(self):
        statements: list[str] = []

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype == "Student Group Student"
            frappe.db.sql = lambda query, *args, **kwargs: statements.append(query)
            module = import_fresh("ifitwala_ed.patches.backfill_student_group_student_active_flags")

            module.execute()

        self.assertEqual(len(statements), 1)
        self.assertIn("UPDATE `tabStudent Group Student`", statements[0])
        self.assertIn("SET active = 1", statements[0])
        self.assertIn("WHERE active IS NULL", statements[0])
        self.assertNotIn("active = 0", statements[0])

    def test_execute_returns_when_child_table_is_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.db.sql = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("sql should not run when Student Group Student is missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_group_student_active_flags")

            module.execute()
