# ifitwala_ed/stock/doctype/inventory_transfer/inventory_transfer.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.stock.inventory.inventory_ledger import make_ledger_entries
from ifitwala_ed.stock.inventory.inventory_utils import coerce_datetime, set_unit_custody
from ifitwala_ed.stock.inventory.inventory_validations import validate_transfer


class InventoryTransfer(Document):
	def validate(self):
		validate_transfer(self)

	def on_submit(self):
		validate_transfer(self)
		rows = self._build_ledger_rows()
		posting_dt = coerce_datetime(self.posting_datetime, fieldname="posting_datetime")
		make_ledger_entries(self.doctype, self.name, posting_dt, rows)
		self._apply_unit_updates()

	def on_cancel(self):
		frappe.throw(_("Inventory Transfers cannot be cancelled in Phase 1."))

	def _build_ledger_rows(self):
		rows = []
		for row in self.items:
			qty = flt(row.qty or 0)
			rows.append(
				{
					"inventory_item": row.inventory_item,
					"inventory_unit": row.inventory_unit,
					"from_location": self.from_location,
					"to_location": self.to_location,
					"qty_change": qty,
				}
			)
		return rows

	def _apply_unit_updates(self):
		custody_fields = {
			"current_location": self.to_location,
			"current_employee": None,
			"current_student": None,
			"current_guardian": None,
		}
		for row in self.items:
			if not row.inventory_unit:
				continue
			set_unit_custody(row.inventory_unit, custody_fields)
