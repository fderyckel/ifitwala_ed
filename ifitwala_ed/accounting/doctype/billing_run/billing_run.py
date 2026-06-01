from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.receivables import money

MAX_LIST_TITLE_LOOKUP = 100


class BillingRun(Document):
    def before_validate(self):
        self._hydrate_scope_from_billing_plan()

    def validate(self):
        self._hydrate_scope_from_billing_plan()
        self._resolve_billing_plan()
        self._validate_scope()
        self._validate_payment_terms_template()
        self._set_runtime_fields()

    def _hydrate_scope_from_billing_plan(self):
        if not self.billing_plan:
            return

        billing_plan = _get_billing_plan_context(self.billing_plan)
        if not billing_plan:
            frappe.throw(_("Program Billing Plan {billing_plan} was not found.").format(billing_plan=self.billing_plan))
        if not billing_plan.is_active:
            frappe.throw(_("Billing Run must use an active Program Billing Plan."))

        if not self.organization:
            self.organization = billing_plan.organization
        if not self.program_offering:
            self.program_offering = billing_plan.program_offering
        if not self.academic_year:
            self.academic_year = billing_plan.academic_year

    def _resolve_billing_plan(self):
        filters = {
            "organization": self.organization,
            "program_offering": self.program_offering,
            "academic_year": self.academic_year,
            "is_active": 1,
        }
        if self.billing_plan:
            if not frappe.db.exists("Program Billing Plan", {"name": self.billing_plan, **filters}):
                frappe.throw(_("Billing Run must use the active Program Billing Plan for this scope."))
            return

        matches = frappe.get_all("Program Billing Plan", filters=filters, pluck="name", limit=2)
        if not matches:
            frappe.throw(_("Create an active Program Billing Plan before generating a Billing Run."))
        if len(matches) > 1:
            frappe.throw(_("Only one active Program Billing Plan can exist for this Billing Run scope."))
        self.billing_plan = matches[0]

    def _validate_scope(self):
        school = frappe.db.get_value("Program Offering", self.program_offering, "school")
        if not school:
            frappe.throw(_("Program Offering is required."))
        if get_school_organization(school) != self.organization:
            frappe.throw(_("Billing Run Program Offering must belong to the same Organization."))

        billing_plan = frappe.db.get_value(
            "Program Billing Plan",
            self.billing_plan,
            ["organization", "program_offering", "academic_year"],
            as_dict=True,
        )
        if not billing_plan:
            frappe.throw(_("Billing Run requires a valid Program Billing Plan."))
        if billing_plan.organization != self.organization:
            frappe.throw(_("Billing Run Organization must match the Program Billing Plan Organization."))
        if billing_plan.program_offering != self.program_offering:
            frappe.throw(_("Billing Run Program Offering must match the Program Billing Plan Program Offering."))
        if billing_plan.academic_year != self.academic_year:
            frappe.throw(_("Billing Run Academic Year must match the Program Billing Plan Academic Year."))

        if self.due_date_from and self.due_date_to and self.due_date_from > self.due_date_to:
            frappe.throw(_("Due Date From cannot be later than Due Date To."))

    def _validate_payment_terms_template(self):
        if not self.payment_terms_template:
            return
        template = frappe.db.get_value(
            "Payment Terms Template",
            self.payment_terms_template,
            ["organization", "disabled"],
            as_dict=True,
        )
        if not template:
            frappe.throw(_("Payment Terms Template not found."))
        if template.organization != self.organization:
            frappe.throw(_("Payment Terms Template must belong to the same Organization."))
        if template.disabled:
            frappe.throw(_("Payment Terms Template is disabled."))

    def _set_runtime_fields(self):
        self.total_invoices = len(self.items or [])
        self.total_rows = sum(int(getattr(row, "billing_row_count", 0) or 0) for row in (self.items or []))
        self.total_amount = money(sum(money(getattr(row, "grand_total", 0) or 0) for row in (self.items or [])))
        if self.status == "Cancelled":
            return
        self.status = "Processed" if self.processed_on else "Draft"


def _get_billing_plan_context(billing_plan: str | None):
    if not billing_plan:
        return None

    return frappe.db.get_value(
        "Program Billing Plan",
        billing_plan,
        ["organization", "program_offering", "academic_year", "is_active"],
        as_dict=True,
    )


@frappe.whitelist()
def generate_draft_invoices(billing_run: str) -> dict:
    doc = frappe.get_doc("Billing Run", billing_run)
    doc.check_permission("write")
    doc.save()

    from ifitwala_ed.accounting.billing.invoice_generation import generate_draft_invoices_for_run

    return generate_draft_invoices_for_run(doc.name)


@frappe.whitelist()
def get_billing_plan_context(billing_plan: str) -> dict:
    doc = frappe.get_doc("Program Billing Plan", billing_plan)
    doc.check_permission("read")
    return {
        "organization": doc.organization,
        "program_offering": doc.program_offering,
        "academic_year": doc.academic_year,
        "is_active": doc.is_active,
    }


def _parse_name_list(value) -> list[str]:
    if not value:
        return []

    parsed = frappe.parse_json(value) if isinstance(value, str) else value
    if isinstance(parsed, str):
        parsed = [parsed]

    names = []
    seen = set()
    for raw_name in parsed or []:
        name = (raw_name or "").strip()
        if not name or name in seen:
            continue
        names.append(name)
        seen.add(name)
        if len(names) >= MAX_LIST_TITLE_LOOKUP:
            break
    return names


def _row_value(row, fieldname: str):
    if isinstance(row, dict):
        return row.get(fieldname)
    return getattr(row, fieldname, None)


@frappe.whitelist()
def get_program_offering_title_map_for_billing_runs(billing_runs=None) -> dict:
    run_names = _parse_name_list(billing_runs)
    if not run_names:
        return {}

    run_rows = frappe.get_list(
        "Billing Run",
        filters={"name": ["in", run_names]},
        fields=["name", "program_offering"],
        limit=len(run_names),
    )
    offering_names = sorted(
        {_row_value(row, "program_offering") for row in run_rows if _row_value(row, "program_offering")}
    )
    offering_titles = {}
    if offering_names:
        offering_titles = {
            _row_value(row, "name"): _row_value(row, "offering_title")
            for row in frappe.get_all(
                "Program Offering",
                filters={"name": ["in", offering_names]},
                fields=["name", "offering_title"],
                limit=len(offering_names),
            )
        }

    return {
        _row_value(row, "name"): {
            "program_offering": _row_value(row, "program_offering"),
            "offering_title": offering_titles.get(_row_value(row, "program_offering"))
            or _row_value(row, "program_offering"),
        }
        for row in run_rows
        if _row_value(row, "name") and _row_value(row, "program_offering")
    }
