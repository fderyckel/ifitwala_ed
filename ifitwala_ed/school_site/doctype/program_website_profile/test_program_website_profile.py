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
			program_is_published=True,
			workflow_state="Approved",
		)
		self.assertEqual(status, "Draft")

	def test_program_profile_status_requires_program_published(self):
		status = compute_program_profile_status(
			program_is_published=False,
			workflow_state="Published",
		)
		self.assertEqual(status, "Draft")
