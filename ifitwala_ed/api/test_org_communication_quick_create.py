# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from contextlib import nullcontext
from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import org_communication_quick_create


class _DummyOrgCommunicationDoc:
    def __init__(self):
        self.name = "COMM-NEW"
        self.title = None
        self.communication_type = None
        self.status = None
        self.priority = None
        self.portal_surface = None
        self.publish_from = None
        self.publish_to = None
        self.brief_start_date = None
        self.brief_end_date = None
        self.brief_order = None
        self.organization = None
        self.school = None
        self.message = None
        self.internal_note = None
        self.interaction_mode = None
        self.allow_private_notes = None
        self.allow_public_thread = None
        self.audiences = []
        self.insert_calls = 0

    def append(self, fieldname, row):
        if fieldname != "audiences":
            raise AssertionError(f"Unexpected child table: {fieldname}")
        self.audiences.append(row)

    def insert(self):
        self.insert_calls += 1
        return self


class TestOrgCommunicationQuickCreate(FrappeTestCase):
    def _create_organization(self) -> str:
        organization = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Quick Create Org {frappe.generate_hash(length=6)}",
                "abbr": f"QC{frappe.generate_hash(length=4)}",
            }
        ).insert(ignore_permissions=True)
        return organization.name

    def test_get_options_returns_context_and_reference_lists(self):
        with (
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.has_permission", return_value=True),
            patch(
                "ifitwala_ed.api.org_communication_quick_create.get_org_communication_context",
                return_value={
                    "default_school": "SCH-1",
                    "default_organization": "ORG-1",
                    "allowed_schools": ["SCH-1"],
                    "allowed_organizations": ["ORG-1"],
                    "is_privileged": False,
                    "can_select_school": True,
                    "lock_to_default_school": False,
                },
            ),
            patch(
                "ifitwala_ed.api.org_communication_quick_create._field_default",
                side_effect=lambda _doctype, fieldname: {
                    "communication_type": "Information",
                    "status": "Draft",
                    "priority": "Normal",
                    "portal_surface": "Everywhere",
                    "interaction_mode": "None",
                    "allow_private_notes": "1",
                    "allow_public_thread": "0",
                }.get(fieldname),
            ),
            patch(
                "ifitwala_ed.api.org_communication_quick_create._field_options",
                side_effect=lambda _doctype, fieldname: {
                    "communication_type": ["Information", "Reminder"],
                    "status": ["Draft", "Scheduled", "Published", "Archived"],
                    "priority": ["Low", "Normal", "High"],
                    "portal_surface": ["Desk", "Morning Brief", "Portal Feed", "Everywhere"],
                    "interaction_mode": ["None", "Staff Comments"],
                }.get(fieldname, []),
            ),
            patch(
                "ifitwala_ed.api.org_communication_quick_create._get_reference_organizations",
                return_value=[{"name": "ORG-1", "organization_name": "Root Org", "abbr": "RO"}],
            ),
            patch(
                "ifitwala_ed.api.org_communication_quick_create._get_reference_schools",
                return_value=[{"name": "SCH-1", "school_name": "Main School", "abbr": "MS", "organization": "ORG-1"}],
            ),
            patch(
                "ifitwala_ed.api.org_communication_quick_create._get_reference_teams",
                return_value=[{"name": "TEAM-1", "team_name": "Ops", "team_code": "OPS", "school": "SCH-1"}],
            ),
            patch(
                "ifitwala_ed.api.org_communication_quick_create._get_reference_student_groups",
                return_value=[
                    {
                        "name": "SG-1",
                        "student_group_name": "Grade 5",
                        "student_group_abbreviation": "G5",
                        "school": "SCH-1",
                        "group_based_on": "Course",
                    }
                ],
            ),
            patch("ifitwala_ed.api.org_communication_quick_create._user_has_any_role", return_value=False),
        ):
            payload = org_communication_quick_create.get_org_communication_quick_create_options()

        self.assertEqual(payload["context"]["default_organization"], "ORG-1")
        self.assertEqual(payload["defaults"]["portal_surface"], "Everywhere")
        self.assertEqual(payload["fields"]["statuses"], ["Draft", "Scheduled", "Published"])
        self.assertEqual(payload["references"]["organizations"][0]["name"], "ORG-1")
        self.assertEqual(payload["references"]["schools"][0]["name"], "SCH-1")
        self.assertEqual(payload["references"]["teams"][0]["name"], "TEAM-1")
        self.assertEqual(payload["references"]["student_groups"][0]["name"], "SG-1")
        self.assertFalse(payload["permissions"]["can_target_wide_school_scope"])
        self.assertNotIn("Organization", payload["fields"]["audience_target_modes"])

    def test_get_options_includes_organization_mode_for_wide_audience_roles(self):
        with (
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.has_permission", return_value=True),
            patch(
                "ifitwala_ed.api.org_communication_quick_create.get_org_communication_context",
                return_value={
                    "default_school": None,
                    "default_organization": "ORG-1",
                    "allowed_schools": [],
                    "allowed_organizations": ["ORG-1"],
                    "is_privileged": True,
                    "can_select_school": True,
                    "lock_to_default_school": False,
                },
            ),
            patch("ifitwala_ed.api.org_communication_quick_create._field_default", return_value=None),
            patch("ifitwala_ed.api.org_communication_quick_create._field_options", return_value=[]),
            patch("ifitwala_ed.api.org_communication_quick_create._get_reference_organizations", return_value=[]),
            patch("ifitwala_ed.api.org_communication_quick_create._get_reference_schools", return_value=[]),
            patch("ifitwala_ed.api.org_communication_quick_create._get_reference_teams", return_value=[]),
            patch("ifitwala_ed.api.org_communication_quick_create._get_reference_student_groups", return_value=[]),
            patch("ifitwala_ed.api.org_communication_quick_create._user_has_any_role", return_value=True),
        ):
            payload = org_communication_quick_create.get_org_communication_quick_create_options()

        self.assertIn("Organization", payload["fields"]["audience_target_modes"])
        self.assertIn("Organization", payload["recipient_rules"])

    def test_create_quick_inserts_org_communication_and_appends_audiences(self):
        doc = _DummyOrgCommunicationDoc()
        cache = Mock()
        cache.get_value.return_value = None
        cache.lock.return_value = nullcontext()

        with (
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.new_doc", return_value=doc),
        ):
            result = org_communication_quick_create.create_org_communication_quick(
                title="Staff update",
                communication_type="Information",
                status="Published",
                priority="High",
                portal_surface="Everywhere",
                organization="ORG-1",
                school="SCH-1",
                message="Important update",
                interaction_mode="Staff Comments",
                allow_private_notes=1,
                allow_public_thread=1,
                client_request_id="req-1",
                audiences=[
                    {
                        "target_mode": "School Scope",
                        "school": "SCH-1",
                        "include_descendants": 1,
                        "to_staff": 1,
                    }
                ],
            )

        self.assertEqual(result["status"], "created")
        self.assertEqual(result["name"], "COMM-NEW")
        self.assertEqual(doc.title, "Staff update")
        self.assertEqual(doc.communication_type, "Information")
        self.assertEqual(doc.status, "Published")
        self.assertEqual(doc.priority, "High")
        self.assertEqual(doc.portal_surface, "Everywhere")
        self.assertEqual(doc.organization, "ORG-1")
        self.assertEqual(doc.school, "SCH-1")
        self.assertEqual(doc.interaction_mode, "Staff Comments")
        self.assertEqual(doc.allow_private_notes, 1)
        self.assertEqual(doc.allow_public_thread, 1)
        self.assertEqual(
            doc.audiences,
            [
                {
                    "target_mode": "School Scope",
                    "school": "SCH-1",
                    "team": None,
                    "student_group": None,
                    "include_descendants": 1,
                    "note": None,
                    "to_staff": 1,
                    "to_students": 0,
                    "to_guardians": 0,
                    "to_community": 0,
                }
            ],
        )
        self.assertEqual(doc.insert_calls, 1)
        cache.set_value.assert_called_once()

    def test_create_quick_returns_cached_result_for_same_client_request_id(self):
        cache = Mock()
        cache.get_value.return_value = frappe.as_json(
            {"ok": True, "status": "created", "name": "COMM-EXISTING", "title": "Cached"}
        )

        with (
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.cache", return_value=cache),
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.new_doc") as new_doc_mock,
        ):
            result = org_communication_quick_create.create_org_communication_quick(
                title="Ignored",
                communication_type="Information",
                status="Draft",
                client_request_id="req-1",
            )

        self.assertEqual(result["status"], "already_processed")
        self.assertEqual(result["name"], "COMM-EXISTING")
        new_doc_mock.assert_not_called()

    def test_create_quick_requires_create_permission(self):
        with patch("ifitwala_ed.api.org_communication_quick_create.frappe.has_permission", return_value=False):
            with self.assertRaises(frappe.PermissionError):
                org_communication_quick_create.create_org_communication_quick(
                    title="Blocked",
                    communication_type="Information",
                    status="Draft",
                )

    def test_create_quick_allows_duplicate_visible_titles(self):
        organization = self._create_organization()
        cache = Mock()
        cache.get_value.return_value = None
        cache.lock.return_value = nullcontext()

        with (
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.api.org_communication_quick_create.frappe.cache", return_value=cache),
        ):
            first = org_communication_quick_create.create_org_communication_quick(
                title="Grade 6 Math Update",
                communication_type="Information",
                status="Draft",
                portal_surface="Desk",
                organization=organization,
                audiences=[
                    {
                        "target_mode": "Organization",
                        "to_staff": 1,
                    }
                ],
            )
            second = org_communication_quick_create.create_org_communication_quick(
                title="Grade 6 Math Update",
                communication_type="Information",
                status="Draft",
                portal_surface="Desk",
                organization=organization,
                audiences=[
                    {
                        "target_mode": "Organization",
                        "to_staff": 1,
                    }
                ],
            )

        self.assertNotEqual(first["name"], second["name"])
        self.assertEqual(first["title"], "Grade 6 Math Update")
        self.assertEqual(second["title"], "Grade 6 Math Update")

        rows = frappe.get_all(
            "Org Communication",
            filters={"organization": organization, "title": "Grade 6 Math Update"},
            fields=["name", "title"],
        )
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0]["name"], rows[1]["name"])
