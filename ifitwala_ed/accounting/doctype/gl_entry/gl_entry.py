import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class GLEntry(Document):
	def validate(self):
		self.validate_account()
		self.validate_amounts()
		self.set_account_currency()

	def validate_account(self):
		if not self.account:
			frappe.throw(_("Account is required"))
		account = frappe.db.get_value(
			"Account", self.account, ["organization", "is_group"], as_dict=True
		)
		if not account:
			frappe.throw(_("Account not found"))
		if account.organization != self.organization:
			frappe.throw(_("Account must belong to the same Organization"))
		if account.is_group:
			frappe.throw(_("Cannot post to a group account"))

	def validate_amounts(self):
		debit = flt(self.debit)
		credit = flt(self.credit)
		if debit == 0 and credit == 0:
			frappe.throw(_("Either Debit or Credit is required"))
		if debit and credit:
			frappe.throw(_("Debit and Credit cannot both be non-zero"))

	def set_account_currency(self):
		if not self.account_currency:
			self.account_currency = frappe.db.get_value("Account", self.account, "account_currency")
		self.debit_in_account_currency = flt(self.debit)
		self.credit_in_account_currency = flt(self.credit)
