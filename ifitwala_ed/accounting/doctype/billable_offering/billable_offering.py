import frappe
from frappe import _
from frappe.model.document import Document


class BillableOffering(Document):
    def validate(self):
        self.validate_income_account()
        self.validate_linked_reference()

    def validate_income_account(self):
        account = frappe.db.get_value(
            "Account", self.income_account, ["organization", "is_group", "root_type"], as_dict=True
        )
        if not account:
            frappe.throw(_("Income account not found"))
        if account.organization != self.organization:
            frappe.throw(_("Income account must belong to the same Organization"))
        if account.is_group:
            frappe.throw(_("Cannot use a group account for income"))
        if account.root_type != "Income":
            frappe.throw(_("Income account must have Root Type 'Income'"))

    def validate_linked_reference(self):
        if self.linked_reference and not self.linked_doctype:
            frappe.throw(_("Linked Type is required when Linked Reference is set"))
