# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class Organization(NestedSet):
	pass


@frappe.whitelist()
def get_children(doctype, parent=None, filters=None):
    """Return tree nodes: children of `parent`, or top-level groups if no parent."""
    filters = filters or {}
    # if no parent passed, show only groups (to build roots)
    if not parent:
        filters.update({"is_group": 1})
    else:
        filters.update({"parent_organization": parent})

    return frappe.get_all(
        "Organization",
        fields=[
            "name as value",
            "organization_name as title",
            "is_group as expandable"
        ],
        filters=filters,
        order_by="name"
    )

@frappe.whitelist()
def get_parents(doctype, name):
    """Return list of parent names up to the root for breadcrumbs."""
    parents = []
    doc = frappe.get_doc("Organization", name)
    while doc.parent_organization:
        parents.append(doc.parent_organization)
        doc = frappe.get_doc("Organization", doc.parent_organization)
    return parents