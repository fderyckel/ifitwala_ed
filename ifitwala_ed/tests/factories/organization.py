# ifitwala_ed/tests/factories/organization.py

from __future__ import annotations

import frappe


def make_organization(prefix: str = "Org"):
    org = frappe.get_doc(
        {
            "doctype": "Organization",
            "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "abbr": f"ORG{frappe.generate_hash(length=4)}",
        }
    )
    org.insert()
    return org


def make_school(organization: str, prefix: str = "School"):
    school = frappe.get_doc(
        {
            "doctype": "School",
            "school_name": f"{prefix} {frappe.generate_hash(length=6)}",
            "abbr": f"S{frappe.generate_hash(length=4)}",
            "organization": organization,
        }
    )
    school.insert()
    return school
