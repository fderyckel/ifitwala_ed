# ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.py

import json

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.validators import validate_page_blocks


class ProgramWebsiteProfile(Document):
	def validate(self):
		self._sync_status_from_program()
		self._validate_unique_profile()
		self._validate_program_slug()
		self._validate_blocks_props_json()
		validate_page_blocks(self)

	def on_update(self):
		self._sync_website_discoverability()

	def after_insert(self):
		self._sync_website_discoverability()

	def on_trash(self):
		self._invalidate_program_list_cache()

	def _sync_status_from_program(self):
		if not self.program:
			return
		is_published = frappe.db.get_value("Program", self.program, "is_published")
		self.status = "Published" if int(is_published or 0) == 1 else "Draft"

	def _validate_unique_profile(self):
		exists = frappe.db.exists(
			"Program Website Profile",
			{
				"program": self.program,
				"school": self.school,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(
				_("A Program Website Profile already exists for this Program and School."),
				frappe.ValidationError,
			)

	def _validate_program_slug(self):
		if self.status != "Published":
			return
		program_slug = frappe.db.get_value("Program", self.program, "program_slug")
		if not program_slug:
			frappe.throw(
				_("Program slug is required before publishing a Program Website Profile."),
				frappe.ValidationError,
			)

	def _sync_website_discoverability(self):
		if self.status == "Published" and self.school:
			from ifitwala_ed.website.bootstrap import ensure_programs_index_page

			ensure_programs_index_page(school_name=self.school)

		self._invalidate_program_list_cache()

	def _invalidate_program_list_cache(self):
		from ifitwala_ed.website.providers.program_list import invalidate_program_list_cache

		invalidate_program_list_cache()

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
