# ifitwala_ed/school_site/doctype/website_snippet/test_website_snippet.py

# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_site.doctype.website_snippet.website_snippet import (
    build_scope_uniqueness_filters,
    normalize_scope_type,
)


class TestWebsiteSnippet(FrappeTestCase):
    def test_normalize_scope_type_defaults_to_global(self):
        self.assertEqual(normalize_scope_type(None), "Global")

    def test_normalize_scope_type_rejects_invalid_scope(self):
        with self.assertRaises(frappe.ValidationError):
            normalize_scope_type("Invalid")

    def test_build_scope_uniqueness_filters_global(self):
        filters = build_scope_uniqueness_filters(
            snippet_id="WELCOME",
            scope_type="Global",
        )
        self.assertEqual(filters, {"snippet_id": "WELCOME", "scope_type": "Global"})

    def test_build_scope_uniqueness_filters_organization(self):
        filters = build_scope_uniqueness_filters(
            snippet_id="WELCOME",
            scope_type="Organization",
            organization="ORG-0001",
        )
        self.assertEqual(
            filters,
            {
                "snippet_id": "WELCOME",
                "scope_type": "Organization",
                "organization": "ORG-0001",
            },
        )

    def test_build_scope_uniqueness_filters_school(self):
        filters = build_scope_uniqueness_filters(
            snippet_id="WELCOME",
            scope_type="School",
            school="SCH-0001",
        )
        self.assertEqual(
            filters,
            {
                "snippet_id": "WELCOME",
                "scope_type": "School",
                "school": "SCH-0001",
            },
        )
