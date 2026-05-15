# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from contextlib import nullcontext
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import policy_signature


class _DummyOrgCommunicationDoc:
    def __init__(self, payload, index):
        self.name = f"COMM-FAMILY-{index}"
        self.title = payload.get("title")
        self.status = payload.get("status")
        self.organization = payload.get("organization")
        self.school = payload.get("school")
        self.audiences = payload.get("audiences") or []

    def insert(self):
        return self


class _DummyCache:
    def __init__(self):
        self.values = {}
        self.hash_values = {}

    def get_value(self, key):
        return self.values.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.values[key] = value

    def hget(self, key, field):
        return (self.hash_values.get(key) or {}).get(field)

    def hset(self, key, field, value):
        self.hash_values.setdefault(key, {})[field] = value

    def lock(self, key, timeout=15):
        return nullcontext()


class TestPolicyFamilyCampaign(FrappeTestCase):
    def test_get_family_policy_campaign_options_filters_to_student_and_guardian_policies(self):
        policy_rows = [
            {
                "policy_version": "PV-STAFF",
                "policy_title": "Employee Handbook",
                "version_label": "v1",
                "applies_to_tokens": ["Staff"],
            },
            {
                "policy_version": "PV-GUARDIAN",
                "policy_title": "Family Privacy",
                "version_label": "v2",
                "applies_to_tokens": ["Guardian"],
            },
            {
                "policy_version": "PV-MIXED",
                "policy_title": "Community Handbook",
                "version_label": "v3",
                "applies_to_tokens": ["Student", "Guardian"],
            },
        ]

        with (
            patch(
                "ifitwala_ed.api.policy_signature._require_roles",
                return_value=("admin@example.com", {"Academic Admin"}),
            ),
            patch("ifitwala_ed.api.policy_signature._", side_effect=lambda text: text),
            patch(
                "ifitwala_ed.api.policy_signature._manager_scope_organizations",
                return_value=["ORG-ROOT"],
            ),
            patch("ifitwala_ed.api.policy_signature.get_descendant_organizations", return_value=["ORG-ROOT"]),
            patch("ifitwala_ed.api.policy_signature._school_options_for_scope", return_value=["SCH-1"]),
            patch(
                "ifitwala_ed.api.policy_signature._family_policy_options_for_scope",
                return_value=policy_rows[1:],
            ),
            patch(
                "ifitwala_ed.api.policy_signature._family_campaign_school_targets",
                return_value=["SCH-1"],
            ),
        ):
            result = policy_signature.get_family_policy_campaign_options(organization="ORG-ROOT")

        self.assertEqual(result["options"]["organizations"], ["ORG-ROOT"])
        self.assertEqual(result["options"]["schools"], ["SCH-1"])
        self.assertEqual(
            [row.get("policy_version") for row in result["options"]["policies"]],
            ["PV-GUARDIAN", "PV-MIXED"],
        )
        self.assertIsNone(result["preview"]["guardian_acknowledgement_mode"])
        self.assertFalse(result["preview"]["guardian_acknowledgement_mode_locked"])
        self.assertEqual(result["preview"]["school_target_count"], 1)

    def test_publish_family_policy_campaign_creates_one_portal_communication_per_selected_audience(self):
        captured_payloads = []
        cache = _DummyCache()

        def fake_get_doc(payload):
            captured_payloads.append(payload)
            return _DummyOrgCommunicationDoc(payload, len(captured_payloads))

        policy_row = {
            "policy_version": "PV-FAMILY",
            "policy_title": "Community Handbook",
            "version_label": "v4",
            "guardian_acknowledgement_mode": "Family Acknowledgement",
            "policy_organization": "ORG-ROOT",
            "policy_school": "",
            "institutional_policy": "POL-1",
            "policy_key": "community_handbook",
            "based_on_version": None,
            "change_summary": "Updated community expectations.",
            "applies_to_tokens": ["Guardian", "Student"],
        }
        preview_payload = {
            "family_audiences": ["Guardian", "Student"],
            "guardian_acknowledgement_mode": "Child Acknowledgement",
            "guardian_acknowledgement_mode_locked": False,
            "school_target_count": 2,
            "audience_previews": [
                {
                    "audience": "Guardian",
                    "audience_label": "Guardians",
                    "workflow_description": "Guardian portal flow",
                    "eligible_targets": 8,
                    "signed": 5,
                    "pending": 3,
                    "completion_pct": 62.5,
                    "skipped_scope": 0,
                },
                {
                    "audience": "Student",
                    "audience_label": "Students",
                    "workflow_description": "Student portal flow",
                    "eligible_targets": 10,
                    "signed": 4,
                    "pending": 6,
                    "completion_pct": 40,
                    "skipped_scope": 0,
                },
            ],
        }

        with (
            patch(
                "ifitwala_ed.api.policy_signature._require_roles",
                return_value=("admin@example.com", {"Academic Admin"}),
            ),
            patch("ifitwala_ed.api.policy_signature._", side_effect=lambda text: text),
            patch(
                "ifitwala_ed.api.policy_signature._manager_scope_organizations",
                return_value=["ORG-ROOT"],
            ),
            patch("ifitwala_ed.api.policy_signature.get_descendant_organizations", return_value=["ORG-ROOT"]),
            patch("ifitwala_ed.api.policy_signature.get_policy_version_context", return_value=policy_row),
            patch(
                "ifitwala_ed.api.policy_signature._policy_scope_applies_to_context",
                return_value=True,
            ),
            patch(
                "ifitwala_ed.api.policy_signature._family_campaign_school_targets",
                return_value=["SCH-A", "SCH-B"],
            ),
            patch(
                "ifitwala_ed.api.policy_signature._family_campaign_preview_payload",
                return_value=preview_payload,
            ),
            patch(
                "ifitwala_ed.api.policy_signature._persist_guardian_acknowledgement_mode_if_needed",
                return_value={**policy_row, "guardian_acknowledgement_mode": "Child Acknowledgement"},
            ) as persist_mode_mock,
            patch.object(policy_signature.frappe, "get_doc", side_effect=fake_get_doc),
            patch.object(policy_signature.frappe, "cache", return_value=cache),
        ):
            first_result = policy_signature.publish_family_policy_campaign(
                policy_version="PV-FAMILY",
                organization="ORG-ROOT",
                audiences=["Guardian", "Student"],
                guardian_acknowledgement_mode="Child Acknowledgement",
                title="Please review this handbook update",
                message="A new acknowledgement is waiting for your family.",
                client_request_id="REQ-1",
            )
            second_result = policy_signature.publish_family_policy_campaign(
                policy_version="PV-FAMILY",
                organization="ORG-ROOT",
                audiences=["Guardian", "Student"],
                guardian_acknowledgement_mode="Child Acknowledgement",
                title="Please review this handbook update",
                message="A new acknowledgement is waiting for your family.",
                client_request_id="REQ-1",
            )

        self.assertEqual(len(captured_payloads), 2)
        self.assertEqual(first_result["status"], "processed")
        self.assertFalse(first_result["idempotent"])
        self.assertEqual(first_result["counts"]["published"], 2)
        self.assertEqual(first_result["counts"]["pending"], 9)
        self.assertEqual(first_result["counts"]["school_targets"], 2)
        self.assertEqual(first_result["guardian_acknowledgement_mode"], "Child Acknowledgement")
        self.assertEqual(
            [first_result["communications"][0]["audience"], first_result["communications"][1]["audience"]],
            ["Guardian", "Student"],
        )
        persist_mode_mock.assert_called_once()
        self.assertEqual(captured_payloads[0]["status"], "Published")
        self.assertEqual(captured_payloads[0]["portal_surface"], "Portal Feed")
        self.assertEqual(
            captured_payloads[0]["audiences"],
            [
                {
                    "target_mode": "School Scope",
                    "school": "SCH-A",
                    "include_descendants": 0,
                    "to_staff": 0,
                    "to_students": 0,
                    "to_guardians": 1,
                },
                {
                    "target_mode": "School Scope",
                    "school": "SCH-B",
                    "include_descendants": 0,
                    "to_staff": 0,
                    "to_students": 0,
                    "to_guardians": 1,
                },
            ],
        )
        self.assertEqual(
            captured_payloads[1]["audiences"],
            [
                {
                    "target_mode": "School Scope",
                    "school": "SCH-A",
                    "include_descendants": 0,
                    "to_staff": 0,
                    "to_students": 1,
                    "to_guardians": 0,
                },
                {
                    "target_mode": "School Scope",
                    "school": "SCH-B",
                    "include_descendants": 0,
                    "to_staff": 0,
                    "to_students": 1,
                    "to_guardians": 0,
                },
            ],
        )
        self.assertEqual(second_result["status"], "already_processed")
        self.assertTrue(second_result["idempotent"])
        self.assertEqual(len(captured_payloads), 2)
