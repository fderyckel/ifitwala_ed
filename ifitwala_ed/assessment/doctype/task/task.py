# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/doctype/task/task.py

import frappe
from frappe import _
from frappe.model.document import Document


class Task(Document):
	def before_validate(self):
		self._set_default_course_from_group()
		self._validate_course_alignment()

	def validate(self):
		self._validate_curriculum_links()
		self._apply_grading_defaults()
		self._warn_if_archived_changes()

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

	def _field_is_required_and_read_only(self, fieldname):
		field = self._doc_meta().get_field(fieldname)
		return bool(field and field.reqd and field.read_only)

	def _field_is_read_only(self, fieldname):
		field = self._doc_meta().get_field(fieldname)
		return bool(field and field.read_only)

	def _set_default_course_from_group(self):
		locked = self._field_is_required_and_read_only("default_course")
		if self.student_group:
			course = frappe.db.get_value("Student Group", self.student_group, "course")
			self.default_course = course
			if not course and locked:
				frappe.throw(_(
					"Selected Student Group has no Course. Choose a course-based Student Group or "
					"adjust the Task schema."
				))
			return

		if locked:
			frappe.throw(_(
				"Select a Student Group to set the creation context, or adjust the Task schema "
				"for default_course."
			))

	def _get_lesson_from_activity(self, lesson_activity):
		if not lesson_activity:
			return None
		info = frappe.db.get_value(
			"Lesson Activity",
			lesson_activity,
			["parent", "parenttype"],
			as_dict=True,
		) or {}
		if info.get("parenttype") and info.get("parenttype") != "Lesson":
			return None
		return info.get("parent")

	def _get_lesson_info(self, lesson_name):
		if not lesson_name:
			return {}
		return frappe.db.get_value(
			"Lesson",
			lesson_name,
			["course", "learning_unit"],
			as_dict=True,
		) or {}

	def _get_course_from_lesson(self, lesson_name):
		info = self._get_lesson_info(lesson_name)
		if not info:
			return None
		if info.get("course"):
			return info.get("course")
		if info.get("learning_unit"):
			return frappe.db.get_value("Learning Unit", info["learning_unit"], "course")
		return None

	def _validate_course_alignment(self):
		default_course = self.default_course
		if not default_course:
			return

		lesson_activity = (
			getattr(self, "lesson_activity", None)
			if self._has_field("lesson_activity")
			else None
		)
		if lesson_activity:
			parent_lesson = self._get_lesson_from_activity(lesson_activity)
			if parent_lesson:
				course = self._get_course_from_lesson(parent_lesson)
				if course and course != default_course:
					frappe.throw(_("Lesson Activity belongs to a different Course than the Task's Course."))

		if self.lesson:
			course = self._get_course_from_lesson(self.lesson)
			if course and course != default_course:
				frappe.throw(_("Lesson belongs to a different Course than the Task's Course."))

	def _validate_curriculum_links(self):
		lesson_activity = (
			getattr(self, "lesson_activity", None)
			if self._has_field("lesson_activity")
			else None
		)
		lesson = self.lesson or None
		learning_unit = self.learning_unit or None

		if lesson_activity:
			parent_lesson = self._get_lesson_from_activity(lesson_activity)
			if lesson:
				if parent_lesson and parent_lesson != lesson:
					frappe.throw(_("Lesson Activity does not belong to the selected Lesson."))
			elif parent_lesson:
				self.lesson = parent_lesson
				lesson = parent_lesson

		if lesson:
			lesson_info = self._get_lesson_info(lesson)
			lesson_unit = lesson_info.get("learning_unit")
			if learning_unit:
				if lesson_unit and lesson_unit != learning_unit:
					frappe.throw(_("Lesson does not belong to the selected Learning Unit."))
			elif lesson_unit:
				self.learning_unit = lesson_unit

	def _clear_grading_defaults(self):
		self.default_grade_scale = None
		self.default_rubric = None
		self.default_max_points = None

	def _apply_grading_defaults(self):
		if self.default_delivery_mode and self.default_delivery_mode != "Assess":
			self.default_grading_mode = "None"
			self._clear_grading_defaults()

		grading_mode = self.default_grading_mode or "None"
		if grading_mode in ("None", "Completion", "Binary"):
			self._clear_grading_defaults()

		if grading_mode == "Points":
			if not self.default_max_points or float(self.default_max_points) <= 0:
				if self._field_is_read_only("default_max_points"):
					frappe.throw(_(
						"Default Max Points is read-only in the schema and blocks Points grading. "
						"Update the schema or choose a different grading mode."
					))
				frappe.throw(_("Default Max Points must be greater than 0 when grading mode is Points."))

		if grading_mode == "Criteria":
			if not self.default_rubric:
				frappe.throw(_("Default Rubric is required when grading mode is Criteria."))

		if (
			self.default_delivery_mode in ("Collect Work", "Assess")
			and self.default_requires_submission in (None, "")
		):
			self.default_requires_submission = 1

	def _warn_if_archived_changes(self):
		if not self.is_archived or self.is_new():
			return

		fields = [
			"default_course",
			"learning_unit",
			"lesson",
			"lesson_activity",
			"default_delivery_mode",
			"default_requires_submission",
			"default_grading_mode",
			"default_max_points",
			"default_grade_scale",
			"default_rubric",
		]
		fields = [field for field in fields if self._has_field(field)]
		if not fields:
			return

		prior = frappe.db.get_value("Task", self.name, fields, as_dict=True) or {}
		if not prior:
			return

		def _norm(value):
			return None if value in ("", None) else value

		changed = [
			field
			for field in fields
			if _norm(prior.get(field)) != _norm(getattr(self, field, None))
		]
		if changed:
			frappe.msgprint(
				_(
					"This Task is archived. Avoid changing grading defaults or curriculum alignment; "
					"archived tasks should be kept stable and used only for reference."
				),
				indicator="orange",
			)
