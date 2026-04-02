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

        planning_stub = types.ModuleType("ifitwala_ed.curriculum.planning")
        planning_stub.normalize_text = lambda value: str(value or "").strip()
        planning_stub.normalize_long_text = lambda value: str(value or "").strip() or None
        planning_stub.normalize_flag = lambda value: 1 if str(value or "").strip() in {"1", "True", "true"} else 0
        planning_stub.user_has_global_curriculum_access = lambda user, roles=None: False
        planning_stub.get_curriculum_manageable_course_names = lambda user, roles=None: ["COURSE-1"]
        planning_stub.user_can_read_course_curriculum = lambda user, course, roles=None: course == "COURSE-1"
        planning_stub.user_can_manage_course_curriculum = lambda user, course, roles=None: course == "COURSE-1"
        planning_stub.assert_can_read_course_curriculum = lambda user, course, roles=None, action_label=None: None
        planning_stub.assert_can_manage_course_curriculum = lambda user, course, roles=None, action_label=None: None
        planning_stub.get_course_plan_row = lambda course_plan: {
            "name": course_plan,
            "course": "COURSE-1",
        }

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.api.courses": courses_stub,
                "ifitwala_ed.curriculum.planning": planning_stub,
            }
        ):
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

    def test_save_question_bank_creates_bank_and_questions(self):
        created = {"bank": 0, "question": 0}

        class FakeBankDoc:
            def __init__(self):
                self.name = "QBK-1"
                self.course = None
                self.bank_title = None
                self.description = None
                self.is_published = 0

            def is_new(self):
                return True

            def insert(self, ignore_permissions=False):
                created["bank"] += 1

        class FakeQuestionDoc:
            def __init__(self):
                self.name = f"QQ-{created['question'] + 1}"
                self.question_bank = None
                self.title = None
                self.question_type = None
                self.is_published = 0
                self.prompt = None
                self.accepted_answers = None
                self.explanation = None
                self.options = []

            def set(self, fieldname, value):
                setattr(self, fieldname, value)

            def is_new(self):
                return True

            def insert(self, ignore_permissions=False):
                created["question"] += 1

        bank_doc = FakeBankDoc()
        question_docs = [FakeQuestionDoc(), FakeQuestionDoc()]

        def fake_new_doc(doctype):
            if doctype == "Quiz Question Bank":
                return bank_doc
            if doctype == "Quiz Question":
                return question_docs.pop(0)
            raise AssertionError(f"Unexpected new_doc call: {doctype}")

        with (
            patch.object(self.quiz_api.frappe, "new_doc", side_effect=fake_new_doc),
            patch.object(self.quiz_api.frappe, "get_all", return_value=[]),
        ):
            payload = self.quiz_api.save_question_bank(
                {
                    "course_plan": "COURSE-PLAN-1",
                    "bank_title": "Cells Check-in",
                    "description": "Shared quiz bank",
                    "is_published": 1,
                    "questions_json": [
                        {
                            "title": "Where is the nucleus?",
                            "question_type": "Single Choice",
                            "is_published": 1,
                            "prompt": "Choose the organelle that stores genetic material.",
                            "options": [
                                {"option_text": "Nucleus", "is_correct": 1},
                                {"option_text": "Ribosome", "is_correct": 0},
                            ],
                        },
                        {
                            "title": "Cell membrane function",
                            "question_type": "Short Answer",
                            "is_published": 1,
                            "prompt": "What does the cell membrane do?",
                            "accepted_answers": "Controls entry and exit",
                        },
                    ],
                }
            )

        self.assertEqual(bank_doc.course, "COURSE-1")
        self.assertEqual(bank_doc.bank_title, "Cells Check-in")
        self.assertEqual(created["bank"], 1)
        self.assertEqual(created["question"], 2)
        self.assertEqual(payload["quiz_question_bank"], "QBK-1")

    def test_list_question_banks_filters_to_manageable_instructor_courses(self):
        with (
            patch.object(self.quiz_api.frappe, "get_roles", return_value=["Instructor"]),
            patch.object(
                self.quiz_api.frappe,
                "get_all",
                return_value=[{"name": "QBK-1", "bank_title": "Cells", "course": "COURSE-1"}],
            ) as get_all,
        ):
            payload = self.quiz_api.list_question_banks()

        self.assertEqual(payload[0]["course"], "COURSE-1")
        self.assertEqual(get_all.call_args.kwargs["filters"]["course"], ["in", ["COURSE-1"]])
