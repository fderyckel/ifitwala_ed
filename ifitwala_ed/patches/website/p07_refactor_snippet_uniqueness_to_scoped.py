# ifitwala_ed/patches/website/p07_refactor_snippet_uniqueness_to_scoped.py

import frappe

from ifitwala_ed.school_site.doctype.website_snippet.website_snippet import normalize_scope_type


def _normalize_existing_snippet_rows():
	rows = frappe.get_all(
		"Website Snippet",
		fields=["name", "scope_type", "organization", "school", "snippet_id"],
		limit_page_length=0,
	)
	for row in rows:
		try:
			scope = normalize_scope_type(row.scope_type)
		except Exception:
			scope = "Global"
		updates = {}
		snippet_id = (row.snippet_id or "").strip()
		if snippet_id != (row.snippet_id or ""):
			updates["snippet_id"] = snippet_id
		if scope != (row.scope_type or ""):
			updates["scope_type"] = scope

		if scope == "Global":
			if row.organization:
				updates["organization"] = None
			if row.school:
				updates["school"] = None
		elif scope == "Organization":
			if row.school:
				updates["school"] = None
		elif scope == "School":
			if row.organization:
				updates["organization"] = None

		if updates:
			frappe.db.set_value(
				"Website Snippet",
				row.name,
				updates,
				update_modified=False,
			)


def execute():
	frappe.reload_doc("school_site", "doctype", "website_snippet")
	_normalize_existing_snippet_rows()
