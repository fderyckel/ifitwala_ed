# ifitwala_ed/tests/factories/organization.py

from __future__ import annotations

import frappe


def make_organization(prefix: str = "Org", *, with_coa: bool = False):
    org = frappe.get_doc(
        {
            "doctype": "Organization",
            "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "abbr": f"ORG{frappe.generate_hash(length=4)}",
        }
    )
    previous_skip_coa = bool(getattr(frappe.flags, "skip_org_coa_setup", False))
    if not with_coa:
        org.flags.skip_coa_setup = True
        frappe.flags.skip_org_coa_setup = True
    try:
        org.insert()
    finally:
        frappe.flags.skip_org_coa_setup = previous_skip_coa
    return org


def make_school(
    organization: str,
    prefix: str = "School",
    *,
    parent_school: str | None = None,
    is_group: int = 0,
):
    # Tests that build school hierarchies must opt into valid NestedSet parents explicitly.
    school = frappe.get_doc(
        {
            "doctype": "School",
            "school_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "abbr": f"S{frappe.generate_hash(length=4)}",
            "organization": organization,
            "parent_school": parent_school,
            "is_group": is_group,
        }
    )
    school.insert()
    return school
