# ifitwala_ed/accounting/doctype/account/test_account.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.accounting.tests.factories import make_account, make_organization


class TestAccount(FrappeTestCase):
    def test_receivable_account_must_be_asset(self):
        org = make_organization("Acct")

        with self.assertRaises(frappe.ValidationError):
            make_account(
                organization=org.name,
                root_type="Liability",
                account_type="Receivable",
                prefix="Bad Receivable",
            )

    def test_parent_account_must_match_organization(self):
        org_a = make_organization("Parent")
        org_b = make_organization("Child")
        parent = make_account(
            organization=org_a.name,
            root_type="Income",
            is_group=1,
            prefix="Parent Income",
        )

        with self.assertRaises(frappe.ValidationError):
            make_account(
                organization=org_b.name,
                root_type="Income",
                parent_account=parent.name,
                prefix="Wrong Org Child",
            )

    def test_parent_account_must_match_root_type(self):
        org = make_organization("Root")
        parent = make_account(
            organization=org.name,
            root_type="Income",
            is_group=1,
            prefix="Income Parent",
        )

        with self.assertRaises(frappe.ValidationError):
            make_account(
                organization=org.name,
                root_type="Expense",
                parent_account=parent.name,
                prefix="Expense Child",
            )
