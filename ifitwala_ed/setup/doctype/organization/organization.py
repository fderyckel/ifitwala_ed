# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils import cint

class Organization(NestedSet):
	def validate(self):
		# Prevent changing parent of root node
		if self.name == "All Organizations" and self.parent_organization:
			frappe.throw(_("The root organization 'All Organizations' cannot have a parent."))

		# Disallow adding a child under a non-group parent (ERPNext-like rule)
		if self.parent_organization:
			parent_is_group = frappe.db.get_value("Organization", self.parent_organization, "is_group")
			if not parent_is_group:
				frappe.throw(
					_("Parent Organization must be a Group. '{0}' is not a Group.")
					.format(self.parent_organization)
				)


@frappe.whitelist()
def get_children(doctype, parent=None, filters=None):
	"""Return tree nodes: children of `parent`, or top-level groups if no parent."""
	filters = filters or {}

	# If no parent passed, show only groups (roots)
	if not parent:
		filters.update({"is_group": 1, "parent_organization": ["is", "not set"]})
	else:
		filters.update({"parent_organization": parent})

	return frappe.get_all(
		"Organization",
		fields=[
			"name as value",
			"organization_name as title",
			"is_group as expandable",
		],
		filters=filters,
		order_by="organization_name asc",
	)


@frappe.whitelist()
def get_parents(doc, name):
	"""Return list of parent names up to the root for breadcrumbs."""
	parents = []
	doc = frappe.get_doc("Organization", name)
	while doc.parent_organization:
		parents.append(doc.parent_organization)
		doc = frappe.get_doc("Organization", doc.parent_organization)
	return parents


@frappe.whitelist()
def add_node(**kwargs):
	"""
	Create a new Organization node from the tree dialog.

	Expected kwargs:
	- organization_name (str)
	- abbr (str)
	- is_group (0/1)
	- parent_organization (str | None | 'All Organizations')
	"""
	org_name = (kwargs.get("organization_name") or "").strip()
	abbr = (kwargs.get("abbr") or "").strip()
	is_group = cint(kwargs.get("is_group") or 0)
	parent = kwargs.get("parent_organization")

	# Root add: treat 'All Organizations' as no parent
	if not parent or parent == "All Organizations":
		parent = None

	if not org_name or not abbr:
		frappe.throw(_("Organization Name and Abbreviation are required."))

	doc = frappe.get_doc({
		"doctype": "Organization",
		"organization_name": org_name,
		"abbr": abbr,
		"is_group": is_group,
		"parent_organization": parent,
	})
	doc.insert()
	return {"name": doc.name}
