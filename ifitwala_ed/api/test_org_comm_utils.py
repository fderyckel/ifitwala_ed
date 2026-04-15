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

    def test_check_audience_match_allows_academic_admin_student_group_filter_without_staff_recipient_overlap(self):
        audiences = [
            frappe._dict(
                target_mode="Student Group",
                school=None,
                include_descendants=0,
                team=None,
                student_group="SG-1",
                to_staff=0,
                to_students=1,
                to_guardians=1,
            )
        ]

        with patch.object(org_comm_utils.frappe, "get_all", return_value=audiences):
            matched = org_comm_utils.check_audience_match(
                "COMM-SG",
                "academic-admin@example.com",
                ["Academic Admin"],
                frappe._dict(name="EMP-1", organization="ORG-1", school="SCH-1"),
                filter_student_group="SG-1",
            )

        self.assertTrue(matched)

    def test_check_audience_match_allows_student_member_on_student_group_row(self):
        audiences = [
            frappe._dict(
                target_mode="Student Group",
                school=None,
                include_descendants=0,
                team=None,
                student_group="SG-1",
                to_staff=0,
                to_students=1,
                to_guardians=0,
            )
        ]

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch(
                "ifitwala_ed.api.org_comm_utils._get_cached_portal_student_context",
                return_value={"student_name": "STU-1", "student_groups": {"SG-1"}, "school_names": {"SCH-1"}},
            ),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-STUDENT",
                "student@example.com",
                ["Student"],
                frappe._dict(),
            )

        self.assertTrue(matched)

    def test_check_audience_match_student_group_filter_respects_student_recipient_flag(self):
        audiences = [
            frappe._dict(
                target_mode="Student Group",
                school=None,
                include_descendants=0,
                team=None,
                student_group="SG-1",
                to_staff=0,
                to_students=0,
                to_guardians=1,
            )
        ]

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch(
                "ifitwala_ed.api.org_comm_utils._get_cached_portal_student_context",
                return_value={"student_name": "STU-1", "student_groups": {"SG-1"}, "school_names": {"SCH-1"}},
            ),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-STUDENT",
                "student@example.com",
                ["Student"],
                frappe._dict(),
                filter_student_group="SG-1",
            )

        self.assertFalse(matched)

    def test_check_audience_match_allows_guardian_member_on_student_group_row(self):
        audiences = [
            frappe._dict(
                target_mode="Student Group",
                school=None,
                include_descendants=0,
                team=None,
                student_group="SG-1",
                to_staff=0,
                to_students=0,
                to_guardians=1,
            )
        ]

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch(
                "ifitwala_ed.api.org_comm_utils._get_cached_guardian_context",
                return_value={
                    "guardian_name": "GRD-0001",
                    "student_names": {"STU-1"},
                    "student_groups": {"SG-1"},
                    "school_names": {"SCH-1"},
                },
            ),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-GUARDIAN",
                "guardian@example.com",
                ["Guardian"],
                frappe._dict(),
            )

        self.assertTrue(matched)

    def test_check_audience_match_allows_academic_admin_descendant_school_scope(self):
        audiences = [
            frappe._dict(
                target_mode="School Scope",
                school="SCH-CHILD",
                include_descendants=0,
                team=None,
                student_group=None,
                to_staff=1,
                to_students=0,
                to_guardians=0,
            )
        ]

        with patch.object(org_comm_utils.frappe, "get_all", return_value=audiences):
            matched = org_comm_utils.check_audience_match(
                "COMM-SCHOOL",
                "academic-admin@example.com",
                ["Academic Admin"],
                frappe._dict(
                    name="EMP-1",
                    organization="ORG-1",
                    school="SCH-PARENT",
                    school_names=["SCH-PARENT", "SCH-CHILD"],
                ),
            )

        self.assertTrue(matched)

    def test_check_audience_match_allows_academic_admin_school_scope_without_staff_recipient_overlap(self):
        audiences = [
            frappe._dict(
                target_mode="School Scope",
                school="SCH-CHILD",
                include_descendants=0,
                team=None,
                student_group=None,
                to_staff=0,
                to_students=1,
                to_guardians=1,
            )
        ]

        with patch.object(org_comm_utils.frappe, "get_all", return_value=audiences):
            matched = org_comm_utils.check_audience_match(
                "COMM-SCHOOL",
                "academic-admin@example.com",
                ["Academic Admin"],
                frappe._dict(
                    name="EMP-1",
                    organization="ORG-1",
                    school="SCH-PARENT",
                    school_names=["SCH-PARENT", "SCH-CHILD"],
                ),
            )

        self.assertTrue(matched)

    def test_check_audience_match_allows_academic_admin_student_group_without_filter(self):
        audiences = [
            frappe._dict(
                target_mode="Student Group",
                school=None,
                include_descendants=0,
                team=None,
                student_group="SG-1",
                to_staff=0,
                to_students=1,
                to_guardians=1,
            )
        ]

        def fake_cached_value(doctype, name, fieldname):
            if (doctype, name, fieldname) == ("Student Group", "SG-1", "school"):
                return "SCH-CHILD"
            return None

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch.object(org_comm_utils.frappe, "get_cached_value", side_effect=fake_cached_value),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-SG",
                "academic-admin@example.com",
                ["Academic Admin"],
                frappe._dict(
                    name="EMP-1",
                    organization="ORG-1",
                    school="SCH-PARENT",
                    school_names=["SCH-PARENT", "SCH-CHILD"],
                ),
            )

        self.assertTrue(matched)

    def test_check_audience_match_rejects_academic_admin_student_group_outside_school_scope(self):
        audiences = [
            frappe._dict(
                target_mode="Student Group",
                school=None,
                include_descendants=0,
                team=None,
                student_group="SG-OUT",
                to_staff=0,
                to_students=1,
                to_guardians=1,
            )
        ]

        def fake_cached_value(doctype, name, fieldname):
            if (doctype, name, fieldname) == ("Student Group", "SG-OUT", "school"):
                return "SCH-OUT"
            return None

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch.object(org_comm_utils.frappe, "get_cached_value", side_effect=fake_cached_value),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-SG",
                "academic-admin@example.com",
                ["Academic Admin"],
                frappe._dict(
                    name="EMP-1",
                    organization="ORG-1",
                    school="SCH-PARENT",
                    school_names=["SCH-PARENT", "SCH-CHILD"],
                ),
                filter_student_group="SG-OUT",
            )

        self.assertFalse(matched)

    def test_check_audience_match_allows_academic_admin_child_organization_scope(self):
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
            )
        ]

        with (
            patch.object(org_comm_utils.frappe, "get_all", return_value=audiences),
            patch.object(org_comm_utils.frappe, "get_cached_value", return_value="ORG-CHILD"),
        ):
            matched = org_comm_utils.check_audience_match(
                "COMM-ORG",
                "academic-admin@example.com",
                ["Academic Admin"],
                frappe._dict(
                    name="EMP-1",
                    organization="ORG-PARENT",
                    school=None,
                    organization_names=["ORG-PARENT", "ORG-CHILD"],
                ),
            )

        self.assertTrue(matched)
