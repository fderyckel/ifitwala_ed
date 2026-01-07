# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime

from ifitwala_ed.assessment.task_delivery_service import (
	bulk_create_outcomes,
	get_delivery_context,
	get_eligible_students,
	resolve_or_create_lesson_instance,
)


class TaskDelivery(Document):
	def before_validate(self):
		self._require_task_and_group()
		context = get_delivery_context(self.student_group)
		self._stamp_context(context)
		self._validate_task_course_alignment(context)
		self._maybe_link_lesson_instance()

	def validate(self):
		self._enforce_post_submit_immutability()
		self._apply_delivery_mode_defaults()
		self._validate_dates()
		self._validate_delivery_mode_coherence()
		self._validate_group_submission()

	def on_submit(self):
		if self.delivery_mode == "Assess" and self.grading_mode == "Criteria":
			self._ensure_rubric_snapshot()

		students = get_eligible_students(self.student_group)
		bulk_create_outcomes(self, students, context=self._current_context())

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

	def _maybe_link_lesson_instance(self):
		if self.lesson_instance:
			return

		explicit = self._explicit_lesson_context()
		if not explicit:
			return

		lesson_instance = resolve_or_create_lesson_instance(self, explicit)
		if lesson_instance:
			self.lesson_instance = lesson_instance

	def _explicit_lesson_context(self):
		context = {}
		if self._has_field("lesson") and getattr(self, "lesson", None):
			context["lesson"] = self.lesson
		if self._has_field("lesson_activity") and getattr(self, "lesson_activity", None):
			context["lesson_activity"] = self.lesson_activity
		if self._has_field("instance_type") and getattr(self, "instance_type", None):
			context["instance_type"] = self.instance_type
		return context or None

	def _apply_delivery_mode_defaults(self):
		if not self.delivery_mode:
			return

		if self.delivery_mode == "Assign Only":
			self.requires_submission = 0
			self.require_grading = 0
			self._clear_grading_fields()
			return

		if self.delivery_mode == "Collect Work":
			self.requires_submission = 1
			self.require_grading = 0
			self._clear_grading_fields()
			return

		if self.delivery_mode == "Assess":
			self.require_grading = 1
			self._ensure_grading_mode()
			self._set_requires_submission_from_defaults()

			if self.grading_mode in ("Completion", "Binary"):
				self._clear_grading_fields(keep_mode=True)

			if self.grading_mode == "Points":
				self.rubric_version = None

			if self.grading_mode == "Criteria":
				self.max_points = None

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
		defaults = self._get_task_defaults()
		default_requires = defaults.get("default_requires_submission")
		if default_requires in (0, 1, "0", "1", True, False):
			self.requires_submission = 1 if int(default_requires) else 0
			return

		if self.grading_mode in ("Points", "Criteria"):
			self.requires_submission = 1
		else:
			self.requires_submission = 0

	def _clear_grading_fields(self, keep_mode=False):
		if not keep_mode:
			self.grading_mode = None
		self.max_points = None
		self.grade_scale = None
		self.rubric_version = None

	def _validate_dates(self):
		available_from = get_datetime(self.available_from) if self.available_from else None
		due_date = get_datetime(self.due_date) if self.due_date else None
		lock_date = get_datetime(self.lock_date) if self.lock_date else None

		if available_from and due_date and available_from > due_date:
			frappe.throw(_("Available From must be before or on Due Date."))

		if due_date and lock_date and due_date > lock_date:
			frappe.throw(_("Due Date must be before or on Lock Date."))

	def _validate_delivery_mode_coherence(self):
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
				if not self.rubric_version and not self._get_task_default_rubric():
					frappe.throw(_("Criteria grading requires a Task rubric."))

	def _validate_group_submission(self):
		if self.group_submission:
			frappe.throw(_("Group submission is paused: subgroup model not implemented."))

	def _get_task_default_rubric(self):
		defaults = self._get_task_defaults()
		if defaults.get("default_rubric"):
			return defaults.get("default_rubric")

		meta = frappe.get_meta("Task")
		fieldnames = [f for f in ("default_rubric", "rubric") if meta.get_field(f)]
		if not fieldnames:
			return None
		values = frappe.db.get_value("Task", self.task, fieldnames, as_dict=True) or {}
		for fieldname in fieldnames:
			if values.get(fieldname):
				return values.get(fieldname)
		return None

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
				"default_rubric",
			)
			if meta.get_field(fieldname)
		]
		if not fields:
			self._task_defaults = {}
			return self._task_defaults

		self._task_defaults = frappe.db.get_value("Task", self.task, fields, as_dict=True) or {}
		return self._task_defaults

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

		rubric = self._get_task_default_rubric()
		if not rubric:
			frappe.throw(_("Cannot create rubric snapshot without a Task rubric."))

		doc = frappe.get_doc({
			"doctype": "Task Rubric Version",
			"task": self.task,
			"task_delivery": self.name,
			"grading_mode": "Criteria",
			"grade_scale": self.grade_scale,
		})
		doc.append("criteria", {
			"assessment_criteria": rubric,
			"criteria_weighting": 1,
			"criteria_max_points": 0,
		})
		doc.insert(ignore_permissions=True)
		self.db_set("rubric_version", doc.name)
		return doc.name

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
			for fieldname in ("grading_mode", "max_points", "grade_scale", "rubric_version"):
				if self._has_field(fieldname) and getattr(before, fieldname) != getattr(self, fieldname):
					frappe.throw(_("Cannot change grading configuration after outcomes exist."))

	def _has_evidence(self):
		outcome_rows = frappe.db.get_values(
			"Task Outcome",
			{"task_delivery": self.name},
			"name",
			as_list=True,
		)
		outcome_names = [row[0] for row in outcome_rows if row and row[0]]
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
