import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from ifitwala_ed.accounting.ledger_utils import make_gl_entries, cancel_gl_entries, validate_posting_date


class PaymentReconciliation(Document):
	def validate(self):
		self.validate_party()
		self.validate_allocations()
		validate_posting_date(self.organization, self.posting_date)

	def validate_party(self):
		party_org = frappe.db.get_value("Account Holder", self.account_holder, "organization")
		if party_org and party_org != self.organization:
			frappe.throw(_("Account Holder must belong to the same Organization"))

	def validate_allocations(self):
		if not self.allocations:
			frappe.throw(_("At least one allocation is required"))

		total_allocated = 0
		for row in self.allocations:
			if flt(row.allocated_amount) <= 0:
				frappe.throw(_("Allocated amount must be greater than zero"))
			invoice = frappe.db.get_value(
				"Sales Invoice",
				row.sales_invoice,
				["organization", "account_holder", "outstanding_amount", "docstatus"],
				as_dict=True,
			)
			if not invoice:
				frappe.throw(_("Sales Invoice {0} not found").format(row.sales_invoice))
			if invoice.docstatus != 1:
				frappe.throw(_("Sales Invoice {0} must be submitted").format(row.sales_invoice))
			if invoice.organization != self.organization:
				frappe.throw(_("Sales Invoice must belong to the same Organization"))
			if invoice.account_holder != self.account_holder:
				frappe.throw(_("Sales Invoice must belong to the same Account Holder"))

			row.outstanding_amount = invoice.outstanding_amount
			if flt(row.allocated_amount) > flt(invoice.outstanding_amount):
				frappe.throw(_("Allocated amount cannot exceed outstanding amount"))
			total_allocated += flt(row.allocated_amount)

		available = get_unallocated_advance(self.organization, self.account_holder)
		if total_allocated > available:
			frappe.throw(_("Allocated amount exceeds available advance balance"))

	def on_submit(self):
		settings = frappe.get_doc("Accounts Settings", self.organization)
		ar_account = settings.default_receivable_account
		advance_account = settings.default_advance_account
		if not ar_account or not advance_account:
			frappe.throw(_("Default receivable and advance accounts are required"))

		total_allocated = sum(flt(row.allocated_amount) for row in self.allocations)

		entries = [
			{
				"organization": self.organization,
				"posting_date": self.posting_date,
				"account": advance_account,
				"party_type": "Account Holder",
				"party": self.account_holder,
				"against": ar_account,
				"remarks": "Advance allocation",
				"debit": total_allocated,
				"credit": 0,
			},
			{
				"organization": self.organization,
				"posting_date": self.posting_date,
				"account": ar_account,
				"party_type": "Account Holder",
				"party": self.account_holder,
				"against": advance_account,
				"remarks": "Advance allocation",
				"debit": 0,
				"credit": total_allocated,
			},
		]

		make_gl_entries(entries, "Payment Reconciliation", self.name)

		for row in self.allocations:
			frappe.db.set_value(
				"Sales Invoice",
				row.sales_invoice,
				"outstanding_amount",
				flt(row.outstanding_amount) - flt(row.allocated_amount),
			)

		apply_advance_to_payment_entries(self.organization, self.account_holder, total_allocated)

	def on_cancel(self):
		cancel_gl_entries("Payment Reconciliation", self.name)
		for row in self.allocations:
			inv_outstanding = frappe.db.get_value("Sales Invoice", row.sales_invoice, "outstanding_amount")
			if inv_outstanding is None:
				continue
			frappe.db.set_value(
				"Sales Invoice",
				row.sales_invoice,
				"outstanding_amount",
				flt(inv_outstanding) + flt(row.allocated_amount),
			)
		apply_advance_to_payment_entries(self.organization, self.account_holder, -sum(flt(row.allocated_amount) for row in self.allocations))



def get_unallocated_advance(organization, account_holder):
	amounts = frappe.get_all(
		"Payment Entry",
		filters={
			"organization": organization,
			"party": account_holder,
			"docstatus": 1,
			"unallocated_amount": [">", 0],
		},
		pluck="unallocated_amount",
	)
	return sum(flt(a) for a in amounts)


def apply_advance_to_payment_entries(organization, account_holder, amount):
	if amount == 0:
		return

	payments = frappe.get_all(
		"Payment Entry",
		filters={
			"organization": organization,
			"party": account_holder,
			"docstatus": 1,
		},
		fields=["name", "unallocated_amount", "posting_date"],
		order_by="posting_date asc, name asc",
	)

	remaining = abs(flt(amount))
	for payment in payments:
		if remaining <= 0:
			break
		current = flt(payment.unallocated_amount)
		if amount > 0:
			reduce_by = min(current, remaining)
			new_value = current - reduce_by
			remaining -= reduce_by
		else:
			increase_by = remaining
			new_value = current + increase_by
			remaining = 0
		frappe.db.set_value("Payment Entry", payment.name, "unallocated_amount", new_value)

	if remaining > 0:
		frappe.throw(_("Unable to reconcile full advance allocation"))
