from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import org_communication_archive


class TestOrgCommunicationArchiveItem(FrappeTestCase):
    def test_get_item_uses_user_linked_employee_scope(self):
        audience_summary = {
            "primary": {
                "scope_type": "School",
                "scope_value": "ISS",
                "scope_label": "International Secondary School",
                "recipients": ["Staff"],
                "include_descendants": 0,
            },
            "chips": [{"type": "recipient", "label": "Staff"}, {"type": "scope", "label": "ISS"}],
            "meta": {"audience_rows": 1, "recipient_count": 1, "has_multiple_audiences": 0},
        }

        def fake_employee_lookup(doctype, filters, fields=None, as_dict=False):
            self.assertEqual(doctype, "Employee")
            self.assertEqual(filters, {"user_id": "staff@example.com"})
            self.assertEqual(fields, ["name", "school", "organization"])
            self.assertTrue(as_dict)
            return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}

        doc = SimpleNamespace(
            name="COMM-0001",
            title="Policy update",
            message="<p><strong>Full body</strong></p>",
            communication_type="Policy Procedure",
            priority="Normal",
            publish_from="2026-03-09 08:00:00",
            activity_program_offering=None,
            activity_booking=None,
            activity_student_group=None,
            get=lambda fieldname: (
                [
                    SimpleNamespace(
                        name="row-file",
                        section_break_sbex="Lesson PDF",
                        file="/private/files/policy.pdf",
                        external_url=None,
                        description=None,
                        file_name="policy.pdf",
                        file_size=2048,
                    ),
                    SimpleNamespace(
                        name="row-link",
                        section_break_sbex="Reference link",
                        file=None,
                        external_url="https://example.com/reference",
                        description=None,
                        file_name=None,
                        file_size=None,
                    ),
                ]
                if fieldname == "attachments"
                else []
            ),
        )

        with (
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.session", frappe._dict({"user": "staff@example.com"})
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.org_communication_archive.frappe.db.get_value", side_effect=fake_employee_lookup),
            patch(
                "ifitwala_ed.api.org_communication_archive.check_audience_match", return_value=True
            ) as audience_match_mock,
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_doc", return_value=doc),
            patch("ifitwala_ed.api.org_communication_archive.get_audience_label", return_value="Staff · ISS"),
            patch(
                "ifitwala_ed.api.org_communication_archive.build_audience_summary",
                return_value=audience_summary,
            ),
        ):
            result = org_communication_archive.get_org_communication_item("COMM-0001")

        audience_match_mock.assert_called_once_with(
            "COMM-0001",
            "staff@example.com",
            ["Academic Staff"],
            {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"},
            allow_owner=True,
        )
        self.assertEqual(result["message_html"], "<p><strong>Full body</strong></p>")
        self.assertEqual(result["audience_label"], "Staff · ISS")
        self.assertEqual(result["audience_summary"], audience_summary)
        self.assertEqual(result["attachments"][0]["row_name"], "row-file")
        self.assertEqual(
            result["attachments"][0]["open_url"],
            "/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?org_communication=COMM-0001&row_name=row-file",
        )
        self.assertEqual(
            result["attachments"][0]["preview_url"],
            "/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?org_communication=COMM-0001&row_name=row-file",
        )
        self.assertEqual(result["attachments"][1]["external_url"], "https://example.com/reference")

    def test_get_item_enriches_academic_admin_with_archive_scope(self):
        doc = SimpleNamespace(
            name="COMM-0002",
            title="Parent school update",
            message="<p>Visible to descendant schools</p>",
            communication_type="Information",
            priority="Normal",
            publish_from="2026-03-09 08:00:00",
            activity_program_offering=None,
            activity_booking=None,
            activity_student_group=None,
            get=lambda fieldname: [],
        )

        with (
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.session",
                frappe._dict({"user": "academic-admin@example.com"}),
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.db.get_value",
                return_value={"name": "EMP-1", "school": "SCH-PARENT", "organization": "ORG-ROOT"},
            ),
            patch(
                "ifitwala_ed.api.org_communication_archive._get_scope",
                return_value=("ORG-ROOT", "SCH-PARENT", ["ORG-ROOT", "ORG-CHILD"], ["SCH-PARENT", "SCH-CHILD"]),
            ),
            patch(
                "ifitwala_ed.api.org_communication_archive.check_audience_match", return_value=True
            ) as audience_match_mock,
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_doc", return_value=doc),
            patch("ifitwala_ed.api.org_communication_archive.get_audience_label", return_value="Staff · SCH"),
            patch("ifitwala_ed.api.org_communication_archive.build_audience_summary", return_value={}),
        ):
            org_communication_archive.get_org_communication_item("COMM-0002")

        audience_match_mock.assert_called_once_with(
            "COMM-0002",
            "academic-admin@example.com",
            ["Academic Admin"],
            {
                "name": "EMP-1",
                "school": "SCH-PARENT",
                "organization": "ORG-ROOT",
                "school_names": ["SCH-PARENT", "SCH-CHILD"],
            },
            allow_owner=True,
        )


