# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import org_comm_utils


class TestOrgCommUtils(FrappeTestCase):
    def test_check_audience_match_allows_owner_when_opted_in_without_scope_filters(self):
        with patch.object(org_comm_utils.frappe, "get_cached_value", return_value="teacher@example.com"):
            matched = org_comm_utils.check_audience_match(
                "COMM-OWNER",
                "teacher@example.com",
                ["Instructor"],
                frappe._dict(name="EMP-1", organization="ORG-1", school="SCH-1"),
                allow_owner=True,
            )

        self.assertTrue(matched)

    def test_check_audience_match_owner_override_respects_explicit_scope_filters(self):
        with (
            patch.object(org_comm_utils.frappe, "get_cached_value", return_value="teacher@example.com"),
            patch.object(org_comm_utils.frappe, "get_all", return_value=[]),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-OWNER",
                "teacher@example.com",
                ["Instructor"],
                frappe._dict(name="EMP-1", organization="ORG-1", school="SCH-1"),
                filter_student_group="SG-1",
                allow_owner=True,
            )

        self.assertFalse(matched)

    def test_check_audience_match_allows_schoolless_staff_on_organization_row(self):
        audiences = [
            frappe._dict(
                target_mode="Organization",
                school=None,
                include_descendants=0,
                team=None,
                student_group=None,
                to_staff=1,
                to_students=0,
                to_guardians=0,
                to_community=0,
            )
        ]

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch.object(org_comm_utils.frappe, "get_cached_value", return_value="ORG-ROOT"),
            patch("ifitwala_ed.api.org_comm_utils.get_ancestor_organizations", return_value=["ORG-CHILD", "ORG-ROOT"]),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-ORG",
                "accounting@example.com",
                ["Employee"],
                frappe._dict(name="EMP-1", organization="ORG-CHILD", school=None),
            )

        self.assertTrue(matched)

    def test_check_audience_match_rejects_staff_outside_organization_row(self):
        audiences = [
            frappe._dict(
                target_mode="Organization",
                school=None,
                include_descendants=0,
                team=None,
                student_group=None,
                to_staff=1,
                to_students=0,
                to_guardians=0,
                to_community=0,
            )
        ]

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch.object(org_comm_utils.frappe, "get_cached_value", return_value="ORG-ROOT"),
            patch("ifitwala_ed.api.org_comm_utils.get_ancestor_organizations", return_value=["ORG-SIBLING"]),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-ORG",
                "marketing@example.com",
                ["Employee"],
                frappe._dict(name="EMP-2", organization="ORG-SIBLING", school=None),
            )

        self.assertFalse(matched)
