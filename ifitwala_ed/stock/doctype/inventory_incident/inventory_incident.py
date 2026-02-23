# ifitwala_ed/stock/doctype/inventory_incident/inventory_incident.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class InventoryIncident(Document):
    def validate(self):
        if not self.incident_type:
            frappe.throw(_("Incident Type is required."))

        unit = self._get_unit()
        if unit and self.incident_type == "Lost" and unit.status == "Lost":
            frappe.throw(_("This unit is already marked as Lost."))

        if self.suggested_amount:
            return

        if unit and unit.inventory_item:
            standard_rate = frappe.db.get_value("Inventory Item", unit.inventory_item, "standard_rate")
            if standard_rate is not None:
                self.suggested_amount = standard_rate

    def on_submit(self):
        unit = self._get_unit()
        if not unit:
            return

        if self.incident_type == "Lost":
            if unit.status != "Retired":
                frappe.db.set_value("Inventory Unit", unit.name, "status", "Lost", update_modified=True)
        elif self.incident_type == "Damaged":
            frappe.db.set_value("Inventory Unit", unit.name, "condition", "Damaged", update_modified=True)

    def _get_unit(self):
        if not self.inventory_unit:
            return None
        return frappe.db.get_value(
            "Inventory Unit",
            self.inventory_unit,
            ["name", "inventory_item", "status"],
            as_dict=True,
        )
