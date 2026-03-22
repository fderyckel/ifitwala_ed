# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, getdate

from ifitwala_ed.accounting.fiscal_year_utils import resolve_fiscal_year
from ifitwala_ed.accounting.ledger_utils import cancel_gl_entries, make_gl_entries, validate_posting_date

PD_ENCUMBRANCE_RESERVE_VOUCHER = "Professional Development Encumbrance Reserve"
PD_ENCUMBRANCE_LIQUIDATION_VOUCHER = "Professional Development Encumbrance Liquidation"


def _reserve_entries(doc) -> list[dict]:
    remarks = _("PD encumbrance reserve for {0}").format(doc.professional_development_request or doc.name)
    return [
        {
            "organization": doc.organization,
            "posting_date": doc.posting_date,
            "account": doc.encumbrance_account,
            "school": doc.school,
            "remarks": remarks,
            "debit": flt(doc.encumbered_amount),
            "credit": 0,
        },
        {
            "organization": doc.organization,
            "posting_date": doc.posting_date,
            "account": doc.clearing_account,
            "school": doc.school,
            "remarks": remarks,
            "debit": 0,
            "credit": flt(doc.encumbered_amount),
        },
    ]


def _liquidation_entries(doc, actual_amount: float, liquidation_date) -> list[dict]:
    remarks = _("PD encumbrance liquidation for {0}").format(doc.professional_development_record or doc.name)
    return [
        {
            "organization": doc.organization,
            "posting_date": liquidation_date,
            "account": doc.expense_account,
            "school": doc.school,
            "remarks": remarks,
            "debit": flt(actual_amount),
            "credit": 0,
        },
        {
            "organization": doc.organization,
            "posting_date": liquidation_date,
            "account": doc.clearing_account,
            "school": doc.school,
            "remarks": remarks,
            "debit": 0,
            "credit": flt(actual_amount),
        },
    ]


def reserve_professional_development_encumbrance(doc) -> str:
    if flt(doc.encumbered_amount) <= 0:
        frappe.db.set_value(
            "Professional Development Encumbrance",
            doc.name,
            {
                "status": "Reserved",
                "fiscal_year": None,
                "released_amount": 0,
                "liquidated_amount": 0,
                "variance_amount": 0,
            },
            update_modified=False,
        )
        return ""

    validate_posting_date(doc.organization, doc.posting_date)
    fiscal_year = resolve_fiscal_year(doc.organization, doc.posting_date)

    make_gl_entries(
        _reserve_entries(doc),
        voucher_type=PD_ENCUMBRANCE_RESERVE_VOUCHER,
        voucher_no=doc.name,
    )
    frappe.db.set_value(
        "Professional Development Encumbrance",
        doc.name,
        {
            "status": "Reserved",
            "fiscal_year": fiscal_year,
            "released_amount": 0,
            "liquidated_amount": 0,
            "variance_amount": 0,
        },
        update_modified=False,
    )
    return fiscal_year


def release_professional_development_encumbrance(doc) -> None:
    if (doc.status or "Draft") == "Released":
        return

    cancel_gl_entries(PD_ENCUMBRANCE_RESERVE_VOUCHER, doc.name)
    frappe.db.set_value(
        "Professional Development Encumbrance",
        doc.name,
        {
            "status": "Released",
            "released_amount": flt(doc.encumbered_amount),
            "liquidated_amount": 0,
            "variance_amount": 0,
        },
        update_modified=False,
    )


def liquidate_professional_development_encumbrance(doc, actual_amount: float, liquidation_date) -> str:
    actual_amount = flt(actual_amount)
    liquidation_date = getdate(liquidation_date)

    cancel_gl_entries(PD_ENCUMBRANCE_RESERVE_VOUCHER, doc.name)

    liquidation_fiscal_year = ""
    if actual_amount > 0:
        validate_posting_date(doc.organization, liquidation_date)
        liquidation_fiscal_year = resolve_fiscal_year(doc.organization, liquidation_date)
        make_gl_entries(
            _liquidation_entries(doc, actual_amount, liquidation_date),
            voucher_type=PD_ENCUMBRANCE_LIQUIDATION_VOUCHER,
            voucher_no=doc.name,
        )

    frappe.db.set_value(
        "Professional Development Encumbrance",
        doc.name,
        {
            "status": "Liquidated",
            "liquidation_date": liquidation_date,
            "liquidation_fiscal_year": liquidation_fiscal_year or None,
            "liquidated_amount": actual_amount,
            "released_amount": max(flt(doc.encumbered_amount) - actual_amount, 0),
            "variance_amount": actual_amount - flt(doc.encumbered_amount),
        },
        update_modified=False,
    )
    return liquidation_fiscal_year
