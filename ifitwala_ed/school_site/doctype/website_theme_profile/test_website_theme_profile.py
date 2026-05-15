# ifitwala_ed/school_site/doctype/website_theme_profile/test_website_theme_profile.py

# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_site.doctype.website_theme_profile.website_theme_profile import (
    THEME_PRESET_RECORDS,
    build_scope_filters,
    ensure_theme_profile_presets,
    normalize_hex_color,
    normalize_scope_type,
)


class TestWebsiteThemeProfile(FrappeTestCase):
    def test_normalize_scope_type_defaults_to_global(self):
        self.assertEqual(normalize_scope_type(None), "Global")

    def test_normalize_scope_type_rejects_invalid_scope(self):
        with self.assertRaises(frappe.ValidationError):
            normalize_scope_type("Regional")

    def test_build_scope_filters_school(self):
        filters = build_scope_filters(
            scope_type="School",
            school="SCH-0001",
        )
        self.assertEqual(
            filters,
            {
                "scope_type": "School",
                "school": "SCH-0001",
            },
        )

    def test_normalize_hex_color_rejects_invalid_value(self):
        with self.assertRaises(frappe.ValidationError):
            normalize_hex_color("rgb(10, 20, 30)", field_label="Primary Color")

    def test_ensure_theme_profile_presets_is_idempotent(self):
        ensure_theme_profile_presets()
        ensure_theme_profile_presets()

        for row in THEME_PRESET_RECORDS:
            records = frappe.get_all(
                "Website Theme Profile",
                filters={
                    "profile_name": row["profile_name"],
                    "scope_type": row["scope_type"],
                },
                fields=["name"],
            )
            self.assertEqual(len(records), 1)
