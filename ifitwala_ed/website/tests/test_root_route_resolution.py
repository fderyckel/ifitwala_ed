# ifitwala_ed/website/tests/test_root_route_resolution.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website import renderer


class TestRootRouteResolution(FrappeTestCase):
    def test_build_render_context_root_returns_public_home_context(self):
        payload = {"template": "ifitwala_ed/website/templates/network_home.html"}

        with patch.object(renderer, "_build_public_home_context", return_value=payload) as mocked_home:
            context = renderer.build_render_context(route="/", preview=False)

        self.assertEqual(context, payload)
        mocked_home.assert_called_once_with(route="/")

    def test_build_render_context_school_directory_uses_directory_context(self):
        payload = {"template": "ifitwala_ed/website/templates/organization_landing.html"}

        with patch.object(renderer, "_build_school_directory_context", return_value=payload) as mocked_directory:
            context = renderer.build_render_context(route="/schools", preview=False)

        self.assertEqual(context, payload)
        mocked_directory.assert_called_once_with(route="/schools")

    def test_public_landing_payload_prefers_default_website_school_for_featured_school(self):
        brand = {
            "brand_name": "Root Org",
            "brand_logo": "/files/root-logo.png",
            "organization_name": "Root Org",
            "organization_logo": "/files/root-logo.png",
            "organization": frappe._dict({"default_website_school": "SCH-1"}),
        }
        school_cards = [
            {
                "name": "SCH-1",
                "label": "Alpha School",
                "tagline": "Default school",
                "description": "Alpha description",
                "logo": "/files/alpha.png",
                "url": "/schools/alpha",
                "organization": "Root Org",
            },
            {
                "name": "SCH-2",
                "label": "Beta School",
                "tagline": "Fallback school",
                "description": "Beta description",
                "logo": "/files/beta.png",
                "url": "/schools/beta",
                "organization": "Root Org",
            },
        ]

        with (
            patch.object(renderer, "get_public_brand_identity", return_value=brand),
            patch.object(renderer, "get_descendant_organization_names", return_value=["ORG-1"]),
            patch.object(renderer, "_get_landing_school_cards", return_value=school_cards),
            patch.object(renderer, "_get_public_program_count", return_value=7),
            patch.object(renderer.frappe, "get_doc", return_value=frappe._dict(name="SCH-1")),
            patch.object(renderer, "resolve_admissions_cta_url", return_value="/apply/inquiry"),
        ):
            payload = renderer._build_public_landing_payload(route="/")

        self.assertEqual(payload["featured_school"]["name"], "SCH-1")
        self.assertEqual(payload["school_count"], 2)
        self.assertEqual(payload["program_count"], 7)
        self.assertEqual(payload["preview_schools"][0]["name"], "SCH-1")

    def test_public_landing_payload_falls_back_to_first_school_when_default_missing(self):
        brand = {
            "brand_name": "Root Org",
            "brand_logo": "/files/root-logo.png",
            "organization_name": "Root Org",
            "organization_logo": "/files/root-logo.png",
            "organization": frappe._dict({"default_website_school": "MISSING"}),
        }
        school_cards = [
            {
                "name": "SCH-2",
                "label": "Beta School",
                "tagline": "First listed school",
                "description": "Beta description",
                "logo": "/files/beta.png",
                "url": "/schools/beta",
                "organization": "Root Org",
            }
        ]

        with (
            patch.object(renderer, "get_public_brand_identity", return_value=brand),
            patch.object(renderer, "get_descendant_organization_names", return_value=["ORG-1"]),
            patch.object(renderer, "_get_landing_school_cards", return_value=school_cards),
            patch.object(renderer, "_get_public_program_count", return_value=0),
            patch.object(renderer.frappe, "get_doc", return_value=frappe._dict(name="SCH-2")),
            patch.object(renderer, "resolve_admissions_cta_url", return_value="/apply/inquiry"),
        ):
            payload = renderer._build_public_landing_payload(route="/")

        self.assertEqual(payload["featured_school"]["name"], "SCH-2")
