# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/file_dispatcher.py

from __future__ import annotations
from typing import Dict, Any, List, Optional

import frappe
from frappe import _
from frappe.model.document import Document


REQUIRED_CLASSIFICATION_FIELDS = {
	"primary_subject_type",
	"primary_subject_id",
	"data_class",
	"purpose",
	"retention_policy",
	"slot",
	"organization",
	"school",
}

ALLOWED_SUBJECT_TYPES = {"Student", "Guardian", "Employee", "Student Applicant"}

def handle_file_after_insert(doc, method=None):
	"""
	Legacy safety-net hooks.

	All governed uploads MUST go through the dispatcher API.
	This hook only finalizes files that already have File Classification.
	"""
	from ifitwala_ed.utilities import file_management
	from ifitwala_ed.utilities import image_utils

	# Step 1: routing / versioning / move to final folder
	try:
		file_management.route_uploaded_file(doc, method)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "File Routing Failed")

	# Step 2: image-specific handling (your existing behaviour)
	try:
		image_utils.handle_file_after_insert(doc, method)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Image Utils After Insert Failed")


def handle_file_on_update(doc, method=None):
	"""
	Legacy safety-net hooks.

	All governed uploads MUST go through the dispatcher API.
	This hook only finalizes files that already have File Classification.
	"""
	from ifitwala_ed.utilities import file_management
	from ifitwala_ed.utilities import image_utils

	try:
		file_management.route_uploaded_file(doc, method)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "File Routing Failed (on_update)")

	try:
		image_utils.handle_file_on_update(doc, method)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Image Utils On Update Failed")


@frappe.whitelist()
def create_and_classify_file(
	*,
	file_kwargs: Dict[str, Any],
	classification: Dict[str, Any],
	secondary_subjects: Optional[List[Dict[str, Any]]] = None,
) -> Document:
	"""
	Authoritative dispatcher entry point for ALL governed file uploads.

	Creates:
	1) File
	2) File Classification (1:1)

	Then relies on File hooks to finalize routing/versioning.
	"""
	from ifitwala_ed.utilities import file_management

	missing = REQUIRED_CLASSIFICATION_FIELDS - set((classification or {}).keys())
	if missing:
		frappe.throw(
			_("Missing mandatory file classification fields: {0}")
			.format(", ".join(sorted(missing)))
		)

	for key in REQUIRED_CLASSIFICATION_FIELDS:
		if classification.get(key) in (None, ""):
			frappe.throw(_("File Classification field {0} is required.").format(key))

	subject_type = classification.get("primary_subject_type")
	if subject_type not in ALLOWED_SUBJECT_TYPES:
		frappe.throw(_("Invalid primary_subject_type."))

	if not file_kwargs:
		frappe.throw(_("file_kwargs is required."))
	if not file_kwargs.get("attached_to_doctype") or not file_kwargs.get("attached_to_name"):
		frappe.throw(_("File attachments must include attached_to_doctype and attached_to_name."))

	frappe.db.savepoint("create_and_classify_file")

	try:
		file_doc = frappe.get_doc({
			"doctype": "File",
			**file_kwargs,
		})
		file_doc.insert(ignore_permissions=True)

		if frappe.db.exists("File Classification", {"file": file_doc.name}):
			frappe.throw(_("File already has a classification."))

		fc = frappe.get_doc({
			"doctype": "File Classification",
			"file": file_doc.name,
			"attached_doctype": file_doc.attached_to_doctype,
			"attached_name": file_doc.attached_to_name,
			"primary_subject_type": classification["primary_subject_type"],
			"primary_subject_id": classification["primary_subject_id"],
			"data_class": classification["data_class"],
			"purpose": classification["purpose"],
			"retention_policy": classification["retention_policy"],
			"slot": classification["slot"],
			"organization": classification["organization"],
			"school": classification["school"],
			"legal_hold": 0,
			"erasure_state": "active",
			"content_hash": file_management.calculate_hash(file_doc),
			"source_file": classification.get("source_file"),
			"upload_source": classification.get("upload_source", "API"),
			"ip_address": getattr(frappe.local, "request_ip", None),
		})
		fc.insert(ignore_permissions=True)

		if secondary_subjects:
			for subj in secondary_subjects:
				if not subj.get("subject_type") or not subj.get("subject_id"):
					frappe.throw(_("Secondary subject entries must include subject_type and subject_id."))
				fc.append("secondary_subjects", {
					"subject_type": subj["subject_type"],
					"subject_id": subj["subject_id"],
					"role": subj.get("role", "referenced"),
				})
			fc.save(ignore_permissions=True)

		# Trigger routing now that governance exists.
		file_doc.save(ignore_permissions=True)

	except Exception:
		frappe.db.rollback(save_point="create_and_classify_file")
		raise

	return file_doc
