import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class AccountingPeriod(Document):
    def validate(self):
        self.validate_dates()
        self.validate_overlap()

    def validate_dates(self):
        if self.start_date and self.end_date:
            if getdate(self.start_date) > getdate(self.end_date):
                frappe.throw(_("Start Date must be before End Date"))

    def validate_overlap(self):
        if not (self.start_date and self.end_date and self.organization):
            return

        overlap = frappe.db.exists(
            "Accounting Period",
            {
                "organization": self.organization,
                "name": ["!=", self.name],
                "start_date": ["<=", self.end_date],
                "end_date": [">=", self.start_date],
            },
        )
        if overlap:
            frappe.throw(_("Accounting Period overlaps an existing period for this Organization"))
