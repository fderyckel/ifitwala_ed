from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import flt, get_datetime, now_datetime

from ifitwala_ed.accounting.receivables import money

CHARGE_BATCH_INVOICE_QUEUE_THRESHOLD = 100
CHARGE_BATCH_PROGRESS_EVENT = "charge_batch_invoice_generation"
CHARGE_BATCH_DONE_EVENT = "charge_batch_invoice_generation_done"


def create_pending_charges_for_batch(charge_batch: str) -> dict:
    batch = frappe.get_doc("Charge Batch", charge_batch)
    if batch.status == "Cancelled":
        frappe.throw(_("Cancelled Charge Batches cannot create charges."))

    batch.save(ignore_permissions=True)

    created = []
    updated = []
    skipped = []

    for row in batch.students or []:
        if row.status == "Blocked":
            skipped.append({"student": row.student, "reason": row.issue})
            continue
        if row.status == "Invoiced":
            skipped.append({"student": row.student, "reason": _("Already invoiced.")})
            continue
        if row.status == "Cancelled":
            skipped.append({"student": row.student, "reason": _("Linked charge is cancelled.")})
            continue

        if row.billable_charge:
            charge = frappe.get_doc("Billable Charge", row.billable_charge)
            if charge.status == "Invoiced":
                skipped.append({"student": row.student, "reason": _("Already invoiced.")})
                continue
            if charge.status == "Cancelled":
                skipped.append({"student": row.student, "reason": _("Linked charge is cancelled.")})
                continue
            _apply_batch_values_to_charge(charge, batch, row)
            charge.save(ignore_permissions=True)
            updated.append(charge.name)
        else:
            existing = _get_existing_open_charge(batch.name, row.student)
            charge = frappe.get_doc("Billable Charge", existing) if existing else frappe.new_doc("Billable Charge")
            if existing and charge.status == "Invoiced":
                row.billable_charge = charge.name
                row.account_holder = charge.account_holder
                row.sales_invoice = charge.sales_invoice
                row.status = "Invoiced"
                skipped.append({"student": row.student, "reason": _("Already invoiced.")})
                continue
            _apply_batch_values_to_charge(charge, batch, row)
            charge.insert(ignore_permissions=True) if not existing else charge.save(ignore_permissions=True)
            row.billable_charge = charge.name
            updated.append(charge.name) if existing else created.append(charge.name)

        row.status = "Charge Created"
        row.account_holder = charge.account_holder
        row.sales_invoice = charge.sales_invoice

    batch.save(ignore_permissions=True)
    return {
        "charge_batch": batch.name,
        "created_count": len(created),
        "updated_count": len(updated),
        "skipped_count": len(skipped),
        "created_charge_names": created,
        "updated_charge_names": updated,
        "skipped": skipped,
    }


def generate_draft_invoices_for_charge_batch_or_enqueue(charge_batch: str, target_user: str | None = None) -> dict:
    _require_sales_invoice_create_permission()
    _lock_charge_batch(charge_batch)
    batch = frappe.get_doc("Charge Batch", charge_batch)
    if batch.status == "Cancelled":
        frappe.throw(_("Cancelled Charge Batches cannot generate invoices."))
    if batch.invoices:
        frappe.throw(_("Charge Batch {charge_batch} has already generated invoices.").format(charge_batch=batch.name))
    if batch.invoice_generation_status in {"Queued", "Processing"}:
        return {
            "charge_batch": batch.name,
            "queued": 1,
            "student_count": 0,
            "message": _("Draft invoice generation is already queued or processing."),
        }

    blocked_rows = [row for row in batch.students or [] if row.status == "Blocked"]
    if blocked_rows:
        frappe.throw(
            _("{count} student row(s) are blocked. Resolve them before generating draft invoices.").format(
                count=len(blocked_rows)
            )
        )

    candidate_count = len(
        [row for row in batch.students or [] if row.status not in {"Blocked", "Cancelled", "Invoiced"}]
    )
    if candidate_count > CHARGE_BATCH_INVOICE_QUEUE_THRESHOLD:
        target_user = target_user or frappe.session.user
        _set_generation_state(batch.name, "Queued", _("0 / {total}").format(total=candidate_count), "")
        frappe.enqueue(
            _run_charge_batch_invoice_generation_job,
            queue="long",
            job_name=f"Generate Charge Batch invoices {batch.name}",
            charge_batch=batch.name,
            target_user=target_user,
            enqueue_after_commit=True,
        )
        return {
            "charge_batch": batch.name,
            "queued": 1,
            "student_count": candidate_count,
            "message": _("{count} student charge(s) queued for draft invoice generation.").format(
                count=candidate_count
            ),
        }

    try:
        return generate_draft_invoices_for_charge_batch(charge_batch, target_user=target_user)
    except Exception as exc:
        _set_generation_state(charge_batch, "Failed", "", str(exc))
        raise


