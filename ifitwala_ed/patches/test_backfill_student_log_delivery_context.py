from __future__ import annotations

from types import ModuleType
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillStudentLogDeliveryContext(TestCase):
    def test_execute_backfills_missing_context_without_runtime_self_heal(self):
        updates: list[tuple[str, str, dict[str, str], bool]] = []
        context_calls: list[tuple[str, str | None, bool]] = []
        school_calls: list[tuple[str, str | None, str | None]] = []

        helper_module = ModuleType("ifitwala_ed.students.doctype.student_log.student_log")

        def get_program_enrollment_context(student, *, on_date=None, require_unique=False):
            context_calls.append((student, on_date, require_unique))
            if student == "STU-0001":
                return {
                    "program": "PROG-1",
                    "academic_year": "AY-2025",
                    "program_offering": "PO-1",
                    "school": "SCH-1",
                }
            return {}

        def resolve_student_log_school(*, student, academic_year, program_offering):
            school_calls.append((student, academic_year, program_offering))
            if (student, academic_year, program_offering) == ("STU-0002", "AY-2025", "PO-2"):
                return "SCH-2"
            return None

        helper_module._get_program_enrollment_context = get_program_enrollment_context
        helper_module._resolve_student_log_school = resolve_student_log_school

        def get_all(doctype: str, **kwargs):
            if doctype != "Student Log":
                raise AssertionError(f"Unexpected get_all doctype: {doctype}")
            self.assertEqual(
                kwargs["fields"],
                ["name", "student", "date", "creation", "program", "academic_year", "program_offering", "school"],
            )
            return [
                {
                    "name": "LOG-0001",
                    "student": "STU-0001",
                    "date": "2025-09-01",
                    "creation": "2025-09-01 08:00:00",
                    "program": None,
                    "academic_year": "",
                    "program_offering": None,
                    "school": None,
                },
                {
                    "name": "LOG-0002",
                    "student": "STU-0002",
                    "date": None,
                    "creation": "2025-09-02 08:00:00",
                    "program": "PROG-2",
                    "academic_year": "AY-2025",
                    "program_offering": "PO-2",
                    "school": None,
                },
                {
                    "name": "LOG-0003",
                    "student": "STU-0003",
                    "date": "2025-09-03",
                    "creation": "2025-09-03 08:00:00",
                    "program": None,
                    "academic_year": None,
                    "program_offering": None,
                    "school": None,
                },
                {
                    "name": "LOG-0004",
                    "student": "",
                    "date": "2025-09-04",
                    "creation": "2025-09-04 08:00:00",
                    "program": None,
                    "academic_year": None,
                    "program_offering": None,
                    "school": None,
                },
            ]

        with stubbed_frappe(
            extra_modules={"ifitwala_ed.students.doctype.student_log.student_log": helper_module}
        ) as frappe:
            frappe.db.table_exists = lambda doctype: True
            frappe.get_all = get_all
            frappe.db.set_value = lambda doctype, name, values, update_modified=False: updates.append(
                (doctype, name, values, update_modified)
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_log_delivery_context")

            module.execute()

        self.assertEqual(
            updates,
            [
                (
                    "Student Log",
                    "LOG-0001",
                    {
                        "program": "PROG-1",
                        "academic_year": "AY-2025",
                        "program_offering": "PO-1",
                        "school": "SCH-1",
                    },
                    False,
                ),
                ("Student Log", "LOG-0002", {"school": "SCH-2"}, False),
            ],
        )
        self.assertEqual(
            context_calls,
            [
                ("STU-0001", "2025-09-01", True),
                ("STU-0002", "2025-09-02", True),
                ("STU-0003", "2025-09-03", True),
            ],
        )
        self.assertEqual(school_calls, [("STU-0002", "AY-2025", "PO-2"), ("STU-0003", None, None)])

    def test_execute_returns_when_required_tables_are_missing(self):
        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype != "Program Enrollment"
            frappe.get_all = lambda *args, **kwargs: (_ for _ in ()).throw(
                AssertionError("get_all should not run when required tables are missing")
            )
            module = import_fresh("ifitwala_ed.patches.backfill_student_log_delivery_context")

            module.execute()
