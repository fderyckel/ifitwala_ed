# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/students/doctype/evidence_tag/evidence_tag.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


_ALLOWED_TARGETS = {
	"Task Submission",
	"Student Reflection Entry",
	"Student Portfolio Item",
}


class EvidenceTag(Document):
	def validate(self):
		if self.target_doctype not in _ALLOWED_TARGETS:
			frappe.throw(_("Unsupported target doctype for Evidence Tag."))
		if not frappe.db.exists(self.target_doctype, self.target_name):
			frappe.throw(_("Target document does not exist."))
		if self.tagged_by_type not in {"Student", "Employee", "System"}:
			frappe.throw(_("Invalid tagged_by_type."))
		if not self.created_on:
			self.created_on = now_datetime()

		self._hydrate_context_from_target()

	def _hydrate_context_from_target(self):
		if self.target_doctype == "Task Submission":
			row = frappe.db.get_value(
				"Task Submission",
				self.target_name,
				["student", "academic_year", "school"],
				as_dict=True,
			)
		elif self.target_doctype == "Student Reflection Entry":
			row = frappe.db.get_value(
				"Student Reflection Entry",
				self.target_name,
				["student", "academic_year", "school"],
				as_dict=True,
			)
		else:
			row = None

		if row:
			self.student = row.get("student") or self.student
			self.academic_year = row.get("academic_year") or self.academic_year
			self.school = row.get("school") or self.school
			if self.school and not self.organization:
				self.organization = frappe.db.get_value("School", self.school, "organization")
