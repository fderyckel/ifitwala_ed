# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet


class Organization(NestedSet):
	pass


@frappe.whitelist()
def get_children(doctype, parent=None, filters=None):
    """
    Return tree nodes: children of `parent`, or top-level groups if no parent.
    """
    filters = frappe.parse_json(filters) or {}

    # Determine if we are at the root level
    if not parent:
        filters.update({"parent_organization": ""})
    else:
        filters.update({"parent_organization": parent})
    
    # Add is_group filter for top-level nodes
    if not parent and "is_group" not in filters:
        filters["is_group"] = 1
    
    # Exclude archived nodes if the field exists
    if frappe.db.has_column("Organization", "archived"):
        filters["archived"] = 0
    
    # Fetch child nodes
    nodes = frappe.get_all(
        "Organization",
        fields=[
            "name as value",
            "organization_name as title",
            "is_group as expandable",
            "archived"
        ],
        filters=filters,
        order_by="name"
    )
    
    # Format response for consistency
    for node in nodes:
        node["expandable"] = 1 if node.get("is_group") else 0
        if "archived" in node:
            node["title"] += " (Archived)" if node["archived"] else ""
    
    return nodes

@frappe.whitelist()
def get_parents(doctype, name):
    """
    Return a list of parent names up to the root for breadcrumbs.
    Optimized for single-query traversal, matching ERPNext structure.
    """
    parents = []
    current = name
    
    while current:
        parent = frappe.db.get_value("Organization", current, "parent_organization")
        if parent:
            parents.append(parent)
            current = parent
        else:
            break
    
    # Return in root-to-leaf order for breadcrumbs
    return parents[::-1]