class TestOrgCommunicationArchiveFeed(FrappeTestCase):
    def test_get_feed_student_group_filter_prefilters_exact_group_scope(self):
        captured = {}

        def fake_sql(query, values=None, as_dict=False):
            captured["query"] = query
            captured["values"] = values or {}
            self.assertTrue(as_dict)
            return [
                frappe._dict(
                    name="COMM-0002",
                    title="Group update",
                    message="<p>Hello group</p>",
                    communication_type="Class Announcement",
                    status="Published",
                    priority="Normal",
                    portal_surface="Everywhere",
                    school="SCH-1",
                    organization="ORG-1",
                    publish_from="2026-04-08 08:00:00",
                    publish_to=None,
                    brief_start_date=None,
                    brief_end_date=None,
                    interaction_mode="Comments",
                    allow_private_notes=0,
                    allow_public_thread=1,
                    activity_program_offering=None,
                    activity_booking=None,
                    activity_student_group="SG-1",
                )
            ]

        with (
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.session", frappe._dict({"user": "staff@example.com"})
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.db.get_value",
                return_value={"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"},
            ),
            patch(
                "ifitwala_ed.api.org_communication_archive._get_scope",
                return_value=("ORG-1", "SCH-1", [], []),
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.db.sql", side_effect=fake_sql),
            patch("ifitwala_ed.api.org_communication_archive.check_audience_match", return_value=True) as match_mock,
            patch("ifitwala_ed.api.org_communication_archive.get_audience_label", return_value="Students · SG-1"),
            patch("ifitwala_ed.api.org_communication_archive.build_audience_summary", return_value={}),
        ):
            result = org_communication_archive.get_org_communication_feed(
                filters={"student_group": "SG-1"},
                start=0,
                page_length=10,
            )

        self.assertIn("activity_student_group = %(filter_student_group)s", captured["query"])
        self.assertIn("a.target_mode = 'Student Group'", captured["query"])
        self.assertEqual(captured["values"]["filter_student_group"], "SG-1")
        match_mock.assert_called_once_with(
            "COMM-0002",
            "staff@example.com",
            ["Academic Admin"],
            {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"},
            filter_team=None,
            filter_student_group="SG-1",
            filter_school=None,
            allow_owner=True,
        )
        self.assertEqual([item["name"] for item in result["items"]], ["COMM-0002"])

    def test_get_feed_keeps_parent_organization_candidates_for_organization_audience(self):
        captured = {}

        def fake_sql(query, values=None, as_dict=False):
            captured["query"] = query
            captured["values"] = values or {}
            self.assertTrue(as_dict)
            return [
                frappe._dict(
                    name="COMM-ROOT",
                    title="Org-wide update",
                    message="<p>Hello staff</p>",
                    communication_type="Information",
                    status="Published",
                    priority="Normal",
                    portal_surface="Everywhere",
                    school=None,
                    organization="ORG-ROOT",
                    publish_from="2026-04-08 08:00:00",
                    publish_to=None,
                    brief_start_date=None,
                    brief_end_date=None,
                    interaction_mode="None",
                    allow_private_notes=0,
                    allow_public_thread=0,
                    activity_program_offering=None,
                    activity_booking=None,
                    activity_student_group=None,
                )
            ]

        with (
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.session", frappe._dict({"user": "staff@example.com"})
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_roles", return_value=["Academic Staff"]),
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.db.get_value",
                return_value={"name": "EMP-1", "school": None, "organization": "ORG-CHILD"},
            ),
            patch(
                "ifitwala_ed.api.org_communication_archive._get_scope",
                return_value=("ORG-CHILD", None, ["ORG-CHILD"], []),
            ),
            patch(
                "ifitwala_ed.api.org_communication_archive.get_ancestor_organizations",
                return_value=["ORG-CHILD", "ORG-ROOT"],
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.db.sql", side_effect=fake_sql),
            patch("ifitwala_ed.api.org_communication_archive.check_audience_match", return_value=True),
            patch("ifitwala_ed.api.org_communication_archive.get_audience_label", return_value="Staff · ORG"),
            patch("ifitwala_ed.api.org_communication_archive.build_audience_summary", return_value={}),
        ):
            result = org_communication_archive.get_org_communication_feed(start=0, page_length=10)

        self.assertIn("organization IN %(org_guard)s", captured["query"])
        self.assertEqual(set(captured["values"]["org_guard"]), {"ORG-CHILD", "ORG-ROOT"})
        self.assertEqual([item["name"] for item in result["items"]], ["COMM-ROOT"])


class TestOrgCommunicationArchiveContext(FrappeTestCase):
    def test_get_archive_context_lists_parent_organizations_for_child_org_user(self):
        def fake_employee_lookup(doctype, filters, fields=None, as_dict=False):
            if doctype == "Employee":
                self.assertEqual(filters, {"user_id": "staff@example.com"})
                self.assertEqual(fields, ["name", "school", "organization"])
                self.assertTrue(as_dict)
                return {"name": "EMP-1", "school": None, "organization": "ORG-CHILD"}
            if doctype == "Instructor":
                self.assertEqual(filters, {"employee": "EMP-1"})
                self.assertEqual(fields, "name")
                return None
            raise AssertionError(f"Unexpected get_value call: {doctype} {filters} {fields}")

        with (
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.session", frappe._dict({"user": "staff@example.com"})
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_roles", return_value=["Academic Staff"]),
            patch("ifitwala_ed.api.org_communication_archive.frappe.db.get_value", side_effect=fake_employee_lookup),
            patch(
                "ifitwala_ed.api.org_communication_archive._get_scope",
                return_value=("ORG-CHILD", None, ["ORG-CHILD"], []),
            ),
            patch(
                "ifitwala_ed.api.org_communication_archive.get_ancestor_organizations",
                return_value=["ORG-CHILD", "ORG-ROOT"],
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.db.sql", return_value=[]),
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.get_all",
                side_effect=[
                    [
                        {"name": "ORG-ROOT", "organization_name": "Root Org", "abbr": "ROOT"},
                        {"name": "ORG-CHILD", "organization_name": "Child Org", "abbr": "CHILD"},
                    ],
                    [],
                ],
            ),
        ):
            result = org_communication_archive.get_archive_context()

        self.assertEqual(
            [row["name"] for row in result["organizations"]],
            ["ORG-ROOT", "ORG-CHILD"],
        )
        self.assertEqual(
            result["defaults"],
            {"school": None, "organization": None, "team": None},
        )
        self.assertEqual(result["base_org"], "ORG-CHILD")
        self.assertEqual(result["base_school"], None)

    def test_get_archive_context_defaults_academic_admin_to_employee_org_and_school(self):
        def fake_employee_lookup(doctype, filters, fields=None, as_dict=False):
            self.assertEqual(doctype, "Employee")
            self.assertEqual(filters, {"user_id": "academic-admin@example.com"})
            self.assertEqual(fields, ["name", "school", "organization"])
            self.assertTrue(as_dict)
            return {"name": "EMP-1", "school": "SCH-1", "organization": "ORG-1"}

        with (
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.session",
                frappe._dict({"user": "academic-admin@example.com"}),
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.api.org_communication_archive.frappe.db.get_value", side_effect=fake_employee_lookup),
            patch(
                "ifitwala_ed.api.org_communication_archive._get_scope",
                return_value=("ORG-1", "SCH-1", ["ORG-1"], ["SCH-1", "SCH-2"]),
            ),
            patch("ifitwala_ed.api.org_communication_archive.frappe.db.sql", return_value=[]),
            patch(
                "ifitwala_ed.api.org_communication_archive.frappe.get_all",
                side_effect=[
                    [
                        {
                            "name": "SG-1",
                            "student_group_abbreviation": "G1",
                            "student_group_name": "Group 1",
                            "school": "SCH-1",
                        },
                        {
                            "name": "SG-2",
                            "student_group_abbreviation": "G2",
                            "student_group_name": "Group 2",
                            "school": "SCH-2",
                        },
                    ],
                    [{"name": "ORG-1", "organization_name": "Org 1", "abbr": "ORG"}],
                    [
                        {"name": "SCH-1", "school_name": "School 1", "abbr": "S1", "organization": "ORG-1"},
                        {"name": "SCH-2", "school_name": "School 2", "abbr": "S2", "organization": "ORG-1"},
                    ],
                ],
            ),
        ):
            result = org_communication_archive.get_archive_context()

        self.assertEqual(
            result["defaults"],
            {"school": "SCH-1", "organization": "ORG-1", "team": None},
        )
        self.assertEqual(
            [row["value"] for row in result["my_groups"]],
            ["SG-1", "SG-2"],
        )
