# ifitwala_ed/accounting/receivables.py

from __future__ import annotations

from dataclasses import dataclass

import frappe
from frappe.utils import add_days, cint, flt, getdate, today


@dataclass(frozen=True)
class InvoiceDimensions:
    school: str | None = None
    program: str | None = None


def get_money_precision() -> int:
    return cint(frappe.db.get_single_value("System Settings", "float_precision", cache=True)) or 2


def money(value) -> float:
    return flt(value, get_money_precision())


def is_zero(value) -> bool:
    precision = get_money_precision()
    tolerance = 1 / (10**precision)
    return abs(flt(value or 0)) < tolerance


def clamp_money(value) -> float:
    rounded = money(value)
    return 0 if is_zero(rounded) else rounded


def resolve_program_offering_dimensions(program_offering: str | None) -> InvoiceDimensions:
    if not program_offering:
        return InvoiceDimensions()

    row = frappe.db.get_value("Program Offering", program_offering, ["school", "program"], as_dict=True)
    if not row:
        return InvoiceDimensions()
    return InvoiceDimensions(
        school=(row.get("school") or "").strip() or None, program=(row.get("program") or "").strip() or None
    )


def resolve_student_school(student: str | None) -> str | None:
    if not student:
        return None
    school = frappe.db.get_value("Student", student, "anchor_school")
    return (school or "").strip() or None


def set_payment_schedule_from_template(doc) -> None:
    if not getattr(doc, "payment_terms_template", None):
        if not getattr(doc, "payment_schedule", None):
            return
        if getattr(doc, "adjustment_type", None) == "Credit Note":
            doc.set("payment_schedule", [])
        return

    if getattr(doc, "adjustment_type", None) == "Credit Note":
        doc.set("payment_schedule", [])
        return

    template = frappe.get_doc("Payment Terms Template", doc.payment_terms_template)
    total = money(abs(doc.grand_total or doc.total or 0))
    if is_zero(total):
        doc.set("payment_schedule", [])
        return

    schedule = []
    allocated = 0.0
    lines = list(template.terms or [])
    for idx, row in enumerate(lines, start=1):
        portion = money(row.invoice_portion or 0)
        if idx == len(lines):
            payment_amount = money(total - allocated)
        else:
            payment_amount = money(total * portion / 100.0)
            allocated = money(allocated + payment_amount)

        schedule.append(
            {
                "term_name": row.term_name,
                "invoice_portion": portion,
                "due_date": add_days(doc.posting_date, cint(row.due_days or 0)),
                "payment_amount": payment_amount,
                "paid_amount": 0,
                "outstanding_amount": payment_amount,
                "status": "Pending",
            }
        )

    doc.set("payment_schedule", schedule)
    if schedule:
        doc.due_date = schedule[0]["due_date"]


def refresh_payment_schedule_balances(doc) -> None:
    rows = list(getattr(doc, "payment_schedule", []) or [])
    if not rows:
        return

    total = money(abs(doc.grand_total or 0))
    outstanding = money(abs(doc.outstanding_amount or 0))
    paid_total = clamp_money(total - outstanding)
    remaining_paid = paid_total
    today_date = getdate(today())

    for row in rows:
        payment_amount = money(row.payment_amount or 0)
        paid_amount = min(payment_amount, remaining_paid)
        remaining_paid = clamp_money(remaining_paid - paid_amount)
        outstanding_amount = clamp_money(payment_amount - paid_amount)

        row.paid_amount = paid_amount
        row.outstanding_amount = outstanding_amount
        if is_zero(outstanding_amount):
            row.status = "Paid"
        elif is_zero(paid_amount):
            row.status = "Overdue" if row.due_date and getdate(row.due_date) < today_date else "Pending"
        else:
            row.status = "Overdue" if row.due_date and getdate(row.due_date) < today_date else "Partly Paid"


def earliest_open_due_date(doc):
    rows = list(getattr(doc, "payment_schedule", []) or [])
    open_due_dates = [
        getdate(row.due_date) for row in rows if not is_zero(row.outstanding_amount or 0) and row.due_date
    ]
    if open_due_dates:
        return min(open_due_dates)
    if getattr(doc, "due_date", None):
        return getdate(doc.due_date)
    if getattr(doc, "posting_date", None):
        return getdate(doc.posting_date)
    return None


