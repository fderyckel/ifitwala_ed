# ifitwala_ed/accounting/doctype/account/test_account.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAccount(FrappeTestCase):
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

    def test_tax_account_must_be_liability(self):
        org = self.make_organization("Tax")

        with self.assertRaises(frappe.ValidationError):
            self.make_account(
                organization=org.name,
                root_type="Asset",
                account_type="Tax",
                prefix="Bad Tax",
            )

    def test_receivable_account_must_be_asset(self):
        org = self.make_organization("Acct")

        with self.assertRaises(frappe.ValidationError):
            self.make_account(
                organization=org.name,
                root_type="Liability",
                account_type="Receivable",
                prefix="Bad Receivable",
            )

    def test_parent_account_must_match_organization(self):
        org_a = self.make_organization("Parent")
        org_b = self.make_organization("Child")
        parent = self.make_account(
            organization=org_a.name,
            root_type="Income",
            is_group=1,
            prefix="Parent Income",
        )

        with self.assertRaises(frappe.ValidationError):
            self.make_account(
                organization=org_b.name,
                root_type="Income",
                parent_account=parent.name,
                prefix="Wrong Org Child",
            )

    def test_parent_account_must_match_root_type(self):
        org = self.make_organization("Root")
        parent = self.make_account(
            organization=org.name,
            root_type="Income",
            is_group=1,
            prefix="Income Parent",
        )

        with self.assertRaises(frappe.ValidationError):
            self.make_account(
                organization=org.name,
                root_type="Expense",
                parent_account=parent.name,
                prefix="Expense Child",
            )
