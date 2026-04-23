from __future__ import annotations

from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class _FakeOutcomeDoc:
    def __init__(self, name: str, *, grading_status: str = "Finalized", task_delivery: str = "TDL-1"):
        self.name = name
        self.task_delivery = task_delivery
        self.grading_status = grading_status
        self.is_published = None
        self.published_on = "stale"
        self.published_by = "stale"
        self.save_calls: list[bool] = []

    def save(self, ignore_permissions: bool = False):
        self.save_calls.append(ignore_permissions)


class TestOutcomePublishApi(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with stubbed_frappe():
            cls.outcome_publish = import_fresh("ifitwala_ed.api.outcome_publish")

    def test_bulk_update_publish_uses_task_outcome_documents(self):
        outcome_one = _FakeOutcomeDoc("OUT-1")
        outcome_two = _FakeOutcomeDoc("OUT-2")
        docs = {outcome_one.name: outcome_one, outcome_two.name: outcome_two}

        with (
            patch.object(
                self.outcome_publish.frappe,
                "get_all",
                return_value=["OUT-1", "OUT-2"],
            ) as get_all,
            patch.object(
                self.outcome_publish.frappe,
                "get_doc",
                side_effect=lambda doctype, name: docs[name],
            ) as get_doc,
        ):
            self.outcome_publish._bulk_update_publish(
                ["OUT-1", "OUT-1", "MISSING", "OUT-2"],
                {
                    "is_published": 1,
                    "published_on": "2026-03-23 09:30:00",
                    "published_by": "teacher@example.com",
                },
            )

        get_all.assert_called_once_with(
            "Task Outcome",
            filters={"name": ["in", ["OUT-1", "MISSING", "OUT-2"]]},
            pluck="name",
            ignore_permissions=True,
        )
        self.assertEqual(
            [call.args for call in get_doc.call_args_list],
            [("Task Outcome", "OUT-1"), ("Task Outcome", "OUT-2")],
        )
        self.assertEqual(outcome_one.is_published, 1)
        self.assertEqual(outcome_one.grading_status, "Released")
        self.assertEqual(outcome_one.published_on, "2026-03-23 09:30:00")
        self.assertEqual(outcome_one.published_by, "teacher@example.com")
        self.assertEqual(outcome_one.save_calls, [True])
        self.assertEqual(outcome_two.is_published, 1)
        self.assertEqual(outcome_two.grading_status, "Released")
        self.assertEqual(outcome_two.published_on, "2026-03-23 09:30:00")
        self.assertEqual(outcome_two.published_by, "teacher@example.com")
        self.assertEqual(outcome_two.save_calls, [True])

    def test_bulk_update_publish_restores_unpublished_status_when_unreleasing(self):
        outcome = _FakeOutcomeDoc("OUT-1", grading_status="Released")

        with (
            patch.object(
                self.outcome_publish.frappe,
                "get_all",
                return_value=["OUT-1"],
            ),
            patch.object(
                self.outcome_publish.frappe,
                "get_doc",
                return_value=outcome,
            ),
            patch.object(
                self.outcome_publish,
                "_resolve_unpublished_status",
                return_value="Moderated",
            ),
        ):
            self.outcome_publish._bulk_update_publish(
                ["OUT-1"],
                {
                    "is_published": 0,
                    "published_on": None,
                    "published_by": None,
                },
            )

        self.assertEqual(outcome.is_published, 0)
        self.assertEqual(outcome.grading_status, "Moderated")
        self.assertIsNone(outcome.published_on)
        self.assertIsNone(outcome.published_by)

    def test_resolve_unpublished_status_prefers_latest_moderator_contribution(self):
        outcome = _FakeOutcomeDoc("OUT-1", grading_status="Released")

        with (
            patch.object(
                self.outcome_publish.frappe,
                "get_all",
                return_value=[{"contribution_type": "Moderator"}],
            ),
            patch.object(self.outcome_publish.frappe.db, "get_value", create=True) as get_value,
        ):
            status = self.outcome_publish._resolve_unpublished_status(outcome)

        get_value.assert_not_called()
        self.assertEqual(status, "Moderated")

    def test_resolve_unpublished_status_falls_back_to_finalized_for_assess_deliveries(self):
        outcome = _FakeOutcomeDoc("OUT-1", grading_status="Released", task_delivery="TDL-42")

        with (
            patch.object(
                self.outcome_publish.frappe,
                "get_all",
                return_value=[],
            ),
            patch.object(
                self.outcome_publish.frappe.db,
                "get_value",
                return_value={"delivery_mode": "Assess"},
                create=True,
            ) as get_value,
        ):
            status = self.outcome_publish._resolve_unpublished_status(outcome)

        get_value.assert_called_once_with("Task Delivery", "TDL-42", ["delivery_mode"], as_dict=True)
        self.assertEqual(status, "Finalized")

    def test_publish_outcomes_passes_current_user_and_timestamp(self):
        with (
            patch.object(self.outcome_publish, "_can_write_gradebook", return_value=True),
            patch.object(self.outcome_publish, "_is_academic_adminish", return_value=False),
            patch.object(self.outcome_publish, "now_datetime", return_value="2026-03-23 10:15:00"),
            patch.object(self.outcome_publish, "_bulk_update_publish") as bulk_update,
            patch.object(
                self.outcome_publish,
                "_get_publish_summaries",
                return_value=[{"outcome_id": "OUT-1", "is_published": True}],
            ),
        ):
            payload = self.outcome_publish.publish_outcomes(payload={"outcome_ids": ["OUT-1"]})

        bulk_update.assert_called_once_with(
            ["OUT-1"],
            {
                "is_published": 1,
                "published_on": "2026-03-23 10:15:00",
                "published_by": self.outcome_publish.frappe.session.user,
            },
        )
        self.assertEqual(payload, {"outcomes": [{"outcome_id": "OUT-1", "is_published": True}]})
