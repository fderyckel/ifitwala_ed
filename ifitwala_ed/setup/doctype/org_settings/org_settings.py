# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class OrgSettings(Document):
	def validate(self):
		self.validate_accounting_defaults()

	def validate_accounting_defaults(self):
		"""
		Validate that selected default accounts match requirements:
		- Exists
		- Not group
		- Not disabled
		- Matches constraints (Root Type, Account Type)
		- Belongs to selected organization (if set)
		"""
		account_fields = {
			"default_accounts_receivable": {"account_type": "Receivable"},
			"default_cash_account": {"account_type": "Cash"},
			"default_bank_account": {"account_type": "Bank"},
			"default_advances_liability_account": {"root_type": "Liability"},
			"default_tax_payable_account": {"account_type": "Tax", "root_type": "Liability"}
		}

		for fieldname, constraints in account_fields.items():
			account_name = self.get(fieldname)
			if not account_name:
				continue
				
			account = frappe.get_doc("Account", account_name)
			
			# Basic checks
			if account.is_group:
				frappe.throw(f"Default account {account_name} cannot be a Group account")
			if account.disabled:
				frappe.throw(f"Default account {account_name} is disabled")
				
			# Constraint checks
			if "root_type" in constraints:
				if account.root_type != constraints["root_type"]:
					frappe.throw(f"Account {account_name} must be of Root Type '{constraints['root_type']}'")
					
			if "account_type" in constraints:
				if account.account_type != constraints["account_type"]:
					frappe.throw(f"Account {account_name} must be of Account Type '{constraints['account_type']}'")
					
			# Organization check
			if self.default_organization and account.organization != self.default_organization:
				frappe.throw(f"Account {account_name} does not belong to the selected Default Organization")