def generate_draft_invoices_for_charge_batch(charge_batch: str, target_user: str | None = None) -> dict:
    _require_sales_invoice_create_permission()
    _lock_charge_batch(charge_batch)
    _set_generation_state(charge_batch, "Processing", _("0 / 0"), "")
    prepare_result = create_pending_charges_for_batch(charge_batch)
    batch = frappe.get_doc("Charge Batch", charge_batch)
    if batch.status == "Cancelled":
        frappe.throw(_("Cancelled Charge Batches cannot generate invoices."))
    if batch.invoices:
        frappe.throw(_("Charge Batch {charge_batch} has already generated invoices.").format(charge_batch=batch.name))

    blocked_rows = [row for row in batch.students or [] if row.status == "Blocked"]
    if blocked_rows:
        frappe.throw(
            _("{count} student row(s) are blocked. Resolve them before generating draft invoices.").format(
                count=len(blocked_rows)
            )
        )

    charges = _get_pending_charges_for_batch(batch.name)
    if not charges:
        frappe.throw(_("No pending Billable Charges matched this Charge Batch."))

    groups: dict[str, list] = {}
    for charge in charges:
        groups.setdefault(charge.account_holder, []).append(charge)

    generated_items = []
    invoice_names = []
    total_amount = 0.0
    total_charges = 0
    total_groups = len(groups)
    _set_generation_state(batch.name, "Processing", _("0 / {total}").format(total=total_groups), "")

    for position, (account_holder, group_charges) in enumerate(sorted(groups.items()), start=1):
        invoice = _create_invoice_from_charges(batch=batch, account_holder=account_holder, charges=group_charges)
        invoice_names.append(invoice.name)
        total_charges += len(group_charges)
        total_amount = money(total_amount + money(invoice.grand_total or 0))

        for charge in group_charges:
            frappe.db.set_value(
                "Billable Charge",
                charge.name,
                {"status": "Invoiced", "sales_invoice": invoice.name},
                update_modified=False,
            )

        generated_items.append(
            {
                "account_holder": account_holder,
                "sales_invoice": invoice.name,
                "billable_charge_count": len(group_charges),
                "grand_total": money(invoice.grand_total or 0),
            }
        )
        _publish_generation_progress(batch.name, position, total_groups, target_user=target_user)

    batch.set("invoices", generated_items)
    batch.processed_on = get_datetime(now_datetime())
    batch.invoice_generation_status = "Completed"
    batch.invoice_generation_progress = _("{position} / {total}").format(position=total_groups, total=total_groups)
    batch.invoice_generation_error = ""
    _sync_batch_student_rows_from_charges(batch)
    batch.save(ignore_permissions=True)

    return {
        "charge_batch": batch.name,
        "invoice_names": invoice_names,
        "invoice_count": len(invoice_names),
        "billable_charge_count": total_charges,
        "grand_total": money(total_amount),
        "prepare_result": prepare_result,
    }


