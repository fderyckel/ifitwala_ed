import frappe
from frappe import _
from frappe.model.document import Document


class SalesTaxesandChargesTemplate(Document):
	def validate(self):
		self.validate_default()
		self.validate_taxes()

	def validate_default(self):
		if not self.is_default:
			return
		exists = frappe.db.exists(
			"Sales Taxes and Charges Template",
			{
				"organization": self.organization,
				"is_default": 1,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(_("Only one default tax template is allowed per Organization"))

	def validate_taxes(self):
		for row in self.taxes:
			if not row.account_head:
				frappe.throw(_("Tax account is required in each row"))
			account = frappe.db.get_value(
				"Account", row.account_head, ["organization", "is_group", "root_type", "account_type"], as_dict=True
			)
			if not account:
				frappe.throw(_("Tax account not found"))
			if account.organization != self.organization:
				frappe.throw(_("Tax account must belong to the same Organization"))
			if account.is_group:
				frappe.throw(_("Cannot use a group account for taxes"))
			if account.root_type != "Liability":
				frappe.throw(_("Tax account must be a Liability account"))
