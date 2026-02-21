# ifitwala_ed/accounting/doctype/sales_taxes_and_charges_template/test_sales_taxes_and_charges_template.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestSalesTaxesandChargesTemplate(FrappeTestCase):
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

    def test_only_one_default_template_per_organization(self):
        org = self.make_organization("Tax Tpl")
        tax_account = self.make_account(
            organization=org.name,
            root_type="Liability",
            account_type="Tax",
            prefix="Tax Liability",
        )

        first = frappe.get_doc(
            {
                "doctype": "Sales Taxes and Charges Template",
                "title": f"Default T1 {frappe.generate_hash(length=6)}",
                "organization": org.name,
                "is_default": 1,
                "taxes": [{"account_head": tax_account.name, "rate": 10}],
            }
        )
        first.insert()

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Sales Taxes and Charges Template",
                    "title": f"Default T2 {frappe.generate_hash(length=6)}",
                    "organization": org.name,
                    "is_default": 1,
                    "taxes": [{"account_head": tax_account.name, "rate": 8}],
                }
            ).insert()
