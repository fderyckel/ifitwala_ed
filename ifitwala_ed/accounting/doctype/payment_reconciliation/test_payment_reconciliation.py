# ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate


class TestPaymentReconciliation(FrappeTestCase):
    def make_organization(self, prefix="Org"):
        org = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"O{frappe.generate_hash(length=4)}",
            }
        )
        org.insert()
        return org

    def make_account(
        self,
        organization,
        root_type,
        account_type=None,
        is_group=0,
        parent_account=None,
        prefix="Account",
    ):
        doc = {
            "doctype": "Account",
            "organization": organization,
            "account_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "root_type": root_type,
            "is_group": 1 if is_group else 0,
        }
        if account_type:
            doc["account_type"] = account_type
        if parent_account:
            doc["parent_account"] = parent_account

        account = frappe.get_doc(doc)
        account.insert()
        return account

    def make_accounts_settings(
        self,
        organization,
        receivable_account,
        advance_account,
        cash_account=None,
        bank_account=None,
        tax_payable_account=None,
    ):
        if frappe.db.exists("Accounts Settings", organization):
            settings = frappe.get_doc("Accounts Settings", organization)
        else:
            settings = frappe.new_doc("Accounts Settings")
            settings.organization = organization

        settings.default_receivable_account = receivable_account
        settings.default_advance_account = advance_account
        settings.default_cash_account = cash_account
        settings.default_bank_account = bank_account
        settings.default_tax_payable_account = tax_payable_account
        settings.save()
        return settings

    def make_account_holder(self, organization, holder_type="Individual", prefix="Account Holder"):
        account_holder = frappe.get_doc(
            {
                "doctype": "Account Holder",
                "organization": organization,
                "account_holder_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "account_holder_type": holder_type,
            }
        )
        account_holder.insert()
        return account_holder

    def make_billable_offering(self, organization, income_account, offering_type="One-off Fee", pricing_mode="Fixed"):
        offering = frappe.get_doc(
            {
                "doctype": "Billable Offering",
                "organization": organization,
                "offering_type": offering_type,
                "income_account": income_account,
                "pricing_mode": pricing_mode,
            }
        )
        offering.insert()
        return offering

    def make_sales_invoice(
        self,
        organization,
        account_holder,
        items,
        posting_date=None,
        taxes=None,
        taxes_and_charges=None,
        program_offering=None,
    ):
        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": organization,
                "account_holder": account_holder,
                "posting_date": posting_date or nowdate(),
                "items": items,
                "taxes": taxes or [],
                "taxes_and_charges": taxes_and_charges,
                "program_offering": program_offering,
            }
        )
        invoice.insert()
        return invoice

    def _base_context_with_advance(self):
        org = self.make_organization("PR")
        receivable = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Receivable",
            prefix="A/R",
        )
        advance = self.make_account(
            organization=org.name,
            root_type="Liability",
            prefix="Advance",
        )
        bank = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Bank",
            prefix="Bank",
        )
        income = self.make_account(
            organization=org.name,
            root_type="Income",
            prefix="Income",
        )

        self.make_accounts_settings(
            organization=org.name,
            receivable_account=receivable.name,
            advance_account=advance.name,
            bank_account=bank.name,
        )

        account_holder = self.make_account_holder(org.name)
        offering = self.make_billable_offering(
            organization=org.name,
            income_account=income.name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = self.make_sales_invoice(
            organization=org.name,
            account_holder=account_holder.name,
            posting_date=nowdate(),
            items=[
                {
                    "billable_offering": offering.name,
                    "charge_source": "Extra",
                    "qty": 1,
                    "rate": 150,
                    "income_account": income.name,
                }
            ],
        )
        invoice.submit()

        payment = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "party_type": "Account Holder",
                "party": account_holder.name,
                "organization": org.name,
                "posting_date": nowdate(),
                "paid_to": bank.name,
                "paid_amount": 200,
                "references": [],
            }
        )
        payment.insert()
        payment.submit()

        return {
            "org": org,
            "receivable": receivable,
            "advance": advance,
            "income": income,
            "account_holder": account_holder,
            "invoice": invoice,
            "payment": payment,
        }

    def test_reconciliation_reduces_outstanding_and_consumes_advance(self):
        ctx = self._base_context_with_advance()

        recon = frappe.get_doc(
            {
                "doctype": "Payment Reconciliation",
                "organization": ctx["org"].name,
                "account_holder": ctx["account_holder"].name,
                "posting_date": nowdate(),
                "allocations": [
                    {
                        "sales_invoice": ctx["invoice"].name,
                        "allocated_amount": 120,
                    }
                ],
            }
        )
        recon.insert()
        recon.submit()

        invoice_outstanding = frappe.db.get_value("Sales Invoice", ctx["invoice"].name, "outstanding_amount")
        self.assertEqual(flt(invoice_outstanding), 30)

        payment_unallocated = frappe.db.get_value("Payment Entry", ctx["payment"].name, "unallocated_amount")
        self.assertEqual(flt(payment_unallocated), 80)

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Payment Reconciliation", "voucher_no": recon.name, "is_cancelled": 0},
            fields=["account", "debit", "credit", "party"],
        )

        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))
        self.assertTrue(any(row.account == ctx["advance"].name and flt(row.debit) == 120 for row in gl_rows))
        self.assertTrue(any(row.account == ctx["receivable"].name and flt(row.credit) == 120 for row in gl_rows))
        self.assertTrue(all(row.party == ctx["account_holder"].name for row in gl_rows))

    def test_cannot_allocate_more_than_available_advance(self):
        ctx = self._base_context_with_advance()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Payment Reconciliation",
                    "organization": ctx["org"].name,
                    "account_holder": ctx["account_holder"].name,
                    "posting_date": nowdate(),
                    "allocations": [
                        {
                            "sales_invoice": ctx["invoice"].name,
                            "allocated_amount": 220,
                        }
                    ],
                }
            ).insert()

    def test_reconciliation_rejects_invoice_from_other_account_holder(self):
        ctx = self._base_context_with_advance()
        other_holder = self.make_account_holder(ctx["org"].name, prefix="Other")
        offering = self.make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="Product",
            pricing_mode="Fixed",
        )
        other_invoice = self.make_sales_invoice(
            organization=ctx["org"].name,
            account_holder=other_holder.name,
            posting_date=nowdate(),
            items=[
                {
                    "billable_offering": offering.name,
                    "charge_source": "Extra",
                    "qty": 1,
                    "rate": 25,
                    "income_account": ctx["income"].name,
                }
            ],
        )
        other_invoice.submit()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Payment Reconciliation",
                    "organization": ctx["org"].name,
                    "account_holder": ctx["account_holder"].name,
                    "posting_date": nowdate(),
                    "allocations": [
                        {
                            "sales_invoice": other_invoice.name,
                            "allocated_amount": 10,
                        }
                    ],
                }
            ).insert()
