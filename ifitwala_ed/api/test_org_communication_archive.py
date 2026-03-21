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
        )
        self.assertEqual(result["message"], "<p><strong>Full body</strong></p>")
        self.assertEqual(result["audience_label"], "Staff · ISS")
        self.assertEqual(result["audience_summary"], audience_summary)
