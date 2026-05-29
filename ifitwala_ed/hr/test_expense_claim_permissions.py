# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import json
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.hr import expense_claim_permissions, expense_claims

EXPENSE_CLAIM_JSON = Path(__file__).parent / "doctype" / "expense_claim" / "expense_claim.json"


class TestExpenseClaimPermissions(FrappeTestCase):
    def test_expense_claim_list_view_uses_employee_name_not_employee_link_title_join(self):
        metadata = json.loads(EXPENSE_CLAIM_JSON.read_text())
        fields = {field["fieldname"]: field for field in metadata["fields"]}

        self.assertNotIn("in_list_view", fields["employee"])
        self.assertEqual(fields["employee_name"].get("in_list_view"), 1)

    def test_expense_claim_status_metadata_matches_runtime_contract(self):
        metadata = json.loads(EXPENSE_CLAIM_JSON.read_text())
        fields = {field["fieldname"]: field for field in metadata["fields"]}
        status_options = set(fields["status"]["options"].splitlines())

        self.assertEqual(status_options, expense_claims.EXPENSE_CLAIM_STATUSES)
        self.assertIn("Needs Info", status_options)
        self.assertNotIn("Needs Info", expense_claims.EXPENSE_CLAIM_LOCKED_STATUSES)

    def test_expense_claim_todo_description_is_namespaced_by_kind(self):
        description = expense_claims._todo_description(
            expense_claims.EXPENSE_CLAIM_TODO_APPROVER_REVIEW,
            "Review expense claim EXC-26-00001",
        )

        self.assertIn(expense_claims.EXPENSE_CLAIM_TODO_MARKER, description)
        self.assertTrue(
            expense_claims._todo_kind_matches(
                description,
                {expense_claims.EXPENSE_CLAIM_TODO_APPROVER_REVIEW},
            )
        )
        self.assertFalse(
            expense_claims._todo_kind_matches(
                description,
                {expense_claims.EXPENSE_CLAIM_TODO_CLAIMANT_UPDATE},
            )
        )

    def test_finance_request_info_moves_approved_claim_to_needs_info(self):
        class FakeClaim:
            name = "EXC-26-00001"
            status = "Approved"
            decision_by = None
            decision_on = None
            decision_notes = None
            flags = frappe._dict()

            def save(self, ignore_permissions=False):
                self.saved_ignore_permissions = ignore_permissions

        claim = FakeClaim()

        with (
            patch("ifitwala_ed.hr.expense_claims.frappe.get_doc", return_value=claim),
            patch("ifitwala_ed.hr.expense_claims._ensure_finance_access") as ensure_finance_access,
            patch("ifitwala_ed.hr.expense_claims._close_expense_claim_todos") as close_todos,
            patch("ifitwala_ed.hr.expense_claims._assign_claimant_update_todo") as assign_claimant_todo,
            patch("ifitwala_ed.hr.expense_claims.now_datetime", return_value="2026-05-29 12:00:00"),
        ):
            returned = expense_claims.request_claim_info(
                "EXC-26-00001",
                notes="Please attach the itemized receipt.",
                acting_user="finance@example.com",
            )

        ensure_finance_access.assert_called_once_with("finance@example.com")
        close_todos.assert_called_once()
        assign_claimant_todo.assert_called_once_with(claim)
        self.assertIs(returned, claim)
        self.assertEqual(claim.status, "Needs Info")
        self.assertEqual(claim.decision_by, "finance@example.com")
        self.assertEqual(claim.decision_notes, "Please attach the itemized receipt.")
        self.assertTrue(claim.saved_ignore_permissions)

    def test_expense_claim_pqc_is_self_or_approver_scoped_for_employee(self):
        with (
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.frappe.get_roles",
                return_value=["Employee"],
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.frappe.db.get_value",
                return_value="HR-EMP-0001",
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.frappe.db.escape",
                side_effect=lambda value: f"'{value}'",
            ),
        ):
            condition = expense_claim_permissions.expense_claim_pqc(user="teacher@example.com")

        self.assertEqual(
            condition,
            "((`tabExpense Claim`.`employee` = 'HR-EMP-0001') OR "
            "(`tabExpense Claim`.`expense_approver` = 'teacher@example.com'))",
        )

    def test_expense_claim_pqc_is_org_and_school_scoped_for_finance(self):
        with (
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.frappe.get_roles",
                return_value=["Accounts User"],
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_user_base_school",
                return_value="SCH-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_descendant_schools",
                return_value=["SCH-ROOT", "SCH-LEAF"],
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.frappe.db.escape",
                side_effect=lambda value: f"'{value}'",
            ),
        ):
            condition = expense_claim_permissions.expense_claim_pqc(user="finance@example.com")

        self.assertEqual(
            condition,
            "`tabExpense Claim`.`organization` IN ('ORG-CHILD', 'ORG-ROOT') AND "
            "(`tabExpense Claim`.`school` IN ('SCH-LEAF', 'SCH-ROOT') OR "
            "COALESCE(`tabExpense Claim`.`school`, '') = '')",
        )

    def test_expense_claim_doc_permission_allows_claimant(self):
        doc = frappe._dict(
            doctype="Expense Claim",
            employee="HR-EMP-0001",
            expense_approver="approver@example.com",
            organization="ORG-1",
            school="SCH-1",
        )
        with patch(
            "ifitwala_ed.hr.expense_claim_permissions.frappe.db.get_value",
            return_value="HR-EMP-0001",
        ):
            allowed = expense_claim_permissions.expense_claim_has_permission(
                doc,
                user="teacher@example.com",
                ptype="read",
            )

        self.assertTrue(allowed)

    def test_expense_claim_doc_permission_blocks_out_of_scope_finance(self):
        doc = frappe._dict(
            doctype="Expense Claim",
            employee="HR-EMP-0002",
            expense_approver="approver@example.com",
            organization="ORG-OTHER",
            school="SCH-1",
        )
        with (
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.frappe.get_roles",
                return_value=["Accounts User"],
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.frappe.db.get_value",
                return_value=None,
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_user_base_org",
                return_value="ORG-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_descendant_organizations",
                return_value=["ORG-ROOT"],
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_user_base_school",
                return_value="SCH-ROOT",
            ),
            patch(
                "ifitwala_ed.hr.expense_claim_permissions.get_descendant_schools",
                return_value=["SCH-ROOT"],
            ),
        ):
            allowed = expense_claim_permissions.expense_claim_has_permission(
                doc,
                user="finance@example.com",
                ptype="read",
            )

        self.assertFalse(allowed)
