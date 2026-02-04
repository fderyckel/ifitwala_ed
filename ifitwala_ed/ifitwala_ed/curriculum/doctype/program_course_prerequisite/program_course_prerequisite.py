# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.curriculum.enrollment_utils import resolve_min_numeric_score


class ProgramCoursePrerequisite(Document):
	def before_save(self):
		existing = None
		if self.name and not self.is_new():
			existing = frappe.db.get_value(
				"Program Course Prerequisite",
				self.name,
				["grade_scale_used", "min_numeric_score"],
				as_dict=True,
			)

		if existing and existing.get("grade_scale_used") and existing.get("min_numeric_score") is not None:
			self._enforce_immutable_snapshot(existing)
		else:
			self._resolve_thresholds(existing)

		self._assert_snapshot()

	def _resolve_thresholds(self, existing):
		min_grade = (self.min_grade or "").strip()
		if not min_grade:
			frappe.throw(_("Minimum Grade is required for prerequisites."))

		grade_scale_used = self.grade_scale_used or (existing or {}).get("grade_scale_used")
		if not grade_scale_used:
			grade_scale_used = _resolve_grade_scale_used(self.required_course, self.parent)

		if not grade_scale_used:
			frappe.throw(
				_("Cannot compute prerequisite threshold: no grade scale found. Set Course.grade_scale or Program.grade_scale.")
			)

		self.grade_scale_used = grade_scale_used
		self.min_numeric_score = resolve_min_numeric_score(min_grade, grade_scale_used)

	def _enforce_immutable_snapshot(self, existing):
		if self.grade_scale_used and self.grade_scale_used != existing.get("grade_scale_used"):
			frappe.throw(_("Grade Scale Used is immutable after first save."))
		self.grade_scale_used = existing.get("grade_scale_used")

		if self.min_numeric_score is not None and existing.get("min_numeric_score") is not None:
			if flt(self.min_numeric_score) != flt(existing.get("min_numeric_score")):
				frappe.throw(_("Minimum Numeric Score is immutable after first save."))
		self.min_numeric_score = existing.get("min_numeric_score")

	def _assert_snapshot(self):
		if not self.grade_scale_used:
			frappe.throw(_("Grade Scale Used is required for prerequisites."))
		if self.min_numeric_score is None:
			frappe.throw(_("Minimum Numeric Score is required for prerequisites."))

		assert self.grade_scale_used
		assert self.min_numeric_score is not None


def _resolve_grade_scale_used(required_course, program):
	grade_scale_used = None
	if required_course:
		grade_scale_used = frappe.db.get_value("Course", required_course, "grade_scale")
	if not grade_scale_used and program:
		grade_scale_used = frappe.db.get_value("Program", program, "grade_scale")
	return grade_scale_used
