# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from ifitwala_ed.hr.doctype.expense_claim.receipts import (
    assert_expense_claim_receipt_upload_access,
    build_expense_claim_receipt_upload_contract,
    get_expense_claim_receipt_context_override,
    run_expense_claim_receipt_post_finalize,
    validate_expense_claim_receipt_finalize_context,
)


def assert_expense_claim_upload_access(expense_claim: str, *, permission_type: str = "write"):
    return assert_expense_claim_receipt_upload_access(expense_claim, permission_type=permission_type)


def build_expense_claim_receipt_contract(expense_claim_doc, *, row_name: str | None = None) -> dict:
    return build_expense_claim_receipt_upload_contract(expense_claim_doc, row_name=row_name)


def validate_expense_claim_finalize_context(upload_session_doc) -> dict | None:
    return validate_expense_claim_receipt_finalize_context(upload_session_doc)


def get_expense_claim_receipt_context_override_for_drive(owner_name: str | None, slot: str | None) -> dict | None:
    return get_expense_claim_receipt_context_override(owner_name, slot)


def run_expense_claim_receipt_post_finalize_for_drive(upload_session_doc, created_file) -> dict:
    return run_expense_claim_receipt_post_finalize(upload_session_doc, created_file)
