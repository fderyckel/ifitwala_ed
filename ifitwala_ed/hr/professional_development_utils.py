# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, getdate, now_datetime

from ifitwala_ed.accounting.professional_development_ledger import (
    liquidate_professional_development_encumbrance,
    release_professional_development_encumbrance,
    reserve_professional_development_encumbrance,
)
from ifitwala_ed.utilities.employee_booking import (
    delete_employee_bookings_for_source,
    find_employee_conflicts,
    upsert_employee_booking,
)

PD_BUDGET_MODES = {
    "School Pool",
    "Employee Allowance",
    "Department Pool",
    "Program Pool",
    "Hybrid",
}
PD_REQUEST_STATUSES = {
    "Draft",
    "Submitted",
    "Under Review",
    "Approved",
    "Rejected",
    "Cancelled",
}
PD_REQUEST_GATE_STATUSES = {"Submitted", "Under Review", "Approved"}
PD_REQUEST_ACTIVE_STATUSES = {"Draft", "Submitted", "Under Review", "Approved"}
PD_REQUEST_LOCKED_STATUSES = {"Submitted", "Under Review", "Approved", "Rejected", "Cancelled"}
PD_RECORD_STATUSES = {"Planned", "Attended", "Completed", "Cancelled", "Liquidated"}
PD_RECORD_LOCKED_STATUSES = {"Cancelled", "Liquidated"}
PD_ENCUMBRANCE_STATUSES = {"Draft", "Reserved", "Released", "Liquidated"}
PD_APPROVAL_ROLES = {"HR Manager", "HR User", "Academic Admin", "System Manager"}
PD_FINANCE_ROLES = {"Accounts Manager", "Accounts User", "System Manager"}


def _get_single_settings() -> dict[str, Any]:
    return frappe.db.get_singles_dict("HR Settings") or {}


def get_current_employee(user: str | None = None) -> dict[str, Any]:
    user = user or frappe.session.user
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": ["in", ["Active", "Temporary Leave"]]},
        ["name", "user_id", "employee_full_name", "organization", "school", "department"],
        as_dict=True,
    )
    if not employee:
        frappe.throw(_("An active employee record is required for Professional Development."), frappe.PermissionError)
    return employee


def get_current_academic_year_for_school(school: str) -> str | None:
    today = getdate()
    rows = frappe.get_all(
        "Academic Year",
        filters={"school": school, "archived": 0},
        fields=["name", "year_start_date", "year_end_date"],
        order_by="year_start_date ASC",
        limit=200,
    )
    if not rows:
        return None

    for row in rows:
        start = row.get("year_start_date")
        end = row.get("year_end_date")
        if start and end and getdate(start) <= today <= getdate(end):
            return row.get("name")

    return rows[-1].get("name")


def _as_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, default=str)


def _append_request_audit(doc, action_label: str, notes: str | None = None, user: str | None = None) -> None:
    if not hasattr(doc, "audit_entries"):
        return

    doc.append(
        "audit_entries",
        {
            "action_label": action_label,
            "action_by": user or frappe.session.user,
            "action_on": now_datetime(),
            "notes": notes or "",
        },
    )


def _validate_school_organization(school: str | None, organization: str | None) -> None:
    if not school or not organization:
        return

    school_org = frappe.db.get_value("School", school, "organization")
    if school_org != organization:
        frappe.throw(_("School must belong to the selected Organization."), title=_("Invalid School Scope"))


def _validate_academic_year_scope(
    academic_year: str | None, school: str | None, *, allow_archived: bool = False
) -> None:
    if not academic_year or not school:
        return

    row = frappe.db.get_value("Academic Year", academic_year, ["school", "archived"], as_dict=True)
    if not row:
        frappe.throw(_("Academic Year is required."), title=_("Missing Academic Year"))
    if row.school != school:
        frappe.throw(_("Academic Year must belong to the selected School."), title=_("Invalid Academic Year"))
    if cint(row.archived or 0) == 1 and not allow_archived:
        frappe.throw(_("Archived Academic Years cannot accept Professional Development activity."))


def _validate_account_organization(account: str | None, organization: str | None, label: str) -> None:
    if not account or not organization:
        return

    account_org = frappe.db.get_value("Account", account, "organization")
    if account_org != organization:
        frappe.throw(_("{0} must belong to the selected Organization.").format(label))


def _compute_estimated_total(cost_rows) -> float:
    total = 0.0
    for row in cost_rows or []:
        amount = flt(getattr(row, "amount", 0))
        if amount < 0:
            frappe.throw(_("PD request costs cannot be negative."))
        total += amount
    return total


def _compute_absence_days(start_datetime, end_datetime) -> float:
    if not start_datetime or not end_datetime:
        return 0

    start_date = getdate(start_datetime)
    end_date = getdate(end_datetime)
    return float((end_date - start_date).days + 1)


def _validate_theme_scope(theme_name: str | None, organization: str | None, school: str | None) -> None:
    if not theme_name:
        return

    theme = frappe.db.get_value(
        "Professional Development Theme",
        theme_name,
        ["organization", "school", "is_active"],
        as_dict=True,
    )
    if not theme:
        frappe.throw(_("Professional Development Theme is invalid."))
    if cint(theme.is_active or 0) != 1:
        frappe.throw(_("Professional Development Theme must be active."))
    if organization and theme.organization != organization:
        frappe.throw(_("Professional Development Theme must belong to the selected Organization."))
    if school and theme.school and theme.school != school:
        frappe.throw(_("Professional Development Theme must belong to the selected School or Organization scope."))


