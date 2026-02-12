# ifitwala_ed/school_site/doctype/website_snippet/website_snippet.py

import frappe
from frappe import _
from frappe.model.document import Document


VALID_SCOPES = {"Global", "Organization", "School"}


def normalize_scope_type(scope_type: str | None) -> str:
	scope = (scope_type or "").strip() or "Global"
	if scope not in VALID_SCOPES:
		frappe.throw(
			_("Invalid scope type: {0}").format(scope),
			frappe.ValidationError,
		)
	return scope


def ensure_scope_indexes():
	frappe.db.add_index("Website Snippet", ["snippet_id", "scope_type"])
	frappe.db.add_index("Website Snippet", ["scope_type", "school"])
	frappe.db.add_index("Website Snippet", ["scope_type", "organization"])


def build_scope_uniqueness_filters(*, snippet_id: str, scope_type: str, organization=None, school=None) -> dict:
	scope = normalize_scope_type(scope_type)
	filters = {
		"snippet_id": (snippet_id or "").strip(),
		"scope_type": scope,
	}
	if scope == "Organization":
		filters["organization"] = organization
	elif scope == "School":
		filters["school"] = school
	return filters


class WebsiteSnippet(Document):
	def validate(self):
		self.snippet_id = (self.snippet_id or "").strip()
		if not self.snippet_id:
			frappe.throw(
				_("Snippet ID is required."),
				frappe.ValidationError,
			)

		scope = normalize_scope_type(self.scope_type)
		self.scope_type = scope

		if scope == "Global":
			self.organization = None
			self.school = None
		elif scope == "Organization":
			if not self.organization:
				frappe.throw(
					_("Organization is required for Organization-scoped snippets."),
					frappe.ValidationError,
				)
			self.school = None
		else:
			if not self.school:
				frappe.throw(
					_("School is required for School-scoped snippets."),
					frappe.ValidationError,
				)
			self.organization = None

		self._validate_scoped_uniqueness()

	def _validate_scoped_uniqueness(self):
		filters = build_scope_uniqueness_filters(
			snippet_id=self.snippet_id,
			scope_type=self.scope_type,
			organization=self.organization,
			school=self.school,
		)
		filters["name"] = ["!=", self.name]

		exists = frappe.db.exists("Website Snippet", filters)
		if not exists:
			return
		frappe.throw(
			_(
				"A Website Snippet with Snippet ID '{0}' already exists for this scope."
			).format(self.snippet_id),
			frappe.ValidationError,
		)


def on_doctype_update():
	ensure_scope_indexes()
