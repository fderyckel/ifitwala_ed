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
        self.assertEqual(result["attachments"][1]["external_url"], "https://example.com/reference")


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
