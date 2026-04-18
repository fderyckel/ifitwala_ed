from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestGradebookSupport(TestCase):
    def test_build_delivery_criteria_payload_derives_local_points_from_delivery_max_points(self):
        quiz_service = types.ModuleType("ifitwala_ed.assessment.quiz_service")
        quiz_service.MANUAL_TYPES = set()

        task_submission_service = types.ModuleType("ifitwala_ed.assessment.task_submission_service")

        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        image_utils.apply_preferred_student_images = lambda rows, **kwargs: rows

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.assessment.quiz_service": quiz_service,
                "ifitwala_ed.assessment.task_submission_service": task_submission_service,
                "ifitwala_ed.utilities.image_utils": image_utils,
            }
        ) as frappe:

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0):
                if doctype == "Task Rubric Criterion":
                    return [
                        {
                            "assessment_criteria": "CRIT-ANALYSIS",
                            "criteria_name": "Analysis",
                            "criteria_weighting": 40,
                            "criteria_max_points": 8,
                        }
                    ]
                if doctype == "Assessment Criteria Level":
                    return [
                        {"parent": "CRIT-ANALYSIS", "achievement_level": "Emerging"},
                        {"parent": "CRIT-ANALYSIS", "achievement_level": "Developing"},
                        {"parent": "CRIT-ANALYSIS", "achievement_level": "Proficient"},
                        {"parent": "CRIT-ANALYSIS", "achievement_level": "Advanced"},
                    ]
                return []

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.gradebook_support")
            payload = module._build_delivery_criteria_payload(
                {
                    "grading_mode": "Criteria",
                    "rubric_version": "TRV-1",
                }
            )

        self.assertEqual(
            payload,
            [
                {
                    "assessment_criteria": "CRIT-ANALYSIS",
                    "criteria_name": "Analysis",
                    "criteria_weighting": 40.0,
                    "levels": [
                        {"level": "Emerging", "points": 2},
                        {"level": "Developing", "points": 4},
                        {"level": "Proficient", "points": 6},
                        {"level": "Advanced", "points": 8},
                    ],
                }
            ],
        )
