import frappe
from frappe import _
from frappe.model.document import Document


class AccountsSettings(Document):
	def validate(self):
		self.validate_accounts()

	def validate_accounts(self):
		account_fields = {
			"default_receivable_account": "Receivable",
			"default_cash_account": "Cash",
			"default_bank_account": "Bank",
			"default_tax_payable_account": "Tax",
		}
		for fieldname, account_type in account_fields.items():
			account = self.get(fieldname)
			if not account:
				continue
			self._validate_account(account, account_type)

		if self.default_advance_account:
			self._validate_account_root_type(self.default_advance_account, "Liability")

	def _validate_account(self, account, account_type):
		self._validate_account_org(account)
		acc_type = frappe.db.get_value("Account", account, "account_type")
		if acc_type and acc_type != account_type:
			frappe.throw(
				_("{0} must be an account of type {1}").format(
					frappe.bold(account), frappe.bold(account_type)
				)
			)

	def _validate_account_root_type(self, account, root_type):
		self._validate_account_org(account)
		acc_root = frappe.db.get_value("Account", account, "root_type")
		if acc_root and acc_root != root_type:
			frappe.throw(
				_("{0} must have Root Type {1}").format(
					frappe.bold(account), frappe.bold(root_type)
				)
			)

	def _validate_account_org(self, account):
		account_org = frappe.db.get_value("Account", account, "organization")
		if account_org and account_org != self.organization:
			frappe.throw(
				_("Account {0} must belong to Organization {1}").format(
					frappe.bold(account), frappe.bold(self.organization)
				)
			)
