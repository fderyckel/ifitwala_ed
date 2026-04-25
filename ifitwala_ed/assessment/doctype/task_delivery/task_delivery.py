# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime

from ifitwala_ed.assessment.check_flags import is_checked
from ifitwala_ed.assessment.task_delivery_service import (
    bulk_create_outcomes,
    get_delivery_context,
    get_eligible_students,
)


class TaskDelivery(Document):
    def before_validate(self):
        self._require_task_and_group()
        context = get_delivery_context(self.student_group)
        self._stamp_context(context)
        self._validate_task_course_alignment(context)
        self._validate_class_teaching_plan_context()
        self._validate_class_session_context()
        self._apply_quiz_defaults()

    def validate(self):
        self._enforce_post_submit_immutability()
        self._apply_delivery_mode_defaults()
        self._validate_dates()
        self._validate_delivery_mode_coherence()
        self._validate_group_submission()

    def on_submit(self):
        self.materialize_roster()

    def materialize_roster(self):
        if self.delivery_mode == "Assess" and self.grading_mode == "Criteria":
            self._ensure_rubric_snapshot()

        students = get_eligible_students(self.student_group)
        outcomes_created = bulk_create_outcomes(self, students, context=self._current_context())
        return {
            "eligible_students": len(students),
            "outcomes_created": outcomes_created,
        }

    def on_cancel(self):
        if self._has_evidence():
            frappe.throw(_("Cannot cancel delivery once evidence exists."))

        frappe.db.delete("Task Outcome", {"task_delivery": self.name})

    def _doc_meta(self):
        if not hasattr(self, "_delivery_meta"):
            self._delivery_meta = frappe.get_meta(self.doctype)
        return self._delivery_meta

    def _has_field(self, fieldname):
        return bool(self._doc_meta().get_field(fieldname))

    def _current_context(self):
        context = {
            "course": getattr(self, "course", None),
            "academic_year": getattr(self, "academic_year", None),
            "school": getattr(self, "school", None),
        }
        if self._has_field("program"):
            context["program"] = getattr(self, "program", None)
        if self._has_field("course_group"):
            context["course_group"] = getattr(self, "course_group", None)
        return context

    def _require_task_and_group(self):
        if not self.task:
            frappe.throw(_("Task is required for Task Delivery."))
        if not self.student_group:
            frappe.throw(_("Student Group is required for Task Delivery."))
        if self._has_field("class_teaching_plan") and not getattr(self, "class_teaching_plan", None):
            frappe.throw(_("Class Teaching Plan is required for Task Delivery."))

    def _stamp_context(self, context):
        field_map = {
            "course": "course",
            "academic_year": "academic_year",
            "school": "school",
            "program": "program",
        }
        for source_key, fieldname in field_map.items():
            if self._has_field(fieldname):
                setattr(self, fieldname, context.get(source_key))

        missing = [
            label
            for label, fieldname in (
                ("Course", "course"),
                ("Academic Year", "academic_year"),
                ("School", "school"),
            )
            if self._has_field(fieldname) and not getattr(self, fieldname, None)
        ]
        if missing:
            frappe.throw(_("Missing context on Student Group: {0}.").format(", ".join(missing)))

    def _get_task_course(self):
        meta = frappe.get_meta("Task")
        fields = []
        for fieldname in ("course", "default_course"):
            if meta.get_field(fieldname):
                fields.append(fieldname)
        if not fields:
            return None

        values = frappe.db.get_value("Task", self.task, fields, as_dict=True) or {}
        for fieldname in fields:
            if values.get(fieldname):
                return values.get(fieldname)
        return None

    def _validate_task_course_alignment(self, context):
        task_course = self._get_task_course()
        delivery_course = context.get("course")
        if task_course and delivery_course and task_course != delivery_course:
            frappe.throw(_("Task course does not match the delivery course."))

    def _validate_class_teaching_plan_context(self):
        if not self._has_field("class_teaching_plan"):
            return

        class_teaching_plan = (getattr(self, "class_teaching_plan", None) or "").strip()
        if not class_teaching_plan:
            frappe.throw(_("Class Teaching Plan is required for Task Delivery."))

        plan = frappe.db.get_value(
            "Class Teaching Plan",
            class_teaching_plan,
            ["name", "student_group", "course", "academic_year", "planning_status"],
            as_dict=True,
        )
        if not plan:
            frappe.throw(_("Class Teaching Plan not found."))
        planning_status = (plan.get("planning_status") or "").strip()
        if planning_status == "Archived":
            frappe.throw(_("Archived Class Teaching Plans cannot receive new assigned work."))
        if planning_status != "Active":
            frappe.throw(_("This class needs an active Class Teaching Plan before assigned work can be created."))
        if plan.get("student_group") and plan.get("student_group") != self.student_group:
            frappe.throw(_("Selected Class Teaching Plan does not belong to this class."))
        if self._has_field("course") and plan.get("course") and plan.get("course") != self.course:
            frappe.throw(_("Selected Class Teaching Plan does not belong to this course."))
        if (
            self._has_field("academic_year")
            and plan.get("academic_year")
            and plan.get("academic_year") != getattr(self, "academic_year", None)
        ):
            frappe.throw(_("Selected Class Teaching Plan does not belong to this academic year."))

    def _validate_class_session_context(self):
        if not self._has_field("class_session") or not getattr(self, "class_session", None):
            return

        session = frappe.db.get_value(
            "Class Session",
            self.class_session,
            ["name", "class_teaching_plan", "student_group", "course", "academic_year"],
            as_dict=True,
        )
        if not session:
            frappe.throw(_("Class Session not found."))

        if (
            self._has_field("class_teaching_plan")
            and session.get("class_teaching_plan")
            and session.get("class_teaching_plan") != getattr(self, "class_teaching_plan", None)
        ):
            frappe.throw(_("Selected class session does not belong to this Class Teaching Plan."))

        if session.get("student_group") and session.get("student_group") != self.student_group:
            frappe.throw(_("Selected class session does not belong to this class."))

        if self._has_field("course") and session.get("course") and session.get("course") != self.course:
            frappe.throw(_("Selected class session does not belong to this course."))

        if (
            self._has_field("academic_year")
            and session.get("academic_year")
            and session.get("academic_year") != getattr(self, "academic_year", None)
        ):
            frappe.throw(_("Selected class session does not belong to this academic year."))

    def _apply_delivery_mode_defaults(self):
        if not self.delivery_mode:
            return

        self._set_allow_feedback_from_defaults()

        if self.delivery_mode == "Assign Only":
            self.requires_submission = 0
            self.require_grading = 0
            if self._has_field("allow_late_submission"):
                self.allow_late_submission = 0
            self._clear_grading_fields(clear_feedback=True)
            return

        if self.delivery_mode == "Collect Work":
            self.requires_submission = 1
            self.require_grading = 0
            self._clear_grading_fields(clear_feedback=True)
            return

        if self.delivery_mode == "Assess":
            self.require_grading = 1
            self._set_grade_scale_from_defaults()
            if self._is_quiz_task():
                self.requires_submission = 0
                self.grading_mode = "Points"
                self.rubric_version = None
                if self._has_field("rubric_scoring_strategy"):
                    self.rubric_scoring_strategy = None
                self.max_points = self._resolve_quiz_max_points()
                return
            self._ensure_grading_mode()
            self._set_requires_submission_from_defaults()

            if self.grading_mode in ("Completion", "Binary"):
                self._clear_grading_fields(keep_mode=True)

            if self.grading_mode == "Points":
                self.rubric_version = None
                if self._has_field("rubric_scoring_strategy"):
                    self.rubric_scoring_strategy = None
                self._set_max_points_from_defaults()

            if self.grading_mode == "Criteria":
                self.max_points = None
                self._set_rubric_scoring_strategy_from_defaults()

    def _ensure_grading_mode(self):
        if self.grading_mode and self.grading_mode != "None":
            return

        defaults = self._get_task_defaults()
        default_mode = defaults.get("default_grading_mode")
        if default_mode and default_mode != "None":
            self.grading_mode = default_mode
            return

        self.grading_mode = "Completion"

    def _set_requires_submission_from_defaults(self):
        if getattr(self.flags, "explicit_requires_submission", False):
            self.requires_submission = 1 if int(self.requires_submission or 0) else 0
            return

        defaults = self._get_task_defaults()
        default_requires = defaults.get("default_requires_submission")
        if default_requires in (0, 1, "0", "1", True, False):
            self.requires_submission = 1 if int(default_requires) else 0
            return

        if self.grading_mode in ("Points", "Criteria"):
            self.requires_submission = 1
        else:
            self.requires_submission = 0

    def _set_allow_feedback_from_defaults(self):
        if not self._has_field("allow_feedback"):
            return
        if getattr(self, "allow_feedback", None) not in (None, ""):
            return

        defaults = self._get_task_defaults()
        default_feedback = defaults.get("default_allow_feedback")
        if default_feedback in (0, 1, "0", "1", True, False):
            self.allow_feedback = 1 if int(default_feedback) else 0

    def _clear_grading_fields(self, keep_mode=False, clear_feedback=False):
        if not keep_mode:
            self.grading_mode = None
        self.max_points = None
        self.grade_scale = None
        self.rubric_version = None
        if self._has_field("rubric_scoring_strategy"):
            self.rubric_scoring_strategy = None
        if clear_feedback and self._has_field("allow_feedback"):
            self.allow_feedback = 0

    def _validate_dates(self):
        available_from = get_datetime(self.available_from) if self.available_from else None
        due_date = get_datetime(self.due_date) if self.due_date else None
        lock_date = get_datetime(self.lock_date) if self.lock_date else None

        if available_from and due_date and available_from > due_date:
            frappe.throw(_("Available From must be before or on Due Date."))

        if due_date and lock_date and due_date > lock_date:
            frappe.throw(_("Due Date must be before or on Lock Date."))

    def _validate_delivery_mode_coherence(self):
        if self._is_quiz_task():
            self._validate_quiz_configuration()

        if self.delivery_mode == "Assign Only":
            if self.requires_submission:
                frappe.throw(_("Assign Only deliveries cannot require submission."))
            if self.grading_mode or self.max_points or self.grade_scale or self.rubric_version:
                frappe.throw(_("Assign Only deliveries cannot include grading settings."))
            return

        if self.delivery_mode == "Collect Work":
            if not self.requires_submission:
                frappe.throw(_("Collect Work deliveries require submission."))
            if self.grading_mode or self.max_points or self.grade_scale or self.rubric_version:
                frappe.throw(_("Collect Work deliveries cannot include grading settings."))
            return

        if self.delivery_mode == "Assess":
            if not self.grading_mode or self.grading_mode == "None":
                frappe.throw(_("Assess deliveries require a grading mode."))

            if self.grading_mode == "Points":
                if not self.max_points or float(self.max_points) <= 0:
                    frappe.throw(_("Max Points must be greater than 0 for Points grading."))

            if self.grading_mode == "Criteria":
                if not self.rubric_version and not self._get_task_criteria_rows():
                    frappe.throw(_("Criteria grading requires Task criteria."))
                if self._has_field("rubric_scoring_strategy") and not self.rubric_scoring_strategy:
                    frappe.throw(_("Rubric Scoring Strategy is required for Criteria grading."))

    def _is_quiz_task(self):
        defaults = self._get_task_defaults()
        return (defaults.get("task_type") or "").strip() == "Quiz" and bool(defaults.get("quiz_question_bank"))

    def _apply_quiz_defaults(self):
        defaults = self._get_task_defaults()
        quiz_fields = (
            "quiz_question_bank",
            "quiz_question_count",
            "quiz_time_limit_minutes",
            "quiz_max_attempts",
            "quiz_pass_percentage",
            "quiz_shuffle_questions",
            "quiz_shuffle_choices",
        )
        if not self._is_quiz_task():
            for fieldname in quiz_fields:
                if self._has_field(fieldname):
                    setattr(
                        self,
                        fieldname,
                        None if fieldname not in {"quiz_shuffle_questions", "quiz_shuffle_choices"} else 0,
                    )
            return

        for fieldname in quiz_fields:
            if self._has_field(fieldname):
                setattr(self, fieldname, defaults.get(fieldname))

    def _resolve_quiz_max_points(self):
        question_count = int(getattr(self, "quiz_question_count", 0) or 0)
        if question_count <= 0:
            frappe.throw(_("Quiz deliveries require Questions Per Attempt to resolve Max Points."))
        return question_count

    def _validate_quiz_configuration(self):
        if self.delivery_mode == "Assess" and self.grading_mode != "Points":
            frappe.throw(_("Assessed quizzes use Points grading in phase 1."))
        if self.requires_submission:
            frappe.throw(_("Quiz deliveries must not require Task Submission evidence."))
        if not getattr(self, "quiz_question_bank", None):
            frappe.throw(_("Quiz deliveries require a Quiz Question Bank snapshot."))
        if int(getattr(self, "quiz_question_count", 0) or 0) <= 0:
            frappe.throw(_("Quiz deliveries require Questions Per Attempt greater than 0."))

    def _validate_group_submission(self):
        if is_checked(self.group_submission):
            frappe.throw(_("Group submission is paused: subgroup model not implemented."))

    def _get_task_criteria_rows(self):
        if not self.task:
            return []

        rows = (
            frappe.db.get_values(
                "Task Template Criterion",
                {
                    "parent": self.task,
                    "parenttype": "Task",
                    "parentfield": "task_criteria",
                },
                ["assessment_criteria", "criteria_weighting", "criteria_max_points"],
                as_dict=True,
            )
            or []
        )

        return [row for row in rows if row.get("assessment_criteria")]

    def _get_task_defaults(self):
        if hasattr(self, "_task_defaults"):
            return self._task_defaults

        if not self.task:
            self._task_defaults = {}
            return self._task_defaults

        meta = frappe.get_meta("Task")
        fields = [
            fieldname
            for fieldname in (
                "default_requires_submission",
                "default_grading_mode",
                "default_allow_feedback",
                "default_rubric_scoring_strategy",
                "default_grade_scale",
                "default_max_points",
                "task_type",
                "quiz_question_bank",
                "quiz_question_count",
                "quiz_time_limit_minutes",
                "quiz_max_attempts",
                "quiz_pass_percentage",
                "quiz_shuffle_questions",
                "quiz_shuffle_choices",
            )
            if meta.get_field(fieldname)
        ]
        if not fields:
            self._task_defaults = {}
            return self._task_defaults

        self._task_defaults = frappe.db.get_value("Task", self.task, fields, as_dict=True) or {}
        return self._task_defaults

    def _set_grade_scale_from_defaults(self):
        if self.grade_scale:
            return
        defaults = self._get_task_defaults()
        if defaults.get("default_grade_scale"):
            self.grade_scale = defaults.get("default_grade_scale")

    def _set_max_points_from_defaults(self):
        if self.max_points not in (None, ""):
            return
        defaults = self._get_task_defaults()
        if defaults.get("default_max_points") not in (None, ""):
            self.max_points = defaults.get("default_max_points")

    def _ensure_rubric_snapshot(self):
        existing = frappe.db.get_value(
            "Task Rubric Version",
            {"task_delivery": self.name},
            "name",
        )
        if existing:
            if not self.rubric_version:
                self.db_set("rubric_version", existing)
            return existing

        criteria_rows = self._get_task_criteria_rows()
        if not criteria_rows:
            frappe.throw(_("Cannot create rubric snapshot without Task criteria."))

        doc = frappe.get_doc(
            {
                "doctype": "Task Rubric Version",
                "task": self.task,
                "task_delivery": self.name,
                "grading_mode": "Criteria",
                "grade_scale": self.grade_scale,
            }
        )
        for row in criteria_rows:
            doc.append(
                "criteria",
                {
                    "assessment_criteria": row.get("assessment_criteria"),
                    "criteria_weighting": row.get("criteria_weighting") or 1,
                    "criteria_max_points": row.get("criteria_max_points") or 0,
                },
            )
        doc.insert(ignore_permissions=True)
        self.db_set("rubric_version", doc.name)
        return doc.name

    def _set_rubric_scoring_strategy_from_defaults(self):
        if not self._has_field("rubric_scoring_strategy"):
            return
        if self.rubric_scoring_strategy:
            return
        defaults = self._get_task_defaults()
        self.rubric_scoring_strategy = defaults.get("default_rubric_scoring_strategy") or "Sum Total"

    def _enforce_post_submit_immutability(self):
        if self.docstatus != 1 or self.is_new():
            return

        before = self.get_doc_before_save()
        if not before:
            return

        for fieldname in ("student_group", "task", "course", "academic_year", "school"):
            if self._has_field(fieldname) and getattr(before, fieldname) != getattr(self, fieldname):
                frappe.throw(_("Cannot change {0} after submission.").format(fieldname.replace("_", " ")))

        if frappe.db.get_value("Task Outcome", {"task_delivery": self.name}, "name"):
            for fieldname in (
                "grading_mode",
                "allow_feedback",
                "max_points",
                "grade_scale",
                "rubric_version",
                "rubric_scoring_strategy",
            ):
                if self._has_field(fieldname) and getattr(before, fieldname) != getattr(self, fieldname):
                    frappe.throw(_("Cannot change grading configuration after outcomes exist."))

    def _has_evidence(self):
        outcome_names = frappe.get_all(
            "Task Outcome",
            filters={"task_delivery": self.name},
            pluck="name",
            limit=0,
        )
        if not outcome_names:
            return False

        if frappe.db.get_value("Task Submission", {"task_outcome": ["in", outcome_names]}, "name"):
            return True
        if frappe.db.get_value("Task Contribution", {"task_outcome": ["in", outcome_names]}, "name"):
            return True
        if frappe.db.get_value(
            "Task Outcome",
            {"task_delivery": self.name, "official_score": ["is", "set"]},
            "name",
        ):
            return True
        if frappe.db.get_value(
            "Task Outcome",
            {"task_delivery": self.name, "official_grade": ["is", "set"]},
            "name",
        ):
            return True

        return False
