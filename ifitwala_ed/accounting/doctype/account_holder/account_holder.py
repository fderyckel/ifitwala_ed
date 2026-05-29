import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.accounting.account_holder_contacts import (
    normalize_account_holder_billing_contacts,
    sync_account_holder_billing_contact_points,
)


class AccountHolder(Document):
    def validate(self):
        if not self.organization:
            frappe.throw(_("Organization is required"))
        normalize_account_holder_billing_contacts(self)

    def on_update(self):
        sync_account_holder_billing_contact_points(self)
