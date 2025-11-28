# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/file_dispatcher.py

from __future__ import annotations
import frappe

def handle_file_after_insert(doc, method=None):
	"""
	Single entry point for File.after_insert.
	1) Route + version the file (all types).
	2) Run image-specific utilities (thumbnails, etc.).
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
	Single entry point for File.on_update.
	Same order: routing first, then image adjustments.
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
