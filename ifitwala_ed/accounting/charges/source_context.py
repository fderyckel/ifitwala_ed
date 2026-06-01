from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from ifitwala_ed.accounting.account_holder_utils import get_school_organization

MAX_CONTEXT_STUDENTS = 50000
SUPPORTED_SOURCE_DOCTYPES = {"Student Group", "Program Offering", "Activity Booking"}


@frappe.whitelist()
def create_charge_batch_from_context(
    source_doctype: str,
    source_name: str,
    billable_offering: str | None = None,
    posting_date: str | None = None,
    due_date: str | None = None,
    payment_terms_template: str | None = None,
    default_qty: float | None = None,
    default_rate: float | None = None,
    description: str | None = None,
) -> dict:
    """Create a Charge Batch from an operational context such as a Student Group or activity."""
    _require_charge_batch_create_permission()

    resolved_doctype = (source_doctype or "").strip()
    resolved_name = (source_name or "").strip()
    if resolved_doctype not in SUPPORTED_SOURCE_DOCTYPES:
        frappe.throw(_("Charge Batch source is not supported."))
    if not resolved_name:
        frappe.throw(_("Source Record is required."))

    context = _build_context(resolved_doctype, resolved_name)
    batch_billable_offering = (billable_offering or context.get("billable_offering") or "").strip()
    batch_payment_terms_template = (payment_terms_template or "").strip()
    batch_due_date = (due_date or "").strip()
    batch_description = (description or context.get("description") or "").strip()
    batch_default_rate = _resolve_default_rate(default_rate, context.get("default_rate"))
    batch_default_qty = flt(default_qty if default_qty not in (None, "") else 1)

    if not batch_billable_offering:
        frappe.throw(_("Billable Offering is required before creating a Charge Batch."))
    if batch_default_qty <= 0:
        frappe.throw(_("Default Qty must be greater than zero."))
    if batch_default_rate is None:
        frappe.throw(_("Default Rate is required before creating a Charge Batch."))
    if batch_default_rate < 0:
        frappe.throw(_("Default Rate cannot be negative."))
    if not batch_payment_terms_template and not batch_due_date:
        frappe.throw(_("Due Date is required when no Payment Terms Template is selected."))

    students = _unique_students(context.get("students") or [])
    if not students:
        frappe.throw(_("No students were found for this Charge Batch source."))

    batch = frappe.get_doc(
        {
            "doctype": "Charge Batch",
            "organization": context["organization"],
            "batch_title": context["batch_title"],
            "source_type": context["source_type"],
            "source_doctype": resolved_doctype,
            "source_name": resolved_name,
            "billable_offering": batch_billable_offering,
            "posting_date": posting_date or getdate(),
            "due_date": batch_due_date or None,
            "payment_terms_template": batch_payment_terms_template or None,
            "default_qty": batch_default_qty,
            "default_rate": batch_default_rate,
            "coverage_start": context.get("coverage_start"),
            "coverage_end": context.get("coverage_end"),
            "description": batch_description,
            "students": [{"student": student} for student in students],
        }
    )
    batch.insert()

    return {
        "charge_batch": batch.name,
        "student_count": len(batch.students or []),
        "ready_count": len([row for row in batch.students or [] if row.status == "Ready"]),
        "blocked_count": len([row for row in batch.students or [] if row.status == "Blocked"]),
    }


def _build_context(source_doctype: str, source_name: str) -> dict:
    if source_doctype == "Student Group":
        return _student_group_context(source_name)
    if source_doctype == "Program Offering":
        return _program_offering_activity_context(source_name)
    if source_doctype == "Activity Booking":
        return _activity_booking_context(source_name)
    frappe.throw(_("Charge Batch source is not supported."))


def _student_group_context(student_group: str) -> dict:
    group = frappe.get_doc("Student Group", student_group)
    group.check_permission("read")

    school = (group.school or "").strip()
    if not school and group.program_offering:
        school = frappe.db.get_value("Program Offering", group.program_offering, "school") or ""
    if not school:
        frappe.throw(_("Student Group is missing School context."))

    rows = frappe.get_all(
        "Student Group Student",
        filters={"parent": group.name, "parenttype": "Student Group"},
        fields=["student", "active"],
        order_by="idx asc",
        limit=MAX_CONTEXT_STUDENTS,
    )
    students = [
        row.get("student")
        for row in rows
        if row.get("student") and (row.get("active") in (None, "") or cint(row.get("active")) == 1)
    ]

    return {
        "organization": get_school_organization(school),
        "batch_title": _("Charge Batch for {source}").format(
            source=group.student_group_name or group.student_group_abbreviation or group.name
        ),
        "source_type": "Student Group",
        "students": students,
        "coverage_start": None,
        "coverage_end": None,
        "description": group.student_group_name or group.name,
    }


def _program_offering_activity_context(program_offering: str) -> dict:
    offering = frappe.get_doc("Program Offering", program_offering)
    offering.check_permission("read")
    if not offering.school:
        frappe.throw(_("Program Offering is missing School."))

    rows = frappe.get_all(
        "Activity Booking",
        filters={
            "program_offering": offering.name,
            "status": "Confirmed",
            "sales_invoice": ["is", "not set"],
        },
        fields=["student"],
        order_by="student asc",
        limit=MAX_CONTEXT_STUDENTS,
    )

    return {
        "organization": get_school_organization(offering.school),
        "batch_title": _("Activity Charge Batch for {source}").format(source=offering.offering_title or offering.name),
        "source_type": "Activity",
        "billable_offering": offering.activity_billable_offering,
        "default_rate": offering.activity_fee_amount,
        "students": [row.get("student") for row in rows if row.get("student")],
        "coverage_start": offering.start_date,
        "coverage_end": offering.end_date,
        "description": _("Activity fee for {source}").format(source=offering.offering_title or offering.name),
    }


def _activity_booking_context(activity_booking: str) -> dict:
    booking = frappe.get_doc("Activity Booking", activity_booking)
    booking.check_permission("read")
    if (booking.status or "").strip() != "Confirmed":
        frappe.throw(_("Only confirmed Activity Bookings can create Charge Batches."))
    if booking.sales_invoice:
        frappe.throw(_("Activity Booking already has a Sales Invoice."))

    offering = frappe.get_doc("Program Offering", booking.program_offering)
    offering.check_permission("read")
    if not offering.school:
        frappe.throw(_("Program Offering is missing School."))

    return {
        "organization": get_school_organization(offering.school),
        "batch_title": _("Activity Charge Batch for {source}").format(source=booking.name),
        "source_type": "Activity",
        "billable_offering": offering.activity_billable_offering,
        "default_rate": booking.amount or offering.activity_fee_amount,
        "students": [booking.student],
        "coverage_start": offering.start_date,
        "coverage_end": offering.end_date,
        "description": _("Activity booking fee for {source}").format(source=offering.offering_title or offering.name),
    }


def _unique_students(students: list[str]) -> list[str]:
    out = []
    seen = set()
    for student in students:
        student_name = (student or "").strip()
        if not student_name or student_name in seen:
            continue
        seen.add(student_name)
        out.append(student_name)
    return out


def _resolve_default_rate(default_rate, context_rate) -> float | None:
    if default_rate not in (None, ""):
        return flt(default_rate)
    if context_rate not in (None, ""):
        return flt(context_rate)
    return None


def _require_charge_batch_create_permission() -> None:
    if not frappe.has_permission("Charge Batch", ptype="create"):
        frappe.throw(_("You do not have permission to create Charge Batches."), frappe.PermissionError)
