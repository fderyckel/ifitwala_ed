# ifitwala_ed/accounting/doctype/accounts_settings/test_accounts_settings.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestAccountsSettings(FrappeTestCase):
    def test_settings_are_named_by_organization(self):
        org = self._make_organization()
        settings = frappe.get_doc("Accounts Settings", org.name)

        self.assertEqual(settings.name, org.name)

    def test_default_accounts_must_belong_to_same_organization(self):
        org_a = self._make_organization("OrgA")
        org_b = self._make_organization("OrgB")
        receivable_a = self._make_account(org_a.name, root_type="Asset", account_type="Receivable")
        receivable_b = self._make_account(org_b.name, root_type="Asset", account_type="Receivable")
        settings = frappe.get_doc("Accounts Settings", org_b.name)
        settings.default_receivable_account = receivable_b.name
        settings.save(ignore_permissions=True)

        settings = frappe.get_doc("Accounts Settings", org_a.name)
        settings.default_receivable_account = receivable_b.name
        with self.assertRaises(frappe.ValidationError):
            settings.save(ignore_permissions=True)

        settings = frappe.get_doc("Accounts Settings", org_b.name)
        settings.default_receivable_account = receivable_a.name
        with self.assertRaises(frappe.ValidationError):
            settings.save(ignore_permissions=True)

    def _make_organization(self, prefix: str = "Org"):
        data = {
            "doctype": "Organization",
            "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "abbr": f"O{frappe.generate_hash(length=4)}",
        }
        if frappe.db.exists("Organization", "All Organizations"):
            data["parent_organization"] = "All Organizations"
        return frappe.get_doc(data).insert(ignore_permissions=True)

    def _make_account(self, organization: str, *, root_type: str, account_type: str | None = None):
        data = {
            "doctype": "Account",
            "organization": organization,
            "account_name": f"Account {frappe.generate_hash(length=6)}",
            "root_type": root_type,
            "is_group": 0,
        }
        if account_type:
            data["account_type"] = account_type
        return frappe.get_doc(data).insert(ignore_permissions=True)
