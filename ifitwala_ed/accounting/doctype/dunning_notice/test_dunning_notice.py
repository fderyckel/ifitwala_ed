# ifitwala_ed/accounting/doctype/dunning_notice/test_dunning_notice.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from ifitwala_ed.accounting.doctype.dunning_notice.dunning_notice import create_payment_requests, load_overdue_items
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestDunningNotice(AccountingTestMixin, FrappeTestCase):
    def test_dunning_notice_loads_overdue_invoices_and_creates_payment_requests(self):
        org = self.make_organization("DUN")
        receivable = self.make_account(org.name, "Asset", account_type="Receivable", prefix="A/R")
        advance = self.make_account(org.name, "Liability", prefix="Advance")
        income = self.make_account(org.name, "Income", prefix="Income")
        self.make_accounts_settings(org.name, receivable.name, advance.name)
        account_holder = self.make_account_holder(org.name)
        offering = self.make_billable_offering(org.name, income.name)

        invoice = self.make_sales_invoice(
            organization=org.name,
            account_holder=account_holder.name,
            billable_offering=offering.name,
            income_account=income.name,
            qty=1,
            rate=120,
            posting_date="2026-01-01",
        )
        invoice.due_date = "2026-01-05"
        invoice.save()
        invoice.submit()

        notice = frappe.get_doc(
            {
                "doctype": "Dunning Notice",
                "organization": org.name,
                "posting_date": "2026-02-10",
                "account_holder": account_holder.name,
                "minimum_days_overdue": 10,
            }
        )
        notice.insert()

        load_overdue_items(notice.name)
        notice.reload()
        self.assertEqual(len(notice.items), 1)
        self.assertEqual(notice.items[0].sales_invoice, invoice.name)
        self.assertEqual(flt(notice.items[0].outstanding_amount), 120)

        created = create_payment_requests(notice.name)
        self.assertEqual(len(created), 1)
        notice.reload()
        self.assertTrue(bool(notice.items[0].payment_request))