def _run_charge_batch_invoice_generation_job(charge_batch: str, target_user: str | None = None) -> None:
    try:
        result = generate_draft_invoices_for_charge_batch(charge_batch, target_user=target_user)
        if target_user:
            frappe.publish_realtime(
                CHARGE_BATCH_DONE_EVENT,
                {"ok": True, "charge_batch": charge_batch, "result": result},
                user=target_user,
            )
    except Exception as exc:
        _set_generation_state(charge_batch, "Failed", "", str(exc))
        if target_user:
            frappe.publish_realtime(
                CHARGE_BATCH_DONE_EVENT,
                {"ok": False, "charge_batch": charge_batch, "error": str(exc)},
                user=target_user,
            )
        raise


def reset_billable_charges_for_invoice(sales_invoice: str) -> None:
    rows = frappe.get_all(
        "Billable Charge",
        filters={"sales_invoice": sales_invoice, "status": "Invoiced"},
        fields=["name", "charge_batch"],
        limit=50000,
    )
    if not rows:
        return

    batch_names = set()
    for row in rows:
        frappe.db.set_value(
            "Billable Charge",
            row.get("name"),
            {"sales_invoice": None, "status": "Pending"},
            update_modified=False,
        )
        if row.get("charge_batch"):
            batch_names.add(row.get("charge_batch"))

    for batch_name in sorted(batch_names):
        refresh_charge_batch(batch_name)


def refresh_charge_batch(charge_batch: str) -> None:
    batch = frappe.get_doc("Charge Batch", charge_batch)
    _sync_batch_student_rows_from_charges(batch)
    batch.set("invoices", _build_invoice_rows_for_batch(batch.name))
    if not batch.invoices:
        batch.processed_on = None
        batch.invoice_generation_status = "Not Queued"
        batch.invoice_generation_progress = ""
        batch.invoice_generation_error = ""
    else:
        batch.invoice_generation_status = "Completed"
        batch.invoice_generation_progress = ""
        batch.invoice_generation_error = ""
    batch.save(ignore_permissions=True)


def _apply_batch_values_to_charge(charge, batch, row) -> None:
    charge.update(
        {
            "organization": batch.organization,
            "charge_batch": batch.name,
            "source_type": batch.source_type,
            "source_doctype": batch.source_doctype,
            "source_name": batch.source_name,
            "billable_offering": batch.billable_offering,
            "student": row.student,
            "account_holder": row.account_holder,
            "posting_date": batch.posting_date,
            "due_date": batch.due_date,
            "payment_terms_template": batch.payment_terms_template,
            "qty": flt(batch.default_qty or 0),
            "rate": money(batch.default_rate or 0),
            "coverage_start": batch.coverage_start,
            "coverage_end": batch.coverage_end,
            "description": batch.description,
            "status": "Pending",
            "sales_invoice": None,
        }
    )


def _get_existing_open_charge(charge_batch: str, student: str) -> str | None:
    rows = frappe.get_all(
        "Billable Charge",
        filters={
            "charge_batch": charge_batch,
            "student": student,
            "status": ["!=", "Cancelled"],
        },
        pluck="name",
        order_by="creation asc",
        limit=2,
    )
    if len(rows) > 1:
        frappe.throw(
            _("Student {student} already has multiple open Billable Charges in this Charge Batch.").format(
                student=student
            )
        )
    return rows[0] if rows else None


def _get_pending_charges_for_batch(charge_batch: str) -> list:
    rows = frappe.get_all(
        "Billable Charge",
        filters={"charge_batch": charge_batch, "status": "Pending", "sales_invoice": ["is", "not set"]},
        pluck="name",
        order_by="account_holder asc, student asc, name asc",
        limit=50000,
    )
    charges = []
    for name in rows:
        charge = frappe.get_doc("Billable Charge", name)
        charge.save(ignore_permissions=True)
        charges.append(charge)
    return charges


