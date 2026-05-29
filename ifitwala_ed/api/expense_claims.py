# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from ifitwala_ed.hr.expense_claims import (
    build_expense_claim_board,
    cancel_claim,
    create_claim_payment,
    decide_claim,
    post_claim_payable,
    save_draft_claim,
    serialize_claim,
    submit_claim,
)


def _ensure_logged_in():
    if not frappe.session.user or frappe.session.user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)


def _coerce_rows(value) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, str):
        parsed = frappe.parse_json(value) or []
        if isinstance(parsed, list):
            return parsed
    if isinstance(value, (list, tuple)):
        return list(value)
    frappe.throw(_("Rows payload must be a JSON array."))


def _claim_payload(
    *,
    expense_claim: str | None = None,
    claim_title: str | None = None,
    claim_date: str | None = None,
    purpose: str | None = None,
    items=None,
) -> dict[str, Any]:
    return {
        "expense_claim": expense_claim,
        "claim_title": claim_title,
        "claim_date": claim_date,
        "purpose": purpose,
        "items": _coerce_rows(items),
    }


@frappe.whitelist()
def get_expense_claim_board():
    _ensure_logged_in()
    return build_expense_claim_board(frappe.session.user)


@frappe.whitelist()
def save_expense_claim_draft(
    expense_claim: str | None = None,
    claim_title: str | None = None,
    claim_date: str | None = None,
    purpose: str | None = None,
    items=None,
):
    _ensure_logged_in()
    doc = save_draft_claim(
        _claim_payload(
            expense_claim=expense_claim,
            claim_title=claim_title,
            claim_date=claim_date,
            purpose=purpose,
            items=items,
        ),
        acting_user=frappe.session.user,
    )
    return {
        "expense_claim": serialize_claim(
            doc.as_dict(), items=[row.as_dict() for row in doc.items], receipts=[row.as_dict() for row in doc.receipts]
        ),
        "board": build_expense_claim_board(frappe.session.user),
    }


@frappe.whitelist()
def submit_expense_claim(
    expense_claim: str,
):
    _ensure_logged_in()
    doc = submit_claim(expense_claim, acting_user=frappe.session.user)
    return {
        "expense_claim": serialize_claim(
            doc.as_dict(), items=[row.as_dict() for row in doc.items], receipts=[row.as_dict() for row in doc.receipts]
        ),
        "board": build_expense_claim_board(frappe.session.user),
    }


@frappe.whitelist()
def decide_expense_claim(
    expense_claim: str,
    decision: str,
    notes: str | None = None,
    sanctioned_items=None,
):
    _ensure_logged_in()
    doc = decide_claim(
        expense_claim,
        decision=decision,
        notes=notes,
        sanctioned_items=_coerce_rows(sanctioned_items),
        acting_user=frappe.session.user,
    )
    return {
        "expense_claim": serialize_claim(
            doc.as_dict(), items=[row.as_dict() for row in doc.items], receipts=[row.as_dict() for row in doc.receipts]
        ),
        "board": build_expense_claim_board(frappe.session.user),
    }


@frappe.whitelist()
def post_expense_claim_payable(
    expense_claim: str,
    payable_account: str,
    expense_account: str | None = None,
    item_accounts=None,
    posting_date: str | None = None,
    remarks: str | None = None,
):
    _ensure_logged_in()
    doc = post_claim_payable(
        expense_claim,
        payable_account=payable_account,
        expense_account=expense_account,
        item_accounts=_coerce_rows(item_accounts),
        posting_date=posting_date,
        remarks=remarks,
        acting_user=frappe.session.user,
    )
    return {
        "expense_claim": serialize_claim(
            doc.as_dict(), items=[row.as_dict() for row in doc.items], receipts=[row.as_dict() for row in doc.receipts]
        ),
        "board": build_expense_claim_board(frappe.session.user),
    }


@frappe.whitelist()
def create_expense_claim_payment(
    expense_claim: str,
    paid_to: str,
    paid_amount: float | None = None,
    posting_date: str | None = None,
    remarks: str | None = None,
):
    _ensure_logged_in()
    payment = create_claim_payment(
        expense_claim,
        paid_to=paid_to,
        paid_amount=paid_amount,
        posting_date=posting_date,
        remarks=remarks,
        acting_user=frappe.session.user,
    )
    return {
        "payment_entry": payment.as_dict(),
        "board": build_expense_claim_board(frappe.session.user),
    }


@frappe.whitelist()
def cancel_expense_claim(expense_claim: str, notes: str | None = None):
    _ensure_logged_in()
    doc = cancel_claim(expense_claim, notes=notes, acting_user=frappe.session.user)
    return {
        "expense_claim": serialize_claim(
            doc.as_dict(), items=[row.as_dict() for row in doc.items], receipts=[row.as_dict() for row in doc.receipts]
        ),
        "board": build_expense_claim_board(frappe.session.user),
    }
