# ifitwala_ed/accounting/fiscal_year_utils.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import formatdate, getdate
from pypika import Order

CACHE_KEY = "ifitwala_ed:accounting:fiscal_years"
FISCAL_YEAR_LABELS = {
    "Posting Date": _("Posting Date"),
}


class FiscalYearError(frappe.ValidationError):
    pass


def _resolve_fiscal_year_label(label: str) -> str:
    return FISCAL_YEAR_LABELS.get(label, label)


def clear_fiscal_year_cache():
    frappe.cache().delete_value(CACHE_KEY)


def get_active_fiscal_years(organization: str | None = None) -> list[dict]:
    cache_bucket = organization or "__all__"
    cached = frappe.cache().hget(CACHE_KEY, cache_bucket) or []
    if cached:
        return cached

    fiscal_year = frappe.qb.DocType("Fiscal Year")
    fiscal_year_organization = frappe.qb.DocType("Fiscal Year Organization")

    query = (
        frappe.qb.from_(fiscal_year)
        .inner_join(fiscal_year_organization)
        .on(fiscal_year_organization.parent == fiscal_year.name)
        .select(
            fiscal_year.name,
            fiscal_year.year,
            fiscal_year.year_start_date,
            fiscal_year.year_end_date,
            fiscal_year_organization.organization,
        )
        .where(fiscal_year.disabled == 0)
        .orderby(fiscal_year.year_start_date, order=Order.desc)
    )

    if organization:
        query = query.where(fiscal_year_organization.organization == organization)

    rows = query.run(as_dict=True)
    frappe.cache().hset(CACHE_KEY, cache_bucket, rows)
    return rows


def get_fiscal_year_date_range(organization: str, fiscal_year_name: str) -> dict:
    for row in get_active_fiscal_years(organization):
        if row.get("name") == fiscal_year_name:
            return {
                "fiscal_year": row.get("name"),
                "from_date": row.get("year_start_date"),
                "to_date": row.get("year_end_date"),
            }

    frappe.throw(
        _("Fiscal Year {fiscal_year} is not active for Organization {organization}").format(
            fiscal_year=frappe.bold(fiscal_year_name), organization=organization
        ),
        FiscalYearError,
    )


def resolve_fiscal_year(
    organization: str,
    posting_date,
    fiscal_year_name: str | None = None,
    label: str = "Posting Date",
    raise_on_missing: bool = True,
):
    if not organization:
        frappe.throw(_("Organization is required to resolve Fiscal Year"), FiscalYearError)

    if not posting_date and not fiscal_year_name:
        return None

    target_date = getdate(posting_date) if posting_date else None
    matching_rows = []
    for row in get_active_fiscal_years(organization):
        name_matches = not fiscal_year_name or row.get("name") == fiscal_year_name
        date_matches = not target_date or (
            getdate(row.get("year_start_date")) <= target_date <= getdate(row.get("year_end_date"))
        )
        if name_matches and date_matches:
            matching_rows.append(row)

    if len(matching_rows) == 1:
        return matching_rows[0]

    if not raise_on_missing:
        return None

    if len(matching_rows) > 1:
        fiscal_years = ", ".join(sorted({row.get("name") for row in matching_rows}))
        frappe.throw(
            _(
                "Date {posting_date} resolves to multiple active Fiscal Years for Organization {organization}: {fiscal_years}"
            ).format(
                posting_date=formatdate(target_date),
                organization=organization,
                fiscal_years=fiscal_years,
            ),
            FiscalYearError,
        )

    if fiscal_year_name:
        frappe.throw(
            _("Fiscal Year {fiscal_year} is not active for Organization {organization}").format(
                fiscal_year=frappe.bold(fiscal_year_name), organization=organization
            ),
            FiscalYearError,
        )

    frappe.throw(
        _("{label} {posting_date} is not in any active Fiscal Year for Organization {organization}").format(
            label=_resolve_fiscal_year_label(label),
            posting_date=formatdate(target_date),
            organization=organization,
        ),
        FiscalYearError,
    )


def fill_date_range_from_fiscal_year(filters: dict, from_key: str = "from_date", to_key: str = "to_date") -> tuple:
    filters = filters or {}
    fiscal_year_name = filters.get("fiscal_year")
    organization = filters.get("organization")
    from_date = filters.get(from_key)
    to_date = filters.get(to_key)

    if fiscal_year_name and organization:
        fiscal_year_range = get_fiscal_year_date_range(organization, fiscal_year_name)
        from_date = from_date or fiscal_year_range["from_date"]
        to_date = to_date or fiscal_year_range["to_date"]

    return from_date, to_date
