# ifitwala_ed/accounting/doctype/payment_reconciliation/test_payment_reconciliation.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from ifitwala_ed.accounting.tests.factories import (
    make_account,
    make_account_holder,
    make_accounts_settings,
    make_billable_offering,
    make_organization,
    make_sales_invoice,
)


class TestPaymentReconciliation(FrappeTestCase):
    def _base_context_with_advance(self):
        org = make_organization("PR")
        receivable = make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Receivable",
            prefix="A/R",
        )
        advance = make_account(
            organization=org.name,
            root_type="Liability",
            prefix="Advance",
        )
        bank = make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Bank",
            prefix="Bank",
        )
        income = make_account(
            organization=org.name,
            root_type="Income",
            prefix="Income",
        )

        make_accounts_settings(
            organization=org.name,
            receivable_account=receivable.name,
            advance_account=advance.name,
            bank_account=bank.name,
        )

        account_holder = make_account_holder(org.name)
        offering = make_billable_offering(
            organization=org.name,
            income_account=income.name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = make_sales_invoice(
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
