from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.accounting.account_holder_utils import get_school_organization
from ifitwala_ed.accounting.billing.rate_policies import (
    AMOUNT_BASIS_CUSTOM_PERCENTAGES,
    AMOUNT_BASIS_OPTIONS,
    AMOUNT_BASIS_PER_PERIOD,
    TERM_SPLIT_PERCENT_TOLERANCE,
)

MAX_LIST_TITLE_LOOKUP = 100


class ProgramBillingPlan(Document):
    def validate(self):
        self._validate_program_offering_scope()
        self._validate_academic_year_membership()
        self._validate_components()
        self._validate_term_splits()
        self._validate_active_uniqueness()

    def _validate_program_offering_scope(self):
        school = frappe.db.get_value("Program Offering", self.program_offering, "school")
        if not school:
            frappe.throw(
                _("Program Offering {program_offering} is missing School.").format(
                    program_offering=self.program_offering
                )
            )
        organization = get_school_organization(school)
        if organization != self.organization:
            frappe.throw(_("Program Offering must belong to the same Organization as the Billing Plan."))

    def _validate_academic_year_membership(self):
        academic_years = _get_program_offering_academic_year_names(self.program_offering)
        if not academic_years:
            frappe.throw(
                _("Program Offering must define at least one Academic Year before Billing Plans can be saved.")
            )

        if self.academic_year:
            if self.academic_year not in academic_years:
                frappe.throw(_("Academic Year must be part of the selected Program Offering."))
            return

        if len(academic_years) == 1:
            self.academic_year = academic_years[0]
            return

        frappe.throw(
            _("Please choose an Academic Year from this Program Offering: {academic_years}.").format(
                academic_years=", ".join(academic_years)
            )
        )

    def _validate_components(self):
        if not self.components:
            frappe.throw(_("At least one Program Billing Plan Component is required."))

        seen_billable_offerings: set[str] = set()
        offering_cache = {}
        for idx, row in enumerate(self.components, start=1):
            amount_basis = row.amount_basis or AMOUNT_BASIS_PER_PERIOD
            if amount_basis not in AMOUNT_BASIS_OPTIONS:
                frappe.throw(
                    _("Row {row_number}: Amount Basis {amount_basis} is not supported.").format(
                        row_number=idx,
                        amount_basis=amount_basis,
                    )
                )
            row.amount_basis = amount_basis
            if amount_basis != AMOUNT_BASIS_PER_PERIOD and self.billing_cadence != "Term":
                frappe.throw(
                    _("Row {row_number}: Annual amount splitting is only available for Term billing plans.").format(
                        row_number=idx
                    )
                )

            if not row.billable_offering:
                frappe.throw(_("Row {row_number}: Billable Offering is required.").format(row_number=idx))
            if row.billable_offering in seen_billable_offerings:
                frappe.throw(
                    _("Row {row_number}: Billable Offering {billable_offering} is duplicated.").format(
                        row_number=idx,
                        billable_offering=row.billable_offering,
                    )
                )
            seen_billable_offerings.add(row.billable_offering)

            if flt(row.qty) <= 0:
                frappe.throw(_("Row {row_number}: Qty must be greater than zero.").format(row_number=idx))
            if flt(row.default_rate) < 0:
                frappe.throw(_("Row {row_number}: Unit Billing Amount cannot be negative.").format(row_number=idx))
            if flt(row.default_rate) == 0 and not (row.description_override or "").strip():
                frappe.throw(
                    _("Row {row_number}: Description Override is required for zero-amount components.").format(
                        row_number=idx
                    )
                )

            offering = offering_cache.get(row.billable_offering)
            if not offering:
                offering = frappe.db.get_value(
                    "Billable Offering",
                    row.billable_offering,
                    ["organization", "offering_type", "disabled"],
                    as_dict=True,
                )
                if not offering:
                    frappe.throw(_("Row {row_number}: Billable Offering not found.").format(row_number=idx))
                offering_cache[row.billable_offering] = offering

            if offering.organization != self.organization:
                frappe.throw(
                    _("Row {row_number}: Billable Offering must belong to the same Organization.").format(
                        row_number=idx
                    )
                )
            if offering.disabled:
                frappe.throw(_("Row {row_number}: Billable Offering is disabled.").format(row_number=idx))
            if offering.offering_type == "Program" and not row.requires_student:
                frappe.throw(
                    _("Row {row_number}: Program Billable Offerings must require student attribution.").format(
                        row_number=idx
                    )
                )

    def _validate_term_splits(self):
        uses_custom_percentages = any(
            (row.amount_basis or AMOUNT_BASIS_PER_PERIOD) == AMOUNT_BASIS_CUSTOM_PERCENTAGES
            for row in (self.components or [])
        )
        if not uses_custom_percentages:
            return

        periods = _get_term_periods_for_plan(self)
        expected_terms = {period["period_key"]: period for period in periods}
        if not expected_terms:
            frappe.throw(_("Custom term split percentages require Academic Terms for this billing plan."))
        if not self.term_splits:
            frappe.throw(_("Set custom term split percentages before saving this billing plan."))

        seen_terms: set[str] = set()
        total_percentage = 0.0
        for idx, row in enumerate(self.term_splits, start=1):
            term = (row.term or "").strip()
            if not term:
                frappe.throw(_("Term Split row {row_number}: Term is required.").format(row_number=idx))
            if term in seen_terms:
                frappe.throw(
                    _("Term Split row {row_number}: Term {term} is duplicated.").format(
                        row_number=idx,
                        term=term,
                    )
                )
            if term not in expected_terms:
                frappe.throw(
                    _("Term Split row {row_number}: Term {term} is not part of this billing plan.").format(
                        row_number=idx,
                        term=term,
                    )
                )

            percentage = flt(row.percentage or 0)
            if percentage < 0:
                frappe.throw(_("Term Split row {row_number}: Percentage cannot be negative.").format(row_number=idx))

            row.term_label = expected_terms[term]["period_label"]
            seen_terms.add(term)
            total_percentage += percentage

        missing_terms = [period["period_label"] for period in periods if period["period_key"] not in seen_terms]
        if missing_terms:
            frappe.throw(
                _("Custom term split percentages are missing for: {terms}.").format(terms=", ".join(missing_terms))
            )

        if abs(total_percentage - 100.0) > TERM_SPLIT_PERCENT_TOLERANCE:
            frappe.throw(
                _("Custom term split percentages must total 100%. Current total is {total}.").format(
                    total=flt(total_percentage, 4)
                )
            )

    def _validate_active_uniqueness(self):
        if not self.is_active:
            return

        existing = frappe.get_all(
            "Program Billing Plan",
            filters={
                "organization": self.organization,
                "program_offering": self.program_offering,
                "academic_year": self.academic_year,
                "is_active": 1,
                "name": ["!=", self.name or ""],
            },
            pluck="name",
            limit=1,
        )
        if existing:
            frappe.throw(
                _("Only one active Program Billing Plan is allowed for this Program Offering and Academic Year.")
            )


