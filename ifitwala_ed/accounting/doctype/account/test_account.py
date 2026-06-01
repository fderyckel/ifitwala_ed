# ifitwala_ed/accounting/doctype/account/test_account.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date

from ifitwala_ed.accounting.doctype.account import account as account_module
from ifitwala_ed.accounting.doctype.account.account import (
    get_account_name_number_update_preview,
    get_account_tree_context,
    get_children,
    get_permission_query_conditions,
    has_permission,
    update_account_name_number,
)
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
        account_number=None,
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
        if account_number:
            doc["account_number"] = account_number

        account = frappe.get_doc(doc)
        account.insert()
        return account

    def make_fiscal_year(self, organization, year="2026"):
        existing = frappe.get_all(
            "Fiscal Year Organization",
            filters={"organization": organization},
            fields=["parent"],
            limit=100,
        )
        for row in existing:
            fiscal_year = frappe.get_doc("Fiscal Year", row.parent)
            if (
                str(fiscal_year.year_start_date) == f"{year}-01-01"
                and str(fiscal_year.year_end_date) == f"{year}-12-31"
            ):
                return fiscal_year

        fiscal_year = frappe.get_doc(
            {
                "doctype": "Fiscal Year",
                "year": f"{organization}-{year}-{frappe.generate_hash(length=4)}",
                "year_start_date": f"{year}-01-01",
                "year_end_date": f"{year}-12-31",
                "organizations": [{"organization": organization}],
            }
        )
        fiscal_year.insert()
        return fiscal_year

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

    def test_account_permission_query_scopes_finance_user_by_employee_org_descendants(self):
        with (
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.get_roles",
                return_value=["Accounts User"],
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.get_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.db.escape",
                side_effect=lambda value: f"'{value}'",
            ),
        ):
            condition = get_permission_query_conditions(user="accounts.user@example.com")

        self.assertEqual(condition, "`tabAccount`.`organization` IN ('ORG-CHILD', 'ORG-ROOT')")

    def test_account_permission_query_blocks_finance_user_without_employee_org(self):
        with (
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.get_roles",
                return_value=["Accounts User"],
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.get_user_base_org",
                return_value=None,
            ),
        ):
            condition = get_permission_query_conditions(user="accounts.user@example.com")

        self.assertEqual(condition, "1=0")

    def test_account_has_permission_allows_descendant_read_and_blocks_sibling(self):
        allowed_doc = frappe._dict(organization="ORG-CHILD")
        blocked_doc = frappe._dict(organization="ORG-SIBLING")

        with (
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.get_roles",
                return_value=["Accounts User"],
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account._get_account_organization_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            self.assertTrue(has_permission(allowed_doc, ptype="read", user="accounts.user@example.com"))
            self.assertFalse(has_permission(blocked_doc, ptype="read", user="accounts.user@example.com"))
            self.assertFalse(has_permission(allowed_doc, ptype="write", user="accounts.user@example.com"))

    def test_account_has_permission_allows_manager_write_inside_scope(self):
        allowed_doc = frappe._dict(organization="ORG-CHILD")

        with (
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.get_roles",
                return_value=["Accounts Manager"],
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account._get_account_organization_scope",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            self.assertTrue(has_permission(allowed_doc, ptype="write", user="accounts.manager@example.com"))

    def test_account_tree_context_defaults_to_employee_org_and_descendant_scope(self):
        with (
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.session",
                frappe._dict(user="accounts.user@example.com"),
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.get_roles",
                return_value=["Accounts User"],
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.get_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
        ):
            context = get_account_tree_context()

        self.assertEqual(context["default_organization"], "ORG-ROOT")
        self.assertEqual(context["allowed_organizations"], ["ORG-ROOT", "ORG-CHILD"])
        self.assertTrue(context["has_scope"])
        self.assertFalse(context["unrestricted"])

    def test_account_tree_context_explains_missing_accounting_role(self):
        with (
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.session",
                frappe._dict(user="employee@example.com"),
            ),
            patch(
                "ifitwala_ed.accounting.doctype.account.account.frappe.get_roles",
                return_value=["Employee"],
            ),
        ):
            context = get_account_tree_context()

        self.assertFalse(context["has_scope"])
        self.assertIn("Accounts User", context["message"])

    def test_account_tree_children_block_out_of_scope_organization(self):
        with patch(
            "ifitwala_ed.accounting.doctype.account.account._account_user_can_access_organization",
            return_value=False,
        ):
            with self.assertRaises(frappe.PermissionError):
                get_children("Account", organization="ORG-SIBLING", is_root=True)

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

    def test_update_account_name_number_renames_and_audits_child_account(self):
        org = self.make_organization("Rename")
        parent = self.make_account(
            organization=org.name,
            root_type="Asset",
            is_group=1,
            prefix="Rename Parent",
        )
        account = self.make_account(
            organization=org.name,
            root_type="Asset",
            parent_account=parent.name,
            prefix="Old Cash",
            account_number=f"RN-{frappe.generate_hash(length=5)}",
        )

        result = update_account_name_number(
            name=account.name,
            account_name="Renamed Cash",
            account_number=f"RN-{frappe.generate_hash(length=5)}",
            reason="Correct chart label for finance users",
        )

        self.assertNotEqual(result["name"], account.name)
        self.assertTrue(frappe.db.exists("Account", result["name"]))
        renamed = frappe.get_doc("Account", result["name"])
        self.assertEqual(renamed.account_name, "Renamed Cash")
        self.assertTrue(result["audit_comment"])
        comment = frappe.db.get_value("Comment", result["audit_comment"], "content")
        self.assertIn("Correct chart label for finance users", comment)
        self.assertIn(account.name, comment)
        self.assertIn(result["name"], comment)

    def test_account_name_number_preview_uses_server_autoname(self):
        org = self.make_organization("Preview")
        parent = self.make_account(
            organization=org.name,
            root_type="Asset",
            is_group=1,
            prefix="Preview Parent",
        )
        account = self.make_account(
            organization=org.name,
            root_type="Asset",
            parent_account=parent.name,
            prefix="Preview Child",
        )
        account_number = f"PV-{frappe.generate_hash(length=5)}"

        preview = get_account_name_number_update_preview(
            name=account.name,
            account_name="Preview Cash",
            account_number=account_number,
        )

        self.assertEqual(preview["name"], f"{account_number} - Preview Cash - {org.abbr}")

    def test_update_account_name_number_updates_account_links(self):
        org = self.make_organization("Links")
        self.make_fiscal_year(org.name)
        asset_parent = self.make_account(
            organization=org.name,
            root_type="Asset",
            is_group=1,
            prefix="Link Asset Parent",
        )
        liability_parent = self.make_account(
            organization=org.name,
            root_type="Liability",
            is_group=1,
            prefix="Link Liability Parent",
        )
        income_parent = self.make_account(
            organization=org.name,
            root_type="Income",
            is_group=1,
            prefix="Link Income Parent",
        )
        expense_parent = self.make_account(
            organization=org.name,
            root_type="Expense",
            is_group=1,
            prefix="Link Expense Parent",
        )
        receivable = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Receivable",
            parent_account=asset_parent.name,
            prefix="Linked Receivable",
            account_number=f"LR-{frappe.generate_hash(length=5)}",
        )
        advance = self.make_account(
            organization=org.name,
            root_type="Liability",
            parent_account=liability_parent.name,
            prefix="Linked Advance",
        )
        bank = self.make_account(
            organization=org.name,
            root_type="Asset",
            account_type="Bank",
            parent_account=asset_parent.name,
            prefix="Linked Bank",
            account_number=f"LB-{frappe.generate_hash(length=5)}",
        )
        income = self.make_account(
            organization=org.name,
            root_type="Income",
            parent_account=income_parent.name,
            prefix="Linked Income",
            account_number=f"LI-{frappe.generate_hash(length=5)}",
        )
        tax = self.make_account(
            organization=org.name,
            root_type="Liability",
            account_type="Tax",
            parent_account=liability_parent.name,
            prefix="Linked Tax",
            account_number=f"LT-{frappe.generate_hash(length=5)}",
        )
        expense = self.make_account(
            organization=org.name,
            root_type="Expense",
            parent_account=expense_parent.name,
            prefix="Linked Expense",
        )

        if frappe.db.exists("Accounts Settings", org.name):
            settings = frappe.get_doc("Accounts Settings", org.name)
        else:
            settings = frappe.new_doc("Accounts Settings")
            settings.organization = org.name
        settings.default_receivable_account = receivable.name
        settings.default_advance_account = advance.name
        settings.default_bank_account = bank.name
        settings.default_tax_payable_account = tax.name
        settings.save()
        gl_entry = frappe.get_doc(
            {
                "doctype": "GL Entry",
                "organization": org.name,
                "posting_date": "2026-01-15",
                "account": receivable.name,
                "debit": 100,
                "voucher_type": "Test",
                "voucher_no": "TEST-ACCOUNT-RENAME",
            }
        )
        gl_entry.insert(ignore_permissions=True)
        offering = frappe.get_doc(
            {
                "doctype": "Billable Offering",
                "organization": org.name,
                "offering_name": f"Account Rename Test {frappe.generate_hash(length=6)}",
                "offering_type": "One-off Fee",
                "income_account": income.name,
                "pricing_mode": "Fixed",
            }
        )
        offering.insert()
        account_holder = frappe.get_doc(
            {
                "doctype": "Account Holder",
                "organization": org.name,
                "account_holder_name": f"Account Rename Holder {frappe.generate_hash(length=6)}",
                "account_holder_type": "Individual",
            }
        )
        account_holder.insert()
        invoice = frappe.get_doc(
            {
                "doctype": "Sales Invoice",
                "account_holder": account_holder.name,
                "organization": org.name,
                "posting_date": "2026-01-15",
                "items": [
                    {
                        "charge_source": "Manual",
                        "description": "Manual rename-link coverage",
                        "qty": 1,
                        "rate": 100,
                        "income_account": income.name,
                    }
                ],
                "taxes": [
                    {
                        "description": "Rename-link tax coverage",
                        "account_head": tax.name,
                        "rate": 7,
                    }
                ],
            }
        )
        invoice.insert()
        payment = frappe.get_doc(
            {
                "doctype": "Payment Entry",
                "payment_type": "Receive",
                "party_type": "Account Holder",
                "party": account_holder.name,
                "organization": org.name,
                "posting_date": "2026-01-15",
                "paid_to": bank.name,
                "paid_amount": 25,
            }
        )
        payment.insert()
        journal_entry = frappe.get_doc(
            {
                "doctype": "Journal Entry",
                "organization": org.name,
                "posting_date": "2026-01-15",
                "voucher_type": "Journal Entry",
                "accounts": [
                    {"account": expense.name, "debit": 50, "credit": 0},
                    {"account": income.name, "debit": 0, "credit": 50},
                ],
            }
        )
        journal_entry.insert()
        invoice_item = invoice.items[0].name
        tax_row = invoice.taxes[0].name
        journal_income_row = next(row.name for row in journal_entry.accounts if row.account == income.name)

        renamed_receivable = update_account_name_number(
            name=receivable.name,
            account_name="Renamed Linked Receivable",
            account_number=f"LR-{frappe.generate_hash(length=5)}",
            reason="Verify linked accounting references update",
        )["name"]
        renamed_income = update_account_name_number(
            name=income.name,
            account_name="Renamed Linked Income",
            account_number=f"LI-{frappe.generate_hash(length=5)}",
            reason="Verify linked income references update",
        )["name"]
        renamed_bank = update_account_name_number(
            name=bank.name,
            account_name="Renamed Linked Bank",
            account_number=f"LB-{frappe.generate_hash(length=5)}",
            reason="Verify linked bank references update",
        )["name"]
        renamed_tax = update_account_name_number(
            name=tax.name,
            account_name="Renamed Linked Tax",
            account_number=f"LT-{frappe.generate_hash(length=5)}",
            reason="Verify linked tax references update",
        )["name"]

        self.assertEqual(
            frappe.db.get_value("Accounts Settings", settings.name, "default_receivable_account"),
            renamed_receivable,
        )
        self.assertEqual(frappe.db.get_value("GL Entry", gl_entry.name, "account"), renamed_receivable)
        self.assertEqual(frappe.db.get_value("Billable Offering", offering.name, "income_account"), renamed_income)
        self.assertEqual(frappe.db.get_value("Sales Invoice Item", invoice_item, "income_account"), renamed_income)
        self.assertEqual(frappe.db.get_value("Sales Taxes and Charges", tax_row, "account_head"), renamed_tax)
        self.assertEqual(frappe.db.get_value("Payment Entry", payment.name, "paid_to"), renamed_bank)
        self.assertEqual(frappe.db.get_value("Journal Entry Account", journal_income_row, "account"), renamed_income)

    def test_update_account_name_number_requires_reason(self):
        org = self.make_organization("Reason")
        parent = self.make_account(
            organization=org.name,
            root_type="Asset",
            is_group=1,
            prefix="Reason Parent",
        )
        account = self.make_account(
            organization=org.name,
            root_type="Asset",
            parent_account=parent.name,
            prefix="Reason Child",
        )

        with self.assertRaises(frappe.ValidationError):
            update_account_name_number(
                name=account.name,
                account_name="Reason Child Renamed",
                reason="",
            )

    def test_update_account_name_number_blocks_non_manager_role(self):
        org = self.make_organization("Role Guard")
        parent = self.make_account(
            organization=org.name,
            root_type="Asset",
            is_group=1,
            prefix="Role Guard Parent",
        )
        account = self.make_account(
            organization=org.name,
            root_type="Asset",
            parent_account=parent.name,
            prefix="Role Guard Child",
        )

        with (
            patch.object(account_module.frappe, "has_permission", return_value=True),
            patch.object(
                account_module.frappe,
                "get_roles",
                return_value=["Accounts User"],
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                update_account_name_number(
                    name=account.name,
                    account_name="Role Guard Child Renamed",
                    reason="Accounts User should not rename accounts",
                )

    def test_update_account_name_number_blocks_root_account(self):
        org = self.make_organization("Root Rename")
        root = self.make_account(
            organization=org.name,
            root_type="Asset",
            is_group=1,
            prefix="Root Rename Parent",
        )

        with self.assertRaises(frappe.ValidationError):
            update_account_name_number(
                name=root.name,
                account_name="Renamed Root",
                reason="Root rename should be blocked",
            )

    def test_update_account_name_number_blocks_duplicate_account_number(self):
        org = self.make_organization("Duplicate Number")
        parent = self.make_account(
            organization=org.name,
            root_type="Asset",
            is_group=1,
            prefix="Duplicate Parent",
        )
        duplicate_number = f"DN-{frappe.generate_hash(length=5)}"
        self.make_account(
            organization=org.name,
            root_type="Asset",
            parent_account=parent.name,
            prefix="Existing Number",
            account_number=duplicate_number,
        )
        account = self.make_account(
            organization=org.name,
            root_type="Asset",
            parent_account=parent.name,
            prefix="Target Number",
        )

        with self.assertRaises(frappe.ValidationError):
            update_account_name_number(
                name=account.name,
                account_name="Target Number Renamed",
                account_number=duplicate_number,
                reason="Try duplicate account number",
            )

    def test_account_rename_idle_guard_blocks_recent_gl_activity(self):
        with (
            patch.object(account_module.frappe, "in_test", False, create=True),
            patch.object(
                account_module.frappe.db,
                "get_value",
                return_value=add_to_date(None, minutes=-1),
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                account_module._ensure_account_rename_idle_system()
