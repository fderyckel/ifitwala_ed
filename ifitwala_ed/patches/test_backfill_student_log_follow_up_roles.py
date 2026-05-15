from __future__ import annotations

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentLogFollowUpRoles(TestCase):
    def test_execute_backfills_missing_roles_from_next_step_or_default(self):
        updates: list[tuple[str, str, dict[str, str], bool]] = []

        def get_all(doctype: str, **kwargs):
            if doctype == "Student Log":
                return [
                    {"name": "LOG-0001", "next_step": "STEP-ROLE", "follow_up_role": None},
                    {"name": "LOG-0002", "next_step": "STEP-DEFAULT", "follow_up_role": ""},
                    {"name": "LOG-0003", "next_step": "STEP-MISSING", "follow_up_role": None},
                    {"name": "LOG-0004", "next_step": None, "follow_up_role": None},
                    {"name": "LOG-0005", "next_step": "STEP-KEEP", "follow_up_role": "Counselor"},
                ]
            if doctype == "Student Log Next Step":
                self.assertEqual(
                    kwargs["filters"],
                    {"name": ["in", ["STEP-DEFAULT", "STEP-MISSING", "STEP-ROLE"]]},
                )
                return [
                    {"name": "STEP-ROLE", "associated_role": "Counselor"},
                    {"name": "STEP-DEFAULT", "associated_role": None},
                    {"name": "STEP-KEEP", "associated_role": "Learning Support"},
                ]
            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Student Log", "Student Log Next Step"}
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_log_follow_up_roles")

            module.execute()

        self.assertEqual(
            updates,
            [
                ("Student Log", "LOG-0001", {"follow_up_role": "Counselor"}, False),
                ("Student Log", "LOG-0002", {"follow_up_role": "Academic Staff"}, False),
            ],
        )

    def test_execute_returns_when_required_tables_are_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_log_follow_up_roles")

            module.execute()
