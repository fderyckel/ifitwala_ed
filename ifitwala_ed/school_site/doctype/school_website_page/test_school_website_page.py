# ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py

# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_site.doctype.school_website_page.school_website_page import (
	compute_school_page_publication_flags,
	normalize_workflow_state,
)
from ifitwala_ed.website.seo_checks import build_seo_assistant_report
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


def _admissions_steps_props():
	return {
		"steps": [
			{"key": "inquire", "title": "Inquire", "description": "", "icon": "mail"},
			{"key": "visit", "title": "Visit", "description": "", "icon": "map"},
		],
		"layout": "horizontal",
	}


class TestSchoolWebsitePage(FrappeTestCase):
	def test_workflow_state_normalization_rejects_invalid_state(self):
		with self.assertRaises(frappe.ValidationError):
			normalize_workflow_state("Invalid State")

	def test_school_page_publication_flags_require_workflow_published(self):
		status, is_published = compute_school_page_publication_flags(
			school_is_public=True,
			workflow_state="Approved",
		)
		self.assertEqual(status, "Draft")
		self.assertEqual(is_published, 0)

	def test_school_page_publication_flags_require_school_readiness(self):
		status, is_published = compute_school_page_publication_flags(
			school_is_public=False,
			workflow_state="Published",
		)
		self.assertEqual(status, "Draft")
		self.assertEqual(is_published, 0)

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

	def test_validate_page_blocks_rejects_admissions_block_for_standard_school_page(self):
		page = frappe._dict(
			{
				"doctype": "School Website Page",
				"page_type": "Standard",
				"blocks": [
					_row(block_type="hero", props={"title": "Home"}, order=1),
					_row(
						block_type="admissions_steps",
						props=_admissions_steps_props(),
						order=2,
					),
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			validate_page_blocks(page)

	def test_validate_page_blocks_allows_admissions_blocks_for_admissions_page(self):
		page = frappe._dict(
			{
				"doctype": "School Website Page",
				"page_type": "Admissions",
				"blocks": [
					_row(
						block_type="admissions_overview",
						props={"heading": "Admissions", "content_html": "<p>Welcome</p>"},
						order=1,
					),
					_row(
						block_type="admissions_steps",
						props=_admissions_steps_props(),
						order=2,
					),
				],
			}
		)
		validate_page_blocks(page)

	def test_validate_page_blocks_rejects_program_intro_for_website_story(self):
		page = frappe._dict(
			{
				"doctype": "Website Story",
				"blocks": [
					_row(block_type="hero", props={"title": "Story"}, order=1),
					_row(
						block_type="program_intro",
						props={"heading": "Program intro"},
						order=2,
					),
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			validate_page_blocks(page)

	def test_validate_page_blocks_rejects_admissions_block_for_program_profile(self):
		page = frappe._dict(
			{
				"doctype": "Program Website Profile",
				"blocks": [
					_row(
						block_type="program_intro",
						props={"heading": "Program"},
						order=1,
					),
					_row(
						block_type="admission_cta",
						props={"intent": "inquire"},
						order=2,
					),
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			validate_page_blocks(page)

	def test_seo_assistant_reports_missing_admissions_cta(self):
		report = build_seo_assistant_report(
			parent_doctype="School Website Page",
			doc_payload={
				"page_type": "Admissions",
				"title": "Admissions",
				"meta_description": "Admissions overview for families.",
				"blocks": [
					{
						"block_type": "admissions_overview",
						"order": 1,
						"idx": 1,
						"is_enabled": 1,
						"props": json.dumps(
							{"heading": "Admissions", "content_html": "<p>Welcome</p>"}
						),
					},
					{
						"block_type": "faq",
						"order": 2,
						"idx": 2,
						"is_enabled": 1,
						"props": json.dumps(
							{
								"items": [
									{"question": "Q1", "answer_html": "<p>A1</p>"},
									{"question": "Q2", "answer_html": "<p>A2</p>"},
								],
								"enable_schema": False,
							}
						),
					},
				],
			},
		)
		codes = {row["code"] for row in report["checks"]}
		self.assertIn("cta_missing_admissions", codes)
		self.assertIn("schema_faq_disabled", codes)

	def test_seo_assistant_reports_h1_issues(self):
		report = build_seo_assistant_report(
			parent_doctype="School Website Page",
			doc_payload={
				"page_type": "Standard",
				"title": "About",
				"meta_description": "About our school.",
				"blocks": [
					{
						"block_type": "rich_text",
						"order": 1,
						"idx": 1,
						"is_enabled": 1,
						"props": json.dumps({"content_html": "<p>Body</p>"}),
					},
					{
						"block_type": "hero",
						"order": 2,
						"idx": 2,
						"is_enabled": 1,
						"props": json.dumps({"title": "About"}),
					},
				],
			},
		)
		codes = {row["code"] for row in report["checks"]}
		self.assertIn("h1_first_block", codes)

	def test_seo_assistant_program_cta_present_clears_program_warning(self):
		report = build_seo_assistant_report(
			parent_doctype="Program Website Profile",
			doc_payload={
				"intro_text": "Program intro",
				"blocks": [
					{
						"block_type": "program_intro",
						"order": 1,
						"idx": 1,
						"is_enabled": 1,
						"props": json.dumps({"heading": "Program", "cta_intent": "apply"}),
					}
				],
			},
		)
		codes = {row["code"] for row in report["checks"]}
		self.assertNotIn("cta_missing_program", codes)
