import types
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestQuizApi(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        courses_stub = types.ModuleType("ifitwala_ed.api.courses")
        courses_stub._require_student_name_for_session_user = lambda: "STU-1"
        courses_stub._build_student_course_scope = lambda student: {"COURSE-1": {}}

        with stubbed_frappe(extra_modules={"ifitwala_ed.api.courses": courses_stub}):
            cls.quiz_api = import_fresh("ifitwala_ed.api.quiz")

    def test_open_session_uses_service_with_student_scope(self):
        with (
            patch.object(self.quiz_api, "_require_student_scope", return_value="STU-1"),
            patch.object(
                self.quiz_api.quiz_service,
                "open_quiz_session",
                return_value={"mode": "attempt", "session": {"attempt_id": "QAT-1"}},
            ) as open_session,
        ):
            payload = self.quiz_api.open_session(task_delivery="TDL-1")

        self.assertEqual(payload["mode"], "attempt")
        open_session.assert_called_once_with(
            task_delivery="TDL-1",
            student="STU-1",
            user=self.quiz_api.frappe.session.user,
        )

    def test_save_attempt_uses_direct_payload_body(self):
        with (
            patch.object(self.quiz_api, "_require_student_for_attempt", return_value="STU-1"),
            patch.object(
                self.quiz_api.quiz_service,
                "save_attempt_responses",
                return_value={"attempt": "QAT-1", "status": "In Progress"},
            ) as save_attempt,
        ):
            payload = self.quiz_api.save_attempt(
                payload={
                    "attempt_id": "QAT-1",
                    "responses": [{"item_id": "QAI-1", "selected_option_ids": ["OPT-1"]}],
                }
            )

        self.assertEqual(payload["attempt"], "QAT-1")
        save_attempt.assert_called_once_with(
            attempt="QAT-1",
            responses=[{"item_id": "QAI-1", "selected_option_ids": ["OPT-1"]}],
            student="STU-1",
        )

    def test_submit_attempt_uses_direct_payload_body(self):
        with (
            patch.object(self.quiz_api, "_require_student_for_attempt", return_value="STU-1"),
            patch.object(
                self.quiz_api.quiz_service,
                "submit_attempt",
                return_value={"attempt": {"name": "QAT-1", "status": "Submitted"}},
            ) as submit_attempt,
        ):
            payload = self.quiz_api.submit_attempt(
                payload={
                    "attempt_id": "QAT-1",
                    "responses": [{"item_id": "QAI-1", "response_text": "cell membrane"}],
                }
            )

        self.assertEqual(payload["attempt"]["status"], "Submitted")
        submit_attempt.assert_called_once_with(
            attempt="QAT-1",
            responses=[{"item_id": "QAI-1", "response_text": "cell membrane"}],
            student="STU-1",
            user=self.quiz_api.frappe.session.user,
        )
