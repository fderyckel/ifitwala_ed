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
		self._enforce_grading_defaults()

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
		return frappe.db.get_value(
			"Lesson",
			lesson_name,
			["course", "learning_unit"],
			as_dict=True,
		) or {}

	def _get_learning_unit_course(self, learning_unit):
		if not learning_unit:
			return None
		return frappe.db.get_value("Learning Unit", learning_unit, "course")

	def _validate_curriculum_alignment(self):
		course = self._get_course_value()
		learning_unit = self.learning_unit or None
		lesson = self.lesson or None

		unit_course = None
		if learning_unit and course:
			unit_course = self._get_learning_unit_course(learning_unit)
			if unit_course and unit_course != course:
				frappe.throw(_("Learning Unit belongs to a different Course than the Task's Course."))

		if not lesson:
			return

		lesson_info = self._get_lesson_info(lesson)
		lesson_unit = lesson_info.get("learning_unit")
		lesson_course = lesson_info.get("course")

		if learning_unit and lesson_unit and lesson_unit != learning_unit:
			frappe.throw(_("Lesson does not belong to the selected Learning Unit."))

		if course:
			if not lesson_course and lesson_unit:
				if lesson_unit == learning_unit and unit_course:
					lesson_course = unit_course
				else:
					lesson_course = self._get_learning_unit_course(lesson_unit)
			if lesson_course and lesson_course != course:
				frappe.throw(_("Lesson belongs to a different Course than the Task's Course."))

	def _clear_grading_defaults(self):
		self.default_grade_scale = None
		self.default_rubric = None
		self.default_max_points = None

	def _enforce_grading_defaults(self):
		if self.default_delivery_mode and self.default_delivery_mode != "Assess":
			self.default_grading_mode = "None"
			self._clear_grading_defaults()
			return

		if self.default_grading_mode == "Points":
			if not self.default_max_points or float(self.default_max_points) <= 0:
				frappe.throw(_("Default Max Points must be greater than 0 when grading mode is Points."))

		if self.default_grading_mode == "Criteria":
			if not self.default_rubric:
				frappe.throw(_("Default Rubric is required when grading mode is Criteria."))
