# ifitwala_ed/school_site/doctype/website_story/website_story.py

import json

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.validators import validate_page_blocks


class WebsiteStory(Document):
	def validate(self):
		self._validate_status()
		self._validate_unique_slug()
		self._validate_blocks_props_json()
		validate_page_blocks(self)

	def _validate_status(self):
		status = (self.status or "").strip() or "Draft"
		if status not in {"Draft", "Published"}:
			frappe.throw(
				_("Invalid status: {0}").format(status),
				frappe.ValidationError,
			)
		self.status = status

	def _validate_unique_slug(self):
		exists = frappe.db.exists(
			"Website Story",
			{
				"school": self.school,
				"slug": self.slug,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(
				_("A story with this slug already exists for this school."),
				frappe.ValidationError,
			)

	def _validate_blocks_props_json(self):
		for row in self.blocks or []:
			raw_props = (row.props or "").strip()
			if not raw_props:
				continue
			try:
				json.loads(raw_props)
			except Exception as exc:
				frappe.throw(
					_("Invalid block props JSON in row {0} ({1}): {2}").format(
						row.idx or "?",
						row.block_type or _("Unknown block"),
						str(exc),
					),
					frappe.ValidationError,
				)
