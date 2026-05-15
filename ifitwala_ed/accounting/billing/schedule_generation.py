from __future__ import annotations

import calendar
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate

from ifitwala_ed.accounting.receivables import money
from ifitwala_ed.utilities.school_tree import get_school_lineage


def sync_billing_schedules_for_plan(program_billing_plan: str) -> dict:
    plan = frappe.get_doc("Program Billing Plan", program_billing_plan)
    periods = get_billing_periods(plan)
    enrollments = frappe.get_all(
        "Program Enrollment",
        filters={
            "program_offering": plan.program_offering,
            "academic_year": plan.academic_year,
            "archived": 0,
        },
        fields=["name", "student", "program_offering", "academic_year"],
        order_by="student asc, name asc",
        limit=5000,
    )
    if not enrollments:
        frappe.throw(
            _("No active Program Enrollments were found for Program Offering {program_offering}.").format(
                program_offering=plan.program_offering
            )
        )

    student_rows = frappe.get_all(
        "Student",
        filters={"name": ["in", [row.get("student") for row in enrollments]]},
        fields=["name", "account_holder"],
        limit=5000,
    )
    account_holders_by_student = {
        (row.get("name") or "").strip(): (row.get("account_holder") or "").strip() or None for row in student_rows
    }

    created_count = 0
    updated_count = 0
    schedule_names: list[str] = []

    for enrollment in enrollments:
        account_holder = account_holders_by_student.get((enrollment.get("student") or "").strip())
        if not account_holder:
            frappe.throw(
                _("Student {student} must have an Account Holder before billing schedules can be generated.").format(
                    student=enrollment.get("student")
                )
            )

        schedule_name, created = _upsert_schedule_for_enrollment(
            plan=plan,
            enrollment=enrollment,
            account_holder=account_holder,
            periods=periods,
        )
        schedule_names.append(schedule_name)
        if created:
            created_count += 1
        else:
            updated_count += 1

    return {
        "program_billing_plan": plan.name,
        "schedule_names": schedule_names,
        "created_count": created_count,
        "updated_count": updated_count,
        "period_count": len(periods),
    }


def get_billing_periods(plan_doc) -> list[dict]:
    academic_year = frappe.get_cached_doc("Academic Year", plan_doc.academic_year)
    year_start = getdate(academic_year.year_start_date)
    year_end = getdate(academic_year.year_end_date)
    if not year_start or not year_end:
        frappe.throw(
            _("Academic Year {academic_year} must have start and end dates.").format(
                academic_year=plan_doc.academic_year
            )
        )

    if plan_doc.billing_cadence == "Annual":
        return [
            {
                "period_key": plan_doc.academic_year,
                "period_label": academic_year.academic_year_name or plan_doc.academic_year,
                "due_date": year_start,
                "coverage_start": year_start,
                "coverage_end": year_end,
            }
        ]

    if plan_doc.billing_cadence == "Term":
        return _get_term_periods(plan_doc.academic_year, plan_doc.program_offering)

    if plan_doc.billing_cadence == "Monthly":
        return _get_monthly_periods(year_start, year_end)

    frappe.throw(_("Unsupported billing cadence {billing_cadence}.").format(billing_cadence=plan_doc.billing_cadence))


