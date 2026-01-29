# ifitwala_ed/school_site/doctype/school_website_page/school_website_page.py

import json

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.utils import normalize_route


class SchoolWebsitePage(Document):
	def before_insert(self):
		self._sync_status_flags()
		self._seed_admissions_blocks()

	def validate(self):
		self._sync_status_flags()
		school_slug = frappe.db.get_value("School", self.school, "website_slug")
		if not school_slug:
			frappe.throw(
				_("School website slug is required to build routes."),
				frappe.ValidationError,
			)

		raw_value = self.route or ""
		raw_route = raw_value.strip()
		if raw_value != raw_route:
			frappe.throw(
				_("Route cannot start or end with whitespace."),
				frappe.ValidationError,
			)
		if not raw_route:
			frappe.throw(
				_("Route is required. Use '/' for the school home page."),
				frappe.ValidationError,
			)

		if raw_route == "/":
			self.full_route = normalize_route(f"/{school_slug}")
		else:
			if raw_route.startswith("/"):
				frappe.throw(
					_("Route must not start with '/'. Use '/' only for the home page."),
					frappe.ValidationError,
				)
			if raw_route.endswith("/"):
				frappe.throw(
					_("Route must not end with '/'. Remove the trailing slash."),
					frappe.ValidationError,
				)
			if "//" in raw_route:
				frappe.throw(
					_("Route must not contain empty segments ('//')."),
					frappe.ValidationError,
				)

			relative = raw_route
			segments = [seg for seg in relative.split("/") if seg]
			if not segments:
				frappe.throw(
					_("Route is required. Use '/' for the school home page."),
					frappe.ValidationError,
				)
			if segments[0] == school_slug:
				frappe.throw(
					_("Do not include the school slug in the route."),
					frappe.ValidationError,
				)

			self.full_route = normalize_route(f"/{school_slug}/{relative}")

		exists = frappe.db.exists(
			"School Website Page",
			{
				"school": self.school,
				"full_route": self.full_route,
				"name": ["!=", self.name],
			},
		)
		if exists:
			frappe.throw(
				_("A page already exists for this school and route."),
				frappe.ValidationError,
			)

	def _sync_status_flags(self):
		status = "Draft"
		if self.school:
			row = frappe.db.get_value(
				"School",
				self.school,
				["website_slug", "is_group"],
				as_dict=True,
			)
			if row and row.website_slug and int(row.is_group or 0) == 0:
				status = "Published"
		self.status = status
		self.is_published = 1 if status == "Published" else 0

	def _seed_admissions_blocks(self):
		if not self.is_new() or self.page_type != "Admissions" or self.blocks:
			return

		steps_props = {
			"steps": [
				{"key": "inquire", "title": "Inquire", "description": "", "icon": "mail"},
				{"key": "visit", "title": "Visit", "description": "", "icon": "map"},
				{"key": "apply", "title": "Apply", "description": "", "icon": "file-text"},
			],
			"layout": "horizontal",
		}

		faq_props = {
			"items": [{"question": "", "answer_html": ""}],
			"enable_schema": False,
			"collapsed_by_default": True,
		}

		self.append(
			"blocks",
			{
				"block_type": "admissions_overview",
				"order": 1,
				"props": json.dumps(
					{"heading": "Admissions", "content_html": "", "max_width": "normal"}
				),
				"is_enabled": 1,
			},
		)
		self.append(
			"blocks",
			{
				"block_type": "admissions_steps",
				"order": 2,
				"props": json.dumps(steps_props),
				"is_enabled": 1,
			},
		)
		self.append(
			"blocks",
			{
				"block_type": "admission_cta",
				"order": 3,
				"props": json.dumps({"intent": "inquire", "style": "primary"}),
				"is_enabled": 1,
			},
		)
		self.append(
			"blocks",
			{
				"block_type": "admission_cta",
				"order": 4,
				"props": json.dumps({"intent": "visit", "style": "secondary"}),
				"is_enabled": 1,
			},
		)
		self.append(
			"blocks",
			{
				"block_type": "admission_cta",
				"order": 5,
				"props": json.dumps({"intent": "apply", "style": "outline"}),
				"is_enabled": 1,
			},
		)
		self.append(
			"blocks",
			{
				"block_type": "faq",
				"order": 6,
				"props": json.dumps(faq_props),
				"is_enabled": 1,
			},
		)
