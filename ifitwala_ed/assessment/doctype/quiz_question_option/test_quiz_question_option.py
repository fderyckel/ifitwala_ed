from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


class TestQuizQuestionOption(TestCase):
    def test_module_exposes_standard_doctype_controller(self):
        with stubbed_frappe():
            module = import_fresh("ifitwala_ed.assessment.doctype.quiz_question_option.quiz_question_option")

        controller = getattr(module, "QuizQuestionOption", None)
        self.assertIsNotNone(controller)
        self.assertEqual(controller.__name__, "QuizQuestionOption")
