# ifitwala_ed/stock/doctype/inventory_unit/inventory_unit.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from ifitwala_ed.stock.inventory.inventory_validations import validate_unit_custody


class InventoryUnit(Document):
	def validate(self):
		validate_unit_custody(self)
		self._validate_serial_requirement()
		self._validate_unique_fields()

	def _validate_serial_requirement(self):
		if not self.inventory_item:
			return
		flags = frappe.db.get_value(
			"Inventory Item",
			self.inventory_item,
			["has_serial_no"],
			as_dict=True,
		)
		if flags and cint(flags.has_serial_no) and not self.serial_no:
			frappe.throw(_("Serial No is required for serial-tracked items."))

	def _validate_unique_fields(self):
		if self.serial_no and frappe.db.exists(
			"Inventory Unit",
			{"serial_no": self.serial_no, "name": ["!=", self.name]},
		):
			frappe.throw(_("Serial No {0} is already assigned.").format(self.serial_no))

		if self.asset_tag and frappe.db.exists(
			"Inventory Unit",
			{"asset_tag": self.asset_tag, "name": ["!=", self.name]},
		):
			frappe.throw(_("Asset Tag {0} is already assigned.").format(self.asset_tag))
