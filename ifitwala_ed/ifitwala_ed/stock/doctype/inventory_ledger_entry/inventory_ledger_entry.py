# ifitwala_ed/stock/doctype/inventory_ledger_entry/inventory_ledger_entry.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class InventoryLedgerEntry(Document):
	def validate(self):
		if not self.is_new():
			frappe.throw(_("Inventory Ledger Entries are append-only. Edits are not permitted."))

	def on_trash(self):
		frappe.throw(_("Inventory Ledger Entries cannot be deleted."))
