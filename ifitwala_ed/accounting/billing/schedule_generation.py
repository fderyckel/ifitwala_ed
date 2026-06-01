from __future__ import annotations

import calendar
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate

from ifitwala_ed.accounting.billing.rate_policies import (
    AMOUNT_BASIS_CUSTOM_PERCENTAGES,
    AMOUNT_BASIS_PER_PERIOD,
    AMOUNT_BASIS_TERM_LENGTH,
)
from ifitwala_ed.accounting.receivables import money
from ifitwala_ed.utilities.school_tree import get_school_lineage


def sync_billing_schedules_for_plan(program_billing_plan: str) -> dict:
    plan = frappe.get_doc("Program Billing Plan", program_billing_plan)
    periods = get_billing_periods(plan)
    enrollments = _get_plan_enrollments(plan)
    if not enrollments:
        frappe.throw(
            _("No active Program Enrollments were found for Program Offering {program_offering}.").format(
                program_offering=plan.program_offering
            )
        )

    account_holders_by_student = _get_account_holders_by_student(enrollments)

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


def get_billing_schedule_generation_preview(program_billing_plan: str) -> dict:
    plan = frappe.get_doc("Program Billing Plan", program_billing_plan)
    periods = get_billing_periods(plan)
    enrollments = _get_plan_enrollments(plan)
    account_holders_by_student = _get_account_holders_by_student(enrollments)
    missing_account_holder_count = sum(
        1 for enrollment in enrollments if not account_holders_by_student.get((enrollment.get("student") or "").strip())
    )
    component_period_rows = _get_component_period_preview_rows(plan, periods)
    period_totals = []
    for period in periods:
        period_key = period["period_key"]
        per_student_total = money(
            sum(row["expected_amount"] for row in component_period_rows if row["period_key"] == period_key)
        )
        period_totals.append(
            {
                "period_key": period_key,
                "period_label": period["period_label"],
                "coverage_start": period["coverage_start"],
                "coverage_end": period["coverage_end"],
                "due_date": period["due_date"],
                "per_student_total": per_student_total,
                "estimated_total": money(per_student_total * len(enrollments)),
            }
        )

    return {
        "program_billing_plan": plan.name,
        "billing_cadence": plan.billing_cadence,
        "enrollment_count": len(enrollments),
        "missing_account_holder_count": missing_account_holder_count,
        "blocked": missing_account_holder_count > 0 or not enrollments,
        "component_rows": component_period_rows,
        "period_totals": period_totals,
        "per_student_total": money(sum(row["per_student_total"] for row in period_totals)),
        "estimated_total": money(sum(row["estimated_total"] for row in period_totals)),
    }


def get_students_missing_account_holders_for_plan(program_billing_plan: str) -> list[dict]:
    plan = frappe.get_doc("Program Billing Plan", program_billing_plan)
    enrollments = _get_plan_enrollments(plan)
    if not enrollments:
        return []

    student_names = sorted(
        {(row.get("student") or "").strip() for row in enrollments if (row.get("student") or "").strip()}
    )
    if not student_names:
        return []

    rows = frappe.get_all(
        "Student",
        filters={"name": ["in", student_names]},
        fields=["name", "student_full_name", "anchor_school", "cohort", "account_holder"],
        order_by="student_full_name asc, name asc",
        limit=len(student_names),
    )
    return [
        {
            "student": row.get("name"),
            "student_name": row.get("student_full_name") or row.get("name"),
            "anchor_school": row.get("anchor_school"),
            "student_cohort": row.get("cohort"),
        }
        for row in rows
        if not (row.get("account_holder") or "").strip()
    ]


def _get_component_period_preview_rows(plan, periods: list[dict]) -> list[dict]:
    components = list(plan.components or [])
    offering_names = sorted({row.billable_offering for row in components if row.billable_offering})
    offering_labels = {}
    if offering_names:
        offering_labels = {
            row.get("name"): row.get("offering_name") or row.get("name")
            for row in frappe.get_all(
                "Billable Offering",
                filters={"name": ["in", offering_names]},
                fields=["name", "offering_name"],
                limit=len(offering_names),
            )
        }

    rows = []
    custom_term_percentages = _get_custom_term_percentages(plan)
    for component in components:
        period_rates = _get_component_period_rates(
            component=component,
            periods=periods,
            custom_term_percentages=custom_term_percentages,
        )
        qty = flt(component.qty or 0)
        for period in periods:
            rate = period_rates[period["period_key"]]
            rows.append(
                {
                    "period_key": period["period_key"],
                    "period_label": period["period_label"],
                    "billable_offering": component.billable_offering,
                    "billable_offering_label": offering_labels.get(component.billable_offering)
                    or component.billable_offering,
                    "qty": qty,
                    "rate": rate,
                    "expected_amount": money(qty * rate),
                    "amount_basis": component.amount_basis or AMOUNT_BASIS_PER_PERIOD,
                }
            )
    return rows


