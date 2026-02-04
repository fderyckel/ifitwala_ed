# ifitwala_ed/stock/doctype/inventory_issue/inventory_issue.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.stock.inventory.inventory_ledger import make_ledger_entries
from ifitwala_ed.stock.inventory.inventory_utils import coerce_datetime, resolve_issued_to, set_unit_custody
from ifitwala_ed.stock.inventory.inventory_validations import validate_issue


class InventoryIssue(Document):
	def validate(self):
		self._validate_acknowledgment()
		validate_issue(self)

	def on_submit(self):
		validate_issue(self)
		rows = self._build_ledger_rows()
		posting_dt = coerce_datetime(None, fieldname="posting_datetime")
		make_ledger_entries(self.doctype, self.name, posting_dt, rows)
		self._apply_unit_updates()

	def on_cancel(self):
		frappe.throw(_("Inventory Issues cannot be cancelled in Phase 1."))

	def _validate_acknowledgment(self):
		if self.terms_accepted:
			missing = []
			if not self.accepted_by_name:
				missing.append(_("Accepted By Name"))
			if not self.accepted_on:
				missing.append(_("Accepted On"))
			if missing:
				frappe.throw(_("Missing acknowledgment fields: {0}.").format(", ".join(missing)))
		elif self.acknowledgment_attachment:
			frappe.throw(_("Terms must be accepted when acknowledgment attachment is provided."))

	def _build_ledger_rows(self):
		issued_to = resolve_issued_to(self)
		to_location = self.issued_to_location if issued_to["type"] == "Location" else None
		rows = []
		for row in self.items:
			qty = flt(row.qty or 0)
			rows.append(
				{
					"inventory_item": row.inventory_item,
					"inventory_unit": row.inventory_unit,
					"from_location": self.issue_from_location,
					"to_location": to_location,
					"qty_change": -abs(qty),
					"remarks": row.remarks,
				}
			)
		return rows

	def _apply_unit_updates(self):
		issued_to = resolve_issued_to(self)
		custody_fields = {
			"current_location": None,
			"current_employee": None,
			"current_student": None,
			"current_guardian": None,
		}
		if issued_to["type"] == "Employee":
			custody_fields["current_employee"] = issued_to["name"]
		elif issued_to["type"] == "Student":
			custody_fields["current_student"] = issued_to["name"]
		elif issued_to["type"] == "Guardian":
			custody_fields["current_guardian"] = issued_to["name"]
		elif issued_to["type"] == "Location":
			custody_fields["current_location"] = issued_to["name"]

		for row in self.items:
			if not row.inventory_unit:
				continue
			set_unit_custody(row.inventory_unit, custody_fields)
			updates = {"status": "Issued"}
			if row.condition_out:
				updates["condition"] = row.condition_out
			frappe.db.set_value("Inventory Unit", row.inventory_unit, updates, update_modified=True)
