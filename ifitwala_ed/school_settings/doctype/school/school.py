# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/school/school.py

import frappe
from frappe import _
from frappe.utils.nestedset import NestedSet
from frappe.cache_manager import clear_defaults_cache
from frappe.contacts.address_and_contact import load_address_and_contact


class School(NestedSet):
	nsm_parent_field = "parent_school"

	def onload(self):
		load_address_and_contact(self, "school")

	def validate(self):
		# Core identity + hierarchy integrity
		self.validate_abbr()
		self.validate_parent_school()  # parent must be group
		self.validate_parent_school_organization()  # parent/child must share org

		# prevent changing Organization on a node that has children.
		# Rationale: avoids accidental cross-org subtree drift and keeps "effective record" resolution sane.
		self.validate_organization_change_policy_a()

	def on_update(self):
		NestedSet.on_update(self)

	def after_save(self):
		if self.is_dirty("abbr"):
			self.update_navbar_item_for_abbreviation_change()

	def on_trash(self):
		NestedSet.validate_if_child_exists(self)
		frappe.utils.nestedset.update_nsm(self)

	def after_rename(self, olddn, newdn, merge=False):
		# when merging, let the target keep its own title; only force-update on regular renames
		if not merge:
			# cheap single-field DB write; avoids extra fetch/save
			self.db_set("school_name", newdn, update_modified=False)
		clear_defaults_cache()

	def validate_abbr(self):
		if not self.abbr:
			self.abbr = "".join([c[0] for c in self.school_name.split()]).upper()

		self.abbr = self.abbr.strip()

		if self.get("__islocal") and len(self.abbr) > 5:
			frappe.throw(_("Abbreviation cannot have more than 5 characters"))

		if not self.abbr.strip():
			frappe.throw(_("Abbreviation is mandatory"))

		# Keep existing behavior; avoid broader refactors here.
		if frappe.db.exists("School", {"abbr": self.abbr, "name": ["!=", self.name]}):
			frappe.throw(_("Abbreviation {0} is already used for another school.").format(self.abbr))

	def validate_parent_school(self):
		if self.parent_school:
			is_group = frappe.db.get_value("School", self.parent_school, "is_group")
			if not is_group:
				frappe.throw(_("Parent School must be a group school."))

	def validate_parent_school_organization(self):
		"""
		Hard invariant:
		If a School has a parent_school, both MUST belong to the same Organization.

		This protects:
		- permission logic that assumes a coherent school tree
		- "effective record" resolution that climbs school ancestors then (optionally) org ancestors
		- multi-school governance where org boundaries are meaningful
		"""
		if not self.parent_school:
			return

		parent_org, parent_school_name = frappe.db.get_value(
			"School",
			self.parent_school,
			["organization", "school_name"],
		) or (None, None)

		# Defensive: if parent is missing or has no org, let Frappe/DB integrity handle it elsewhere.
		if not parent_org:
			return

		child_org = (self.organization or "").strip()
		parent_org = (parent_org or "").strip()

		if child_org and parent_org and child_org != parent_org:
			frappe.throw(
				_(
					"School \"{child}\" belongs to Organization \"{child_org}\", "
					"but its Parent School \"{parent}\" belongs to Organization \"{parent_org}\".\n\n"
					"Parent and child schools must belong to the same Organization.\n"
					"Fix: either change this School’s Organization to \"{parent_org}\" "
					"or choose a different Parent School under \"{child_org}\"."
				).format(
					child=self.school_name or self.name,
					child_org=child_org,
					parent=parent_school_name or self.parent_school,
					parent_org=parent_org,
				)
			)

	def validate_organization_change_policy_a(self):
		"""
		Block changing a School's Organization if it has children.

		Reason:
		Changing org on a parent would either:
		- silently strand children in a different org (invalid), or
		- require a subtree migration workflow (out of scope for now).

		So we force the user to:
		- migrate the subtree intentionally (future tool), or
		- only change org when the node is a leaf.
		"""
		# New docs: nothing to compare
		if self.get("__islocal"):
			return

		# Only act when Organization is being changed
		if not self.is_dirty("organization"):
			return

		# If this node has children, block the change.
		# (cheap existence check; avoids loading nestedset ranges)
		has_children = frappe.db.exists("School", {"parent_school": self.name})
		if not has_children:
			return

		before = self.get_doc_before_save()
		old_org = (before.organization or "").strip() if before else ""
		new_org = (self.organization or "").strip()

		frappe.throw(
			_(
				"Cannot change Organization for School \"{school}\" because it has child schools.\n\n"
				"Current Organization: \"{old_org}\"\n"
				"Requested Organization: \"{new_org}\"\n\n"
				"Policy: a School with children cannot change Organization (to prevent cross-organization trees).\n"
				"Fix: move/re-parent child schools first (or use a future subtree migration tool), "
				"then change the Organization when this School becomes a leaf."
			).format(
				school=self.school_name or self.name,
				old_org=old_org,
				new_org=new_org,
			)
		)

	def update_navbar_item_for_abbreviation_change(self):
		old_abbr = self.get_doc_before_save().abbr
		new_url = f"/school/{self.abbr}"
		old_url = f"/school/{old_abbr}"

		ws = frappe.get_single("Website Settings")

		for item in ws.top_bar_items:
			if item.url == old_url:
				item.url = new_url
				item.label = self.school_name
				ws.save(ignore_permissions=True)
				frappe.msgprint(_("Navbar item updated to new abbreviation."))
				break


