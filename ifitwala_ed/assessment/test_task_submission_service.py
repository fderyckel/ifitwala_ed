# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import StubPermissionError, StubValidationError, import_fresh, stubbed_frappe


class TestTaskSubmissionService(TestCase):
    def test_get_next_submission_version_uses_aggregate_field_dict(self):
        with stubbed_frappe() as frappe:
            captured = {}

            def fake_get_all(doctype, filters=None, fields=None, **kwargs):
                captured["doctype"] = doctype
                captured["filters"] = filters
                captured["fields"] = fields
                return [{"max_version": 4}]

            frappe.db.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.assessment.task_submission_service")

            self.assertEqual(module.get_next_submission_version("OUT-1"), 5)
            self.assertEqual(captured["doctype"], "Task Submission")
            self.assertEqual(captured["filters"], {"task_outcome": "OUT-1"})
            self.assertEqual(captured["fields"], [{"MAX": "version", "as": "max_version"}])

    def test_get_next_submission_version_falls_back_to_first_version(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_all = lambda *args, **kwargs: [{"max_version": None}]

            module = import_fresh("ifitwala_ed.assessment.task_submission_service")

            self.assertEqual(module.get_next_submission_version("OUT-1"), 1)

    def test_create_student_submission_rejects_mismatched_expected_student(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_value = lambda *args, **kwargs: {
                "student": "STU-OTHER",
                "student_group": "GRP-1",
                "course": "COURSE-1",
                "academic_year": "AY-1",
                "school": "SCH-1",
                "task_delivery": "TD-1",
                "task": "TASK-1",
            }

            module = import_fresh("ifitwala_ed.assessment.task_submission_service")

            with self.assertRaises(StubPermissionError):
                module.create_student_submission(
                    {"task_outcome": "OUT-1", "text_content": "My answer"},
                    user="student@example.com",
                    expected_student="STU-SELF",
                )

    def test_create_student_submission_rejects_tasks_that_do_not_require_submission(self):
        with stubbed_frappe() as frappe:

            def fake_get_value(doctype, name, fieldnames=None, **kwargs):
                if doctype == "Task Outcome":
                    return {
                        "student": "STU-1",
                        "student_group": "GRP-1",
                        "course": "COURSE-1",
                        "academic_year": "AY-1",
                        "school": "SCH-1",
                        "task_delivery": "TD-1",
                        "task": "TASK-1",
                    }
                if doctype == "Task Delivery":
                    return {
                        "requires_submission": 0,
                    }
                return None

            frappe.db.get_value = fake_get_value

            module = import_fresh("ifitwala_ed.assessment.task_submission_service")

            with self.assertRaises(StubValidationError):
                module.create_student_submission(
                    {"task_outcome": "OUT-1", "text_content": "My answer"},
                    user="student@example.com",
                    expected_student="STU-1",
                )

    def test_create_student_submission_inserts_owner_before_attaching_uploaded_files(self):
        with stubbed_frappe() as frappe:
            order = []
            outcome_updates = {}

            class FakeSubmissionDoc:
                def __init__(self):
                    self.name = None
                    self.attachments = []

                def append(self, fieldname, value):
                    if fieldname == "attachments":
                        self.attachments.append(value)

                def insert(self, ignore_permissions=False):
                    order.append("insert")
                    self.name = "TSU-NEW"
                    return self

                def save(self, ignore_permissions=False):
                    order.append("save")
                    return self

            def fake_get_value(doctype, name, fieldnames=None, **kwargs):
                if doctype == "Task Outcome":
                    return {
                        "student": "STU-1",
                        "student_group": "GRP-1",
                        "course": "COURSE-1",
                        "academic_year": "AY-1",
                        "school": "SCH-1",
                        "task_delivery": "TD-1",
                        "task": "TASK-1",
                    }
                if doctype == "Task Delivery":
                    return {
                        "requires_submission": 1,
                    }
                return None

            frappe.db.get_value = fake_get_value
            frappe.db.get_all = lambda *args, **kwargs: [{"max_version": None}]
            frappe.db.set_value = lambda doctype, name, values, update_modified=True: outcome_updates.update(values)
            frappe.new_doc = lambda doctype: FakeSubmissionDoc()

            module = import_fresh("ifitwala_ed.assessment.task_submission_service")
            module.mark_contributions_stale = lambda *args, **kwargs: None

            def fake_attach(submission_doc, outcome_row, uploaded_files, upload_source=None):
                order.append("attach")
                self.assertEqual(submission_doc.name, "TSU-NEW")
                self.assertEqual(outcome_row.get("student"), "STU-1")
                self.assertEqual(uploaded_files, [{"file_name": "lab-report.pdf", "content": b"pdf"}])
                submission_doc.append(
                    "attachments",
                    {
                        "file": "/private/files/lab-report.pdf",
                        "file_name": "lab-report.pdf",
                        "file_size": 3,
                        "public": 0,
                    },
                )

            module._attach_submission_files = fake_attach

            result = module.create_student_submission(
                {"task_outcome": "OUT-1", "text_content": "My answer"},
                user="student@example.com",
                uploaded_files=[{"file_name": "lab-report.pdf", "content": b"pdf"}],
                expected_student="STU-1",
            )

        self.assertEqual(result["submission_id"], "TSU-NEW")
        self.assertEqual(order, ["insert", "attach", "save"])
        self.assertEqual(
            outcome_updates,
            {
                "has_submission": 1,
                "has_new_submission": 1,
                "submission_status": "Submitted",
            },
        )


class TestTaskContributionService(TestCase):
    def test_get_latest_submission_version_uses_aggregate_field_dict(self):
        with stubbed_frappe() as frappe:
            captured = {}

            def fake_get_all(doctype, filters=None, fields=None, **kwargs):
                captured["doctype"] = doctype
                captured["filters"] = filters
                captured["fields"] = fields
                return [{"max_version": 7}]

            frappe.db.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.assessment.task_contribution_service")

            self.assertEqual(module.get_latest_submission_version("OUT-1"), 7)
            self.assertEqual(captured["doctype"], "Task Submission")
            self.assertEqual(captured["filters"], {"task_outcome": "OUT-1"})
            self.assertEqual(captured["fields"], [{"MAX": "version", "as": "max_version"}])

    def test_get_latest_submission_version_defaults_to_zero(self):
        with stubbed_frappe() as frappe:
            frappe.db.get_all = lambda *args, **kwargs: []

            module = import_fresh("ifitwala_ed.assessment.task_contribution_service")

            self.assertEqual(module.get_latest_submission_version("OUT-1"), 0)

    def test_mark_contributions_stale_returns_cursor_rowcount(self):
        with stubbed_frappe() as frappe:
            captured = {}

            def fake_sql(query, params=None, **kwargs):
                captured["query"] = query
                captured["params"] = params
                return ()

            frappe.db.sql = fake_sql
            frappe.db._cursor = SimpleNamespace(rowcount=2)

            module = import_fresh("ifitwala_ed.assessment.task_contribution_service")

            result = module.mark_contributions_stale("OUT-1", latest_submission_id="SUB-1")

        self.assertEqual(result, 2)
        self.assertIn("UPDATE `tabTask Contribution`", captured["query"])
        self.assertEqual(
            captured["params"],
            {
                "outcome": "OUT-1",
                "submission": "SUB-1",
                "user": "unit.test@example.com",
            },
        )

    def test_mark_contributions_stale_defaults_to_zero_without_cursor_rowcount(self):
        with stubbed_frappe() as frappe:
            frappe.db.sql = lambda *args, **kwargs: ()

            module = import_fresh("ifitwala_ed.assessment.task_contribution_service")

            self.assertEqual(module.mark_contributions_stale("OUT-1"), 0)