def _upsert_schedule_for_enrollment(
    *, plan, enrollment: dict, account_holder: str, periods: list[dict]
) -> tuple[str, bool]:
    existing_name = frappe.db.get_value(
        "Billing Schedule",
        {"program_enrollment": enrollment.get("name"), "billing_plan": plan.name},
        "name",
    )
    created = not bool(existing_name)
    doc = frappe.new_doc("Billing Schedule") if created else frappe.get_doc("Billing Schedule", existing_name)
    doc.organization = plan.organization
    doc.program_enrollment = enrollment.get("name")
    doc.program_offering = plan.program_offering
    doc.academic_year = plan.academic_year
    doc.billing_plan = plan.name
    doc.student = enrollment.get("student")
    doc.account_holder = account_holder

    existing_rows_by_key = {
        _compose_row_key(getattr(row, "plan_component_id", None), getattr(row, "period_key", None)): row
        for row in (doc.rows or [])
    }
    desired_row_keys: set[str] = set()

    for component in plan.components or []:
        for period in periods:
            row_key = _compose_row_key(component.name, period["period_key"])
            desired_row_keys.add(row_key)
            existing_row = existing_rows_by_key.get(row_key)
            if existing_row and existing_row.sales_invoice:
                continue

            values = {
                "plan_component_id": component.name,
                "period_key": period["period_key"],
                "period_label": period["period_label"],
                "billable_offering": component.billable_offering,
                "qty": flt(component.qty or 0),
                "rate": money(component.default_rate or 0),
                "requires_student": 1 if component.requires_student else 0,
                "description": component.description_override,
                "due_date": period["due_date"],
                "coverage_start": period["coverage_start"],
                "coverage_end": period["coverage_end"],
                "expected_amount": money(flt(component.qty or 0) * flt(component.default_rate or 0)),
                "status": "Pending",
            }
            if existing_row:
                for fieldname, value in values.items():
                    setattr(existing_row, fieldname, value)
                existing_row.sales_invoice = None
                existing_row.billing_run = None
            else:
                doc.append("rows", values)

    for row in doc.rows or []:
        row_key = _compose_row_key(getattr(row, "plan_component_id", None), getattr(row, "period_key", None))
        if row_key not in desired_row_keys and not row.sales_invoice:
            row.status = "Cancelled"
            row.billing_run = None

    doc.save(ignore_permissions=True)
    return doc.name, created


def _get_term_periods(academic_year: str, program_offering: str) -> list[dict]:
    offering_school = frappe.db.get_value("Program Offering", program_offering, "school")
    if not offering_school:
        frappe.throw(
            _("Program Offering {program_offering} is missing School.").format(program_offering=program_offering)
        )

    term_rows = frappe.get_all(
        "Term",
        filters={"academic_year": academic_year, "term_type": "Academic"},
        fields=["name", "school", "term_name", "term_start_date", "term_end_date"],
        order_by="term_start_date asc, name asc",
        limit=200,
    )
    school_scope = get_school_lineage(offering_school)
    scoped_rows = []
    for school_name in school_scope:
        scoped_rows = [row for row in term_rows if (row.get("school") or "").strip() == school_name]
        if scoped_rows:
            break
    if not scoped_rows:
        scoped_rows = [row for row in term_rows if not (row.get("school") or "").strip()]
    if not scoped_rows:
        frappe.throw(
            _(
                "Academic Terms must be configured for Academic Year {academic_year} before term billing schedules can be generated."
            ).format(academic_year=academic_year)
        )

    periods = []
    for row in scoped_rows:
        term_start = getdate(row.get("term_start_date"))
        term_end = getdate(row.get("term_end_date"))
        if not term_start or not term_end:
            frappe.throw(
                _("Term {term} must have start and end dates before term billing schedules can be generated.").format(
                    term=row.get("name")
                )
            )
        periods.append(
            {
                "period_key": row.get("name"),
                "period_label": row.get("term_name") or row.get("name"),
                "due_date": term_start,
                "coverage_start": term_start,
                "coverage_end": term_end,
            }
        )
    return periods


def _get_monthly_periods(start_date: date, end_date: date) -> list[dict]:
    periods = []
    cursor = start_date
    while cursor <= end_date:
        month_end_day = calendar.monthrange(cursor.year, cursor.month)[1]
        natural_month_end = date(cursor.year, cursor.month, month_end_day)
        coverage_start = cursor
        coverage_end = natural_month_end if natural_month_end <= end_date else end_date
        periods.append(
            {
                "period_key": f"{cursor.year:04d}-{cursor.month:02d}",
                "period_label": formatdate(coverage_start, "MMM yyyy"),
                "due_date": coverage_start,
                "coverage_start": coverage_start,
                "coverage_end": coverage_end,
            }
        )
        cursor = coverage_end + timedelta(days=1)
    return periods


def _compose_row_key(plan_component_id: str | None, period_key: str | None) -> str:
    return f"{(plan_component_id or '').strip()}::{(period_key or '').strip()}"
