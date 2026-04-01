# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/task/task.py

import frappe
from frappe import _
from frappe.model.document import Document


class Task(Document):
    def before_validate(self):
        self._require_course()
        self._validate_curriculum_alignment()

    def validate(self):
        self._enforce_quiz_defaults()
        self._validate_task_criteria_unique()
        self._enforce_grading_defaults()
        self._validate_governed_attachments()

    def on_trash(self):
        used = frappe.db.get_value("Task Delivery", {"task": self.name}, "name")
        if used:
            frappe.throw(_("This Task is already used in a delivery. Archive it instead."))

    def _doc_meta(self):
        if not hasattr(self, "_task_meta"):
            self._task_meta = frappe.get_meta(self.doctype)
        return self._task_meta

    def _has_field(self, fieldname):
        return bool(self._doc_meta().get_field(fieldname))

    def _course_fieldname(self):
        if self._has_field("course"):
            return "course"
        if self._has_field("default_course"):
            return "default_course"
        return None

    def _get_course_value(self):
        fieldname = self._course_fieldname()
        if not fieldname:
            return None
        return getattr(self, fieldname, None)

    def _require_course(self):
        fieldname = self._course_fieldname()
        if not fieldname:
            return
        field = self._doc_meta().get_field(fieldname)
        if field and field.reqd and not getattr(self, fieldname, None):
            frappe.throw(_("Select a Course or adjust the Task schema."))

    def _get_lesson_info(self, lesson_name):
        if not lesson_name:
            return {}
        return (
            frappe.db.get_value(
                "Lesson",
                lesson_name,
                ["course", "unit_plan"],
                as_dict=True,
            )
            or {}
        )

    def _get_unit_plan_course(self, unit_plan_name):
        if not unit_plan_name:
            return None
        return frappe.db.get_value("Unit Plan", unit_plan_name, "course")

    def _validate_curriculum_alignment(self):
        course = self._get_course_value()
        unit_plan_name = self.unit_plan or None
        lesson = self.lesson or None

        unit_course = None
        if unit_plan_name and course:
            unit_course = self._get_unit_plan_course(unit_plan_name)
            if unit_course and unit_course != course:
                frappe.throw(_("Unit Plan belongs to a different Course than the Task's Course."))

        if not lesson:
            return

        lesson_info = self._get_lesson_info(lesson)
        lesson_unit = lesson_info.get("unit_plan")
        lesson_course = lesson_info.get("course")

        if unit_plan_name and lesson_unit and lesson_unit != unit_plan_name:
            frappe.throw(_("Lesson does not belong to the selected Unit Plan."))

        if course:
            if not lesson_course and lesson_unit:
                if lesson_unit == unit_plan_name and unit_course:
                    lesson_course = unit_course
                else:
                    lesson_course = self._get_unit_plan_course(lesson_unit)
            if lesson_course and lesson_course != course:
                frappe.throw(_("Lesson belongs to a different Course than the Task's Course."))

    def _clear_grading_defaults(self):
        self.default_grade_scale = None
        self.default_max_points = None

    def _clear_quiz_defaults(self):
        for fieldname in (
            "quiz_question_bank",
            "quiz_question_count",
            "quiz_time_limit_minutes",
            "quiz_max_attempts",
            "quiz_pass_percentage",
            "quiz_shuffle_questions",
            "quiz_shuffle_choices",
        ):
            if self._has_field(fieldname):
                setattr(
                    self, fieldname, None if fieldname not in {"quiz_shuffle_questions", "quiz_shuffle_choices"} else 0
                )

    def _count_published_quiz_questions(self, question_bank):
        if not question_bank:
            return 0
        return int(
            frappe.db.count(
                "Quiz Question",
                {"question_bank": question_bank, "is_published": 1},
            )
            or 0
        )

    def _enforce_quiz_defaults(self):
        if (self.task_type or "").strip() != "Quiz":
            self._clear_quiz_defaults()
            return

        if not self.quiz_question_bank:
            frappe.throw(_("Quiz tasks require a Quiz Question Bank."))

        available_questions = self._count_published_quiz_questions(self.quiz_question_bank)
        if available_questions <= 0:
            frappe.throw(_("Quiz Question Bank must contain at least one published Quiz Question."))

        question_count = int(self.quiz_question_count or 0) if self.quiz_question_count not in (None, "") else 0
        if question_count < 0:
            frappe.throw(_("Questions Per Attempt cannot be negative."))
        if question_count and question_count > available_questions:
            frappe.throw(_("Questions Per Attempt cannot exceed the published questions in the bank."))
        if not question_count:
            self.quiz_question_count = available_questions

        if self.quiz_time_limit_minutes not in (None, "") and int(self.quiz_time_limit_minutes or 0) <= 0:
            frappe.throw(_("Time Limit must be greater than 0 minutes."))

        if self.quiz_max_attempts not in (None, "") and int(self.quiz_max_attempts or 0) < 0:
            frappe.throw(_("Maximum Attempts cannot be negative."))

        if self.quiz_pass_percentage not in (None, ""):
            try:
                pass_percentage = float(self.quiz_pass_percentage)
            except Exception:
                frappe.throw(_("Pass Percentage must be a number between 0 and 100."))
            if pass_percentage < 0 or pass_percentage > 100:
                frappe.throw(_("Pass Percentage must be between 0 and 100."))

    def _enforce_grading_defaults(self):
        if (self.task_type or "").strip() == "Quiz":
            if self.default_delivery_mode == "Assess":
                self.default_grading_mode = "Points"
                self.default_max_points = int(self.quiz_question_count or 0)
                if not self.default_max_points:
                    frappe.throw(_("Assessed quizzes require Questions Per Attempt to resolve Max Points."))
            else:
                self.default_grading_mode = "None"
                self._clear_grading_defaults()
            return

        if self.default_delivery_mode and self.default_delivery_mode != "Assess":
            self.default_grading_mode = "None"
            self._clear_grading_defaults()
            return

        if self.default_grading_mode == "Points":
            if not self.default_max_points or float(self.default_max_points) <= 0:
                frappe.throw(_("Default Max Points must be greater than 0 when grading mode is Points."))

        if self.default_grading_mode == "Criteria":
            if not self.default_rubric_scoring_strategy:
                self.default_rubric_scoring_strategy = "Sum Total"
            if not self._has_task_criteria():
                frappe.throw(_("At least one Task Criteria row is required when grading mode is Criteria."))

    def _has_task_criteria(self):
        rows = self.get("task_criteria") or []
        return any((row.get("assessment_criteria") or "").strip() for row in rows)

    def _validate_task_criteria_unique(self):
        rows = self.get("task_criteria") or []
        seen = set()
        for row in rows:
            criteria = (row.get("assessment_criteria") or "").strip()
            if not criteria:
                continue
            if criteria in seen:
                frappe.throw(_("Duplicate Assessment Criteria in Task Criteria are not allowed."))
            seen.add(criteria)

    def _validate_governed_attachments(self):
        rows = self.get("attachments") or []
        if not rows:
            return

        before = None if self.is_new() else self.get_doc_before_save()
        unchanged_files = {}
        if before:
            for row in before.get("attachments") or []:
                row_name = (row.get("name") or "").strip()
                if row_name:
                    unchanged_files[row_name] = (row.get("file") or "").strip()

        for row in rows:
            file_url = (row.get("file") or "").strip()
            if not file_url:
                continue

            row_name = (row.get("name") or "").strip()
            if row_name and unchanged_files.get(row_name) == file_url:
                continue

            if not self.name:
                frappe.throw(_("Save the Task before attaching governed resources."))

            file_name = frappe.db.get_value(
                "File",
                {
                    "attached_to_doctype": "Task",
                    "attached_to_name": self.name,
                    "file_url": file_url,
                },
                "name",
            )
            if not file_name:
                frappe.throw(_("Task resources must be uploaded through the governed Task resource action."))

            if not row_name:
                frappe.throw(_("Task resource rows must carry a stable governed row key."))

            binding_name = frappe.db.get_value(
                "Drive Binding",
                {
                    "binding_doctype": "Task",
                    "binding_name": self.name,
                    "binding_role": "task_resource",
                    "slot": f"supporting_material__{row_name}",
                    "file": file_name,
                    "status": "active",
                },
                "name",
            )
            if binding_name:
                continue

            drive_file_name = frappe.db.get_value(
                "Drive File",
                {
                    "owner_doctype": "Task",
                    "owner_name": self.name,
                    "slot": f"supporting_material__{row_name}",
                    "file": file_name,
                    "status": ["in", ["active", "processing", "blocked"]],
                },
                "name",
            )
            if not drive_file_name:
                frappe.throw(_("Task resource rows must resolve to an active governed Drive file or binding."))
