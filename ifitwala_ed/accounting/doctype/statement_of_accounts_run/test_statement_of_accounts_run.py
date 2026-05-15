# ifitwala_ed/accounting/doctype/statement_of_accounts_run/test_statement_of_accounts_run.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from ifitwala_ed.accounting.doctype.statement_of_accounts_run.statement_of_accounts_run import (
    load_account_holders,
    mark_processed,
)
from ifitwala_ed.accounting.test_support import AccountingTestMixin


class TestStatementOfAccountsRun(AccountingTestMixin, FrappeTestCase):
    def test_statement_run_groups_open_balances_by_account_holder(self):
        org = self.make_organization("SOA")
        receivable = self.make_account(org.name, "Asset", account_type="Receivable", prefix="A/R")
        advance = self.make_account(org.name, "Liability", prefix="Advance")
        income = self.make_account(org.name, "Income", prefix="Income")
        self.make_accounts_settings(org.name, receivable.name, advance.name)
        account_holder = self.make_account_holder(org.name)
        offering = self.make_billable_offering(org.name, income.name)

        invoice_a = self.make_sales_invoice(
            organization=org.name,
            account_holder=account_holder.name,
            billable_offering=offering.name,
            income_account=income.name,
            qty=1,
            rate=100,
            posting_date="2026-01-01",
        )
        invoice_a.submit()
        invoice_b = self.make_sales_invoice(
            organization=org.name,
            account_holder=account_holder.name,
            billable_offering=offering.name,
            income_account=income.name,
            qty=1,
            rate=60,
            posting_date="2026-01-15",
        )
        invoice_b.submit()

        run = frappe.get_doc(
            {
                "doctype": "Statement Of Accounts Run",
                "organization": org.name,
                "as_of_date": "2026-02-10",
            }
        )
        run.insert()

        load_account_holders(run.name)
        run.reload()
        self.assertEqual(len(run.items), 1)
        self.assertEqual(run.items[0].account_holder, account_holder.name)
        self.assertEqual(flt(run.items[0].statement_balance), 160)
        self.assertEqual(run.items[0].invoice_count, 2)

        mark_processed(run.name)
        run.reload()
        self.assertEqual(run.status, "Processed")
