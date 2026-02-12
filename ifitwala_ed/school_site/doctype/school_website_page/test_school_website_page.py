# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website.validators import validate_page_blocks


def _row(*, block_type: str, props=None, order: int = 1, is_enabled: int = 1):
	return frappe._dict(
		{
			"block_type": block_type,
			"order": order,
			"idx": order,
			"is_enabled": is_enabled,
			"props": json.dumps(props or {}),
		}
	)


class TestSchoolWebsitePage(FrappeTestCase):
	def test_validate_page_blocks_rejects_empty_enabled_set(self):
		page = frappe._dict({"blocks": []})
		with self.assertRaises(frappe.ValidationError):
			validate_page_blocks(page)

	def test_validate_page_blocks_rejects_unknown_block_type(self):
		page = frappe._dict(
			{
				"blocks": [
					_row(block_type="hero", props={"title": "Home"}, order=1),
					_row(block_type="not_registered", props={"title": "Unknown"}, order=2),
				]
			}
		)
		with self.assertRaises(frappe.ValidationError):
			validate_page_blocks(page)

	def test_validate_page_blocks_rejects_first_block_without_h1_owner(self):
		page = frappe._dict(
			{
				"blocks": [
					_row(
						block_type="rich_text",
						props={"content_html": "<p>Body</p>", "max_width": "normal"},
						order=1,
					),
					_row(block_type="hero", props={"title": "Home"}, order=2),
				]
			}
		)
		with self.assertRaises(frappe.ValidationError):
			validate_page_blocks(page)

	def test_validate_page_blocks_normalizes_legacy_cta_props(self):
		legacy_cta = _row(
			block_type="cta",
			props={"cta_label": "Apply", "cta_link": "/admissions/apply"},
			order=2,
		)
		page = frappe._dict(
			{
				"blocks": [
					_row(block_type="hero", props={"title": "Home"}, order=1),
					legacy_cta,
				]
			}
		)

		validate_page_blocks(page)
		parsed = json.loads(legacy_cta.props)
		self.assertEqual(parsed.get("button_label"), "Apply")
		self.assertEqual(parsed.get("button_link"), "/admissions/apply")
