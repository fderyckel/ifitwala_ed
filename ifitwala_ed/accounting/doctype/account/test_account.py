# ifitwala_ed/accounting/doctype/account/test_account.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.doctype.account.account import get_children
from ifitwala_ed.accounting.doctype.account.chart_of_accounts.chart_of_accounts import sync_account_types_from_chart
from ifitwala_ed.accounting.doctype.account.chart_of_accounts.verified.standard_chart_of_accounts import (
    get as get_standard_chart,
)


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

    def test_account_name_is_qualified_by_organization_abbr(self):
        org = self.make_organization("Naming")
        account = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Cash",
            prefix="Cash Box",
        )

        self.assertTrue(account.name.endswith(f" - {org.abbr}"))

    def test_tree_children_are_scoped_by_organization(self):
        org = self.make_organization("Tree")

        roots = get_children("Account", organization=org.name, is_root=True)

        self.assertTrue(roots)
        self.assertIn("Application of Funds (Assets)", {row.get("title") for row in roots})

        asset_root_name = next(row.get("value") for row in roots if row.get("title") == "Application of Funds (Assets)")
        children = get_children("Account", organization=org.name, parent=asset_root_name)
        self.assertIn("Current Assets", {row.get("title") for row in children})

    def test_sync_account_types_from_standard_chart_backfills_missing_values(self):
        org = self.make_organization("Types")
        debtors = frappe.get_all(
            "Account",
            filters={"organization": org.name, "account_name": "Debtors"},
            fields=["name", "account_type"],
            limit=1,
        )[0]

        frappe.db.set_value("Account", debtors.name, "account_type", "", update_modified=False)
        updated = sync_account_types_from_chart(org.name, chart=get_standard_chart())
        account_type = frappe.db.get_value("Account", debtors.name, "account_type")

        self.assertGreaterEqual(updated, 1)
        self.assertEqual(account_type, "Receivable")
