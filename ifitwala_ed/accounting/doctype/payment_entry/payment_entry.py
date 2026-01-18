import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from ifitwala_ed.accounting.ledger_utils import make_gl_entries, cancel_gl_entries, validate_posting_date


class PaymentEntry(Document):
	def validate(self):
		self.validate_party()
		self.validate_paid_to_account()
		self.validate_references()
		self.validate_amounts()
		validate_posting_date(self.organization, self.posting_date)

	def validate_party(self):
		party_org = frappe.db.get_value("Account Holder", self.party, "organization")
		if party_org and party_org != self.organization:
			frappe.throw(_("Account Holder must belong to the same Organization"))

	def validate_paid_to_account(self):
		account = frappe.db.get_value(
			"Account", self.paid_to, ["organization", "is_group", "account_type"], as_dict=True
		)
		if not account:
			frappe.throw(_("Paid To account not found"))
		if account.organization != self.organization:
			frappe.throw(_("Paid To account must belong to the same Organization"))
		if account.is_group:
			frappe.throw(_("Cannot post to a group account"))
		if account.account_type not in ["Bank", "Cash"]:
			frappe.throw(_("Paid To account must be a Bank or Cash account"))

	def validate_references(self):
		total_allocated = 0
		for ref in self.references:
			if ref.reference_doctype != "Sales Invoice":
				frappe.throw(_("Only Sales Invoice references are supported"))
			inv = frappe.db.get_value(
				"Sales Invoice",
				ref.reference_name,
				["organization", "account_holder", "grand_total", "outstanding_amount", "docstatus"],
				as_dict=True,
			)
			if not inv:
				frappe.throw(_("Sales Invoice {0} not found").format(ref.reference_name))
			if inv.docstatus != 1:
				frappe.throw(_("Sales Invoice {0} must be submitted").format(ref.reference_name))
			if inv.organization != self.organization:
				frappe.throw(_("Sales Invoice must belong to the same Organization"))
			if inv.account_holder != self.party:
				frappe.throw(_("Sales Invoice must belong to the same Account Holder"))

			ref.total_amount = inv.grand_total
			ref.outstanding_amount = inv.outstanding_amount

			if flt(ref.allocated_amount) > flt(inv.outstanding_amount):
				frappe.throw(_("Allocated amount cannot exceed outstanding amount"))
			total_allocated += flt(ref.allocated_amount)

		if total_allocated > flt(self.paid_amount):
			frappe.throw(_("Allocated amount cannot exceed Paid Amount"))

		self.unallocated_amount = flt(self.paid_amount) - total_allocated

	def validate_amounts(self):
		if flt(self.paid_amount) <= 0:
			frappe.throw(_("Paid Amount must be greater than zero"))

	def on_submit(self):
		settings = frappe.get_doc("Accounts Settings", self.organization)
		ar_account = settings.default_receivable_account
		advance_account = settings.default_advance_account
		if not ar_account or not advance_account:
			frappe.throw(_("Default receivable and advance accounts are required"))

		entries = [
			{
				"organization": self.organization,
				"posting_date": self.posting_date,
				"account": self.paid_to,
				"party_type": None,
				"party": None,
				"against": ar_account,
				"remarks": self.remarks,
				"debit": self.paid_amount,
				"credit": 0,
			}
		]

		allocated = 0
		for ref in self.references:
			if flt(ref.allocated_amount) == 0:
				continue
			allocated += flt(ref.allocated_amount)
			entries.append(
				{
					"organization": self.organization,
					"posting_date": self.posting_date,
					"account": ar_account,
					"party_type": "Account Holder",
					"party": self.party,
					"against": self.paid_to,
					"remarks": self.remarks,
					"debit": 0,
					"credit": ref.allocated_amount,
				}
			)
			frappe.db.set_value(
				"Sales Invoice",
				ref.reference_name,
				"outstanding_amount",
				flt(ref.outstanding_amount) - flt(ref.allocated_amount),
			)

		if self.unallocated_amount > 0:
			entries.append(
				{
					"organization": self.organization,
					"posting_date": self.posting_date,
					"account": advance_account,
					"party_type": "Account Holder",
					"party": self.party,
					"against": self.paid_to,
					"remarks": self.remarks,
					"debit": 0,
					"credit": self.unallocated_amount,
				}
			)

		make_gl_entries(entries, "Payment Entry", self.name)

	def on_cancel(self):
		cancel_gl_entries("Payment Entry", self.name)
		for ref in self.references:
			inv = frappe.db.get_value("Sales Invoice", ref.reference_name, "outstanding_amount")
			if inv is None:
				continue
			frappe.db.set_value(
				"Sales Invoice",
				ref.reference_name,
				"outstanding_amount",
				flt(inv) + flt(ref.allocated_amount),
			)