def _create_invoice_from_charges(*, batch, account_holder: str, charges: list):
    invoice = frappe.new_doc("Sales Invoice")
    invoice.update(
        {
            "account_holder": account_holder,
            "organization": batch.organization,
            "posting_date": batch.posting_date,
            "remarks": _("Generated from Charge Batch {charge_batch}.").format(charge_batch=batch.name),
        }
    )
    if batch.payment_terms_template:
        invoice.payment_terms_template = batch.payment_terms_template
    else:
        invoice.due_date = batch.due_date

    for charge in charges:
        invoice.append(
            "items",
            {
                "billable_charge": charge.name,
                "billable_offering": charge.billable_offering,
                "charge_source": "Extra",
                "description": charge.description,
                "student": charge.student,
                "qty": charge.qty,
                "rate": charge.rate,
            },
        )

    invoice.insert()
    return invoice


def _sync_batch_student_rows_from_charges(batch) -> None:
    charge_rows = frappe.get_all(
        "Billable Charge",
        filters={"charge_batch": batch.name},
        fields=["name", "student", "account_holder", "status", "sales_invoice"],
        order_by="creation asc",
        limit=50000,
    )
    charges_by_student = {row.get("student"): row for row in charge_rows if row.get("student")}
    for row in batch.students or []:
        charge = charges_by_student.get(row.student)
        if not charge:
            continue
        row.billable_charge = charge.get("name")
        row.account_holder = charge.get("account_holder")
        row.sales_invoice = charge.get("sales_invoice")
        if charge.get("status") == "Invoiced":
            row.status = "Invoiced"
        elif charge.get("status") == "Cancelled":
            row.status = "Cancelled"
        else:
            row.status = "Charge Created"


def _build_invoice_rows_for_batch(charge_batch: str) -> list[dict]:
    rows = frappe.get_all(
        "Billable Charge",
        filters={"charge_batch": charge_batch, "status": "Invoiced", "sales_invoice": ["is", "set"]},
        fields=["sales_invoice"],
        order_by="sales_invoice asc",
        limit=50000,
    )
    invoice_names = sorted({row.get("sales_invoice") for row in rows if row.get("sales_invoice")})
    if not invoice_names:
        return []

    invoices = {
        row.get("name"): row
        for row in frappe.get_all(
            "Sales Invoice",
            filters={"name": ["in", invoice_names], "docstatus": ["<", 2]},
            fields=["name", "account_holder", "grand_total"],
            limit=len(invoice_names),
        )
    }
    counts = {
        row.get("sales_invoice"): 0 for row in rows if row.get("sales_invoice") and row.get("sales_invoice") in invoices
    }
    for row in rows:
        invoice_name = row.get("sales_invoice")
        if invoice_name in counts:
            counts[invoice_name] += 1

    out = []
    for invoice_name in invoice_names:
        invoice = invoices.get(invoice_name)
        if not invoice:
            continue
        out.append(
            {
                "account_holder": invoice.get("account_holder"),
                "sales_invoice": invoice_name,
                "billable_charge_count": counts.get(invoice_name) or 0,
                "grand_total": money(invoice.get("grand_total") or 0),
            }
        )
    return out


def _require_sales_invoice_create_permission() -> None:
    if not frappe.has_permission("Sales Invoice", ptype="create"):
        frappe.throw(_("You do not have permission to create Sales Invoices."), frappe.PermissionError)


def _lock_charge_batch(charge_batch: str) -> None:
    frappe.db.sql("select name from `tabCharge Batch` where name = %s for update", (charge_batch,))


def _set_generation_state(charge_batch: str, status: str, progress: str = "", error: str = "") -> None:
    frappe.db.set_value(
        "Charge Batch",
        charge_batch,
        {
            "invoice_generation_status": status,
            "invoice_generation_progress": progress,
            "invoice_generation_error": error,
        },
        update_modified=False,
    )


def _publish_generation_progress(
    charge_batch: str,
    position: int,
    total: int,
    *,
    target_user: str | None = None,
) -> None:
    progress = _("{position} / {total}").format(position=position, total=total)
    _set_generation_state(charge_batch, "Processing", progress, "")
    if not target_user:
        return
    frappe.publish_realtime(
        CHARGE_BATCH_PROGRESS_EVENT,
        {
            "charge_batch": charge_batch,
            "progress": [position, total],
            "progress_label": _("Generating draft invoices"),
        },
        user=target_user,
    )
