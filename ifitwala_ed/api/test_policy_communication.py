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
                to_community=0,
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
                    "to_community": 0,
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
                    to_community=0,
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
            patch("ifitwala_ed.api.policy_communication._resolve_org_root_school", return_value="SCH-A"),
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
                to_community=0,
            )

        self.assertEqual(result["target_scope"], policy_communication.SCOPE_ORGANIZATION_ALL_SCHOOLS)
        self.assertEqual(result["school"], "SCH-A")
        self.assertEqual(len(captured["payload"]["audiences"]), 2)
        self.assertEqual(captured["payload"]["audiences"][0]["target_mode"], "School Scope")
