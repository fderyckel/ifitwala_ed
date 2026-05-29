import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class BillableOffering(Document):
    def autoname(self):
        organization_abbr = frappe.db.get_value("Organization", self.organization, "abbr")
        if not organization_abbr:
            frappe.throw(_("Organization Abbreviation is required before creating a Billable Offering."))

        self.name = make_autoname(f"BO-{organization_abbr}-.####")

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
