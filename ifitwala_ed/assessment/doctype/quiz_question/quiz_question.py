# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class QuizQuestion(Document):
    def validate(self):
        self._validate_question_type()
        self._validate_choice_payload()
        self._validate_short_answer_payload()

    def _validate_question_type(self):
        allowed = {"Single Choice", "Multiple Answer", "True / False", "Short Answer", "Essay"}
        question_type = (self.question_type or "").strip()
        if question_type not in allowed:
            frappe.throw(_("Unsupported quiz question type."))

    def _option_rows(self):
        return [row for row in (self.get("options") or []) if (row.get("option_text") or "").strip()]

    def _accepted_answers(self):
        return [row.strip().lower() for row in str(self.accepted_answers or "").splitlines() if row.strip()]

    def _validate_choice_payload(self):
        question_type = (self.question_type or "").strip()
        option_rows = self._option_rows()
        correct_count = sum(1 for row in option_rows if int(row.get("is_correct") or 0) == 1)

        if question_type in {"Single Choice", "Multiple Answer", "True / False"}:
            if len(option_rows) < 2:
                frappe.throw(_("Choice-based quiz questions require at least two options."))
            if correct_count <= 0:
                frappe.throw(_("Choice-based quiz questions require at least one correct option."))
            if question_type in {"Single Choice", "True / False"} and correct_count != 1:
                frappe.throw(_("Single-choice and True / False questions require exactly one correct option."))
            if question_type == "True / False" and len(option_rows) != 2:
                frappe.throw(_("True / False questions require exactly two options."))
            return

        if option_rows:
            frappe.throw(_("Options are only allowed for choice-based quiz questions."))

    def _validate_short_answer_payload(self):
        question_type = (self.question_type or "").strip()
        answers = self._accepted_answers()
        if question_type == "Short Answer":
            if not answers:
                frappe.throw(_("Short Answer questions require at least one accepted answer."))
            return

        if answers:
            frappe.throw(_("Accepted Answers are only allowed for Short Answer questions."))
