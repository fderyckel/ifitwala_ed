# ifitwala_ed/accounting/doctype/journal_entry/test_journal_entry.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from ifitwala_ed.accounting.tests.factories import make_account, make_organization


class TestJournalEntry(FrappeTestCase):
    def test_unbalanced_journal_entry_is_rejected(self):
        org = make_organization("JE")
        debit_account = make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Cash",
            prefix="JE Cash",
        )
        credit_account = make_account(
            organization=org.name,
            root_type="Income",
            prefix="JE Income",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Journal Entry",
                    "organization": org.name,
                    "posting_date": "2026-02-01",
                    "voucher_type": "Journal Entry",
                    "accounts": [
                        {"account": debit_account.name, "debit": 100, "credit": 0},
                        {"account": credit_account.name, "debit": 0, "credit": 90},
                    ],
                }
            ).insert()

    def test_submit_creates_balanced_gl_entries(self):
        org = make_organization("JE GL")
        debit_account = make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Cash",
            prefix="JE Debit",
        )
        credit_account = make_account(
            organization=org.name,
            root_type="Income",
            prefix="JE Credit",
        )

        je = frappe.get_doc(
            {
                "doctype": "Journal Entry",
                "organization": org.name,
                "posting_date": "2026-02-01",
                "voucher_type": "Journal Entry",
                "accounts": [
                    {"account": debit_account.name, "debit": 250, "credit": 0},
                    {"account": credit_account.name, "debit": 0, "credit": 250},
                ],
            }
        )
        je.insert()
        je.submit()

        gl_rows = frappe.get_all(
            "GL Entry",
            filters={"voucher_type": "Journal Entry", "voucher_no": je.name, "is_cancelled": 0},
            fields=["debit", "credit"],
        )

        self.assertEqual(len(gl_rows), 2)
        self.assertEqual(sum(flt(row.debit) for row in gl_rows), sum(flt(row.credit) for row in gl_rows))
