# ifitwala_ed/setup/doctype/file_classification/file_classification.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document


ALLOWED_PRIMARY_SUBJECT_TYPES = {"Student", "Guardian", "Employee", "Student Applicant"}
REQUIRED_FIELDS = (
	"file",
	"primary_subject_type",
	"primary_subject_id",
	"data_class",
	"purpose",
	"retention_policy",
	"slot",
	"organization",
	"school",
)


class FileClassification(Document):
	def validate(self):
		self._validate_required_fields()
		self._validate_primary_subject_type()
		self._sync_attached_fields()
		self._ensure_unique_file()

	def _validate_required_fields(self):
		for fieldname in REQUIRED_FIELDS:
			if not self.get(fieldname):
				frappe.throw(_("{0} is required.").format(fieldname.replace("_", " ").title()))

	def _validate_primary_subject_type(self):
		if self.primary_subject_type not in ALLOWED_PRIMARY_SUBJECT_TYPES:
			frappe.throw(_("Invalid primary_subject_type."))

	def _sync_attached_fields(self):
		if not self.file:
			return
		file_row = frappe.db.get_value(
			"File",
			self.file,
			["attached_to_doctype", "attached_to_name"],
			as_dict=True,
		)
		if not file_row:
			frappe.throw(_("Referenced File does not exist."))

		if not file_row.get("attached_to_doctype") or not file_row.get("attached_to_name"):
			frappe.throw(_("File must be attached to a business document before classification."))

		if self.attached_doctype and self.attached_doctype != file_row.get("attached_to_doctype"):
			frappe.throw(_("attached_doctype must match the File attachment."))
		if self.attached_name and self.attached_name != file_row.get("attached_to_name"):
			frappe.throw(_("attached_name must match the File attachment."))

		self.attached_doctype = file_row.get("attached_to_doctype")
		self.attached_name = file_row.get("attached_to_name")

	def _ensure_unique_file(self):
		if not self.file:
			return
		exists = frappe.db.exists(
			"File Classification",
			{"file": self.file, "name": ["!=", self.name]},
		)
		if exists:
			frappe.throw(_("File already has a classification."))
