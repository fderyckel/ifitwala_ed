# ifitwala_ed/school_site/doctype/program_website_profile/test_program_website_profile.py

# Copyright (c) 2026, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_site.doctype.program_website_profile.program_website_profile import (
    compute_program_profile_status,
    normalize_workflow_state,
)


class TestProgramWebsiteProfile(FrappeTestCase):
    def test_workflow_state_normalization_rejects_invalid_state(self):
        with self.assertRaises(frappe.ValidationError):
            normalize_workflow_state("Invalid State")

    def test_program_profile_status_requires_workflow_published(self):
        status = compute_program_profile_status(
            school_is_public=True,
            program_is_published=True,
            has_program_slug=True,
            workflow_state="Approved",
        )
        self.assertEqual(status, "Draft")

    def test_program_profile_status_requires_school_and_program_readiness(self):
        status = compute_program_profile_status(
            school_is_public=False,
            program_is_published=False,
            has_program_slug=False,
            workflow_state="Published",
        )
        self.assertEqual(status, "Draft")

    def test_program_profile_status_respects_publication_window(self):
        status = compute_program_profile_status(
            school_is_public=True,
            program_is_published=True,
            has_program_slug=True,
            workflow_state="Published",
            publish_at="2099-01-01 08:00:00",
        )
        self.assertEqual(status, "Draft")
