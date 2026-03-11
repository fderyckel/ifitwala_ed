# ifitwala_ed/accounting/doctype/payment_request/test_payment_request.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt, nowdate

from ifitwala_ed.accounting.doctype.payment_request.payment_request import create_from_sales_invoice, mark_sent
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestPaymentRequest(AccountingTestMixin, FrappeTestCase):
    def _base_context(self):
        org = self.make_organization("PRQ")
        school = self.make_school(org.name, "PRQ School")
        receivable = self.make_account(org.name, "Asset", account_type="Receivable", prefix="A/R")
        advance = self.make_account(org.name, "Liability", prefix="Advance")
        bank = self.make_account(org.name, "Asset", account_type="Bank", prefix="Bank")
        income = self.make_account(org.name, "Income", prefix="Income")
        self.make_accounts_settings(org.name, receivable.name, advance.name, bank_account=bank.name)

        account_holder = self.make_account_holder(org.name)
        student = self.make_student(org.name, account_holder.name, school=school.name, prefix="Request")
        program_offering = self.make_program_offering(org.name, school=school.name)
        offering = self.make_billable_offering(org.name, income.name, offering_type="Program")
        invoice = self.make_sales_invoice(
            organization=org.name,
            account_holder=account_holder.name,
            billable_offering=offering.name,
            income_account=income.name,
            student=student.name,
            qty=1,
            rate=100,
            program_offering=program_offering.name,
            posting_date=nowdate(),
        )
        invoice.submit()

        return {
            "org": org,
            "bank": bank,
            "account_holder": account_holder,
            "invoice": invoice,
        }

    def test_payment_request_tracks_invoice_until_paid(self):
        ctx = self._base_context()

        request_name = create_from_sales_invoice(ctx["invoice"].name)
        request = frappe.get_doc("Payment Request", request_name)
        self.assertEqual(request.status, "Draft")
        self.assertEqual(flt(request.requested_amount), 100)
        self.assertEqual(request.sales_invoice, ctx["invoice"].name)

        mark_sent(request.name)
        request.reload()
        self.assertEqual(request.status, "Sent")

        payment = frappe.get_doc(
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
                        "allocated_amount": 100,
                    }
                ],
            }
        )
        payment.insert()
        payment.submit()

        request.reload()
        self.assertEqual(request.status, "Paid")
        self.assertEqual(flt(request.outstanding_amount), 0)