def get_submitted_credit_note_total(invoice_name: str) -> float:
    rows = frappe.get_all(
        "Sales Invoice",
        filters={
            "against_sales_invoice": invoice_name,
            "adjustment_type": "Credit Note",
            "docstatus": 1,
        },
        fields=["grand_total"],
        limit_page_length=2000,
    )
    return money(sum(abs(flt(row.get("grand_total") or 0)) for row in rows))


def compute_cash_paid_amount(doc) -> float:
    credit_total = get_submitted_credit_note_total(doc.name) if getattr(doc, "name", None) else 0
    base_total = money(abs(doc.grand_total or 0))
    outstanding = money(abs(doc.outstanding_amount or 0))
    return clamp_money(base_total - outstanding - credit_total)


def compute_invoice_status(doc) -> str:
    if doc.docstatus == 2:
        return "Cancelled"
    if doc.docstatus == 0:
        return "Draft"
    if getattr(doc, "adjustment_type", None) == "Credit Note":
        return "Credit Note"

    outstanding = money(doc.outstanding_amount or 0)
    if is_zero(outstanding):
        credit_total = get_submitted_credit_note_total(doc.name) if getattr(doc, "name", None) else 0
        if credit_total and is_zero(compute_cash_paid_amount(doc)):
            return "Credited"
        return "Paid"

    credit_total = get_submitted_credit_note_total(doc.name) if getattr(doc, "name", None) else 0
    cash_paid = compute_cash_paid_amount(doc)
    due_date = earliest_open_due_date(doc)
    is_overdue = bool(due_date and due_date < getdate(today()))

    if credit_total and is_zero(cash_paid):
        return "Partly Credited"
    if is_overdue:
        return "Overdue"
    if cash_paid > 0:
        return "Partly Paid"
    return "Unpaid"


def sync_payment_requests_for_invoice(invoice_name: str) -> None:
    names = frappe.get_all(
        "Payment Request",
        filters={"sales_invoice": invoice_name},
        pluck="name",
    )
    for name in names:
        doc = frappe.get_doc("Payment Request", name)
        doc.flags.ignore_validate_update_after_submit = True
        doc.save(ignore_permissions=True)


def sync_dunning_notices_for_invoice(invoice_name: str) -> None:
    parents = frappe.get_all(
        "Dunning Notice Item",
        filters={"sales_invoice": invoice_name},
        fields=["parent"],
        limit_page_length=2000,
    )
    for row in parents:
        name = (row.get("parent") or "").strip()
        if not name:
            continue
        doc = frappe.get_doc("Dunning Notice", name)
        doc.flags.ignore_permissions = True
        doc.save(ignore_permissions=True)


def sync_invoice_runtime_state(doc) -> None:
    refresh_payment_schedule_balances(doc)
    doc.status = compute_invoice_status(doc)


def persist_submitted_invoice_runtime_state(invoice_name: str) -> None:
    doc = frappe.get_doc("Sales Invoice", invoice_name)
    refresh_payment_schedule_balances(doc)
    credit_note_total = get_submitted_credit_note_total(invoice_name)
    paid_amount = compute_cash_paid_amount(doc)
    status = compute_invoice_status(doc)

    frappe.db.set_value(
        "Sales Invoice",
        invoice_name,
        {
            "paid_amount": paid_amount,
            "credit_note_total": credit_note_total,
            "status": status,
        },
    )

    for row in doc.payment_schedule or []:
        frappe.db.set_value(
            "Sales Invoice Payment Schedule",
            row.name,
            {
                "paid_amount": money(row.paid_amount or 0),
                "outstanding_amount": money(row.outstanding_amount or 0),
                "status": row.status,
            },
        )

    sync_payment_requests_for_invoice(invoice_name)
    sync_dunning_notices_for_invoice(invoice_name)


def build_invoice_dimensions(doc) -> InvoiceDimensions:
    header_dimensions = resolve_program_offering_dimensions(getattr(doc, "program_offering", None))
    if header_dimensions.school or header_dimensions.program:
        return header_dimensions

    schools = set()
    programs = set()
    for row in getattr(doc, "items", []) or []:
        school = (getattr(row, "school", None) or "").strip() or None
        program = (getattr(row, "program", None) or "").strip() or None
        if school:
            schools.add(school)
        if program:
            programs.add(program)

    return InvoiceDimensions(
        school=next(iter(schools)) if len(schools) == 1 else None,
        program=next(iter(programs)) if len(programs) == 1 else None,
    )


def apply_invoice_dimensions(doc) -> None:
    dims = build_invoice_dimensions(doc)
    doc.school = dims.school
    doc.program = dims.program
