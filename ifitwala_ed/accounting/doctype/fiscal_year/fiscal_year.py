# ifitwala_ed/accounting/doctype/fiscal_year/fiscal_year.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_years, getdate

from ifitwala_ed.accounting.fiscal_year_utils import clear_fiscal_year_cache


class FiscalYear(Document):
    def validate(self):
        self.validate_organizations()
        self.validate_dates()
        self.validate_overlap()

    def on_update(self):
        clear_fiscal_year_cache()

    def on_trash(self):
        clear_fiscal_year_cache()

    def validate_organizations(self):
        organizations = []
        for row in self.organizations or []:
            if not row.organization:
                frappe.throw(_("Organization is required on each Fiscal Year row"))
            if row.organization in organizations:
                frappe.throw(
                    _("Organization {organization} is duplicated in this Fiscal Year").format(
                        organization=row.organization
                    )
                )
            organizations.append(row.organization)

        if not organizations:
            frappe.throw(_("At least one Organization is required"))

    def validate_dates(self):
        self.validate_from_to_dates("year_start_date", "year_end_date")
        if self.is_short_year:
            return

        expected_end_date = add_days(add_years(self.year_start_date, 1), -1)
        if getdate(self.year_end_date) != getdate(expected_end_date):
            frappe.throw(_("Fiscal Year End Date should be one year after Fiscal Year Start Date"))

    def validate_overlap(self):
        if not (self.year_start_date and self.year_end_date):
            return

        organizations = [row.organization for row in self.organizations or [] if row.organization]
        if not organizations:
            return

        fiscal_year = frappe.qb.DocType("Fiscal Year")
        fiscal_year_organization = frappe.qb.DocType("Fiscal Year Organization")
        name = self.name or self.year

        rows = (
            frappe.qb.from_(fiscal_year)
            .inner_join(fiscal_year_organization)
            .on(fiscal_year_organization.parent == fiscal_year.name)
            .select(fiscal_year.name, fiscal_year_organization.organization)
            .where(
                (fiscal_year.name != name)
                & (fiscal_year.disabled == 0)
                & (fiscal_year.year_start_date <= self.year_end_date)
                & (fiscal_year.year_end_date >= self.year_start_date)
                & (fiscal_year_organization.organization.isin(organizations))
            )
        ).run(as_dict=True)

        if rows:
            details = ", ".join(sorted({f"{row.name} ({row.organization})" for row in rows}))
            frappe.throw(_("Fiscal Year overlaps with existing active scope: {details}").format(details=details))
