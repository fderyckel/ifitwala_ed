# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_settings.doctype.school.school import replace_abbr
from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestSchool(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_replace_abbr_renames_only_explicit_school_scoped_doctypes(self):
        rename_calls = []

        def fake_get_all(doctype, **kwargs):
            self.assertEqual(kwargs.get("filters"), {"school": "SCH-001"})
            if doctype == "Academic Year":
                return [frappe._dict(name="OLD 2025-2026", academic_year_name="2025-2026")]
            if doctype == "School Calendar":
                return [frappe._dict(name="OLD 2025-2026", calendar_name="2025-2026")]
            if doctype == "School Schedule":
                return [frappe._dict(name="OLD Weekly", schedule_name="Weekly")]
            self.fail(f"Unexpected doctype lookup: {doctype}")

        def fake_rename_doc(doctype, old_name, new_name):
            rename_calls.append((doctype, old_name, new_name))

        with (
            patch("ifitwala_ed.school_settings.doctype.school.school.frappe.only_for"),
            patch("ifitwala_ed.school_settings.doctype.school.school.frappe.db.set_value"),
            patch(
                "ifitwala_ed.school_settings.doctype.school.school.frappe.get_all",
                side_effect=fake_get_all,
            ),
            patch(
                "ifitwala_ed.school_settings.doctype.school.school.frappe.rename_doc",
                side_effect=fake_rename_doc,
            ),
            patch("ifitwala_ed.school_settings.doctype.school.school.frappe.db.sql") as sql_mock,
        ):
            replace_abbr("SCH-001", "OLD", "NEW")

        sql_mock.assert_not_called()
        self.assertEqual(
            rename_calls,
            [
                ("Academic Year", "OLD 2025-2026", "NEW 2025-2026"),
                ("School Calendar", "OLD 2025-2026", "NEW 2025-2026"),
                ("School Schedule", "OLD Weekly", "NEW Weekly"),
            ],
        )

    def test_publishing_school_seeds_default_website_pages_and_seo_profiles(self):
        organization = make_organization(prefix="Website Org")
        school = make_school(organization.name, prefix="Website School")
        school.about_snippet = "<p>A welcoming school community.</p>"
        school.more_info = "<p>More about our learning approach.</p>"
        school.school_tagline = "Curiosity with purpose"
        school.is_published = 1
        school.save(ignore_permissions=True)

        school.reload()
        self.assertTrue(bool((school.website_slug or "").strip()))
        self.assertEqual(
            frappe.db.get_value("Organization", organization.name, "default_website_school"),
            school.name,
        )

        rows = frappe.get_all(
            "School Website Page",
            filters={"school": school.name},
            fields=["route", "page_type", "seo_profile", "title", "workflow_state", "is_published"],
            order_by="route asc",
        )
        by_route = {row.route: row for row in rows}

        self.assertEqual(set(by_route), {"/", "about", "admissions", "programs"})
        self.assertEqual(by_route["admissions"].page_type, "Admissions")
        self.assertTrue(all(bool((row.seo_profile or "").strip()) for row in rows))
        self.assertTrue(all(row.workflow_state == "Published" for row in rows))
        self.assertTrue(all(int(row.is_published or 0) == 1 for row in rows))

        admissions_page = frappe.get_doc(
            "School Website Page",
            frappe.db.get_value(
                "School Website Page",
                {"school": school.name, "route": "admissions"},
                "name",
            ),
        )
        self.assertEqual(
            [row.block_type for row in admissions_page.blocks],
            ["admissions_overview", "rich_text", "admissions_steps", "faq", "admission_cta", "admission_cta"],
        )
        self.assertEqual(
            [
                frappe.parse_json(row.props).get("intent")
                for row in admissions_page.blocks
                if row.block_type == "admission_cta"
            ],
            ["inquire", "apply"],
        )

        seo_profile = frappe.get_doc("Website SEO Profile", by_route["/"].seo_profile)
        self.assertEqual(seo_profile.meta_title, school.school_name)
        self.assertEqual(
            seo_profile.canonical_url,
            frappe.utils.get_url(f"/schools/{school.website_slug}"),
        )

    def test_publishing_school_includes_visit_cta_when_visit_route_is_configured(self):
        organization = make_organization(prefix="Visit Route Org")
        school = make_school(organization.name, prefix="Visit Route School")
        school.admissions_visit_route = f"/schools/{school.name.lower().replace(' ', '-')}/visit"
        school.is_published = 1
        school.save(ignore_permissions=True)

        admissions_page = frappe.get_doc(
            "School Website Page",
            frappe.db.get_value(
                "School Website Page",
                {"school": school.name, "route": "admissions"},
                "name",
            ),
        )
        self.assertEqual(
            [
                frappe.parse_json(row.props).get("intent")
                for row in admissions_page.blocks
                if row.block_type == "admission_cta"
            ],
            ["inquire", "visit", "apply"],
        )
