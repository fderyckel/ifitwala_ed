# ifitwala_ed/admission/api/cockpit/enrollment_plan.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from ifitwala_ed.admission.api.cockpit.access import _to_text
from ifitwala_ed.admission.api.cockpit.urls import _doc_url


def _build_applicant_enrollment_plan_state(applicant_names: list[str]) -> dict[str, dict]:
    normalized_applicants = list(dict.fromkeys(name for name in applicant_names if _to_text(name)))
    state_by_applicant = {
        applicant_name: {
            "has_plan": False,
            "name": None,
            "status": None,
            "open_url": None,
            "offer_expires_on": None,
            "program_enrollment_request": None,
            "program_enrollment_request_url": None,
            "can_send_offer": False,
            "can_hydrate_request": False,
            "deposit": _empty_deposit_state(),
        }
        for applicant_name in normalized_applicants
    }

    if not normalized_applicants or not frappe.db.table_exists("Applicant Enrollment Plan"):
        return state_by_applicant

    plan_rows = frappe.get_all(
        "Applicant Enrollment Plan",
        filters={"student_applicant": ["in", normalized_applicants]},
        fields=[
            "name",
            "student_applicant",
            "status",
            "offer_expires_on",
            "program_enrollment_request",
            "deposit_required",
            "deposit_amount",
            "deposit_due_date",
            "deposit_billable_offering",
            "deposit_terms_source",
            "deposit_override_status",
            "deposit_academic_approved_by",
            "deposit_finance_approved_by",
            "deposit_invoice",
            "creation",
            "modified",
        ],
        order_by="creation desc, modified desc",
        limit=10000,
    )

    latest_by_applicant: dict[str, dict] = {}
    request_names: set[str] = set()
    invoice_names: set[str] = set()
    for row in plan_rows:
        applicant_name = _to_text(row.get("student_applicant"))
        if not applicant_name or applicant_name in latest_by_applicant:
            continue

        latest_by_applicant[applicant_name] = row

        request_name = _to_text(row.get("program_enrollment_request"))
        if request_name:
            request_names.add(request_name)
        invoice_name = _to_text(row.get("deposit_invoice"))
        if invoice_name:
            invoice_names.add(invoice_name)

    existing_request_names: set[str] = set()
    if request_names and frappe.db.table_exists("Program Enrollment Request"):
        existing_request_names = set(
            frappe.get_all(
                "Program Enrollment Request",
                filters={"name": ["in", sorted(request_names)]},
                pluck="name",
            )
        )

    invoice_map: dict[str, dict] = {}
    if invoice_names and frappe.db.table_exists("Sales Invoice"):
        invoice_map = {
            _to_text(row.get("name")): row
            for row in frappe.get_all(
                "Sales Invoice",
                filters={"name": ["in", sorted(invoice_names)]},
                fields=[
                    "name",
                    "docstatus",
                    "status",
                    "grand_total",
                    "paid_amount",
                    "outstanding_amount",
                    "due_date",
                ],
                limit=max(len(invoice_names), 1),
            )
        }

    for applicant_name in normalized_applicants:
        row = latest_by_applicant.get(applicant_name)
        if not row:
            continue

        plan_name = _to_text(row.get("name"))
        status = _to_text(row.get("status")) or None
        request_name = _to_text(row.get("program_enrollment_request"))
        if request_name and existing_request_names and request_name not in existing_request_names:
            request_name = ""

        state_by_applicant[applicant_name] = {
            "has_plan": bool(plan_name),
            "name": plan_name or None,
            "status": status,
            "open_url": _doc_url("Applicant Enrollment Plan", plan_name) if plan_name else None,
            "offer_expires_on": row.get("offer_expires_on"),
            "program_enrollment_request": request_name or None,
            "program_enrollment_request_url": (
                _doc_url("Program Enrollment Request", request_name) if request_name else None
            ),
            "can_send_offer": status == "Committee Approved",
            "can_hydrate_request": status == "Offer Accepted" and not request_name,
            "deposit": _deposit_state_from_plan_row(row, invoice_map),
        }

    return state_by_applicant


def _empty_deposit_state() -> dict:
    return {
        "deposit_required": False,
        "deposit_amount": 0,
        "deposit_due_date": None,
        "deposit_billable_offering": None,
        "terms_source": "School Default",
        "override_status": "Not Required",
        "requires_override_approval": False,
        "academic_approved": False,
        "finance_approved": False,
        "invoice": None,
        "invoice_status": None,
        "docstatus": None,
        "amount": 0,
        "paid_amount": 0,
        "outstanding_amount": 0,
        "due_date": None,
        "is_overdue": False,
        "is_paid": False,
        "blocker_label": None,
        "can_generate_invoice": False,
    }


def _deposit_state_from_plan_row(row: dict, invoice_map: dict[str, dict]) -> dict:
    required = bool(cint(row.get("deposit_required") or 0))
    invoice_name = _to_text(row.get("deposit_invoice"))
    invoice = invoice_map.get(invoice_name) if invoice_name else None
    invoice_status = _to_text((invoice or {}).get("status")) or None
    docstatus = cint((invoice or {}).get("docstatus") or 0) if invoice else None
    outstanding = flt((invoice or {}).get("outstanding_amount") if invoice else row.get("deposit_amount") or 0)
    due_date = (invoice or {}).get("due_date") or row.get("deposit_due_date")
    due_date_text = str(due_date) if due_date else None
    is_paid = bool(docstatus == 1 and (invoice_status in {"Paid", "Credited"} or outstanding <= 0))
    is_overdue = bool(outstanding > 0 and due_date and getdate(due_date) < getdate(nowdate()))
    terms_source = _to_text(row.get("deposit_terms_source")) or "School Default"
    override_status = _to_text(row.get("deposit_override_status")) or "Not Required"
    requires_override = bool(required and terms_source == "Manual Override" and override_status != "Approved")

    blocker_label = None
    if required:
        if requires_override:
            blocker_label = _("Deposit terms need academic and finance approval")
        elif not invoice_name:
            blocker_label = _("Deposit not generated")
        elif invoice_status == "Draft":
            blocker_label = _("Deposit invoice pending finance review")
        elif is_paid:
            blocker_label = _("Deposit paid")
        elif is_overdue:
            blocker_label = _("Deposit overdue")
        elif outstanding > 0:
            blocker_label = _("Deposit unpaid")

    return {
        "deposit_required": required,
        "deposit_amount": flt(row.get("deposit_amount") or 0),
        "deposit_due_date": str(row.get("deposit_due_date")) if row.get("deposit_due_date") else None,
        "deposit_billable_offering": _to_text(row.get("deposit_billable_offering")) or None,
        "terms_source": terms_source,
        "override_status": override_status,
        "requires_override_approval": requires_override,
        "academic_approved": bool(_to_text(row.get("deposit_academic_approved_by"))),
        "finance_approved": bool(_to_text(row.get("deposit_finance_approved_by"))),
        "invoice": invoice_name or None,
        "invoice_status": invoice_status,
        "docstatus": docstatus,
        "amount": flt((invoice or {}).get("grand_total") if invoice else row.get("deposit_amount") or 0),
        "paid_amount": flt((invoice or {}).get("paid_amount") if invoice else 0),
        "outstanding_amount": outstanding,
        "due_date": due_date_text,
        "is_overdue": is_overdue,
        "is_paid": is_paid,
        "blocker_label": blocker_label,
        "can_generate_invoice": bool(required and not invoice_name and not requires_override),
    }
