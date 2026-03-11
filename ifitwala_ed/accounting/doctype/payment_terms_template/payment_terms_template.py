# ifitwala_ed/accounting/doctype/payment_terms_template/payment_terms_template.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.accounting.receivables import is_zero, money


class PaymentTermsTemplate(Document):
    def validate(self):
        if not self.terms:
            frappe.throw(_("At least one payment term is required."))

        total_portion = 0.0
        for idx, row in enumerate(self.terms, start=1):
            if not row.term_name:
                frappe.throw(_("Row {0}: Term Name is required.").format(idx))
            if flt(row.invoice_portion) <= 0:
                frappe.throw(_("Row {0}: Invoice Portion must be greater than zero.").format(idx))
            if flt(row.due_days) < 0:
                frappe.throw(_("Row {0}: Due Days cannot be negative.").format(idx))
            total_portion = money(total_portion + flt(row.invoice_portion))

        if not is_zero(total_portion - 100):
            frappe.throw(_("Payment terms must add up to 100%."))

    def on_update(self):
        if not self.is_default:
            return
        frappe.db.sql(
            """
            update `tabPayment Terms Template`
            set is_default = 0
            where organization = %s and name != %s
            """,
            (self.organization, self.name),
        )
