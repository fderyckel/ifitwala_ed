from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime, today

from ifitwala_ed.accounting.receivables import money


def generate_draft_invoice_for_schedule(billing_schedule: str, row_ids: list[str] | None = None) -> dict:
    schedule = frappe.get_doc("Billing Schedule", billing_schedule)
    target_rows = _get_schedule_target_rows(schedule, row_ids=row_ids)
    if not target_rows:
        frappe.throw(_("No pending Billing Schedule rows are available to invoice."))

    invoice = _create_invoice_from_row_refs(
        row_refs=[{"schedule": schedule, "row": row} for row in target_rows],
        organization=schedule.organization,
        account_holder=schedule.account_holder,
        program_offering=schedule.program_offering,
        posting_date=getdate(today()),
        due_date=getdate(target_rows[0].due_date),
        payment_terms_template=None,
        remarks=_("Generated from Billing Schedule {billing_schedule}").format(billing_schedule=schedule.name),
    )
    _link_rows_to_invoice(
        row_refs=[{"schedule_name": schedule.name, "row_name": row.name} for row in target_rows],
        sales_invoice=invoice.name,
        billing_run=None,
    )
    return {
        "sales_invoice": invoice.name,
        "billing_schedule": schedule.name,
        "row_ids": [row.name for row in target_rows],
    }


def generate_draft_invoices_for_run(billing_run: str) -> dict:
    run = frappe.get_doc("Billing Run", billing_run)
    if run.status == "Cancelled":
        frappe.throw(_("Cancelled Billing Runs cannot generate invoices."))
    if run.processed_on:
        frappe.throw(_("Billing Run {billing_run} has already been processed.").format(billing_run=run.name))

    row_groups = _get_run_target_groups(run)
    if not row_groups:
        frappe.throw(_("No pending Billing Schedule rows matched this Billing Run."))

    generated_items = []
    invoice_names = []
    total_rows = 0
    total_amount = 0.0

    for (_account_holder, period_key), row_refs in row_groups.items():
        invoice = _create_invoice_from_row_refs(
            row_refs=row_refs,
            organization=run.organization,
            account_holder=row_refs[0]["schedule"].account_holder,
            program_offering=run.program_offering,
            posting_date=getdate(run.posting_date),
            due_date=getdate(row_refs[0]["row"].due_date),
            payment_terms_template=run.payment_terms_template,
            remarks=_("Generated from Billing Run {billing_run}").format(billing_run=run.name),
        )
        invoice_names.append(invoice.name)
        total_rows += len(row_refs)
        total_amount = money(total_amount + money(invoice.grand_total or 0))

        _link_rows_to_invoice(
            row_refs=[
                {"schedule_name": row_ref["schedule"].name, "row_name": row_ref["row"].name} for row_ref in row_refs
            ],
            sales_invoice=invoice.name,
            billing_run=run.name,
        )
        generated_items.append(
            {
                "account_holder": row_refs[0]["schedule"].account_holder,
                "period_key": period_key,
                "sales_invoice": invoice.name,
                "billing_schedule_count": len({row_ref["schedule"].name for row_ref in row_refs}),
                "billing_row_count": len(row_refs),
                "grand_total": money(invoice.grand_total or 0),
            }
        )

    run.set("items", generated_items)
    run.processed_on = get_datetime(now_datetime())
    run.save(ignore_permissions=True)

    return {
        "billing_run": run.name,
        "invoice_names": invoice_names,
        "invoice_count": len(invoice_names),
        "billing_row_count": total_rows,
        "grand_total": money(total_amount),
    }


def reset_billing_rows_for_invoice(sales_invoice: str) -> None:
    rows = frappe.get_all(
        "Billing Schedule Row",
        filters={"sales_invoice": sales_invoice, "parenttype": "Billing Schedule"},
        fields=["name", "parent", "billing_run"],
        limit=50000,
    )
    if not rows:
        return

    parent_names = set()
    billing_run_names = set()
    for row in rows:
        frappe.db.set_value(
            "Billing Schedule Row",
            row.get("name"),
            {
                "sales_invoice": None,
                "billing_run": None,
                "status": "Pending",
            },
            update_modified=False,
        )
        parent_names.add(row.get("parent"))
        if row.get("billing_run"):
            billing_run_names.add(row.get("billing_run"))

    from ifitwala_ed.accounting.doctype.billing_schedule.billing_schedule import refresh_billing_schedule

    for parent_name in parent_names:
        refresh_billing_schedule(parent_name)

    for billing_run_name in billing_run_names:
        _refresh_billing_run_after_invoice_reset(billing_run_name)


def _get_schedule_target_rows(schedule_doc, row_ids: list[str] | None = None):
    rows = [
        row for row in (schedule_doc.rows or []) if row.status == "Pending" and not getattr(row, "sales_invoice", None)
    ]
    if row_ids:
        requested = set(row_ids)
        rows = [row for row in rows if row.name in requested]
    else:
        rows.sort(key=lambda row: (getdate(row.due_date), row.period_key or "", row.idx or 0))
        if rows:
            earliest_period_key = rows[0].period_key
            rows = [row for row in rows if row.period_key == earliest_period_key]
    return rows


