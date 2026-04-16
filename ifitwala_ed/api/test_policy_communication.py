# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import policy_communication


class _DummyOrgCommunicationDoc:
    def __init__(self, payload):
        self.name = "COMM-POLICY"
        self.title = payload.get("title")
        self.status = payload.get("status")
        self.school = payload.get("school")
        self.organization = payload.get("organization")
        self.audiences = payload.get("audiences") or []

    def insert(self):
        return self


class TestPolicyCommunication(FrappeTestCase):
    def test_create_policy_amendment_communication_supports_organization_staff_scope(self):
        captured = {}

        def fake_get_doc(payload):
            captured["payload"] = payload
            return _DummyOrgCommunicationDoc(payload)

        policy_row = {
            "policy_version": "PV-001",
            "policy_title": "Employee Handbook",
            "version_label": "v2",
            "policy_organization": "ORG-ROOT",
            "policy_school": "",
            "based_on_version": None,
            "applies_to_tokens": ["Staff"],
        }

        with (
            patch("ifitwala_ed.api.policy_communication.ensure_policy_admin"),
            patch("ifitwala_ed.api.policy_communication._policy_row", return_value=policy_row),
            patch.object(policy_communication.frappe, "get_doc", side_effect=fake_get_doc),
        ):
            result = policy_communication.create_policy_amendment_communication(
                policy_version="PV-001",
                title="Employee Handbook update",
                message_html="<p>Updated</p>",
                target_scope="Organization Staff",
                brief_start_date="2026-03-26",
                brief_end_date="2026-04-01",
                publish_from="2026-03-26 08:00:00",
                publish_to="2026-04-02 08:00:00",
                to_staff=1,
                to_students=0,
                to_guardians=0,
            )

        self.assertEqual(result["target_scope"], policy_communication.SCOPE_ORGANIZATION_STAFF)
        self.assertEqual(result["school"], "")
        self.assertEqual(captured["payload"]["school"], "")
        self.assertEqual(captured["payload"]["organization"], "ORG-ROOT")
        self.assertEqual(
            captured["payload"]["audiences"],
            [
                {
                    "target_mode": "Organization",
                    "to_staff": 1,
                    "to_students": 0,
                    "to_guardians": 0,
                }
            ],
        )

    def test_create_policy_amendment_communication_rejects_non_staff_organization_staff_scope(self):
        policy_row = {
            "policy_version": "PV-001",
            "policy_title": "Employee Handbook",
            "version_label": "v2",
            "policy_organization": "ORG-ROOT",
            "policy_school": "",
            "based_on_version": None,
            "applies_to_tokens": ["Staff"],
        }

        with (
            patch("ifitwala_ed.api.policy_communication.ensure_policy_admin"),
            patch("ifitwala_ed.api.policy_communication._policy_row", return_value=policy_row),
        ):
            with self.assertRaises(frappe.ValidationError):
                policy_communication.create_policy_amendment_communication(
                    policy_version="PV-001",
                    title="Employee Handbook update",
                    message_html="<p>Updated</p>",
                    target_scope="Organization Staff",
                    brief_start_date="2026-03-26",
                    brief_end_date="2026-04-01",
                    publish_from="2026-03-26 08:00:00",
                    publish_to="2026-04-02 08:00:00",
                    to_staff=1,
                    to_students=1,
                    to_guardians=0,
                )

    def test_create_policy_amendment_communication_preserves_school_fanout_scope(self):
        captured = {}

        def fake_get_doc(payload):
            captured["payload"] = payload
            return _DummyOrgCommunicationDoc(payload)

        policy_row = {
            "policy_version": "PV-002",
            "policy_title": "Attendance Policy",
            "version_label": "v3",
            "policy_organization": "ORG-ROOT",
            "policy_school": "",
            "based_on_version": None,
            "applies_to_tokens": ["Staff", "Student"],
        }

        with (
            patch("ifitwala_ed.api.policy_communication.ensure_policy_admin"),
            patch("ifitwala_ed.api.policy_communication._policy_row", return_value=policy_row),
            patch("ifitwala_ed.api.policy_communication._get_organization_schools", return_value=["SCH-A", "SCH-B"]),
            patch.object(policy_communication.frappe, "get_doc", side_effect=fake_get_doc),
        ):
            result = policy_communication.create_policy_amendment_communication(
                policy_version="PV-002",
                title="Attendance Policy update",
                message_html="<p>Updated</p>",
                target_scope="Schools in Organization",
                brief_start_date="2026-03-26",
                brief_end_date="2026-04-01",
                publish_from="2026-03-26 08:00:00",
                publish_to="2026-04-02 08:00:00",
                to_staff=1,
                to_students=1,
                to_guardians=0,
            )

        self.assertEqual(result["target_scope"], policy_communication.SCOPE_ORGANIZATION_ALL_SCHOOLS)
        self.assertEqual(result["school"], "")
        self.assertEqual(captured["payload"]["school"], "")
        self.assertEqual(len(captured["payload"]["audiences"]), 2)
        self.assertEqual(captured["payload"]["audiences"][0]["target_mode"], "School Scope")

    def test_create_policy_amendment_communication_includes_descendant_organization_schools(self):
        captured = {}

        def fake_get_doc(payload):
            captured["payload"] = payload
            return _DummyOrgCommunicationDoc(payload)

        policy_row = {
            "policy_version": "PV-ORG",
            "policy_title": "Parent Policy",
            "version_label": "v1",
            "policy_organization": "ORG-ROOT",
            "policy_school": "",
            "based_on_version": None,
            "applies_to_tokens": ["Student", "Guardian"],
        }

        school_rows = [
            {"name": "SCH-CHILD-A"},
            {"name": "SCH-CHILD-B"},
        ]

        with (
            patch("ifitwala_ed.api.policy_communication.ensure_policy_admin"),
            patch("ifitwala_ed.api.policy_communication._policy_row", return_value=policy_row),
            patch(
                "ifitwala_ed.api.policy_communication.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch.object(policy_communication.frappe, "get_all", return_value=school_rows),
            patch.object(policy_communication.frappe, "get_doc", side_effect=fake_get_doc),
        ):
            result = policy_communication.create_policy_amendment_communication(
                policy_version="PV-ORG",
                title="Parent Policy update",
                message_html="<p>Updated</p>",
                target_scope="Schools in Organization",
                brief_start_date="2026-03-26",
                brief_end_date="2026-04-01",
                publish_from="2026-03-26 08:00:00",
                publish_to="2026-04-02 08:00:00",
                to_staff=0,
                to_students=1,
                to_guardians=1,
            )

        self.assertEqual(result["target_scope"], policy_communication.SCOPE_ORGANIZATION_ALL_SCHOOLS)
        self.assertEqual(result["school"], "")
        self.assertEqual(captured["payload"]["school"], "")
        self.assertEqual(
            captured["payload"]["audiences"],
            [
                {
                    "target_mode": "School Scope",
                    "school": "SCH-CHILD-A",
                    "include_descendants": 0,
                    "to_staff": 0,
                    "to_students": 1,
                    "to_guardians": 1,
                },
                {
                    "target_mode": "School Scope",
                    "school": "SCH-CHILD-B",
                    "include_descendants": 0,
                    "to_staff": 0,
                    "to_students": 1,
                    "to_guardians": 1,
                },
            ],
        )

    def test_get_policy_inform_payload_allows_academic_admin_without_default_school_via_org_communication(self):
        policy_row = {
            "policy_version": "PV-003",
            "institutional_policy": "POL-1",
            "policy_key": "POL-KEY",
            "policy_title": "Dress Code",
            "version_label": "v1",
            "policy_organization": "ORG-ROOT",
            "policy_school": "SCH-ROOT",
            "based_on_version": None,
            "change_summary": "Updated hem length.",
            "change_stats": {"added": 1, "removed": 0, "modified": 2},
            "diff_html": "<p>diff</p>",
            "policy_text": '<h1>policy</h1><p>Allowed</p><script>alert(1)</script><img src="x" onerror="alert(2)">',
        }

        with (
            patch(
                "ifitwala_ed.api.policy_communication.frappe.session",
                frappe._dict({"user": "academic-admin@example.com"}),
            ),
            patch.object(policy_communication.frappe, "get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.api.policy_communication._policy_row", return_value=policy_row),
            patch("ifitwala_ed.api.policy_communication.is_policy_within_user_scope", return_value=False),
            patch(
                "ifitwala_ed.api.policy_communication._get_active_employee_context",
                return_value={"name": "EMP-1", "school": None, "organization": "ORG-ROOT"},
            ),
            patch(
                "ifitwala_ed.api.policy_communication.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch.object(
                policy_communication.frappe,
                "get_all",
                return_value=[frappe._dict(name="SCH-ROOT"), frappe._dict(name="SCH-CHILD")],
            ),
            patch("ifitwala_ed.api.policy_communication.check_audience_match", return_value=True),
            patch.object(
                policy_communication.frappe,
                "db",
                frappe._dict(
                    get_value=lambda doctype, name, fields, as_dict=False: {
                        "organization": "ORG-ROOT",
                        "school": "SCH-ROOT",
                    }
                ),
            ),
            patch("ifitwala_ed.api.policy_communication.get_staff_policy_signature_state_for_user", return_value={}),
            patch("ifitwala_ed.api.policy_communication.get_policy_version_history_rows", return_value=[]),
        ):
            result = policy_communication.get_policy_inform_payload(
                policy_version="PV-003",
                org_communication="COMM-POLICY",
            )

        self.assertEqual(result["policy_version"], "PV-003")
        self.assertEqual(result["policy_school"], "SCH-ROOT")
        self.assertIn("<h2>policy</h2>", result["policy_text_html"])
        self.assertIn("<p>Allowed</p>", result["policy_text_html"])
        self.assertNotIn("<script", result["policy_text_html"])
        self.assertNotIn("onerror", result["policy_text_html"])

    def test_get_policy_inform_payload_rejects_unrelated_org_communication(self):
        policy_row = {
            "policy_version": "PV-003",
            "institutional_policy": "POL-1",
            "policy_key": "POL-KEY",
            "policy_title": "Dress Code",
            "version_label": "v1",
            "policy_organization": "ORG-ROOT",
            "policy_school": "SCH-ROOT",
            "based_on_version": None,
            "change_summary": "",
            "change_stats": {"added": 0, "removed": 0, "modified": 0},
            "diff_html": "",
            "policy_text": "<p>policy</p>",
        }

        with (
            patch(
                "ifitwala_ed.api.policy_communication.frappe.session",
                frappe._dict({"user": "academic-admin@example.com"}),
            ),
            patch.object(policy_communication.frappe, "get_roles", return_value=["Academic Admin"]),
            patch("ifitwala_ed.api.policy_communication._policy_row", return_value=policy_row),
            patch("ifitwala_ed.api.policy_communication.is_policy_within_user_scope", return_value=False),
            patch(
                "ifitwala_ed.api.policy_communication._get_active_employee_context",
                return_value={"name": "EMP-1", "school": None, "organization": "ORG-ROOT"},
            ),
            patch(
                "ifitwala_ed.api.policy_communication.get_descendant_organizations",
                return_value=["ORG-ROOT", "ORG-CHILD"],
            ),
            patch.object(
                policy_communication.frappe,
                "get_all",
                return_value=[frappe._dict(name="SCH-ROOT"), frappe._dict(name="SCH-CHILD")],
            ),
            patch("ifitwala_ed.api.policy_communication.check_audience_match", return_value=True),
            patch.object(
                policy_communication.frappe,
                "db",
                frappe._dict(
                    get_value=lambda doctype, name, fields, as_dict=False: {
                        "organization": "ORG-OTHER",
                        "school": "SCH-OTHER",
                    }
                ),
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                policy_communication.get_policy_inform_payload(
                    policy_version="PV-003",
                    org_communication="COMM-OTHER",
                )
