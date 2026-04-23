from __future__ import annotations

from unittest import TestCase
from unittest.mock import Mock

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestBackfillTaskDeliveryLaunchArtifacts(TestCase):
    def test_execute_repairs_only_submitted_deliveries_missing_launch_artifacts(self):
        submitted_rows = [
            {"name": "TDL-OUTCOMES", "grading_mode": "Points", "rubric_version": None},
            {"name": "TDL-RUBRIC", "grading_mode": "Criteria", "rubric_version": None},
            {"name": "TDL-CURRENT", "grading_mode": "Criteria", "rubric_version": "TRV-0001"},
        ]
        delivery_with_missing_outcomes = Mock()
        delivery_with_missing_rubric = Mock()

        def _get_all(doctype, **kwargs):
            if doctype == "Task Delivery":
                return submitted_rows
            if doctype == "Task Outcome":
                return ["TDL-RUBRIC", "TDL-CURRENT"]
            return []

        def _get_doc(doctype, name):
            if name == "TDL-OUTCOMES":
                return delivery_with_missing_outcomes
            if name == "TDL-RUBRIC":
                return delivery_with_missing_rubric
            raise AssertionError(f"unexpected get_doc request for {doctype} {name}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Task Delivery", "Task Outcome"}
            frappe.get_all = _get_all
            frappe.get_doc = _get_doc
            module = import_fresh("ifitwala_ed.patches.backfill_task_delivery_launch_artifacts")

            module.execute()

        delivery_with_missing_outcomes.materialize_roster.assert_called_once_with()
        delivery_with_missing_rubric.materialize_roster.assert_called_once_with()

    def test_execute_logs_and_continues_when_one_delivery_backfill_fails(self):
        failing_delivery = Mock()
        failing_delivery.materialize_roster.side_effect = RuntimeError("boom")
        healthy_delivery = Mock()
        logs: list[tuple[str | None, str]] = []

        def _get_all(doctype, **kwargs):
            if doctype == "Task Delivery":
                return [
                    {"name": "TDL-FAIL", "grading_mode": "Points", "rubric_version": None},
                    {"name": "TDL-OK", "grading_mode": "Points", "rubric_version": None},
                ]
            if doctype == "Task Outcome":
                return []
            return []

        def _get_doc(doctype, name):
            if name == "TDL-FAIL":
                return failing_delivery
            if name == "TDL-OK":
                return healthy_delivery
            raise AssertionError(f"unexpected get_doc request for {doctype} {name}")

        with stubbed_frappe() as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Task Delivery", "Task Outcome"}
            frappe.get_all = _get_all
            frappe.get_doc = _get_doc
            frappe.as_json = lambda payload, indent=2: str(payload)
            frappe.log_error = lambda message, title=None: logs.append((title, message))
            module = import_fresh("ifitwala_ed.patches.backfill_task_delivery_launch_artifacts")

            module.execute()

        healthy_delivery.materialize_roster.assert_called_once_with()
        self.assertEqual(logs[0][0], "Task Delivery Launch Artifact Backfill Failed")
        self.assertIn("TDL-FAIL", logs[0][1])
