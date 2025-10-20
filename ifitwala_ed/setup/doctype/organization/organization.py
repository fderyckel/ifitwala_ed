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
		# Disallow adding a child under a non-group parent
		if self.parent_organization:
			parent_is_group = frappe.db.get_value("Organization", self.parent_organization, "is_group")
			if not parent_is_group:
				frappe.throw(_("Parent Organization must be a Group. '{0}' is not a Group.")
					.format(self.parent_organization))


@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False, **kwargs):
	"""Return tree nodes: children of `parent`, or top-level groups if root."""
	filters = dict(kwargs.get("filters") or {})

	# Treat virtual root label as no parent
	if is_root or not parent or parent == "All Organizations":
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
		# show in nested-set order
		order_by="lft asc",
		filters=filters,
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

	Accepts both our prompt fields and the standard treeview args:
	- organization_name (str, reqd)
	- abbr (str, reqd)
	- is_group (0/1)
	- parent_organization OR parent (str | None | 'All Organizations')
	"""
	org_name = (kwargs.get("organization_name") or "").strip()
	abbr = (kwargs.get("abbr") or "").strip()
	is_group = cint(kwargs.get("is_group") or 0)

	parent = kwargs.get("parent_organization") or kwargs.get("parent")
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
