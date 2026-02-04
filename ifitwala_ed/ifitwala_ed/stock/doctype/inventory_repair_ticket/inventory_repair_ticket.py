# ifitwala_ed/stock/doctype/inventory_repair_ticket/inventory_repair_ticket.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class InventoryRepairTicket(Document):
	def validate(self):
		unit_status = self._get_unit_status()
		if unit_status in {"Lost", "Retired"}:
			frappe.throw(_("Cannot open a repair ticket for a Lost or Retired unit."))

	def on_submit(self):
		if not self.opened_on:
			self.db_set("opened_on", now_datetime())
		frappe.db.set_value("Inventory Unit", self.inventory_unit, "status", "Under Repair", update_modified=True)

	@frappe.whitelist()
	def close_ticket(self):
		if self.status == "Closed":
			frappe.throw(_("This repair ticket is already closed."))

		closed_on = now_datetime()
		frappe.db.set_value(
			self.doctype,
			self.name,
			{"status": "Closed", "closed_on": closed_on},
			update_modified=True,
		)
		self.status = "Closed"
		self.closed_on = closed_on

		unit_location = frappe.db.get_value("Inventory Unit", self.inventory_unit, "current_location")
		if unit_location:
			frappe.db.set_value("Inventory Unit", self.inventory_unit, "status", "Available", update_modified=True)

	def _get_unit_status(self):
		if not self.inventory_unit:
			return None
		return frappe.db.get_value("Inventory Unit", self.inventory_unit, "status")
