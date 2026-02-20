# ifitwala_ed/accounting/doctype/sales_invoice/test_sales_invoice.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from ifitwala_ed.accounting.tests.factories import (
    make_account,
    make_account_holder,
    make_accounts_settings,
    make_billable_offering,
    make_organization,
    make_school,
    make_student,
)


class TestSalesInvoice(FrappeTestCase):
    def _base_context(self):
        org = make_organization("SI")
        school = make_school(org.name, "SI School")

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
        income = make_account(
            organization=org.name,
            root_type="Income",
            prefix="Income",
        )
        tax = make_account(
            organization=org.name,
            root_type="Liability",
            account_type="Tax",
            prefix="Tax",
        )

        make_accounts_settings(
            organization=org.name,
            receivable_account=receivable.name,
            advance_account=advance.name,
        )

        ah_primary = make_account_holder(org.name, prefix="Primary")
        ah_other = make_account_holder(org.name, prefix="Other")

        return {
            "org": org,
            "school": school,
            "receivable": receivable,
            "advance": advance,
            "income": income,
            "tax": tax,
            "ah_primary": ah_primary,
            "ah_other": ah_other,
        }

    def test_student_account_holder_must_match_invoice_account_holder(self):
        ctx = self._base_context()

        student = make_student(
            organization=ctx["org"].name,
            account_holder=ctx["ah_other"].name,
            school=ctx["school"].name,
            prefix="Mismatch",
        )
        offering = make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="Program",
            pricing_mode="Fixed",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Sales Invoice",
                    "organization": ctx["org"].name,
                    "account_holder": ctx["ah_primary"].name,
                    "posting_date": nowdate(),
                    "items": [
                        {
                            "billable_offering": offering.name,
                            "charge_source": "Program Offering",
                            "student": student.name,
                            "qty": 1,
                            "rate": 100,
                            "income_account": ctx["income"].name,
                        }
                    ],
                }
            ).insert()

    def test_submit_posts_balanced_double_entry_gl(self):
        ctx = self._base_context()
        offering = make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": ctx["org"].name,
                "account_holder": ctx["ah_primary"].name,
                "posting_date": nowdate(),
                "items": [
                    {
                        "billable_offering": offering.name,
                        "charge_source": "Extra",
                        "qty": 2,
                        "rate": 50,
                        "income_account": ctx["income"].name,
                    }
                ],
                "taxes": [
                    {
                        "account_head": ctx["tax"].name,
                        "rate": 10,
                        "included_in_print_rate": 0,
                    }
                ],
            }
        )
        invoice.insert()
        invoice.submit()

        self.assertEqual(flt(invoice.total), 100)
        self.assertEqual(flt(invoice.total_taxes), 10)
        self.assertEqual(flt(invoice.grand_total), 110)

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Sales Invoice", "voucher_no": invoice.name, "is_cancelled": 0},
            fields=["account", "debit", "credit", "party", "party_type"],
        )

        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))
        self.assertTrue(
            any(
                row.account == ctx["receivable"].name
                and row.party_type == "Account Holder"
                and row.party == ctx["ah_primary"].name
                and flt(row.debit) == 110
                for row in gl_rows
            )
        )

    def test_inclusive_tax_keeps_grand_total_constant_and_balanced(self):
        ctx = self._base_context()
        offering = make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": ctx["org"].name,
                "account_holder": ctx["ah_primary"].name,
                "posting_date": nowdate(),
                "items": [
                    {
                        "billable_offering": offering.name,
                        "charge_source": "Extra",
                        "qty": 1,
                        "rate": 100,
                        "income_account": ctx["income"].name,
                    }
                ],
                "taxes": [
                    {
                        "account_head": ctx["tax"].name,
                        "rate": 10,
                        "included_in_print_rate": 1,
                    }
                ],
            }
        )
        invoice.insert()
        invoice.submit()

        self.assertAlmostEqual(flt(invoice.grand_total), 100, places=6)
        self.assertAlmostEqual(flt(invoice.total_taxes), 100 - (100 / 1.1), places=6)

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Sales Invoice", "voucher_no": invoice.name, "is_cancelled": 0},
            fields=["debit", "credit"],
        )
        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))

    def test_submitted_invoice_is_immutable_for_amount_lines(self):
        ctx = self._base_context()
        offering = make_billable_offering(
            organization=ctx["org"].name,
            income_account=ctx["income"].name,
            offering_type="One-off Fee",
            pricing_mode="Fixed",
        )

        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "organization": ctx["org"].name,
                "account_holder": ctx["ah_primary"].name,
                "posting_date": nowdate(),
                "items": [
                    {
                        "billable_offering": offering.name,
                        "charge_source": "Extra",
                        "qty": 1,
                        "rate": 100,
                        "income_account": ctx["income"].name,
                    }
                ],
            }
        )
        invoice.insert()
        invoice.submit()

        invoice.reload()
        invoice.items[0].rate = 120
        with self.assertRaises(frappe.ValidationError):
            invoice.save()
