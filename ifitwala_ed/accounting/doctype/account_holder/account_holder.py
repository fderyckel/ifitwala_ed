import frappe
from frappe import _
from frappe.model.document import Document


class AccountHolder(Document):
    def validate(self):
        if not self.organization:
            frappe.throw(_("Organization is required"))
