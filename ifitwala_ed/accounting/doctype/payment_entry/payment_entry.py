# ifitwala_ed/accounting/doctype/payment_entry/payment_entry.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.accounting.ledger_utils import cancel_gl_entries, make_gl_entries, validate_posting_date
from ifitwala_ed.accounting.receivables import clamp_money, is_zero, money, persist_submitted_invoice_runtime_state


class PaymentEntry(Document):
    def validate(self):
        self.validate_party()
        self.validate_paid_to_account()
        self.validate_references()
        self.validate_amounts()
        self.set_reference_dimensions()
        validate_posting_date(self.organization, self.posting_date)

    def validate_party(self):
        if self.payment_type == "Receive":
            if self.party_type != "Account Holder":
                frappe.throw(_("Receive Payment Entries require Account Holder party type"))
            party_org = frappe.db.get_value("Account Holder", self.party, "organization")
            if party_org and party_org != self.organization:
                frappe.throw(_("Account Holder must belong to the same Organization"))
            return

        if self.payment_type == "Pay":
            if self.party_type != "Employee":
                frappe.throw(_("Pay Payment Entries require Employee party type"))
            party_org = frappe.db.get_value("Employee", self.party, "organization")
            if party_org and party_org != self.organization:
                frappe.throw(_("Employee must belong to the same Organization"))
            return

        frappe.throw(_("Unsupported Payment Type"))

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
        total_allocated = 0.0
        if self.payment_type == "Pay" and not self.references:
            frappe.throw(_("Pay Payment Entries require at least one Expense Claim reference"))

        for ref in self.references:
            if self.payment_type == "Receive":
                self._validate_sales_invoice_reference(ref)
            elif self.payment_type == "Pay":
                self._validate_expense_claim_reference(ref)
            else:
                frappe.throw(_("Unsupported Payment Type"))

            allocated_amount = self._validate_allocated_amount(ref)
            total_allocated = money(total_allocated + allocated_amount)

        if total_allocated > money(self.paid_amount or 0) and not is_zero(
            total_allocated - money(self.paid_amount or 0)
        ):
            frappe.throw(_("Allocated amount cannot exceed Paid Amount"))

        self.unallocated_amount = clamp_money(money(self.paid_amount or 0) - total_allocated)
        if self.payment_type == "Pay" and not is_zero(self.unallocated_amount):
            frappe.throw(_("Pay Payment Entries must be fully allocated to Expense Claims"))

    def _validate_sales_invoice_reference(self, ref):
        if ref.reference_doctype != "Sales Invoice":
            frappe.throw(_("Receive Payment Entries only support Sales Invoice references"))
        inv = frappe.db.get_value(
            "Sales Invoice",
            ref.reference_name,
            [
                "organization",
                "account_holder",
                "grand_total",
                "outstanding_amount",
                "docstatus",
                "status",
            ],
            as_dict=True,
        )
        if not inv:
            frappe.throw(_("Sales Invoice {sales_invoice} not found").format(sales_invoice=ref.reference_name))
        if inv.docstatus != 1:
            frappe.throw(_("Sales Invoice {sales_invoice} must be submitted").format(sales_invoice=ref.reference_name))
        if inv.organization != self.organization:
            frappe.throw(_("Sales Invoice must belong to the same Organization"))
        if inv.account_holder != self.party:
            frappe.throw(_("Sales Invoice must belong to the same Account Holder"))
        if inv.status == "Credit Note":
            frappe.throw(_("Credit notes cannot be used as payment references"))

        ref.total_amount = money(inv.grand_total or 0)
        ref.outstanding_amount = money(inv.outstanding_amount or 0)
        ref.payment_schedule_term = self._get_open_schedule_term(ref.reference_name)

    def _validate_expense_claim_reference(self, ref):
        if ref.reference_doctype != "Expense Claim":
            frappe.throw(_("Pay Payment Entries only support Expense Claim references"))
        claim_rows = frappe.db.sql(
            """
            SELECT
                organization,
                employee,
                sanctioned_total,
                outstanding_amount,
                status,
                payable_account
            FROM `tabExpense Claim`
            WHERE name = %s
            FOR UPDATE
            """,
            (ref.reference_name,),
            as_dict=True,
        )
        claim = claim_rows[0] if claim_rows else None
        if not claim:
            frappe.throw(_("Expense Claim {claim} not found").format(claim=ref.reference_name))
        if claim.organization != self.organization:
            frappe.throw(_("Expense Claim must belong to the same Organization"))
        if claim.employee != self.party:
            frappe.throw(_("Expense Claim must belong to the same Employee"))
        if claim.status != "Payable Posted":
            frappe.throw(_("Expense Claim must be posted to payable before payment"))
        if not claim.payable_account:
            frappe.throw(_("Expense Claim is missing payable account"))

        ref.total_amount = money(claim.sanctioned_total or 0)
        ref.outstanding_amount = money(claim.outstanding_amount or 0)
        ref.payment_schedule_term = None

    def _validate_allocated_amount(self, ref):
        allocated_amount = money(ref.allocated_amount or 0)
        if allocated_amount < 0:
            frappe.throw(_("Allocated amount cannot be negative"))
        if allocated_amount > ref.outstanding_amount and not is_zero(allocated_amount - ref.outstanding_amount):
            frappe.throw(_("Allocated amount cannot exceed outstanding amount"))
        return allocated_amount

    def _get_open_schedule_term(self, sales_invoice: str) -> str | None:
        row = frappe.get_all(
            "Sales Invoice Payment Schedule",
            filters={
                "parent": sales_invoice,
                "parenttype": "Sales Invoice",
                "outstanding_amount": [">", 0],
            },
            fields=["term_name", "due_date"],
            order_by="due_date asc, idx asc",
            limit=1,
        )
        if not row:
            return None
        return row[0].get("term_name")

    def validate_amounts(self):
        if money(self.paid_amount or 0) <= 0:
            frappe.throw(_("Paid Amount must be greater than zero"))

    def set_reference_dimensions(self):
        if not self.references:
            self.school = None
            self.program = None
            return

        if self.payment_type == "Pay":
            rows = frappe.get_all(
                "Expense Claim",
                filters={"name": ["in", [ref.reference_name for ref in self.references if ref.reference_name]]},
                fields=["name", "school"],
                limit=max(50, len(self.references) + 10),
            )
            schools = {row.get("school") for row in rows if row.get("school")}
            self.school = next(iter(schools)) if len(schools) == 1 else None
            self.program = None
            return

        rows = frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", [ref.reference_name for ref in self.references if ref.reference_name]]},
            fields=["name", "school", "program"],
            limit=max(50, len(self.references) + 10),
        )
        schools = {row.get("school") for row in rows if row.get("school")}
        programs = {row.get("program") for row in rows if row.get("program")}
        self.school = next(iter(schools)) if len(schools) == 1 else None
        self.program = next(iter(programs)) if len(programs) == 1 else None

    def on_submit(self):
        if self.payment_type == "Pay":
            self._on_submit_pay()
            return

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
                "debit": money(self.paid_amount),
                "credit": 0,
                "school": self.school,
                "program": self.program,
            }
        ]

        for ref in self.references:
            allocated_amount = money(ref.allocated_amount or 0)
            if is_zero(allocated_amount):
                continue
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
                    "credit": allocated_amount,
                    "school": self.school,
                    "program": self.program,
                }
            )
            frappe.db.set_value(
                "Sales Invoice",
                ref.reference_name,
                "outstanding_amount",
                clamp_money(money(ref.outstanding_amount or 0) - allocated_amount),
            )
            persist_submitted_invoice_runtime_state(ref.reference_name)

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
                    "credit": money(self.unallocated_amount),
                    "school": self.school,
                    "program": self.program,
                }
            )

        make_gl_entries(entries, "Payment Entry", self.name)

    def _on_submit_pay(self):
        entries = [
            {
                "organization": self.organization,
                "posting_date": self.posting_date,
                "account": self.paid_to,
                "party_type": None,
                "party": None,
                "against": None,
                "remarks": self.remarks,
                "debit": 0,
                "credit": money(self.paid_amount),
                "school": self.school,
                "program": self.program,
            }
        ]

        against_accounts = []
        for ref in self.references:
            allocated_amount = money(ref.allocated_amount or 0)
            if is_zero(allocated_amount):
                continue
            payable_account = frappe.db.get_value("Expense Claim", ref.reference_name, "payable_account")
            if not payable_account:
                frappe.throw(_("Expense Claim is missing payable account"))
            against_accounts.append(payable_account)
            entries.append(
                {
                    "organization": self.organization,
                    "posting_date": self.posting_date,
                    "account": payable_account,
                    "party_type": "Employee",
                    "party": self.party,
                    "against": self.paid_to,
                    "remarks": self.remarks,
                    "debit": allocated_amount,
                    "credit": 0,
                    "school": self.school,
                    "program": self.program,
                }
            )

        entries[0]["against"] = ", ".join(sorted(set(against_accounts)))
        make_gl_entries(entries, "Payment Entry", self.name)

        from ifitwala_ed.hr.expense_claims import apply_expense_claim_payment

        for ref in self.references:
            allocated_amount = money(ref.allocated_amount or 0)
            if is_zero(allocated_amount):
                continue
            apply_expense_claim_payment(
                ref.reference_name,
                allocated_amount=allocated_amount,
                payment_entry=self.name,
                posting_datetime=self.posting_date,
            )

    def on_cancel(self):
        if self.payment_type == "Pay":
            self._on_cancel_pay()
            return

        cancel_gl_entries("Payment Entry", self.name)
        for ref in self.references:
            inv = money(frappe.db.get_value("Sales Invoice", ref.reference_name, "outstanding_amount") or 0)
            frappe.db.set_value(
                "Sales Invoice",
                ref.reference_name,
                "outstanding_amount",
                clamp_money(inv + money(ref.allocated_amount or 0)),
            )
            persist_submitted_invoice_runtime_state(ref.reference_name)

    def _on_cancel_pay(self):
        cancel_gl_entries("Payment Entry", self.name)

        from ifitwala_ed.hr.expense_claims import apply_expense_claim_payment

        for ref in self.references:
            allocated_amount = money(ref.allocated_amount or 0)
            if is_zero(allocated_amount):
                continue
            apply_expense_claim_payment(
                ref.reference_name,
                allocated_amount=allocated_amount,
                payment_entry=self.name,
                cancel=True,
            )
