from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.normalize_default_website_staff_showcase import (
    _looks_like_legacy_default_showcase_props,
)


class TestNormalizeDefaultWebsiteStaffShowcase(FrappeTestCase):
    def test_detects_legacy_home_showcase_props(self):
        self.assertTrue(
            _looks_like_legacy_default_showcase_props(
                route="/",
                props={
                    "title": "Leadership & Administration",
                    "roles": ["Head", "Principal"],
                    "limit": 6,
                },
            )
        )

    def test_rejects_customized_showcase_props(self):
        self.assertFalse(
            _looks_like_legacy_default_showcase_props(
                route="about",
                props={
                    "title": "Leadership & Administration",
                    "roles": ["Head", "Principal"],
                    "limit": 12,
                    "staff_limit": 14,
                },
            )
        )
