# ifitwala_ed/stock/doctype/inventory_return/inventory_return.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.stock.inventory.inventory_ledger import make_ledger_entries
from ifitwala_ed.stock.inventory.inventory_utils import coerce_datetime, resolve_returned_from, set_unit_custody
from ifitwala_ed.stock.inventory.inventory_validations import validate_return


class InventoryReturn(Document):
    def validate(self):
        validate_return(self)

    def on_submit(self):
        validate_return(self)
        rows = self._build_ledger_rows()
        posting_dt = coerce_datetime(self.posting_datetime, fieldname="posting_datetime")
        make_ledger_entries(self.doctype, self.name, posting_dt, rows)
        self._apply_unit_updates()

    def on_cancel(self):
        frappe.throw(_("Inventory Returns cannot be cancelled in Phase 1."))

    def _build_ledger_rows(self):
        returned_from = resolve_returned_from(self)
        from_location = self.returned_from_location if returned_from["type"] == "Location" else None
        rows = []
        for row in self.items:
            qty = flt(row.qty or 0)
            rows.append(
                {
                    "inventory_item": row.inventory_item,
                    "inventory_unit": row.inventory_unit,
                    "from_location": from_location,
                    "to_location": self.return_to_location,
                    "qty_change": abs(qty),
                    "remarks": row.remarks,
                }
            )
        return rows

    def _apply_unit_updates(self):
        custody_fields = {
            "current_location": self.return_to_location,
            "current_employee": None,
            "current_student": None,
            "current_guardian": None,
        }
        for row in self.items:
            if not row.inventory_unit:
                continue
            current_status = frappe.db.get_value("Inventory Unit", row.inventory_unit, "status")
            new_status = "Under Repair" if current_status == "Under Repair" else "Available"
            set_unit_custody(row.inventory_unit, custody_fields)
            updates = {"status": new_status}
            if row.condition_in:
                updates["condition"] = row.condition_in
            frappe.db.set_value("Inventory Unit", row.inventory_unit, updates, update_modified=True)
