from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestGradebookSupport(TestCase):
    def test_get_student_meta_map_requests_derivative_only_student_images(self):
        helper_state = {"calls": []}

        quiz_service = types.ModuleType("ifitwala_ed.assessment.quiz_service")
        quiz_service.MANUAL_TYPES = set()
        task_submission_service = types.ModuleType("ifitwala_ed.assessment.task_submission_service")
        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = (
            "profile_image_thumb",
            "profile_image_card",
            "profile_image_medium",
        )

        def apply_preferred_student_images(rows, **kwargs):
            helper_state["calls"].append(kwargs)
            return rows

        image_utils.apply_preferred_student_images = apply_preferred_student_images

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.assessment.quiz_service": quiz_service,
                "ifitwala_ed.assessment.task_submission_service": task_submission_service,
                "ifitwala_ed.utilities.image_utils": image_utils,
            }
        ) as frappe:
            frappe.get_meta = lambda doctype: types.SimpleNamespace(
                get_field=lambda fieldname: fieldname in {"student_preferred_name", "student_id", "student_image"}
            )

            def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=0):
                self.assertEqual(doctype, "Student")
                self.assertEqual(limit, 0)
                return [
                    {
                        "name": "STU-0001",
                        "student_preferred_name": "Amina",
                        "student_id": "S-001",
                        "student_image": "/private/files/student/original.png",
                    }
                ]

            frappe.get_all = fake_get_all

            module = import_fresh("ifitwala_ed.api.gradebook_support")
            payload = module._get_student_meta_map(["STU-0001"])

        self.assertEqual(payload["STU-0001"]["student_id"], "S-001")
        self.assertEqual(
            helper_state["calls"],
            [
                {
                    "student_field": "name",
                    "image_field": "student_image",
                    "slots": (
                        "profile_image_thumb",
                        "profile_image_card",
                        "profile_image_medium",
                    ),
                    "fallback_to_original": False,
                    "request_missing_derivatives": True,
                }
            ],
        )

    def test_build_delivery_criteria_payload_derives_local_points_from_delivery_max_points(self):
        quiz_service = types.ModuleType("ifitwala_ed.assessment.quiz_service")
        quiz_service.MANUAL_TYPES = set()

        task_submission_service = types.ModuleType("ifitwala_ed.assessment.task_submission_service")

        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = (
            "profile_image_thumb",
            "profile_image_card",
            "profile_image_medium",
        )
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
