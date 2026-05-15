from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestQuizService(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with stubbed_frappe():
            cls.quiz_service = import_fresh("ifitwala_ed.assessment.quiz_service")

    def test_score_item_marks_exact_single_choice_match_correct(self):
        result = self.quiz_service._score_item(
            {
                "question_type": "Single Choice",
                "grading_payload": '{"correct_ids":["OPT-2"]}',
                "response_payload": '["OPT-2"]',
            }
        )

        self.assertEqual(result["score"], 1.0)
        self.assertFalse(result["manual_pending"])
        self.assertEqual(result["updates"]["is_correct"], 1)

    def test_score_item_marks_short_answer_by_normalized_match(self):
        result = self.quiz_service._score_item(
            {
                "question_type": "Short Answer",
                "grading_payload": '{"accepted_answers":["mitosis","cell division"]}',
                "response_text": "Mitosis",
            }
        )

        self.assertEqual(result["score"], 1.0)
        self.assertEqual(result["updates"]["is_correct"], 1)

    def test_score_item_flags_essay_for_manual_review_until_awarded(self):
        result = self.quiz_service._score_item(
            {
                "question_type": "Essay",
                "grading_payload": '{"question_type":"Essay"}',
                "awarded_score": None,
            }
        )

        self.assertIsNone(result["score"])
        self.assertTrue(result["manual_pending"])
        self.assertEqual(result["updates"]["requires_manual_grading"], 1)

    def test_public_attempt_summary_redacts_assessed_feedback(self):
        summary = self.quiz_service._public_attempt_summary(
            {
                "name": "QAT-1",
                "attempt_number": 2,
                "status": "Submitted",
                "submitted_on": None,
                "score": 7.0,
                "percentage": 70.0,
                "passed": 1,
                "requires_manual_review": 0,
            },
            show_grade=False,
        )

        self.assertEqual(summary["attempt_id"], "QAT-1")
        self.assertIsNone(summary["score"])
        self.assertIsNone(summary["percentage"])
        self.assertEqual(summary["passed"], 0)

    def test_public_review_item_redacts_correctness_when_feedback_is_withheld(self):
        payload = self.quiz_service._public_review_item(
            {
                "name": "QAI-1",
                "position": 1,
                "question_type": "Single Choice",
                "prompt_html": "<p>Pick one</p>",
                "option_payload": '[{"id":"OPT-1","text":"A"}]',
                "response_payload": '["OPT-1"]',
                "response_text": None,
                "awarded_score": 1.0,
                "is_correct": 1,
                "requires_manual_grading": 0,
            },
            grading_payload={
                "correct_ids": ["OPT-2"],
                "accepted_answers": ["answer"],
                "explanation": "<p>Because</p>",
            },
            show_grade=False,
            show_feedback=False,
        )

        self.assertEqual(payload["selected_option_ids"], ["OPT-1"])
        self.assertIsNone(payload["awarded_score"])
        self.assertEqual(payload["is_correct"], 0)
        self.assertEqual(payload["correct_option_ids"], [])
        self.assertIsNone(payload["explanation_html"])

    def test_student_release_view_uses_release_payload_for_assessed_quizzes(self):
        with patch.object(
            self.quiz_service.task_feedback_service,
            "build_released_result_payload",
            return_value={
                "outcome_id": "OUT-1",
                "grade_visible": True,
                "feedback_visible": False,
                "publication": {
                    "feedback_visibility": "hidden",
                    "grade_visibility": "student",
                    "derived_from_legacy_outcome": False,
                    "legacy_outcome_published": False,
                },
                "official": {
                    "score": 8,
                    "grade": "B",
                    "grade_value": 3,
                    "feedback": None,
                },
                "feedback": None,
            },
        ) as build_release:
            payload = self.quiz_service._student_release_view(
                {"delivery_mode": "Assess"},
                "OUT-1",
            )

        build_release.assert_called_once_with("OUT-1", audience="student")
        self.assertTrue(payload["grade_visible"])
        self.assertFalse(payload["feedback_visible"])
        self.assertEqual(payload["released_result"]["official"]["score"], 8)

    def test_save_attempt_responses_rejects_expired_attempts(self):
        with (
            patch.object(
                self.quiz_service,
                "_get_attempt_bundle",
                return_value=(
                    {
                        "name": "QAT-1",
                        "status": "In Progress",
                        "expires_on": "2026-03-13 10:00:00",
                    },
                    {},
                    {},
                ),
            ),
            patch.object(self.quiz_service, "_attempt_expired", return_value=True),
        ):
            with self.assertRaises(self.quiz_service.frappe.ValidationError):
                self.quiz_service.save_attempt_responses(
                    attempt="QAT-1",
                    responses=[{"item_id": "QAI-1", "response_text": "mitosis"}],
                    student="STU-1",
                )
