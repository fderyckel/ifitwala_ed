# ifitwala_ed/accounting/doctype/payment_entry/test_payment_entry.py

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


class TestPaymentEntry(FrappeTestCase):
    def _base_context(self):
        org = make_organization("PE")
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
                    "rate": 120,
                    "income_account": income.name,
                }
            ],
        )
        invoice.submit()

        return {
            "org": org,
            "receivable": receivable,
            "advance": advance,
            "bank": bank,
            "account_holder": account_holder,
            "invoice": invoice,
        }

    def test_allocated_amount_cannot_exceed_invoice_outstanding(self):
        ctx = self._base_context()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Payment Entry",
                    "payment_type": "Receive",
                    "party_type": "Account Holder",
                    "party": ctx["account_holder"].name,
                    "organization": ctx["org"].name,
                    "posting_date": nowdate(),
                    "paid_to": ctx["bank"].name,
                    "paid_amount": 100,
                    "references": [
                        {
                            "reference_doctype": "Sales Invoice",
                            "reference_name": ctx["invoice"].name,
                            "allocated_amount": 121,
                        }
                    ],
                }
            ).insert()

    def test_unallocated_amount_posts_to_advance_liability(self):
        ctx = self._base_context()

        pe = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "party_type": "Account Holder",
                "party": ctx["account_holder"].name,
                "organization": ctx["org"].name,
                "posting_date": nowdate(),
                "paid_to": ctx["bank"].name,
                "paid_amount": 200,
                "references": [
                    {
                        "reference_doctype": "Sales Invoice",
                        "reference_name": ctx["invoice"].name,
                        "allocated_amount": 120,
                    }
                ],
            }
        )
        pe.insert()
        pe.submit()

        self.assertEqual(flt(pe.unallocated_amount), 80)

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Payment Entry", "voucher_no": pe.name, "is_cancelled": 0},
            fields=["account", "party", "debit", "credit"],
        )

        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))
        self.assertEqual(
            sum(flt(row.credit) for row in gl_rows if row.account == ctx["receivable"].name),
            120,
        )
        self.assertTrue(
            any(
                row.account == ctx["advance"].name and row.party == ctx["account_holder"].name and flt(row.credit) == 80
                for row in gl_rows
            )
        )

        outstanding = frappe.db.get_value("Sales Invoice", ctx["invoice"].name, "outstanding_amount")
        self.assertEqual(flt(outstanding), 0)
