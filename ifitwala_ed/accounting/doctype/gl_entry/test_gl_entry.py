# ifitwala_ed/accounting/doctype/gl_entry/test_gl_entry.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.tests.factories import make_account, make_organization


class TestGLEntry(FrappeTestCase):
    def test_group_accounts_cannot_receive_postings(self):
        org = make_organization("GL")
        group_account = make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Cash",
            is_group=1,
            prefix="Cash Group",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "GL Entry",
                    "organization": org.name,
                    "posting_date": "2026-01-15",
                    "account": group_account.name,
                    "debit": 100,
                    "credit": 0,
                }
            ).insert()

    def test_gl_entry_requires_exactly_one_side(self):
        org = make_organization("GL Side")
        account = make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Cash",
            prefix="Cash Leaf",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "GL Entry",
                    "organization": org.name,
                    "posting_date": "2026-01-15",
                    "account": account.name,
                    "debit": 100,
                    "credit": 100,
                }
            ).insert()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "GL Entry",
                    "organization": org.name,
                    "posting_date": "2026-01-15",
                    "account": account.name,
                    "debit": 0,
                    "credit": 0,
                }
            ).insert()
