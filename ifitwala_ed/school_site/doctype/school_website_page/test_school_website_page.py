# ifitwala_ed/school_site/doctype/school_website_page/test_school_website_page.py

# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_site.doctype.school_website_page.school_website_page import (
    build_school_website_page_name,
    compute_school_page_publication_flags,
    normalize_workflow_state,
)
from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website.block_registry import get_block_definition_map
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
    def test_school_website_page_block_select_options_match_block_registry(self):
        block_json_path = (
            Path(__file__).resolve().parents[1] / "school_website_page_block" / "school_website_page_block.json"
        )
        payload = json.loads(block_json_path.read_text())
        block_field = next(field for field in payload["fields"] if field.get("fieldname") == "block_type")
        configured_options = {
            option.strip() for option in (block_field.get("options") or "").splitlines() if option.strip()
        }
        registered_types = set(get_block_definition_map())
        self.assertFalse(sorted(registered_types - configured_options))

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

    def test_school_page_publication_flags_respect_publish_window(self):
        status, is_published = compute_school_page_publication_flags(
            school_is_public=True,
            workflow_state="Published",
            publish_at="2099-01-01 08:00:00",
        )
        self.assertEqual(status, "Draft")
        self.assertEqual(is_published, 0)

    def test_build_school_website_page_name_uses_school_name_and_route(self):
        organization = make_organization(prefix="Name Org")
        school = make_school(organization.name, prefix="Name School")

        self.assertEqual(
            build_school_website_page_name(school=school.name, route="/"),
            f"{school.school_name} - Home [home]",
        )
        self.assertEqual(
            build_school_website_page_name(school=school.name, route="about/team"),
            f"{school.school_name} - About > Team [about__team]",
        )

    def test_draft_school_website_page_can_save_without_blocks(self):
        organization = make_organization(prefix="Draft Org")
        school = make_school(organization.name, prefix="Draft School")
        school.website_slug = f"draft-{frappe.generate_hash(length=6)}"
        school.save(ignore_permissions=True)

        page = frappe.get_doc(
            {
                "doctype": "School Website Page",
                "school": school.name,
                "route": "/",
                "page_type": "Standard",
                "title": school.school_name,
            }
        )
        page.insert()

        self.assertEqual(page.name, f"{school.school_name} - Home [home]")
        self.assertEqual(page.full_route, f"/schools/{school.website_slug}")
        self.assertEqual(page.workflow_state, "Draft")
        self.assertEqual(page.status, "Draft")
        self.assertEqual(page.is_published, 0)

    def test_non_draft_school_website_page_requires_enabled_block(self):
        organization = make_organization(prefix="Review Org")
        school = make_school(organization.name, prefix="Review School")
        school.website_slug = f"review-{frappe.generate_hash(length=6)}"
        school.save(ignore_permissions=True)

        page = frappe.get_doc(
            {
                "doctype": "School Website Page",
                "school": school.name,
                "route": "about",
                "page_type": "Standard",
                "title": "About",
                "workflow_state": "In Review",
            }
        )

        with self.assertRaises(frappe.ValidationError):
            page.insert()

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

    def test_validate_page_blocks_rejects_legacy_cta_props(self):
        page = frappe._dict(
            {
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(
                        block_type="cta",
                        props={"cta_label": "Apply", "cta_link": "/admissions/apply"},
                        order=2,
                    ),
                ]
            }
        )

        with self.assertRaises(frappe.ValidationError):
            validate_page_blocks(page)

    def test_validate_page_blocks_rejects_string_boolean_for_program_list(self):
        page = frappe._dict(
            {
                "doctype": "School Website Page",
                "page_type": "Standard",
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(
                        block_type="program_list",
                        props={"school_scope": "current", "show_intro": "false"},
                        order=2,
                    ),
                ],
            }
        )

        with self.assertRaises(frappe.ValidationError):
            validate_page_blocks(page)

    def test_validate_page_blocks_rejects_invalid_cta_link(self):
        page = frappe._dict(
            {
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(
                        block_type="cta",
                        props={
                            "title": "Apply",
                            "text": "Start here.",
                            "button_label": "Inquire",
                            "button_link": "inqiury",
                        },
                        order=2,
                    ),
                ]
            }
        )

        with self.assertRaises(frappe.ValidationError):
            validate_page_blocks(page)

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

    def test_validate_page_blocks_allows_section_carousel_for_standard_school_page(self):
        page = frappe._dict(
            {
                "doctype": "School Website Page",
                "page_type": "Standard",
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(
                        block_type="section_carousel",
                        props={
                            "heading": "Activities",
                            "content_html": "<p>Explore activities.</p>",
                            "items": [{"image": "/files/activity-1.jpg", "caption": "Sports Day"}],
                        },
                        order=2,
                    ),
                ],
            }
        )
        validate_page_blocks(page)

    def test_validate_page_blocks_allows_extended_leadership_props(self):
        page = frappe._dict(
            {
                "doctype": "School Website Page",
                "page_type": "Standard",
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(
                        block_type="leadership",
                        props={
                            "title": "Leadership & Administration",
                            "description": "Meet our school team.",
                            "leadership_title": "Academic Leadership",
                            "staff_title": "Faculty & Staff",
                            "role_profiles": ["Academic Admin"],
                            "role_scopes": [
                                {
                                    "role_profile": "Academic Admin",
                                    "school_scope": "current_and_descendants",
                                    "descendant_depth": 1,
                                }
                            ],
                            "limit": 4,
                            "staff_limit": 8,
                            "show_staff_carousel": True,
                        },
                        order=2,
                    ),
                ],
            }
        )
        validate_page_blocks(page)

    def test_validate_page_blocks_allows_staff_directory_props_for_standard_school_page(self):
        page = frappe._dict(
            {
                "doctype": "School Website Page",
                "page_type": "Standard",
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(
                        block_type="staff_directory",
                        props={
                            "title": "Faculty & Staff",
                            "description": "Meet the people shaping learning every day.",
                            "designations": ["Teacher"],
                            "role_profiles": ["Counselor"],
                            "show_search": True,
                            "show_designation_filter": True,
                            "show_role_profile_filter": True,
                            "limit": 12,
                            "empty_state_title": "Directory coming soon",
                            "empty_state_text": "Profiles appear automatically when staff are marked for the website.",
                        },
                        order=2,
                    ),
                ],
            }
        )
        validate_page_blocks(page)

    def test_validate_page_blocks_rejects_staff_directory_for_website_story(self):
        page = frappe._dict(
            {
                "doctype": "Website Story",
                "blocks": [
                    _row(block_type="hero", props={"title": "Story"}, order=1),
                    _row(
                        block_type="staff_directory",
                        props={"title": "Faculty & Staff"},
                        order=2,
                    ),
                ],
            }
        )
        with self.assertRaises(frappe.ValidationError):
            validate_page_blocks(page)

    def test_validate_page_blocks_allows_story_feed_and_academic_calendar_for_standard_school_page(self):
        page = frappe._dict(
            {
                "doctype": "School Website Page",
                "page_type": "Standard",
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(block_type="story_feed", props={"title": "Stories", "limit": 3}, order=2),
                    _row(
                        block_type="academic_calendar",
                        props={"title": "Academic Calendar", "include_terms": True, "include_holidays": True},
                        order=3,
                    ),
                ],
            }
        )
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

    def test_validate_page_blocks_allows_course_blocks_for_course_profile(self):
        page = frappe._dict(
            {
                "doctype": "Course Website Profile",
                "blocks": [
                    _row(
                        block_type="course_intro",
                        props={"heading": "Course"},
                        order=1,
                    ),
                    _row(
                        block_type="learning_highlights",
                        props={"heading": "Highlights"},
                        order=2,
                    ),
                ],
            }
        )
        validate_page_blocks(page)

    def test_validate_page_blocks_rejects_course_intro_for_standard_school_page(self):
        page = frappe._dict(
            {
                "doctype": "School Website Page",
                "page_type": "Standard",
                "blocks": [
                    _row(block_type="hero", props={"title": "Home"}, order=1),
                    _row(
                        block_type="course_intro",
                        props={"heading": "Course"},
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
                        "props": json.dumps({"heading": "Admissions", "content_html": "<p>Welcome</p>"}),
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

    def test_seo_assistant_course_cta_present_clears_course_warning(self):
        report = build_seo_assistant_report(
            parent_doctype="Course Website Profile",
            doc_payload={
                "course": "Course",
                "intro_text": "Course intro",
                "blocks": [
                    {
                        "block_type": "course_intro",
                        "order": 1,
                        "idx": 1,
                        "is_enabled": 1,
                        "props": json.dumps({"heading": "Course", "cta_intent": "inquire"}),
                    }
                ],
            },
        )
        codes = {row["code"] for row in report["checks"]}
        self.assertNotIn("cta_missing_course", codes)
