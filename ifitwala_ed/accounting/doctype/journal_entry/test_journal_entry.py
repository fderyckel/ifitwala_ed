# ifitwala_ed/accounting/doctype/journal_entry/test_journal_entry.py

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt


class TestJournalEntry(FrappeTestCase):
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

    def test_journal_entry_rejects_accounts_from_other_organizations(self):
        org_a = self.make_organization("JE Org A")
        org_b = self.make_organization("JE Org B")
        debit_account = self.make_account(
            organization=org_a.name,
            root_type="Asset",
            account_type="Cash",
            prefix="JE Debit A",
        )
        credit_account = self.make_account(
            organization=org_b.name,
            root_type="Income",
            prefix="JE Credit B",
        )

        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc(
                {
                    "doctype": "Journal Entry",
                    "organization": org_a.name,
                    "posting_date": "2026-02-01",
                    "voucher_type": "Journal Entry",
                    "accounts": [
                        {"account": debit_account.name, "debit": 100, "credit": 0},
                        {"account": credit_account.name, "debit": 0, "credit": 100},
                    ],
                }
            ).insert()

    def test_unbalanced_journal_entry_is_rejected(self):
        org = self.make_organization("JE")
        debit_account = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Cash",
            prefix="JE Cash",
        )
        credit_account = self.make_account(
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
        org = self.make_organization("JE GL")
        debit_account = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Cash",
            prefix="JE Debit",
        )
        credit_account = self.make_account(
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
