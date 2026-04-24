from __future__ import annotations

import frappe
from frappe import _

LEGACY_ORGANIZATION = "All Organizations"


def execute():
    if not frappe.db.table_exists("Designation") or not frappe.db.table_exists("Organization"):
        return

    legacy_designations = frappe.get_all(
        "Designation",
        filters={"organization": LEGACY_ORGANIZATION},
        pluck="name",
        order_by="name asc",
        limit=0,
    )
    legacy_designations = sorted(str(name).strip() for name in legacy_designations or [] if str(name).strip())
    if not legacy_designations:
        return

    real_organizations = frappe.get_all(
        "Organization",
        filters={"name": ["!=", LEGACY_ORGANIZATION]},
        pluck="name",
        order_by="lft asc, name asc",
        limit=2,
    )
    real_organizations = [str(name).strip() for name in real_organizations or [] if str(name).strip()]

    if len(real_organizations) != 1:
        _throw_ambiguous_mapping(legacy_designations)

    target_organization = real_organizations[0]
    for designation in legacy_designations:
        frappe.db.set_value(
            "Designation",
            designation,
            "organization",
            target_organization,
            update_modified=False,
        )


def _throw_ambiguous_mapping(legacy_designations: list[str]) -> None:
    preview = ", ".join(legacy_designations[:20])
    if len(legacy_designations) > 20:
        preview = f"{preview}, ..."

    frappe.throw(
        _(
            "Legacy Designation rows use All Organizations and cannot be mapped automatically: {designations}. "
            "Add an explicit cleanup patch with the target Organization for each row."
        ).format(designations=preview)
    )
