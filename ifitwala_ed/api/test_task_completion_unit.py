from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _task_completion_stub_modules():
    courses = types.ModuleType("ifitwala_ed.api.courses")
    courses._require_student_name_for_session_user = lambda: "STU-1"
    courses._serialize_scalar = lambda value: value

    task_outcome_service = types.ModuleType("ifitwala_ed.assessment.task_outcome_service")
    task_outcome_service.set_assign_only_completion = lambda *args, **kwargs: {
        "outcome": args[0],
        "is_complete": 1,
        "completed_on": "2026-04-22 09:15:00",
    }

    return {
        "ifitwala_ed.api.courses": courses,
        "ifitwala_ed.assessment.task_outcome_service": task_outcome_service,
    }


class TestTaskCompletionApiUnit(TestCase):
    def test_mark_assign_only_complete_uses_student_owned_direct_completion_path(self):
        with stubbed_frappe(extra_modules=_task_completion_stub_modules()):
            calls = []

            def fake_mark_assign_only_completion(
                outcome_id, *, is_complete, expected_student=None, ignore_permissions=False
            ):
                calls.append(
                    {
                        "outcome_id": outcome_id,
                        "is_complete": is_complete,
                        "expected_student": expected_student,
                        "ignore_permissions": ignore_permissions,
                    }
                )
                return {
                    "outcome": outcome_id,
                    "is_complete": 1,
                    "completed_on": "2026-04-22 09:15:00",
                }

            module = import_fresh("ifitwala_ed.api.task_completion")
            module.task_outcome_service.set_assign_only_completion = fake_mark_assign_only_completion

            payload = module.mark_assign_only_complete(payload={"task_outcome": "OUT-1"})

        self.assertEqual(
            calls,
            [
                {
                    "outcome_id": "OUT-1",
                    "is_complete": 1,
                    "expected_student": "STU-1",
                    "ignore_permissions": True,
                }
            ],
        )
        self.assertEqual(
            payload,
            {
                "task_outcome": "OUT-1",
                "is_complete": 1,
                "completed_on": "2026-04-22 09:15:00",
            },
        )

    def test_mark_assign_only_complete_accepts_flat_kwargs(self):
        with stubbed_frappe(extra_modules=_task_completion_stub_modules()):
            module = import_fresh("ifitwala_ed.api.task_completion")
            payload = module.mark_assign_only_complete(task_outcome="OUT-2")

        self.assertEqual(payload["task_outcome"], "OUT-2")
        self.assertEqual(payload["is_complete"], 1)