def _get_program_offering_academic_year_names(program_offering: str | None) -> list[str]:
    return [
        row["academic_year"]
        for row in _get_program_offering_academic_year_rows(program_offering)
        if row.get("academic_year")
    ]


def _get_program_offering_academic_year_rows(program_offering: str | None) -> list[dict]:
    if not program_offering:
        return []

    rows = frappe.get_all(
        "Program Offering Academic Year",
        filters={"parent": program_offering, "parenttype": "Program Offering"},
        fields=["academic_year", "idx"],
        order_by="idx asc",
    )
    academic_year_names = [row.get("academic_year") for row in rows if row.get("academic_year")]
    if not academic_year_names:
        return []

    year_meta = {
        row.name: row
        for row in frappe.get_all(
            "Academic Year",
            filters={"name": ["in", academic_year_names]},
            fields=["name", "academic_year_name", "year_start_date", "year_end_date"],
        )
    }

    out = []
    for row in rows:
        academic_year = row.get("academic_year")
        if not academic_year:
            continue
        meta = year_meta.get(academic_year)
        out.append(
            {
                "academic_year": academic_year,
                "academic_year_name": meta.academic_year_name if meta else academic_year,
                "year_start_date": meta.year_start_date if meta else None,
                "year_end_date": meta.year_end_date if meta else None,
            }
        )
    return out


def _get_term_periods_for_plan(plan_doc) -> list[dict]:
    from ifitwala_ed.accounting.billing.schedule_generation import get_billing_periods

    return get_billing_periods(
        frappe._dict(
            {
                "academic_year": plan_doc.academic_year,
                "program_offering": plan_doc.program_offering,
                "billing_cadence": "Term",
            }
        )
    )


