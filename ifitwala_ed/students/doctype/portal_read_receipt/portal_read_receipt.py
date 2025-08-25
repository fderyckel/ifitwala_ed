# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class PortalReadReceipt(Document):
	# ifitwala_ed/portal/doctype/portal_read_receipt/portal_read_receipt.py
	def on_doctype_update():
		frappe.db.add_index("Portal Read Receipt",
			["user","reference_doctype","reference_name"],
			index_name="user_ref", unique=True)

