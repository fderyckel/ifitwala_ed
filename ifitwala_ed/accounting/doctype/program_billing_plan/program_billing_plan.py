from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from ifitwala_ed.accounting.account_holder_utils import get_school_organization


class ProgramBillingPlan(Document):
    def validate(self):
        self._validate_program_offering_scope()
        self._validate_academic_year_membership()
        self._validate_components()
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
                frappe.throw(_("Row {row_number}: Default Rate cannot be negative.").format(row_number=idx))
            if flt(row.default_rate) == 0 and not (row.description_override or "").strip():
                frappe.throw(
                    _("Row {row_number}: Description Override is required for zero-rate components.").format(
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


@frappe.whitelist()
def get_program_offering_academic_years(program_offering: str | None, organization: str | None = None) -> list[dict]:
    if not program_offering:
        return []

    if not _can_read_offering_academic_years_for_billing(program_offering, organization):
        frappe.throw(_("Not permitted to read Program Offering Academic Years."), frappe.PermissionError)

    return _get_program_offering_academic_year_rows(program_offering)


@frappe.whitelist()
def generate_billing_schedules(program_billing_plan: str) -> dict:
    doc = frappe.get_doc("Program Billing Plan", program_billing_plan)
    doc.check_permission("read")

    from ifitwala_ed.accounting.billing.schedule_generation import sync_billing_schedules_for_plan

    return sync_billing_schedules_for_plan(program_billing_plan)
