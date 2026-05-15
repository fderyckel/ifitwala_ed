# ifitwala_ed/accounting/doctype/gl_entry/test_gl_entry.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestGLEntry(FrappeTestCase):
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

    def test_gl_entry_account_must_belong_to_same_organization(self):
        org_a = self.make_organization("GL Org A")
        org_b = self.make_organization("GL Org B")
        account_a = self.make_account(
            organization=org_a.name,
            root_type="Asset",
            account_type="Cash",
            prefix="Cash Org A",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "GL Entry",
                    "organization": org_b.name,
                    "posting_date": "2026-01-15",
                    "account": account_a.name,
                    "debit": 100,
                    "credit": 0,
                }
            ).insert()

    def test_group_accounts_cannot_receive_postings(self):
        org = self.make_organization("GL")
        group_account = self.make_account(
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
        org = self.make_organization("GL Side")
        account = self.make_account(
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