def _validate_budget_mode_targeting(doc) -> None:
    mode = (doc.budget_mode or "").strip()
    if mode not in PD_BUDGET_MODES:
        frappe.throw(_("Invalid Professional Development budget mode."))

    if mode == "Employee Allowance" and not doc.employee:
        frappe.throw(_("Employee Allowance budgets require an Employee."))
    if mode == "Department Pool" and not doc.department:
        frappe.throw(_("Department Pool budgets require a Department."))
    if mode == "Program Pool" and not doc.program:
        frappe.throw(_("Program Pool budgets require a Program."))


def _validate_employee_scope(
    employee: str | None, organization: str | None, school: str | None
) -> dict[str, Any] | None:
    if not employee:
        return None

    row = frappe.db.get_value(
        "Employee",
        employee,
        ["organization", "school", "department", "user_id"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Employee is invalid."))
    if organization and row.organization != organization:
        frappe.throw(_("Employee must belong to the selected Organization."))
    if school and row.school and row.school != school:
        frappe.throw(_("Employee must belong to the selected School."))
    return row


def _validate_pgp_links(doc) -> None:
    if doc.pgp_plan:
        plan = frappe.db.get_value("PGP Plan", doc.pgp_plan, ["employee"], as_dict=True)
        if not plan:
            frappe.throw(_("PGP Plan is invalid."))

        employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
        if employee_user and plan.employee and plan.employee != employee_user:
            frappe.throw(_("PGP Plan must belong to the same employee user account."))

    if doc.pgp_goal:
        goal = frappe.db.get_value("PGP Goal", doc.pgp_goal, ["school", "academic_year"], as_dict=True)
        if not goal:
            frappe.throw(_("PGP Goal is invalid."))
        if goal.school and goal.school != doc.school:
            frappe.throw(_("PGP Goal must match the selected School."))
        if goal.academic_year and goal.academic_year != doc.academic_year:
            frappe.throw(_("PGP Goal must match the selected Academic Year."))


def _build_request_validation_snapshot(doc) -> dict[str, Any]:
    budget = None
    budget_available = None
    budget_matches_scope = True
    budget_active = True
    if doc.professional_development_budget:
        budget = frappe.db.get_value(
            "Professional Development Budget",
            doc.professional_development_budget,
            [
                "name",
                "organization",
                "school",
                "academic_year",
                "employee",
                "department",
                "budget_mode",
                "budget_amount",
                "reserved_amount",
                "liquidated_amount",
                "available_amount",
                "is_active",
            ],
            as_dict=True,
        )
        if budget:
            budget_available = flt(budget.available_amount)
            budget_active = cint(budget.is_active or 0) == 1
            budget_matches_scope = (
                budget.organization == doc.organization
                and budget.school == doc.school
                and budget.academic_year == doc.academic_year
            )

    conflicts = find_employee_conflicts(doc.employee, doc.start_datetime, doc.end_datetime) if doc.employee else []
    issues: list[str] = []

    if not budget:
        issues.append(_("A Professional Development Budget is required."))
    elif not budget_active:
        issues.append(_("Selected Professional Development Budget is inactive."))
    elif not budget_matches_scope:
        issues.append(_("Selected Professional Development Budget is outside the request scope."))
    elif flt(doc.estimated_total) > budget_available:
        issues.append(_("Selected Professional Development Budget does not have enough available funds."))

    if conflicts:
        issues.append(_("Employee already has a scheduling conflict for the requested time window."))

    if not doc.academic_year:
        issues.append(_("Academic Year is required."))

    return {
        "captured_on": now_datetime(),
        "valid": 0 if issues else 1,
        "requires_override": 1 if issues else 0,
        "issues": issues,
        "budget": {
            "name": budget.name if budget else None,
            "available_amount": budget_available,
            "budget_mode": budget.budget_mode if budget else None,
            "matches_scope": 1 if budget_matches_scope else 0,
            "is_active": 1 if budget_active else 0,
        },
        "conflicts": [
            {
                "source_doctype": conflict.source_doctype,
                "source_name": conflict.source_name,
                "booking_type": conflict.booking_type,
                "start": conflict.start,
                "end": conflict.end,
            }
            for conflict in conflicts
        ],
    }


def _build_budget_snapshot(doc) -> dict[str, Any]:
    budget = frappe.db.get_value(
        "Professional Development Budget",
        doc.professional_development_budget,
        [
            "name",
            "budget_mode",
            "pool_label",
            "professional_development_theme",
            "employee",
            "department",
            "program",
            "budget_amount",
            "reserved_amount",
            "liquidated_amount",
            "available_amount",
        ],
        as_dict=True,
    )
    if not budget:
        return {}

    return {
        "captured_on": now_datetime(),
        "budget": budget.name,
        "budget_mode": budget.budget_mode,
        "pool_label": budget.pool_label,
        "professional_development_theme": budget.professional_development_theme,
        "employee": budget.employee,
        "department": budget.department,
        "program": budget.program,
        "budget_amount": flt(budget.budget_amount),
        "reserved_amount": flt(budget.reserved_amount),
        "liquidated_amount": flt(budget.liquidated_amount),
        "available_amount": flt(budget.available_amount),
    }


def freeze_request_snapshots(doc) -> None:
    validation_snapshot = _build_request_validation_snapshot(doc)
    budget_snapshot = _build_budget_snapshot(doc)

    doc.validation_status = "Valid" if cint(validation_snapshot.get("valid") or 0) == 1 else "Invalid"
    doc.requires_override = cint(validation_snapshot.get("requires_override") or 0)
    doc.validation_snapshot_json = _as_json(validation_snapshot)
    doc.budget_snapshot_json = _as_json(budget_snapshot)


def validate_professional_development_theme(doc) -> None:
    doc.theme_name = (doc.theme_name or "").strip()
    if not doc.theme_name:
        frappe.throw(_("Theme Name is required."))
    _validate_school_organization(doc.school, doc.organization)


def validate_professional_development_budget(doc) -> None:
    _validate_school_organization(doc.school, doc.organization)
    _validate_academic_year_scope(doc.academic_year, doc.school)
    _validate_theme_scope(doc.professional_development_theme, doc.organization, doc.school)
    _validate_budget_mode_targeting(doc)
    _validate_employee_scope(doc.employee, doc.organization, doc.school)

    _validate_account_organization(doc.encumbrance_account, doc.organization, _("Encumbrance Account"))
    _validate_account_organization(doc.expense_account, doc.organization, _("Expense Account"))
    _validate_account_organization(doc.clearing_account, doc.organization, _("Clearing Account"))

    if flt(doc.budget_amount) < 0 or flt(doc.reserved_amount) < 0 or flt(doc.liquidated_amount) < 0:
        frappe.throw(_("Professional Development Budget amounts cannot be negative."))

    doc.available_amount = flt(doc.budget_amount) - flt(doc.reserved_amount) - flt(doc.liquidated_amount)

    if doc.available_amount < 0:
        frappe.throw(_("Professional Development Budget cannot have a negative available amount."))


def _enforce_request_edit_lock(doc) -> None:
    previous = doc.get_doc_before_save()
    if not previous or doc.flags.ignore_professional_development_lock:
        return

    if previous.status in PD_REQUEST_LOCKED_STATUSES:
        frappe.throw(_("Professional Development Request is locked after submission or decision."))


def validate_professional_development_request(doc) -> None:
    _enforce_request_edit_lock(doc)

    employee_row = _validate_employee_scope(doc.employee, doc.organization, doc.school)
    if employee_row:
        doc.organization = doc.organization or employee_row.organization
        doc.school = doc.school or employee_row.school

    _validate_school_organization(doc.school, doc.organization)
    _validate_academic_year_scope(doc.academic_year, doc.school)
    _validate_theme_scope(doc.professional_development_theme, doc.organization, doc.school)
    _validate_pgp_links(doc)

    status = (doc.status or "Draft").strip() or "Draft"
    if status not in PD_REQUEST_STATUSES:
        frappe.throw(_("Invalid Professional Development Request status."))
    doc.status = status

    if doc.professional_development_budget:
        budget = frappe.db.get_value(
            "Professional Development Budget",
            doc.professional_development_budget,
            ["organization", "school", "academic_year", "employee", "department", "is_active"],
            as_dict=True,
        )
        if not budget:
            frappe.throw(_("Professional Development Budget is invalid."))
        if cint(budget.is_active or 0) != 1:
            frappe.throw(_("Professional Development Budget must be active."))
        if (
            budget.organization != doc.organization
            or budget.school != doc.school
            or budget.academic_year != doc.academic_year
        ):
            frappe.throw(
                _("Professional Development Budget must match the request organization, school, and Academic Year.")
            )
        if budget.employee and budget.employee != doc.employee:
            frappe.throw(_("Selected Professional Development Budget is restricted to another employee."))
        if budget.department:
            employee_department = frappe.db.get_value("Employee", doc.employee, "department")
            if employee_department != budget.department:
                frappe.throw(_("Selected Professional Development Budget is restricted to another department."))

    start_dt = get_datetime(doc.start_datetime) if doc.start_datetime else None
    end_dt = get_datetime(doc.end_datetime) if doc.end_datetime else None
    if not start_dt or not end_dt or end_dt <= start_dt:
        frappe.throw(_("Professional Development start and end datetime are required and must be ordered."))

    doc.absence_days = flt(doc.absence_days) or _compute_absence_days(start_dt, end_dt)
    doc.estimated_total = _compute_estimated_total(getattr(doc, "costs", None))

    duplicate = frappe.get_all(
        "Professional Development Request",
        filters={
            "name": ["!=", doc.name or ""],
            "employee": doc.employee,
            "academic_year": doc.academic_year,
            "title": doc.title,
            "start_datetime": doc.start_datetime,
            "status": ["in", sorted(PD_REQUEST_ACTIVE_STATUSES)],
        },
        fields=["name"],
        limit=1,
    )
    if duplicate:
        frappe.throw(
            _("An active Professional Development Request already exists for this employee, title, and start time.")
        )

    if doc.status in PD_REQUEST_GATE_STATUSES:
        freeze_request_snapshots(doc)

    if doc.status == "Approved":
        if doc.validation_status != "Valid" and not (cint(doc.override_approved or 0) == 1 and doc.override_reason):
            frappe.throw(_("Override approval and reason are required before approving a blocked PD request."))
        if not doc.professional_development_record:
            frappe.throw(_("Approved Professional Development Request requires a committed record link."))


def _enforce_record_edit_lock(doc) -> None:
    previous = doc.get_doc_before_save()
    if not previous or doc.flags.ignore_professional_development_lock:
        return

    if previous.status in PD_RECORD_LOCKED_STATUSES:
        frappe.throw(_("Professional Development Record is locked in its terminal state."))


def validate_professional_development_record(doc) -> None:
    _enforce_record_edit_lock(doc)

    status = (doc.status or "Planned").strip() or "Planned"
    if status not in PD_RECORD_STATUSES:
        frappe.throw(_("Invalid Professional Development Record status."))
    doc.status = status

    _validate_employee_scope(doc.employee, doc.organization, doc.school)
    _validate_school_organization(doc.school, doc.organization)
    _validate_academic_year_scope(doc.academic_year, doc.school)
    _validate_theme_scope(doc.professional_development_theme, doc.organization, doc.school)

    if doc.professional_development_request:
        request_row = frappe.db.get_value(
            "Professional Development Request",
            doc.professional_development_request,
            ["employee", "organization", "school", "academic_year"],
            as_dict=True,
        )
        if not request_row:
            frappe.throw(_("Professional Development Request is invalid."))
        if (
            request_row.employee != doc.employee
            or request_row.organization != doc.organization
            or request_row.school != doc.school
            or request_row.academic_year != doc.academic_year
        ):
            frappe.throw(_("Professional Development Record must match its request scope."))


def validate_professional_development_outcome(doc) -> None:
    _validate_employee_scope(doc.employee, doc.organization, doc.school)
    _validate_school_organization(doc.school, doc.organization)
    _validate_academic_year_scope(doc.academic_year, doc.school)

    if flt(doc.actual_total) < 0:
        frappe.throw(_("Professional Development Outcome actual total cannot be negative."))

    if doc.professional_development_record:
        record_row = frappe.db.get_value(
            "Professional Development Record",
            doc.professional_development_record,
            ["employee", "organization", "school", "academic_year"],
            as_dict=True,
        )
        if not record_row:
            frappe.throw(_("Professional Development Record is invalid."))
        if (
            record_row.employee != doc.employee
            or record_row.organization != doc.organization
            or record_row.school != doc.school
            or record_row.academic_year != doc.academic_year
        ):
            frappe.throw(_("Professional Development Outcome must match its record scope."))

    if cint(doc.liquidation_ready or 0) == 1:
        settings = _get_single_settings()
        if cint(settings.get("pd_require_completion_evidence") or 0) == 1 and not (doc.evidence or []):
            frappe.throw(_("Completion evidence is required before liquidation."))
        if cint(settings.get("pd_require_liquidation_reflection") or 0) == 1 and not (doc.reflection or "").strip():
            frappe.throw(_("A reflection is required before liquidation."))


def validate_professional_development_encumbrance(doc) -> None:
    status = (doc.status or "Draft").strip() or "Draft"
    if status not in PD_ENCUMBRANCE_STATUSES:
        frappe.throw(_("Invalid Professional Development Encumbrance status."))
    doc.status = status

    _validate_school_organization(doc.school, doc.organization)
    _validate_academic_year_scope(doc.academic_year, doc.school, allow_archived=True)
    _validate_account_organization(doc.encumbrance_account, doc.organization, _("Encumbrance Account"))
    _validate_account_organization(doc.expense_account, doc.organization, _("Expense Account"))
    _validate_account_organization(doc.clearing_account, doc.organization, _("Clearing Account"))

    if flt(doc.encumbered_amount) < 0 or flt(doc.liquidated_amount) < 0 or flt(doc.released_amount) < 0:
        frappe.throw(_("Professional Development Encumbrance amounts cannot be negative."))

    if doc.professional_development_budget:
        budget = frappe.db.get_value(
            "Professional Development Budget",
            doc.professional_development_budget,
            ["organization", "school", "academic_year", "encumbrance_account", "expense_account", "clearing_account"],
            as_dict=True,
        )
        if not budget:
            frappe.throw(_("Professional Development Budget is invalid."))
        if (
            budget.organization != doc.organization
            or budget.school != doc.school
            or budget.academic_year != doc.academic_year
        ):
            frappe.throw(_("Professional Development Encumbrance must match its budget scope."))


def _lock_budget_row(budget_name: str) -> dict[str, Any]:
    rows = frappe.db.sql(
        """
        SELECT
            name,
            budget_amount,
            reserved_amount,
            liquidated_amount,
            available_amount,
            is_active
        FROM `tabProfessional Development Budget`
        WHERE name = %s
        FOR UPDATE
        """,
        (budget_name,),
        as_dict=True,
    )
    if not rows:
        frappe.throw(_("Professional Development Budget was not found."))
    return rows[0]


def reserve_budget_amount(budget_name: str, amount: float) -> None:
    amount = flt(amount)
    if amount <= 0:
        return

    row = _lock_budget_row(budget_name)
    if cint(row.is_active or 0) != 1:
        frappe.throw(_("Professional Development Budget is inactive."))

    available = flt(row.budget_amount) - flt(row.reserved_amount) - flt(row.liquidated_amount)
    if amount > available:
        frappe.throw(_("Professional Development Budget does not have enough available funds."))

    reserved_amount = flt(row.reserved_amount) + amount
    available_amount = flt(row.budget_amount) - reserved_amount - flt(row.liquidated_amount)
    frappe.db.set_value(
        "Professional Development Budget",
        budget_name,
        {
            "reserved_amount": reserved_amount,
            "available_amount": available_amount,
        },
        update_modified=False,
    )


def release_budget_amount(budget_name: str, amount: float) -> None:
    amount = flt(amount)
    if amount <= 0:
        return

    row = _lock_budget_row(budget_name)
    reserved_amount = max(flt(row.reserved_amount) - amount, 0)
    available_amount = flt(row.budget_amount) - reserved_amount - flt(row.liquidated_amount)
    frappe.db.set_value(
        "Professional Development Budget",
        budget_name,
        {
            "reserved_amount": reserved_amount,
            "available_amount": available_amount,
        },
        update_modified=False,
    )


def liquidate_budget_amount(
    budget_name: str,
    reserved_amount_to_release: float,
    actual_amount: float,
    *,
    allow_overrun: bool = False,
) -> None:
    reserved_amount_to_release = flt(reserved_amount_to_release)
    actual_amount = flt(actual_amount)

    row = _lock_budget_row(budget_name)
    current_reserved = flt(row.reserved_amount)
    current_liquidated = flt(row.liquidated_amount)
    budget_amount = flt(row.budget_amount)

    if reserved_amount_to_release > current_reserved:
        frappe.throw(_("Professional Development Budget does not have enough reserved balance to liquidate."))

    new_reserved = current_reserved - reserved_amount_to_release
    new_liquidated = current_liquidated + actual_amount
    new_available = budget_amount - new_reserved - new_liquidated

    if new_available < 0 and not allow_overrun:
        frappe.throw(_("Professional Development Budget liquidation would exceed the available budget."))

    frappe.db.set_value(
        "Professional Development Budget",
        budget_name,
        {
            "reserved_amount": new_reserved,
            "liquidated_amount": new_liquidated,
            "available_amount": new_available,
        },
        update_modified=False,
    )


def _create_or_update_record_from_request(request_doc):
    record_name = (request_doc.professional_development_record or "").strip()
    if record_name:
        record = frappe.get_doc("Professional Development Record", record_name)
    else:
        record = frappe.new_doc("Professional Development Record")

    record.flags.ignore_professional_development_lock = True
    record.professional_development_request = request_doc.name
    record.employee = request_doc.employee
    record.organization = request_doc.organization
    record.school = request_doc.school
    record.academic_year = request_doc.academic_year
    record.professional_development_budget = request_doc.professional_development_budget
    record.professional_development_theme = request_doc.professional_development_theme
    record.title = request_doc.title
    record.professional_development_type = request_doc.professional_development_type
    record.provider_name = request_doc.provider_name
    record.location = request_doc.location
    record.start_datetime = request_doc.start_datetime
    record.end_datetime = request_doc.end_datetime
    record.estimated_total = request_doc.estimated_total
    record.status = "Planned"
    record.actual_total = flt(record.actual_total or 0)

    if record.is_new():
        record.insert(ignore_permissions=True)
    else:
        record.save(ignore_permissions=True)

    return record


def _create_or_update_encumbrance_from_request(request_doc, record_doc):
    if flt(request_doc.estimated_total) <= 0:
        return None

    encumbrance_name = (request_doc.professional_development_encumbrance or "").strip()
    if encumbrance_name:
        encumbrance = frappe.get_doc("Professional Development Encumbrance", encumbrance_name)
    else:
        budget = frappe.get_doc("Professional Development Budget", request_doc.professional_development_budget)
        encumbrance = frappe.get_doc(
            {
                "doctype": "Professional Development Encumbrance",
                "organization": request_doc.organization,
                "school": request_doc.school,
                "academic_year": request_doc.academic_year,
                "professional_development_budget": request_doc.professional_development_budget,
                "professional_development_request": request_doc.name,
                "professional_development_record": record_doc.name,
                "posting_date": getdate(now_datetime()),
                "encumbrance_account": budget.encumbrance_account,
                "expense_account": budget.expense_account,
                "clearing_account": budget.clearing_account,
                "encumbered_amount": request_doc.estimated_total,
                "status": "Draft",
            }
        )

    encumbrance.professional_development_record = record_doc.name
    encumbrance.encumbered_amount = request_doc.estimated_total
    if encumbrance.is_new():
        encumbrance.insert(ignore_permissions=True)
    else:
        encumbrance.save(ignore_permissions=True)

    return encumbrance


def _materialize_record_booking(record_doc) -> str:
    return upsert_employee_booking(
        employee=record_doc.employee,
        start=record_doc.start_datetime,
        end=record_doc.end_datetime,
        source_doctype="Professional Development Record",
        source_name=record_doc.name,
        booking_type="Professional Development",
        blocks_availability=1,
        school=record_doc.school,
        academic_year=record_doc.academic_year,
    )


def _ensure_request_write_access(doc, user: str | None = None) -> None:
    user = user or frappe.session.user
    if not frappe.has_permission("Professional Development Request", doc=doc, ptype="write", user=user):
        frappe.throw(
            _("You do not have permission to modify this Professional Development Request."), frappe.PermissionError
        )


def _ensure_record_write_access(doc, user: str | None = None) -> None:
    user = user or frappe.session.user
    if not frappe.has_permission("Professional Development Record", doc=doc, ptype="write", user=user):
        frappe.throw(
            _("You do not have permission to modify this Professional Development Record."), frappe.PermissionError
        )


def _ensure_decision_access(user: str | None = None) -> None:
    user = user or frappe.session.user
    if not (set(frappe.get_roles(user)) & PD_APPROVAL_ROLES):
        frappe.throw(
            _("Only HR or Academic Admin roles can decide Professional Development Requests."), frappe.PermissionError
        )


def _ensure_liquidation_access(user: str | None = None) -> None:
    user = user or frappe.session.user
    if not (set(frappe.get_roles(user)) & PD_FINANCE_ROLES):
        frappe.throw(
            _("Only finance-authorized roles can liquidate Professional Development Records."), frappe.PermissionError
        )


def submit_request(request_doc, *, acting_user: str | None = None):
    acting_user = acting_user or frappe.session.user
    _ensure_request_write_access(request_doc, acting_user)

    if request_doc.status != "Draft":
        frappe.throw(_("Only draft Professional Development Requests can be submitted."))

    request_doc.flags.ignore_professional_development_lock = True
    request_doc.status = "Submitted"
    request_doc.submitted_by = acting_user
    request_doc.submitted_on = now_datetime()
    freeze_request_snapshots(request_doc)
    _append_request_audit(request_doc, "Submitted", user=acting_user)
    request_doc.save(ignore_permissions=True)

    settings = _get_single_settings()
    should_auto_approve = (
        settings.get("pd_approval_routing") == "Auto Approve Within Budget"
        and flt(request_doc.estimated_total) <= flt(settings.get("pd_auto_approve_threshold") or 0)
        and request_doc.validation_status == "Valid"
        and cint(request_doc.requires_override or 0) == 0
    )
    if should_auto_approve:
        decide_request(
            request_doc,
            decision="approve",
            acting_user=acting_user,
            notes=_("Auto-approved within threshold."),
            skip_permission=True,
        )

    return frappe.get_doc("Professional Development Request", request_doc.name)


def decide_request(
    request_doc,
    *,
    decision: str,
    acting_user: str | None = None,
    notes: str | None = None,
    skip_permission: bool = False,
):
    acting_user = acting_user or frappe.session.user
    if not skip_permission:
        _ensure_decision_access(acting_user)

    if request_doc.status == "Approved" and decision == "approve":
        return frappe.get_doc("Professional Development Request", request_doc.name)

    if request_doc.status not in {"Submitted", "Under Review"}:
        frappe.throw(_("Only submitted or under-review Professional Development Requests can be decided."))

    decision = (decision or "").strip().lower()
    if decision not in {"approve", "reject"}:
        frappe.throw(_("Decision must be approve or reject."))

    request_doc.flags.ignore_professional_development_lock = True

    if decision == "reject":
        request_doc.status = "Rejected"
        request_doc.decision_by = acting_user
        request_doc.decision_on = now_datetime()
        _append_request_audit(request_doc, "Rejected", notes=notes, user=acting_user)
        request_doc.save(ignore_permissions=True)
        return request_doc

    if request_doc.validation_status != "Valid" and not (
        cint(request_doc.override_approved or 0) == 1 and (request_doc.override_reason or "").strip()
    ):
        frappe.throw(
            _("Override approval and reason are required before approving this Professional Development Request.")
        )

    record = _create_or_update_record_from_request(request_doc)
    encumbrance = _create_or_update_encumbrance_from_request(request_doc, record)

    if encumbrance and encumbrance.status != "Reserved":
        reserve_budget_amount(request_doc.professional_development_budget, request_doc.estimated_total)
        reserve_professional_development_encumbrance(encumbrance)

    booking_name = _materialize_record_booking(record)
    record.flags.ignore_professional_development_lock = True
    record.employee_booking = booking_name
    record.professional_development_encumbrance = encumbrance.name if encumbrance else None
    record.status = "Planned"
    record.save(ignore_permissions=True)

    request_doc.status = "Approved"
    request_doc.decision_by = acting_user
    request_doc.decision_on = now_datetime()
    request_doc.professional_development_record = record.name
    request_doc.professional_development_encumbrance = encumbrance.name if encumbrance else None
    _append_request_audit(request_doc, "Approved", notes=notes, user=acting_user)
    request_doc.save(ignore_permissions=True)

    return frappe.get_doc("Professional Development Request", request_doc.name)


def cancel_request(request_doc, *, acting_user: str | None = None, notes: str | None = None):
    acting_user = acting_user or frappe.session.user
    _ensure_request_write_access(request_doc, acting_user)

    if request_doc.status == "Cancelled":
        return request_doc
    if request_doc.status == "Rejected":
        frappe.throw(_("Rejected Professional Development Requests cannot be cancelled again."))

    if request_doc.professional_development_record:
        record = frappe.get_doc("Professional Development Record", request_doc.professional_development_record)
        cancel_record(record, acting_user=acting_user, notes=notes)

    request_doc.flags.ignore_professional_development_lock = True
    request_doc.status = "Cancelled"
    request_doc.decision_by = acting_user
    request_doc.decision_on = now_datetime()
    _append_request_audit(request_doc, "Cancelled", notes=notes, user=acting_user)
    request_doc.save(ignore_permissions=True)
    return request_doc


def cancel_record(record_doc, *, acting_user: str | None = None, notes: str | None = None):
    acting_user = acting_user or frappe.session.user
    _ensure_record_write_access(record_doc, acting_user)

    if record_doc.status == "Cancelled":
        return record_doc
    if record_doc.status == "Liquidated":
        frappe.throw(_("Liquidated Professional Development Records cannot be cancelled."))

    delete_employee_bookings_for_source("Professional Development Record", record_doc.name)

    if record_doc.professional_development_encumbrance:
        encumbrance = frappe.get_doc(
            "Professional Development Encumbrance", record_doc.professional_development_encumbrance
        )
        if encumbrance.status == "Reserved":
            release_budget_amount(record_doc.professional_development_budget, encumbrance.encumbered_amount)
            release_professional_development_encumbrance(encumbrance)

    record_doc.flags.ignore_professional_development_lock = True
    record_doc.status = "Cancelled"
    record_doc.employee_booking = None
    record_doc.save(ignore_permissions=True)

    if record_doc.professional_development_request:
        request_doc = frappe.get_doc("Professional Development Request", record_doc.professional_development_request)
        request_doc.flags.ignore_professional_development_lock = True
        request_doc.status = "Cancelled"
        request_doc.decision_by = acting_user
        request_doc.decision_on = now_datetime()
        _append_request_audit(request_doc, "Record Cancelled", notes=notes, user=acting_user)
        request_doc.save(ignore_permissions=True)

    return record_doc


def complete_record(
    record_doc,
    *,
    actual_total: float,
    completion_date,
    reflection: str | None = None,
    evidence_rows: list[dict[str, Any]] | None = None,
    liquidation_ready: int = 1,
    acting_user: str | None = None,
):
    acting_user = acting_user or frappe.session.user
    _ensure_record_write_access(record_doc, acting_user)

    if record_doc.status in {"Cancelled", "Liquidated"}:
        frappe.throw(_("This Professional Development Record cannot be completed in its current state."))

    actual_total = flt(actual_total)
    evidence_rows = evidence_rows or []

    existing_name = frappe.db.get_value(
        "Professional Development Outcome",
        {"professional_development_record": record_doc.name},
        "name",
    )
    if existing_name:
        outcome = frappe.get_doc("Professional Development Outcome", existing_name)
        outcome.evidence = []
    else:
        outcome = frappe.new_doc("Professional Development Outcome")

    outcome.employee = record_doc.employee
    outcome.organization = record_doc.organization
    outcome.school = record_doc.school
    outcome.academic_year = record_doc.academic_year
    outcome.professional_development_record = record_doc.name
    outcome.completion_date = completion_date
    outcome.reflection = reflection or ""
    outcome.actual_total = actual_total
    outcome.liquidation_ready = cint(liquidation_ready or 0)

    for row in evidence_rows:
        outcome.append(
            "evidence",
            {
                "evidence_label": row.get("evidence_label") or "",
                "attachment": row.get("attachment") or "",
                "notes": row.get("notes") or "",
            },
        )

    if outcome.is_new():
        outcome.insert(ignore_permissions=True)
    else:
        outcome.save(ignore_permissions=True)

    record_doc.flags.ignore_professional_development_lock = True
    record_doc.professional_development_outcome = outcome.name
    record_doc.actual_total = actual_total
    record_doc.status = "Completed"
    record_doc.save(ignore_permissions=True)

    if record_doc.professional_development_request:
        request_doc = frappe.get_doc("Professional Development Request", record_doc.professional_development_request)
        request_doc.flags.ignore_professional_development_lock = True
        _append_request_audit(request_doc, "Completed", user=acting_user)
        request_doc.save(ignore_permissions=True)

    return outcome


def liquidate_record(
    record_doc,
    *,
    actual_total: float | None = None,
    liquidation_date=None,
    acting_user: str | None = None,
):
    acting_user = acting_user or frappe.session.user
    _ensure_liquidation_access(acting_user)
    _ensure_record_write_access(record_doc, acting_user)

    if record_doc.status == "Cancelled":
        frappe.throw(_("Cancelled Professional Development Records cannot be liquidated."))
    if record_doc.status == "Liquidated":
        return record_doc

    if record_doc.professional_development_outcome:
        outcome = frappe.get_doc("Professional Development Outcome", record_doc.professional_development_outcome)
        actual_amount = flt(actual_total if actual_total is not None else outcome.actual_total)
    else:
        actual_amount = flt(actual_total)

    liquidation_date = liquidation_date or getdate(now_datetime())

    if record_doc.professional_development_encumbrance:
        request_doc = (
            frappe.get_doc("Professional Development Request", record_doc.professional_development_request)
            if record_doc.professional_development_request
            else None
        )
        allow_overrun = bool(
            request_doc and cint(request_doc.override_approved or 0) == 1 and request_doc.override_reason
        )

        encumbrance = frappe.get_doc(
            "Professional Development Encumbrance", record_doc.professional_development_encumbrance
        )
        liquidate_budget_amount(
            record_doc.professional_development_budget,
            encumbrance.encumbered_amount,
            actual_amount,
            allow_overrun=allow_overrun,
        )
        liquidate_professional_development_encumbrance(encumbrance, actual_amount, liquidation_date)

    record_doc.flags.ignore_professional_development_lock = True
    record_doc.status = "Liquidated"
    record_doc.actual_total = actual_amount
    record_doc.save(ignore_permissions=True)

    if record_doc.professional_development_outcome:
        outcome = frappe.get_doc("Professional Development Outcome", record_doc.professional_development_outcome)
        outcome.liquidation_ready = 0
        outcome.save(ignore_permissions=True)

    if record_doc.professional_development_request:
        request_doc = frappe.get_doc("Professional Development Request", record_doc.professional_development_request)
        request_doc.flags.ignore_professional_development_lock = True
        _append_request_audit(request_doc, "Liquidated", user=acting_user)
        request_doc.save(ignore_permissions=True)

    return record_doc


def _matching_budget_for_employee(budget_row: dict[str, Any], employee_row: dict[str, Any]) -> bool:
    if budget_row.get("employee") and budget_row.get("employee") != employee_row.get("name"):
        return False
    if budget_row.get("department") and budget_row.get("department") != employee_row.get("department"):
        return False
    return True


def get_request_context_for_user(user: str | None = None, budget_name: str | None = None) -> dict[str, Any]:
    user = user or frappe.session.user
    employee = get_current_employee(user)
    academic_year = get_current_academic_year_for_school(employee.school)

    theme_rows = frappe.get_all(
        "Professional Development Theme",
        filters={
            "organization": employee.organization,
            "is_active": 1,
        },
        fields=["name", "theme_name", "school"],
        order_by="theme_name ASC",
    )
    theme_options = [
        {
            "value": row.name,
            "label": row.theme_name,
            "school": row.school,
        }
        for row in theme_rows
        if not row.school or row.school == employee.school
    ]

    budget_rows = frappe.get_all(
        "Professional Development Budget",
        filters={
            "organization": employee.organization,
            "school": employee.school,
            "academic_year": academic_year,
            "is_active": 1,
        },
        fields=[
            "name",
            "budget_mode",
            "pool_label",
            "professional_development_theme",
            "employee",
            "department",
            "program",
            "available_amount",
        ],
        order_by="pool_label ASC",
    )
    budget_options = [
        {
            "value": row.name,
            "label": f"{row.pool_label} ({row.budget_mode})",
            "budget_mode": row.budget_mode,
            "professional_development_theme": row.professional_development_theme,
            "available_amount": flt(row.available_amount),
        }
        for row in budget_rows
        if _matching_budget_for_employee(row, employee)
    ]

    selected_budget = next((row for row in budget_options if row["value"] == budget_name), None)

    plan_rows = frappe.get_all(
        "PGP Plan",
        filters={"employee": employee.user_id},
        fields=["name"],
        order_by="modified DESC",
    )
    plan_options = []
    for row in plan_rows:
        goal_rows = frappe.get_all(
            "PGP Plan Goal",
            filters={"parent": row.name, "parenttype": "PGP Plan"},
            fields=["goal"],
        )
        plan_options.append(
            {
                "value": row.name,
                "label": row.name,
                "goals": [
                    {
                        "value": goal_row.goal,
                        "label": goal_row.goal,
                    }
                    for goal_row in goal_rows
                    if goal_row.goal
                ],
            }
        )

    return {
        "viewer": {
            "user": user,
            "employee": employee.name,
            "employee_name": employee.employee_full_name,
            "organization": employee.organization,
            "school": employee.school,
            "academic_year": academic_year,
            "department": employee.department,
        },
        "defaults": {
            "professional_development_budget": selected_budget["value"] if selected_budget else None,
            "professional_development_theme": selected_budget["professional_development_theme"]
            if selected_budget
            else None,
        },
        "options": {
            "themes": theme_options,
            "budgets": budget_options,
            "pgp_plans": plan_options,
            "types": [
                "Conference",
                "Workshop",
                "Certification",
                "Online Course",
                "Coaching",
                "Internal Training",
                "Other",
            ],
        },
        "settings": {
            "budget_mode": _get_single_settings().get("pd_budget_mode"),
        },
    }


def build_my_growth_board(user: str | None = None) -> dict[str, Any]:
    user = user or frappe.session.user
    employee = get_current_employee(user)
    academic_year = get_current_academic_year_for_school(employee.school)
    context = get_request_context_for_user(user)
    now = now_datetime()

    request_rows = frappe.get_all(
        "Professional Development Request",
        filters={"employee": employee.name},
        fields=[
            "name",
            "title",
            "professional_development_type",
            "status",
            "professional_development_theme",
            "professional_development_budget",
            "start_datetime",
            "end_datetime",
            "estimated_total",
            "validation_status",
            "requires_override",
        ],
        order_by="start_datetime DESC",
        limit=50,
    )
    record_rows = frappe.get_all(
        "Professional Development Record",
        filters={"employee": employee.name},
        fields=[
            "name",
            "professional_development_request",
            "title",
            "professional_development_type",
            "status",
            "start_datetime",
            "end_datetime",
            "estimated_total",
            "actual_total",
            "professional_development_outcome",
        ],
        order_by="start_datetime DESC",
        limit=50,
    )
    budget_rows = context["options"]["budgets"]

    upcoming_records = [
        row
        for row in record_rows
        if row.get("status") in {"Planned", "Attended", "Completed"} and get_datetime(row.get("end_datetime")) >= now
    ]
    completion_backlog = [
        row
        for row in record_rows
        if row.get("status") in {"Planned", "Attended"} and get_datetime(row.get("end_datetime")) < now
    ]

    return {
        "generated_at": now,
        "viewer": {
            "user": user,
            "employee": employee.name,
            "employee_name": employee.employee_full_name,
            "organization": employee.organization,
            "school": employee.school,
            "academic_year": academic_year,
        },
        "settings": {
            "budget_mode": _get_single_settings().get("pd_budget_mode"),
            "require_completion_evidence": cint(_get_single_settings().get("pd_require_completion_evidence") or 0),
            "require_liquidation_reflection": cint(
                _get_single_settings().get("pd_require_liquidation_reflection") or 0
            ),
        },
        "summary": {
            "open_requests": len([row for row in request_rows if row.get("status") in {"Submitted", "Under Review"}]),
            "upcoming_records": len(upcoming_records),
            "completion_backlog": len(completion_backlog),
            "available_budget_total": sum(flt(row.get("available_amount") or 0) for row in budget_rows),
        },
        "request_options": context["options"],
        "requests": request_rows,
        "records": record_rows,
        "completion_backlog": completion_backlog,
        "budget_rows": budget_rows,
        "expiring_items": [],
    }


def handle_academic_year_close_for_professional_development(
    academic_year_names: list[str],
    school_scope: list[str],
) -> dict[str, int]:
    if not academic_year_names or not school_scope:
        return {"requests_cancelled": 0, "records_cancelled": 0}

    settings = _get_single_settings()
    open_requests = frappe.get_all(
        "Professional Development Request",
        filters={
            "academic_year": ["in", academic_year_names],
            "school": ["in", school_scope],
            "status": ["in", ["Draft", "Submitted", "Under Review", "Approved"]],
        },
        fields=["name", "status"],
        limit=500,
    )
    open_records = frappe.get_all(
        "Professional Development Record",
        filters={
            "academic_year": ["in", academic_year_names],
            "school": ["in", school_scope],
            "status": ["in", ["Planned", "Attended", "Completed"]],
        },
        fields=["name", "status"],
        limit=500,
    )

    if settings.get("pd_year_close_policy") == "Require Manual Carry Forward" and (open_requests or open_records):
        frappe.throw(
            _(
                "Professional Development still has open requests or records in this Academic Year scope. Resolve them before closure."
            ),
            title=_("PD Year Close Blocked"),
        )

    cancelled_requests = 0
    cancelled_records = 0
    for row in open_records:
        record = frappe.get_doc("Professional Development Record", row.name)
        cancel_record(record, acting_user=frappe.session.user, notes=_("Academic Year closure"))
        cancelled_records += 1

    for row in open_requests:
        request_doc = frappe.get_doc("Professional Development Request", row.name)
        if request_doc.status != "Cancelled":
            cancel_request(request_doc, acting_user=frappe.session.user, notes=_("Academic Year closure"))
            cancelled_requests += 1

    return {"requests_cancelled": cancelled_requests, "records_cancelled": cancelled_records}