def _can_read_offering_academic_years_for_billing(program_offering: str, organization: str | None) -> bool:
    if frappe.has_permission("Program Offering", ptype="read", doc=program_offering):
        return True

    can_use_billing_plan = frappe.has_permission("Program Billing Plan", ptype="create") or frappe.has_permission(
        "Program Billing Plan", ptype="write"
    )
    if not can_use_billing_plan or not organization:
        return False

    school = frappe.db.get_value("Program Offering", program_offering, "school")
    return bool(school and get_school_organization(school) == organization)


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
def get_program_offering_title_map_for_billing_plans(program_billing_plans=None) -> dict:
    plan_names = _parse_name_list(program_billing_plans)
    if not plan_names:
        return {}

    plan_rows = frappe.get_list(
        "Program Billing Plan",
        filters={"name": ["in", plan_names]},
        fields=["name", "program_offering"],
        limit=len(plan_names),
    )
    offering_names = sorted(
        {_row_value(row, "program_offering") for row in plan_rows if _row_value(row, "program_offering")}
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
        for row in plan_rows
        if _row_value(row, "name") and _row_value(row, "program_offering")
    }


@frappe.whitelist()
def get_program_offering_academic_years(program_offering: str | None, organization: str | None = None) -> list[dict]:
    if not program_offering:
        return []

    if not _can_read_offering_academic_years_for_billing(program_offering, organization):
        frappe.throw(_("Not permitted to read Program Offering Academic Years."), frappe.PermissionError)

    return _get_program_offering_academic_year_rows(program_offering)


@frappe.whitelist()
def get_term_split_terms(
    program_offering: str | None,
    academic_year: str | None,
    organization: str | None = None,
) -> list[dict]:
    if not program_offering:
        frappe.throw(_("Select Program Offering before editing term split percentages."))
    if not academic_year:
        frappe.throw(_("Select Academic Year before editing term split percentages."))

    if not _can_read_offering_academic_years_for_billing(program_offering, organization):
        frappe.throw(_("Not permitted to read Program Offering Academic Years."), frappe.PermissionError)

    academic_years = _get_program_offering_academic_year_names(program_offering)
    if academic_year not in academic_years:
        frappe.throw(_("Academic Year must be part of the selected Program Offering."))

    periods = _get_term_periods_for_plan(
        frappe._dict(
            {
                "academic_year": academic_year,
                "program_offering": program_offering,
            }
        )
    )
    total_days = sum(_period_day_count(period) for period in periods)
    if total_days <= 0:
        frappe.throw(_("Academic Terms must have valid date ranges before term split percentages can be edited."))

    return [
        {
            "term": period["period_key"],
            "term_label": period["period_label"],
            "coverage_start": period["coverage_start"],
            "coverage_end": period["coverage_end"],
            "day_count": _period_day_count(period),
            "length_percentage": flt((_period_day_count(period) / total_days) * 100.0, 4),
        }
        for period in periods
    ]


def _period_day_count(period: dict) -> int:
    return (period["coverage_end"] - period["coverage_start"]).days + 1


@frappe.whitelist()
def generate_billing_schedules(program_billing_plan: str) -> dict:
    doc = frappe.get_doc("Program Billing Plan", program_billing_plan)
    doc.check_permission("read")

    from ifitwala_ed.accounting.billing.schedule_generation import (
        get_students_missing_account_holders_for_plan,
        sync_billing_schedules_for_plan,
    )

    missing_students = get_students_missing_account_holders_for_plan(program_billing_plan)
    if missing_students:
        return {
            "ok": False,
            "requires_account_holder_setup": True,
            "program_billing_plan": doc.name,
            "organization": doc.organization,
            "program_offering": doc.program_offering,
            "academic_year": doc.academic_year,
            "missing_students": missing_students,
            "missing_count": len(missing_students),
            "tool_doctype": "Student Account Holder Tool",
        }

    result = sync_billing_schedules_for_plan(program_billing_plan)
    result["ok"] = True
    return result


@frappe.whitelist()
def preview_billing_schedule_generation(program_billing_plan: str) -> dict:
    doc = frappe.get_doc("Program Billing Plan", program_billing_plan)
    doc.check_permission("read")

    from ifitwala_ed.accounting.billing.schedule_generation import get_billing_schedule_generation_preview

    return get_billing_schedule_generation_preview(program_billing_plan)