def _get_run_target_groups(run_doc) -> dict[tuple[str, str], list[dict]]:
    schedule_headers = frappe.get_all(
        "Billing Schedule",
        filters={
            "organization": run_doc.organization,
            "program_offering": run_doc.program_offering,
            "academic_year": run_doc.academic_year,
            "billing_plan": run_doc.billing_plan,
        },
        fields=["name", "account_holder", "student", "program_offering"],
        order_by="account_holder asc, student asc, name asc",
        limit=5000,
    )
    if not schedule_headers:
        return {}

    schedule_names = [row.get("name") for row in schedule_headers]
    schedule_map = {row.get("name"): frappe.get_doc("Billing Schedule", row.get("name")) for row in schedule_headers}
    row_records = frappe.get_all(
        "Billing Schedule Row",
        filters={"parent": ["in", schedule_names], "parenttype": "Billing Schedule", "status": "Pending"},
        fields=[
            "name",
            "parent",
            "period_key",
            "period_label",
            "billable_offering",
            "qty",
            "rate",
            "requires_student",
            "description",
            "due_date",
            "coverage_start",
            "coverage_end",
            "sales_invoice",
        ],
        order_by="due_date asc, parent asc, idx asc",
        limit=50000,
    )

    groups: dict[tuple[str, str], list[dict]] = {}
    for record in row_records:
        if record.get("sales_invoice"):
            continue
        due_date = getdate(record.get("due_date")) if record.get("due_date") else None
        if run_doc.due_date_from and due_date and due_date < getdate(run_doc.due_date_from):
            continue
        if run_doc.due_date_to and due_date and due_date > getdate(run_doc.due_date_to):
            continue

        schedule = schedule_map.get(record.get("parent"))
        if not schedule:
            continue

        row_doc = next((row for row in (schedule.rows or []) if row.name == record.get("name")), None)
        if not row_doc:
            continue

        key = (schedule.account_holder, record.get("period_key") or "")
        groups.setdefault(key, []).append({"schedule": schedule, "row": row_doc})

    return groups


def _create_invoice_from_row_refs(
    *,
    row_refs: list[dict],
    organization: str,
    account_holder: str,
    program_offering: str,
    posting_date,
    due_date,
    payment_terms_template: str | None,
    remarks: str,
):
    invoice = frappe.new_doc("Sales Invoice")
    invoice.update(
        {
            "account_holder": account_holder,
            "organization": organization,
            "program_offering": program_offering,
            "posting_date": posting_date,
            "remarks": remarks,
        }
    )
    if payment_terms_template:
        invoice.payment_terms_template = payment_terms_template
    else:
        invoice.due_date = due_date

    for row_ref in row_refs:
        schedule = row_ref["schedule"]
        row = row_ref["row"]
        invoice.append(
            "items",
            {
                "billable_offering": row.billable_offering,
                "program_offering": schedule.program_offering,
                "charge_source": "Program Offering",
                "description": row.description,
                "student": schedule.student if row.requires_student else None,
                "qty": row.qty,
                "rate": row.rate,
            },
        )

    invoice.insert()
    return invoice


def _link_rows_to_invoice(*, row_refs: list[dict], sales_invoice: str, billing_run: str | None) -> None:
    parent_names = set()
    for row_ref in row_refs:
        frappe.db.set_value(
            "Billing Schedule Row",
            row_ref["row_name"],
            {
                "sales_invoice": sales_invoice,
                "billing_run": billing_run or "",
                "status": "Invoiced",
            },
            update_modified=False,
        )
        parent_names.add(row_ref["schedule_name"])

    from ifitwala_ed.accounting.doctype.billing_schedule.billing_schedule import refresh_billing_schedule

    for parent_name in parent_names:
        refresh_billing_schedule(parent_name)


def _refresh_billing_run_after_invoice_reset(billing_run: str) -> None:
    if not billing_run:
        return

    run = frappe.get_doc("Billing Run", billing_run)
    retained_items = []
    for item in run.items or []:
        sales_invoice = (getattr(item, "sales_invoice", None) or "").strip()
        if not sales_invoice:
            continue
        invoice_state = frappe.db.get_value(
            "Sales Invoice",
            sales_invoice,
            ["name", "docstatus", "status"],
            as_dict=True,
        )
        if not invoice_state:
            continue
        if int(invoice_state.get("docstatus") or 0) == 2 or (invoice_state.get("status") or "").strip() == "Cancelled":
            continue
        retained_items.append(
            {
                "account_holder": item.account_holder,
                "period_key": item.period_key,
                "sales_invoice": sales_invoice,
                "billing_schedule_count": item.billing_schedule_count,
                "billing_row_count": item.billing_row_count,
                "grand_total": item.grand_total,
            }
        )

    run.set("items", retained_items)
    if not retained_items:
        run.processed_on = None
    run.save(ignore_permissions=True)
