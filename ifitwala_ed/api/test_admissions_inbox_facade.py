# ifitwala_ed/api/test_admissions_inbox_facade.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import admissions_inbox


class TestAdmissionsInboxFacade(TestCase):
    def test_inbox_context_endpoint_remains_whitelisted(self):
        self.assertIn(admissions_inbox.get_admissions_inbox_context, frappe.whitelisted)
        self.assertIn(admissions_inbox.search_admissions_inbox_assignees, frappe.whitelisted)

    def test_inbox_context_delegates_to_domain_implementation(self):
        with patch(
            "ifitwala_ed.api.admissions_inbox.get_admissions_inbox_context_impl",
            return_value={"queues": []},
        ) as impl:
            self.assertEqual(
                admissions_inbox.get_admissions_inbox_context(
                    organization="ORG-1",
                    school="SCH-1",
                    limit="20",
                ),
                {"queues": []},
            )

        impl.assert_called_once_with(organization="ORG-1", school="SCH-1", limit="20")

    def test_assignee_search_delegates_to_domain_implementation(self):
        with patch(
            "ifitwala_ed.api.admissions_inbox.search_admissions_inbox_assignees_impl",
            return_value=[{"value": "staff@example.com"}],
        ) as impl:
            self.assertEqual(
                admissions_inbox.search_admissions_inbox_assignees(
                    context_doctype="Inquiry",
                    context_name="INQ-1",
                    organization="ORG-1",
                    school="SCH-1",
                    assignment_lane="Staff",
                    query="staff",
                    limit="20",
                ),
                [{"value": "staff@example.com"}],
            )

        impl.assert_called_once_with(
            context_doctype="Inquiry",
            context_name="INQ-1",
            organization="ORG-1",
            school="SCH-1",
            assignment_lane="Staff",
            query="staff",
            limit="20",
        )
