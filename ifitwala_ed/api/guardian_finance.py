# ifitwala_ed/api/guardian_finance.py

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe.utils import cint, flt, now_datetime

from ifitwala_ed.api.guardian_home import _resolve_guardian_scope


@frappe.whitelist()
def get_guardian_finance_snapshot() -> dict[str, Any]:
    user = frappe.session.user
    guardian_name, children = _resolve_guardian_scope(user)
    scope = _resolve_finance_scope(user=user, guardian_name=guardian_name, children=children)
    invoices = _get_invoice_rows(scope)
    payments = _get_payment_rows(scope)

    total_outstanding = sum(flt(row.get("outstanding_amount") or 0) for row in invoices)
    payment_total = sum(flt(row.get("paid_amount") or 0) for row in payments)
    open_invoices = sum(1 for row in invoices if flt(row.get("outstanding_amount") or 0) > 0)
    overdue_invoices = sum(1 for row in invoices if (row.get("status") or "").strip() == "Overdue")

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "guardian": {"name": guardian_name},
            "finance_access": bool(scope["authorized_account_holders"]),
            "access_reason": scope["access_reason"],
        },
        "family": {"children": scope["children"]},
        "account_holders": scope["account_holders"],
        "invoices": invoices,
        "payments": payments,
        "counts": {
            "total_invoices": len(invoices),
            "open_invoices": open_invoices,
            "overdue_invoices": overdue_invoices,
            "payment_history_count": len(payments),
            "total_outstanding": total_outstanding,
            "total_paid": payment_total,
        },
    }


