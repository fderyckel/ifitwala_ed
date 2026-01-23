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


def create_and_classify_file(
	*,
	file_doc,
	primary_subject_type,
	primary_subject_id,
	data_class,
	purpose,
	slot,
	organization,
	school,
	is_private=0,
):
	"""
	Authoritative file creation + governance enforcement.
	This method is the ONLY allowed entry point.
	"""

	# ---- Hard validation (no defaults, no guessing)
	required = {
		"primary_subject_type": primary_subject_type,
		"primary_subject_id": primary_subject_id,
		"data_class": data_class,
		"purpose": purpose,
		"slot": slot,
		"organization": organization,
	}
	for k, v in required.items():
		if not v:
			frappe.throw(_(f"Missing required file governance field: {k}"))

	# ---- Create File (transport layer)
	file_doc.is_private = is_private
	file_doc.save(ignore_permissions=True)

	# ---- Load settings
	settings = frappe.get_single("File Management Settings")
	retention_days = frappe.db.get_value(
		"File Retention Policy",
		{"data_class": data_class, "purpose": purpose},
		"retention_days",
	)

	if retention_days is None:
		frappe.throw(
			_("No retention policy defined for {0} / {1}")
			.format(data_class, purpose)
		)

	retention_until = frappe.utils.add_days(frappe.utils.today(), retention_days)

	# ---- Enforce single-slot versioning
	existing = frappe.get_all(
		"File Classification",
		filters={
			"primary_subject_type": primary_subject_type,
			"primary_subject_id": primary_subject_id,
			"slot": slot,
			"is_current": 1,
		},
		pluck="name",
	)

	for name in existing:
		old = frappe.get_doc("File Classification", name)
		old.is_current = 0
		old.save(ignore_permissions=True)

	# ---- Create authoritative classification
	classification = frappe.get_doc({
		"doctype": "File Classification",
		"file": file_doc.name,
		"primary_subject_type": primary_subject_type,
		"primary_subject_id": primary_subject_id,
		"data_class": data_class,
		"purpose": purpose,
		"slot": slot,
		"is_current": 1,
		"organization": organization,
		"school": school,
		"retention_until": retention_until,
	})

	classification.insert(ignore_permissions=True)

	return file_doc
