from __future__ import annotations

from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentLogFollowUpAssignments(TestCase):
    def test_execute_repairs_unambiguous_assignment_drift(self):
        todo_creations: list[dict[str, str]] = []
        updates: list[tuple[str, str, dict[str, str], bool]] = []

        helper_module = ModuleType("ifitwala_ed.students.doctype.student_log.student_log")
        helper_module._insert_follow_up_todo = lambda **kwargs: todo_creations.append(kwargs)

        def get_all(doctype: str, **kwargs):
            if doctype == "Student Log":
                return [
                    {
                        "name": "LOG-0001",
                        "student_name": "Focus Student",
                        "school": "SCH-1",
                        "next_step": "STEP-1",
                        "follow_up_status": "In Progress",
                        "follow_up_person": "old@example.com",
                        "follow_up_role": "Counselor",
                    },
                    {
                        "name": "LOG-0002",
                        "student_name": "Focus Student",
                        "school": "SCH-1",
                        "next_step": "STEP-1",
                        "follow_up_status": "Open",
                        "follow_up_person": "assignee@example.com",
                        "follow_up_role": "Counselor",
                    },
                    {
                        "name": "LOG-0003",
                        "student_name": "Focus Student",
                        "school": "SCH-1",
                        "next_step": "STEP-1",
                        "follow_up_status": "Open",
                        "follow_up_person": "multi@example.com",
                        "follow_up_role": "Counselor",
                    },
                    {
                        "name": "LOG-0004",
                        "student_name": "Focus Student",
                        "school": "SCH-1",
                        "next_step": "STEP-1",
                        "follow_up_status": "In Progress",
                        "follow_up_person": "inprogress@example.com",
                        "follow_up_role": "Counselor",
                    },
                    {
                        "name": "LOG-0005",
                        "student_name": "Focus Student",
                        "school": "SCH-1",
                        "next_step": "STEP-1",
                        "follow_up_status": "Open",
                        "follow_up_person": "norole@example.com",
                        "follow_up_role": "Counselor",
                    },
                ]

            if doctype == "ToDo":
                self.assertEqual(
                    kwargs["filters"]["reference_name"],
                    ["in", ["LOG-0001", "LOG-0002", "LOG-0003", "LOG-0004", "LOG-0005"]],
                )
                return [
                    {"name": "TODO-1", "reference_name": "LOG-0001", "allocated_to": "assignee@example.com"},
                    {"name": "TODO-2", "reference_name": "LOG-0003", "allocated_to": "multi@example.com"},
                    {"name": "TODO-3", "reference_name": "LOG-0003", "allocated_to": "other@example.com"},
                ]

            raise AssertionError(f"Unexpected get_all doctype: {doctype}")

        def exists(doctype: str, filters=None):
            if doctype != "Has Role":
                raise AssertionError(f"Unexpected exists doctype: {doctype}")
            return filters["parent"] in {"assignee@example.com", "multi@example.com", "inprogress@example.com"}

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.students.doctype.student_log.student_log": helper_module}
        ) as frappe:
            frappe.db.table_exists = lambda doctype: True
            frappe.get_all = get_all
            frappe.db.exists = exists
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_log_follow_up_assignments")

            module.execute()

        self.assertEqual(
            updates,
            [
                (
                    "Student Log",
                    "LOG-0001",
                    {"follow_up_person": "assignee@example.com", "follow_up_status": "Open"},
                    False,
                )
            ],
        )
        self.assertEqual(
            todo_creations,
            [
                {
                    "log_name": "LOG-0002",
                    "student_name": "Focus Student",
                    "allocated_to": "assignee@example.com",
                    "school": "SCH-1",
                    "next_step": "STEP-1",
                }
            ],
        )

    def test_execute_returns_when_required_tables_are_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype != "ToDo"
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_log_follow_up_assignments")

            module.execute()