def _resolve_finance_scope(*, user: str, guardian_name: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    student_names = [child.get("student") for child in children if child.get("student")]
    guardian_row = (
        frappe.db.get_value(
            "Guardian",
            guardian_name,
            ["guardian_email", "is_financial_guardian"],
            as_dict=True,
        )
        or {}
    )
    guardian_email = str(guardian_row.get("guardian_email") or "").strip().lower()
    user_email = str(user or "").strip().lower()
    guardian_is_financial = cint(guardian_row.get("is_financial_guardian") or 0) == 1

    student_rows = frappe.get_all(
        "Student",
        filters={"name": ["in", student_names]} if student_names else {"name": ["in", [""]]},
        fields=["name", "student_full_name", "anchor_school", "account_holder"],
        order_by="student_full_name asc, name asc",
    )
    student_map = {row.get("name"): row for row in student_rows if row.get("name")}
    child_rows = []
    for child in children:
        student = child.get("student")
        student_row = student_map.get(student, {})
        child_rows.append(
            {
                "student": student,
                "full_name": child.get("full_name") or student_row.get("student_full_name") or student,
                "school": child.get("school") or student_row.get("anchor_school") or "",
                "account_holder": student_row.get("account_holder") or "",
            }
        )

    holder_names = sorted(
        {(row.get("account_holder") or "").strip() for row in child_rows if (row.get("account_holder") or "").strip()}
    )
    holder_rows = frappe.get_all(
        "Account Holder",
        filters={"name": ["in", holder_names]} if holder_names else {"name": ["in", [""]]},
        fields=[
            "name",
            "account_holder_name",
            "organization",
            "status",
            "primary_email",
            "primary_phone",
        ],
        order_by="account_holder_name asc, name asc",
    )
    holder_map = {row.get("name"): row for row in holder_rows if row.get("name")}
    children_by_holder: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in child_rows:
        holder = (row.get("account_holder") or "").strip()
        if not holder:
            continue
        children_by_holder[holder].append(
            {
                "student": row.get("student") or "",
                "full_name": row.get("full_name") or row.get("student") or "",
                "school": row.get("school") or "",
            }
        )

    authorized_holder_names: list[str] = []
    account_holder_payload: list[dict[str, Any]] = []
    for holder_name in holder_names:
        holder = holder_map.get(holder_name, {})
        primary_email = str(holder.get("primary_email") or "").strip().lower()
        has_email_match = bool(primary_email and primary_email in {guardian_email, user_email})
        if not (guardian_is_financial or has_email_match):
            continue

        authorized_holder_names.append(holder_name)
        account_holder_payload.append(
            {
                "account_holder": holder_name,
                "label": holder.get("account_holder_name") or holder_name,
                "organization": holder.get("organization") or "",
                "status": holder.get("status") or "",
                "primary_email": holder.get("primary_email") or "",
                "primary_phone": holder.get("primary_phone") or "",
                "students": children_by_holder.get(holder_name, []),
            }
        )

    account_holder_payload.sort(key=lambda row: (row.get("label") or "", row.get("account_holder") or ""))

    access_reason = ""
    if children and not authorized_holder_names:
        access_reason = "no_authorized_account_holders"

    return {
        "children": child_rows,
        "student_names": student_names,
        "authorized_account_holders": authorized_holder_names,
        "account_holders": account_holder_payload,
        "children_by_holder": children_by_holder,
        "access_reason": access_reason,
    }


def _get_invoice_rows(scope: dict[str, Any]) -> list[dict[str, Any]]:
    authorized_holder_names = scope["authorized_account_holders"]
    if not authorized_holder_names:
        return []

    invoice_rows = frappe.get_all(
        "Sales Invoice",
        filters={"account_holder": ["in", authorized_holder_names], "docstatus": 1},
        fields=[
            "name",
            "account_holder",
            "organization",
            "school",
            "program",
            "posting_date",
            "due_date",
            "grand_total",
            "paid_amount",
            "outstanding_amount",
            "status",
            "remarks",
        ],
        order_by="posting_date desc, due_date desc, modified desc",
        limit_page_length=200,
    )
    invoice_names = [row.get("name") for row in invoice_rows if row.get("name")]
    invoice_item_rows = frappe.get_all(
        "Sales Invoice Item",
        filters={
            "parent": ["in", invoice_names],
            "student": ["in", scope["student_names"]],
        }
        if invoice_names and scope["student_names"]
        else {"parent": ["in", [""]]},
        fields=["parent", "student", "description"],
        order_by="parent asc, idx asc",
        limit_page_length=1000,
    )
    student_name_map = {row.get("student"): row.get("full_name") for row in scope["children"] if row.get("student")}
    students_by_invoice: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen_pairs: set[tuple[str, str]] = set()
    for row in invoice_item_rows:
        parent = row.get("parent")
        student = row.get("student")
        if not parent or not student or (parent, student) in seen_pairs:
            continue
        seen_pairs.add((parent, student))
        students_by_invoice[parent].append(
            {
                "student": student,
                "full_name": student_name_map.get(student) or student,
            }
        )

    out: list[dict[str, Any]] = []
    for row in invoice_rows:
        out.append(
            {
                "sales_invoice": row.get("name"),
                "account_holder": row.get("account_holder") or "",
                "organization": row.get("organization") or "",
                "school": row.get("school") or "",
                "program": row.get("program") or "",
                "posting_date": str(row.get("posting_date") or ""),
                "due_date": str(row.get("due_date") or ""),
                "grand_total": flt(row.get("grand_total") or 0),
                "paid_amount": flt(row.get("paid_amount") or 0),
                "outstanding_amount": flt(row.get("outstanding_amount") or 0),
                "status": row.get("status") or "",
                "remarks": row.get("remarks") or "",
                "students": students_by_invoice.get(row.get("name"), []),
            }
        )
    return out


def _get_payment_rows(scope: dict[str, Any]) -> list[dict[str, Any]]:
    authorized_holder_names = scope["authorized_account_holders"]
    if not authorized_holder_names:
        return []

    payment_rows = frappe.get_all(
        "Payment Entry",
        filters={
            "party_type": "Account Holder",
            "party": ["in", authorized_holder_names],
            "docstatus": 1,
        },
        fields=[
            "name",
            "party",
            "organization",
            "school",
            "program",
            "posting_date",
            "paid_amount",
            "unallocated_amount",
            "remarks",
        ],
        order_by="posting_date desc, modified desc",
        limit_page_length=200,
    )
    payment_names = [row.get("name") for row in payment_rows if row.get("name")]
    ref_rows = frappe.get_all(
        "Payment Entry Reference",
        filters={
            "parent": ["in", payment_names],
            "reference_doctype": "Sales Invoice",
        }
        if payment_names
        else {"parent": ["in", [""]]},
        fields=["parent", "reference_name", "allocated_amount"],
        order_by="parent asc, idx asc",
        limit_page_length=1000,
    )
    refs_by_payment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in ref_rows:
        parent = row.get("parent")
        if not parent:
            continue
        refs_by_payment[parent].append(
            {
                "sales_invoice": row.get("reference_name") or "",
                "allocated_amount": flt(row.get("allocated_amount") or 0),
            }
        )

    out: list[dict[str, Any]] = []
    for row in payment_rows:
        out.append(
            {
                "payment_entry": row.get("name"),
                "account_holder": row.get("party") or "",
                "organization": row.get("organization") or "",
                "school": row.get("school") or "",
                "program": row.get("program") or "",
                "posting_date": str(row.get("posting_date") or ""),
                "paid_amount": flt(row.get("paid_amount") or 0),
                "unallocated_amount": flt(row.get("unallocated_amount") or 0),
                "remarks": row.get("remarks") or "",
                "references": refs_by_payment.get(row.get("name"), []),
            }
        )
    return out
