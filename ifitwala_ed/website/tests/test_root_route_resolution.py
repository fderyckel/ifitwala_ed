# ifitwala_ed/website/tests/test_root_route_resolution.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website import renderer


class TestRootRouteResolution(FrappeTestCase):
    def test_build_render_context_root_returns_redirect_payload(self):
        with patch.object(renderer, "_resolve_root_redirect_url", return_value="/schools/demo"):
            context = renderer.build_render_context(route="/", preview=False)

        self.assertEqual(context.get("redirect_location"), "/schools/demo")

    def test_root_redirect_uses_default_website_school_when_valid(self):
        organization = frappe._dict(
            {
                "name": "ORG-1",
                "organization_name": "Root Org",
                "default_website_school": "SCH-1",
            }
        )
        school_row = frappe._dict(
            {
                "name": "SCH-1",
                "website_slug": "demo",
                "is_published": 1,
                "organization": "ORG-1",
            }
        )

        with (
            patch.object(renderer, "_resolve_landing_organization", return_value=organization),
            patch.object(
                renderer,
                "_get_descendant_organization_names",
                return_value=["ORG-1"],
            ),
            patch.object(renderer.frappe.db, "get_value", return_value=school_row),
        ):
            result = renderer._resolve_root_redirect_url()

        self.assertEqual(result, "/schools/demo")

    def test_root_redirect_falls_back_to_first_published_school_when_default_invalid(self):
        organization = frappe._dict(
            {
                "name": "ORG-1",
                "organization_name": "Root Org",
                "default_website_school": "SCH-1",
            }
        )
        fallback_school = frappe._dict(
            {
                "name": "SCH-2",
                "website_slug": "fallback",
            }
        )

        with (
            patch.object(renderer, "_resolve_landing_organization", return_value=organization),
            patch.object(
                renderer,
                "_get_descendant_organization_names",
                return_value=["ORG-1"],
            ),
            patch.object(
                renderer.frappe.db,
                "get_value",
                side_effect=[None, fallback_school],
            ),
        ):
            result = renderer._resolve_root_redirect_url()

        self.assertEqual(result, "/schools/fallback")

    def test_root_redirect_falls_back_to_school_discovery_when_no_school_available(self):
        organization = frappe._dict(
            {
                "name": "ORG-1",
                "organization_name": "Root Org",
                "default_website_school": "",
            }
        )

        with (
            patch.object(renderer, "_resolve_landing_organization", return_value=organization),
            patch.object(
                renderer,
                "_get_descendant_organization_names",
                return_value=["ORG-1"],
            ),
            patch.object(renderer.frappe.db, "get_value", return_value=None),
        ):
            result = renderer._resolve_root_redirect_url()

        self.assertEqual(result, "/schools")
