# Copyright (c) 2024, fdR and contributors
# For license information, please see license.txt

# ifitwala_ed/setup/doctype/organization/organization.py

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.utils import cint

VIRTUAL_ROOT = "All Organizations"

class Organization(NestedSet):
	def validate(self):
		if self.name == VIRTUAL_ROOT and self.parent_organization:
			frappe.throw(_("The root organization '{0}' cannot have a parent.").format(VIRTUAL_ROOT))
		if self.parent_organization:
			parent_is_group = frappe.db.get_value("Organization", self.parent_organization, "is_group")
			if not parent_is_group:
				frappe.throw(_("Parent Organization must be a Group. '{0}' is not a Group.")
					.format(self.parent_organization))
		self.validate_default_website_school()

	def validate_default_website_school(self):
		default_school = (self.default_website_school or "").strip()
		if not default_school:
			return

		school_org = frappe.db.get_value("School", default_school, "organization")
		if not school_org:
			frappe.throw(
				_("Default Website School '{0}' was not found.").format(default_school),
				frappe.ValidationError,
			)

		if school_org != self.name:
			frappe.throw(
				_(
					"Default Website School must belong to this Organization.\n"
					"School '{0}' belongs to '{1}', not '{2}'."
				).format(default_school, school_org, self.name),
				frappe.ValidationError,
			)

@frappe.whitelist()
def get_children(doctype, parent=None, is_root=False, **kwargs):
	"""
	Return children of `parent`. For virtual root, return top-level orgs.
	Top-level = parent_organization in [NULL, "", VIRTUAL_ROOT] to support legacy rows.
	"""
	filters = dict(kwargs.get("filters") or {})

	# Never show the virtual root as a child
	filters.update({"name": ["!=", VIRTUAL_ROOT]})

	if is_root or not parent or parent == VIRTUAL_ROOT:
		# cover NULL, empty string, and legacy 'VIRTUAL_ROOT'
		filters.update({"parent_organization": ["in", [None, "", VIRTUAL_ROOT]]})
	else:
		filters.update({"parent_organization": parent})

	rows = frappe.get_all(
		"Organization",
		fields=[
			"name as value",
			"organization_name as title",
			"is_group as expandable",
		],
		order_by="lft asc",
		filters=filters,
	)

	# normalize expandable to 0/1 for the tree widget
	for r in rows:
		r["expandable"] = 1 if r.get("expandable") else 0
	return rows

@frappe.whitelist()
def get_parents(doc, name):
	parents = []
	doc = frappe.get_doc("Organization", name)
	while doc.parent_organization:
		parents.append(doc.parent_organization)
		doc = frappe.get_doc("Organization", doc.parent_organization)
	return parents

@frappe.whitelist()
def add_node(**kwargs):
	org_name = (kwargs.get("organization_name") or "").strip()
	abbr = (kwargs.get("abbr") or "").strip()
	is_group = cint(kwargs.get("is_group") or 0)

	parent = kwargs.get("parent_organization") or kwargs.get("parent")
	if not parent or parent == VIRTUAL_ROOT:
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
