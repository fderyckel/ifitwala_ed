# ifitwala_ed/website/providers/content_snippet.py

import frappe
from frappe import _

from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def _get_snippet(snippet_id: str, school):
	if not snippet_id:
		return None

	organization = school.organization if school else None

	if school:
		name = frappe.db.get_value(
			"Website Snippet",
			{"snippet_id": snippet_id, "scope_type": "School", "school": school.name},
			"name",
		)
		if name:
			return frappe.get_doc("Website Snippet", name)

	if organization:
		name = frappe.db.get_value(
			"Website Snippet",
			{"snippet_id": snippet_id, "scope_type": "Organization", "organization": organization},
			"name",
		)
		if name:
			return frappe.get_doc("Website Snippet", name)

	name = frappe.db.get_value(
		"Website Snippet",
		{"snippet_id": snippet_id, "scope_type": "Global"},
		"name",
	)
	if name:
		return frappe.get_doc("Website Snippet", name)
	return None


def get_context(*, school, page, block_props):
	snippet_id = block_props.get("snippet_id")
	snippet = _get_snippet(snippet_id, school)
	if not snippet:
		frappe.throw(
			_("Content snippet not found or not available for this scope."),
			frappe.ValidationError,
		)

	content = sanitize_html(snippet.content or "", allow_headings_from="h2")
	return {
		"data": {
			"content": content,
		}
	}
