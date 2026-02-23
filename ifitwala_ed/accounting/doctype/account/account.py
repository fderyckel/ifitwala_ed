import frappe
from frappe import _
from frappe.model.document import Document


class Account(Document):
    def validate(self):
        self.validate_organization()
        self.validate_root_type()
        self.set_report_type()
        self.validate_parent()
        self.validate_account_type()
        self.validate_group()

    def set_report_type(self):
        if self.root_type in ["Asset", "Liability", "Equity"]:
            self.report_type = "Balance Sheet"
        elif self.root_type in ["Income", "Expense"]:
            self.report_type = "Profit and Loss"

    def validate_organization(self):
        if not self.organization:
            frappe.throw(_("Organization is required"))

    def validate_root_type(self):
        if not self.root_type:
            frappe.throw(_("Root Type is required"))

    def validate_parent(self):
        if self.parent_account:
            parent = frappe.get_doc("Account", self.parent_account)

            if not parent:
                frappe.throw(_("Parent account not found"))

            if parent.organization != self.organization:
                frappe.throw(_("Parent account must belong to the same organization"))

            if parent.root_type != self.root_type:
                frappe.throw(_("Root Type must be the same as parent account"))

            if self.name and parent.name == self.name:
                frappe.throw(_("You cannot be your own parent"))

    def validate_account_type(self):
        if not self.account_type:
            return

        if self.account_type in ["Bank", "Cash", "Receivable"]:
            if self.root_type != "Asset":
                frappe.throw(_("Account Type '{0}' must have Root Type 'Asset'").format(self.account_type))

        if self.account_type == "Tax":
            if self.root_type != "Liability":
                frappe.throw(_("Account Type 'Tax' must have Root Type 'Liability'"))

    def validate_group(self):
        # Posting rules enforced at transaction posting time.
        pass