@frappe.whitelist()
def enqueue_replace_abbr(school, old, new):
	kwargs = dict(school=school, old=old, new=new)
	frappe.enqueue("ifitwala_ed.school_settings.doctype.school.school.replace_abbr", **kwargs)


@frappe.whitelist()
def replace_abbr(school, old, new):
	new = new.strip()
	if not new:
		frappe.throw(_("Abbr can not be blank or space"))

	frappe.only_for("System Manager")

	frappe.db.set_value("School", school, "abbr", new)

	def _rename_record(doc):
		parts = doc[0].rsplit(" - ", 1)
		if len(parts) == 1 or parts[1].lower() == old.lower():
			frappe.rename_doc(dt, doc[0], parts[0] + " - " + new)

	def _rename_records(dt):
		# rename is expensive so let's be economical with memory usage
		doc = (d for d in frappe.db.sql("select name from `tab%s` where school=%s" % (dt, "%s"), school))
		for d in doc:
			_rename_record(d)


def get_name_with_abbr(name, school):
	school_abbr = frappe.db.get_value("School", school, "abbr")
	parts = name.split(" - ")
	if parts[-1].lower() != school_abbr.lower():
		parts.append(school_abbr)
	return " - ".join(parts)

@frappe.whitelist()
def get_children(doctype, parent=None, school=None, is_root=False):
	# TreeView behavior:
	# - "All Schools" is a UI sentinel (not a real School record)
	# - When a School is selected in the tree filter, TreeView sets BOTH:
	#     parent=<selected_school> and school=<selected_school>
	# - We intentionally use `parent` as the expansion root. `school` is redundant.
	if parent is None or parent == "All Schools":
		parent = ""

	return frappe.db.sql(
		"""
		SELECT
			name as value,
			is_group as expandable
		FROM
			`tab{doctype}` comp
		WHERE
			ifnull(parent_school, "")={parent}
		""".format(
			doctype=doctype,
			parent=frappe.db.escape(parent),
		),
		as_dict=1,
	)


@frappe.whitelist()
def add_node():
	from frappe.desk.treeview import make_tree_args

	args = frappe.form_dict
	args = make_tree_args(**args)

	if args.parent_school == "All Schools":
		args.parent_school = None

	frappe.get_doc(args).insert()


@frappe.whitelist()
def add_school_to_navbar(school_name, abbreviation, website_slug=None):
	url_segment = website_slug or abbreviation
	url_path = f"/school/{url_segment}"
	ws = frappe.get_single("Website Settings")

	existing = next((item for item in ws.top_bar_items if item.url == url_path), None)

	if existing:
		if existing.label != school_name:
			existing.label = school_name
			ws.save(ignore_permissions=True)
			return "Updated existing nav item."
		return "Nav item already exists."

	# Add new item
	ws.append(
		"top_bar_items",
		{
			"label": school_name,
			"url": url_path,
			"parent_label": "Home",
		},
	)
	ws.save(ignore_permissions=True)
	return "Added new nav item."