def _get_plan_enrollments(plan) -> list[dict]:
    return frappe.get_all(
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


def _get_account_holders_by_student(enrollments: list[dict]) -> dict[str, str | None]:
    student_names = sorted(
        {(row.get("student") or "").strip() for row in enrollments if (row.get("student") or "").strip()}
    )
    if not student_names:
        return {}

    student_rows = frappe.get_all(
        "Student",
        filters={"name": ["in", student_names]},
        fields=["name", "account_holder"],
        limit=len(student_names),
    )
    return {(row.get("name") or "").strip(): (row.get("account_holder") or "").strip() or None for row in student_rows}


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
        return get_term_billing_periods(plan_doc.academic_year, plan_doc.program_offering)

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

    custom_term_percentages = _get_custom_term_percentages(plan)
    for component in plan.components or []:
        period_rates = _get_component_period_rates(
            component=component,
            periods=periods,
            custom_term_percentages=custom_term_percentages,
        )
        for period in periods:
            row_key = _compose_row_key(component.name, period["period_key"])
            desired_row_keys.add(row_key)
            existing_row = existing_rows_by_key.get(row_key)
            if existing_row and existing_row.sales_invoice:
                continue

            rate = period_rates[period["period_key"]]
            values = {
                "plan_component_id": component.name,
                "period_key": period["period_key"],
                "period_label": period["period_label"],
                "billable_offering": component.billable_offering,
                "qty": flt(component.qty or 0),
                "rate": rate,
                "requires_student": 1 if component.requires_student else 0,
                "description": component.description_override,
                "due_date": period["due_date"],
                "coverage_start": period["coverage_start"],
                "coverage_end": period["coverage_end"],
                "expected_amount": money(flt(component.qty or 0) * rate),
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


def get_term_billing_periods(academic_year: str, program_offering: str) -> list[dict]:
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
        if term_start > term_end:
            frappe.throw(
                _("Term {term} must not end before it starts before term billing schedules can be generated.").format(
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


def _get_component_period_rates(*, component, periods: list[dict], custom_term_percentages: dict[str, float]) -> dict:
    amount_basis = component.amount_basis or AMOUNT_BASIS_PER_PERIOD
    default_rate = money(component.default_rate or 0)
    if amount_basis == AMOUNT_BASIS_PER_PERIOD:
        return {period["period_key"]: default_rate for period in periods}

    if amount_basis == AMOUNT_BASIS_TERM_LENGTH:
        weights = _get_term_length_weights(periods)
        return _split_rate_by_weights(default_rate, periods, weights)

    if amount_basis == AMOUNT_BASIS_CUSTOM_PERCENTAGES:
        weights = {}
        for period in periods:
            period_key = period["period_key"]
            if period_key not in custom_term_percentages:
                frappe.throw(
                    _("Custom term split percentage is missing for {period}.").format(period=period["period_label"])
                )
            weights[period_key] = custom_term_percentages[period_key] / 100.0
        return _split_rate_by_weights(default_rate, periods, weights)

    frappe.throw(_("Unsupported amount basis {amount_basis}.").format(amount_basis=amount_basis))


def _get_term_length_weights(periods: list[dict]) -> dict[str, float]:
    day_counts = {period["period_key"]: _period_day_count(period) for period in periods}
    invalid_periods = [period["period_label"] for period in periods if day_counts.get(period["period_key"], 0) <= 0]
    if invalid_periods:
        frappe.throw(
            _("Academic Terms must have valid date ranges before annual amount splitting can be used: {terms}.").format(
                terms=", ".join(invalid_periods)
            )
        )
    total_days = sum(day_counts.values())
    if total_days <= 0:
        frappe.throw(_("Academic Terms must have valid date ranges before annual amount splitting can be used."))
    return {period_key: day_count / total_days for period_key, day_count in day_counts.items()}


def _split_rate_by_weights(default_rate: float, periods: list[dict], weights: dict[str, float]) -> dict[str, float]:
    rates = {}
    allocated = 0.0
    for idx, period in enumerate(periods, start=1):
        period_key = period["period_key"]
        if idx == len(periods):
            rate = money(default_rate - allocated)
        else:
            rate = money(default_rate * flt(weights.get(period_key) or 0))
            allocated = money(allocated + rate)
        rates[period_key] = rate
    return rates


def _get_custom_term_percentages(plan) -> dict[str, float]:
    return {
        (row.term or "").strip(): flt(row.percentage or 0)
        for row in (plan.term_splits or [])
        if (row.term or "").strip()
    }


def _period_day_count(period: dict) -> int:
    return (period["coverage_end"] - period["coverage_start"]).days + 1


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
