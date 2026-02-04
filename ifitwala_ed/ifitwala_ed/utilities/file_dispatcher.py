# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/file_dispatcher.py

from __future__ import annotations
from typing import Dict, Any, List, Optional

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.utilities import file_management

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

def _missing_required_fields(classification: Dict[str, Any]) -> List[str]:
	missing = REQUIRED_CLASSIFICATION_FIELDS - set(classification.keys())
	if (
		"school" in missing
		and classification.get("primary_subject_type") == "Employee"
	):
		missing.remove("school")
	return sorted(missing)


def _validate_classification_payload(classification: Dict[str, Any]) -> None:
	if not isinstance(classification, dict):
		frappe.throw(_("classification must be a dict."))

	missing = _missing_required_fields(classification)
	if missing:
		frappe.throw(
			_("Missing mandatory file classification fields: {0}")
			.format(", ".join(missing))
		)

	primary_subject_type = classification.get("primary_subject_type")
	if primary_subject_type not in ALLOWED_SUBJECT_TYPES:
		frappe.throw(_("Invalid primary_subject_type."))

	for fieldname in REQUIRED_CLASSIFICATION_FIELDS:
		if fieldname == "school" and primary_subject_type == "Employee":
			continue
		if not classification.get(fieldname):
			frappe.throw(_("{0} is required.").format(fieldname.replace("_", " ").title()))


def _get_next_version_number(*, primary_subject_type: str, primary_subject_id: str, slot: str) -> int:
	row = frappe.db.get_all(
		"File Classification",
		fields=["max(version_number) as max_ver"],
		filters={
			"primary_subject_type": primary_subject_type,
			"primary_subject_id": primary_subject_id,
			"slot": slot,
		},
	)
	max_ver = 0
	if row and row[0].get("max_ver") is not None:
		max_ver = int(row[0]["max_ver"])
	return max_ver + 1


def _mark_previous_versions_inactive(*, primary_subject_type: str, primary_subject_id: str, slot: str) -> None:
	existing = frappe.get_all(
		"File Classification",
		filters={
			"primary_subject_type": primary_subject_type,
			"primary_subject_id": primary_subject_id,
			"slot": slot,
			"is_current_version": 1,
		},
		pluck="name",
	)
	for name in existing:
		frappe.db.set_value(
			"File Classification",
			name,
			"is_current_version",
			0,
			update_modified=False,
		)


def _resolve_retention_until(classification: Dict[str, Any]):
	if not frappe.db.exists("DocType", "File Retention Policy"):
		frappe.logger().warning(
			"[file_dispatcher] File Retention Policy doctype missing; retention_until left empty."
		)
		return None

	retention_days = frappe.db.get_value(
		"File Retention Policy",
		{
			"data_class": classification["data_class"],
			"purpose": classification["purpose"],
		},
		"retention_days",
	)
	if retention_days is None:
		frappe.throw(
			_("No retention policy defined for data_class '{0}' and purpose '{1}'")
			.format(classification["data_class"], classification["purpose"])
		)

	return frappe.utils.add_days(frappe.utils.today(), retention_days)


def _build_file_classification_payload(
	*,
	file_doc: Document,
	classification: Dict[str, Any],
) -> Dict[str, Any]:
	retention_until = _resolve_retention_until(classification)
	payload = {
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
		"legal_hold": 0,
		"erasure_state": "active",
		"content_hash": file_management.calculate_hash(file_doc),
		"source_file": classification.get("source_file"),
		"upload_source": classification.get("upload_source", "API"),
		"ip_address": frappe.local.request_ip if frappe.request else None,
	}
	if retention_until:
		payload["retention_until"] = retention_until
	if classification.get("school") or classification.get("primary_subject_type") != "Employee":
		payload["school"] = classification.get("school")
	return payload


def _append_secondary_subjects(fc: Document, secondary_subjects: Optional[List[Dict[str, Any]]]) -> None:
	if not secondary_subjects:
		return

	for subj in secondary_subjects:
		if not subj.get("subject_type") or not subj.get("subject_id"):
			frappe.throw(_("Secondary subject entries must include subject_type and subject_id"))

		fc.append("secondary_subjects", {
			"subject_type": subj["subject_type"],
			"subject_id": subj["subject_id"],
			"role": subj.get("role", "referenced"),
		})

	fc.save(ignore_permissions=True)


def _classify_file_doc(
	*,
	file_doc: Document,
	classification: Dict[str, Any],
	secondary_subjects: Optional[List[Dict[str, Any]]] = None,
	context_override: Optional[Dict[str, Any]] = None,
) -> Document:
	_validate_classification_payload(classification)

	if not file_doc:
		frappe.throw(_("File is required for classification."))
	if not (file_doc.attached_to_doctype and file_doc.attached_to_name):
		frappe.throw(_("File must be attached to a business document before classification."))
	if frappe.db.exists("File Classification", {"file": file_doc.name}):
		frappe.throw(_("File already has a classification."))

	primary_subject_type = classification["primary_subject_type"]
	primary_subject_id = classification["primary_subject_id"]
	slot = classification["slot"]

	_mark_previous_versions_inactive(
		primary_subject_type=primary_subject_type,
		primary_subject_id=primary_subject_id,
		slot=slot,
	)
	version_number = _get_next_version_number(
		primary_subject_type=primary_subject_type,
		primary_subject_id=primary_subject_id,
		slot=slot,
	)

	payload = _build_file_classification_payload(
		file_doc=file_doc,
		classification=classification,
	)
	payload["version_number"] = version_number
	payload["is_current_version"] = 1

	fc = frappe.get_doc(payload)
	fc.insert(ignore_permissions=True)

	_append_secondary_subjects(fc, secondary_subjects)

	file_management.route_uploaded_file(
		file_doc,
		method="dispatcher",
		context_override=context_override,
	)

	try:
		from ifitwala_ed.utilities import image_utils
		image_utils.handle_governed_file_after_classification(file_doc)
	except Exception:
		frappe.log_error(frappe.get_traceback(), "Governed Image Derivative Failed")

	return file_doc


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
	context_override: Optional[Dict[str, Any]] = None,
):
	"""
	Authoritative dispatcher entry point for ALL governed file uploads.

	Creates:
	1) File
	2) File Classification (1:1)

	Then finalizes routing/versioning after classification.
	"""
	if not isinstance(file_kwargs, dict):
		frappe.throw(_("file_kwargs must be a dict."))

	_validate_classification_payload(classification)

	file_doc = frappe.get_doc({
		"doctype": "File",
		**file_kwargs,
	})
	file_doc.flags.governed_upload = True
	file_doc.insert(ignore_permissions=True)

	return _classify_file_doc(
		file_doc=file_doc,
		classification=classification,
		secondary_subjects=secondary_subjects,
		context_override=context_override,
	)


def classify_existing_file(
	*,
	file_doc: Document,
	classification: Dict[str, Any],
	secondary_subjects: Optional[List[Dict[str, Any]]] = None,
	context_override: Optional[Dict[str, Any]] = None,
) -> Document:
	"""
	Classify an already-created File (legacy attach flows).
	"""
	return _classify_file_doc(
		file_doc=file_doc,
		classification=classification,
		secondary_subjects=secondary_subjects,
		context_override=context_override,
	)
