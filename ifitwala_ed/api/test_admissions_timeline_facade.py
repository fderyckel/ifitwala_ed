# ifitwala_ed/api/test_admissions_timeline_facade.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import admissions_timeline


class TestAdmissionsTimelineFacade(TestCase):
    def test_timeline_context_endpoint_remains_whitelisted(self):
        self.assertIn(admissions_timeline.get_admissions_timeline_context, frappe.whitelisted)

    def test_timeline_context_delegates_to_domain_implementation(self):
        with patch(
            "ifitwala_ed.api.admissions_timeline.get_admissions_timeline_context_impl",
            return_value={"items": []},
        ) as impl:
            self.assertEqual(
                admissions_timeline.get_admissions_timeline_context(
                    context_doctype="Student Applicant",
                    context_name="APP-1",
                    limit="30",
                ),
                {"items": []},
            )

        impl.assert_called_once_with(
            context_doctype="Student Applicant",
            context_name="APP-1",
            limit="30",
        )
