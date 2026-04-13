# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


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
