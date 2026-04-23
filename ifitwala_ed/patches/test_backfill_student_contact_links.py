from __future__ import annotations

from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentContactLinks(TestCase):
    def test_execute_backfills_only_named_students_with_email(self):
        student_one = Mock()
        student_two = Mock()

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Student", "Contact"}
            frappe.get_all = lambda doctype, **kwargs: ["STU-0001", "", None, "STU-0002"]
            frappe.get_doc = lambda doctype, name: {
                "STU-0001": student_one,
                "STU-0002": student_two,
            }[name]

            module = import_fresh("ifitwala_ed.patches.backfill_student_contact_links")
            module.execute()

        student_one.ensure_contact_and_link.assert_called_once_with()
        student_two.ensure_contact_and_link.assert_called_once_with()

    def test_execute_returns_when_required_tables_are_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )

            module = import_fresh("ifitwala_ed.patches.backfill_student_contact_links")
            module.execute()
