# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

# ifitwala_ed/assessment/doctype/task_feedback_workspace/test_task_feedback_workspace.py

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _import_task_feedback_workspace_module():
    task_feedback_service = types.ModuleType("ifitwala_ed.assessment.task_feedback_service")
    task_feedback_service.FEEDBACK_INTENT_OPTIONS = ("comment",)
    task_feedback_service.FEEDBACK_ITEM_KINDS = ("annotation",)
    task_feedback_service.FEEDBACK_WORKFLOW_STATES = ("draft",)
    task_feedback_service.PUBLICATION_VISIBILITY_STATES = ("private",)
    task_feedback_service.normalize_feedback_anchor_payload = lambda *_args, **_kwargs: {}

    with stubbed_frappe(extra_modules={"ifitwala_ed.assessment.task_feedback_service": task_feedback_service}):
        return import_fresh("ifitwala_ed.assessment.doctype.task_feedback_workspace.task_feedback_workspace")


class TestTaskFeedbackWorkspace(TestCase):
    def test_unique_index_exists_matches_ordered_columns(self):
        module = _import_task_feedback_workspace_module()
        rows = [
            {
                "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                "Non_unique": 0,
                "Seq_in_index": 1,
                "Column_name": "task_outcome",
            },
            {
                "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                "Non_unique": 0,
                "Seq_in_index": 2,
                "Column_name": "task_submission",
            },
        ]

        self.assertTrue(module._unique_index_exists(rows, ["task_outcome", "task_submission"]))

    def test_ensure_indexes_recreates_existing_named_non_unique_index_as_unique(self):
        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.assessment.task_feedback_service": types.SimpleNamespace(
                    FEEDBACK_INTENT_OPTIONS=("comment",),
                    FEEDBACK_ITEM_KINDS=("annotation",),
                    FEEDBACK_WORKFLOW_STATES=("draft",),
                    PUBLICATION_VISIBILITY_STATES=("private",),
                    normalize_feedback_anchor_payload=lambda *_args, **_kwargs: {},
                )
            }
        ) as frappe:
            index_states = [
                [
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 1,
                        "Seq_in_index": 1,
                        "Column_name": "task_outcome",
                    },
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 1,
                        "Seq_in_index": 2,
                        "Column_name": "task_submission",
                    },
                ],
                [
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 0,
                        "Seq_in_index": 1,
                        "Column_name": "task_outcome",
                    },
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 0,
                        "Seq_in_index": 2,
                        "Column_name": "task_submission",
                    },
                ],
                [
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 0,
                        "Seq_in_index": 1,
                        "Column_name": "task_outcome",
                    },
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 0,
                        "Seq_in_index": 2,
                        "Column_name": "task_submission",
                    },
                ],
                [
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 0,
                        "Seq_in_index": 1,
                        "Column_name": "task_outcome",
                    },
                    {
                        "Key_name": "uniq_task_feedback_workspace_outcome_submission",
                        "Non_unique": 0,
                        "Seq_in_index": 2,
                        "Column_name": "task_submission",
                    },
                ],
            ]
            sql_calls = []

            def fake_sql(query, as_dict=False):
                sql_calls.append(query)
                if query.startswith("SHOW INDEX"):
                    return index_states.pop(0)
                return []

            frappe.db.sql = fake_sql

            module = import_fresh("ifitwala_ed.assessment.doctype.task_feedback_workspace.task_feedback_workspace")
            module._ensure_indexes()

        self.assertIn(
            "ALTER TABLE `tabTask Feedback Workspace` DROP INDEX `uniq_task_feedback_workspace_outcome_submission`",
            sql_calls,
        )
        self.assertIn(
            "ALTER TABLE `tabTask Feedback Workspace` ADD UNIQUE INDEX `uniq_task_feedback_workspace_outcome_submission` (`task_outcome`, `task_submission`)",
            sql_calls,
        )
