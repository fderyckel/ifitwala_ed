from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.family_consent import (
    AUDIENCE_GUARDIAN,
    AUDIENCE_STUDENT,
    DECISION_MODE_APPROVE_DECLINE,
    SIGNER_RULE_ANY_GUARDIAN,
    SIGNER_RULE_STUDENT_SELF,
    SUBJECT_SCOPE_PER_STUDENT,
    _decision_status_label,
    _get_or_create_student_contact,
    _request_is_executable,
    get_guardian_consent_home_summary,
    get_student_consent_home_summary,
)


class TestFamilyConsentPortalContracts(FrappeTestCase):
    def test_request_is_executable_allows_phase2a_guardian_and_student_modes(self):
        guardian_request = {
            "subject_scope": SUBJECT_SCOPE_PER_STUDENT,
            "audience_mode": AUDIENCE_GUARDIAN,
            "signer_rule": SIGNER_RULE_ANY_GUARDIAN,
            "decision_mode": DECISION_MODE_APPROVE_DECLINE,
        }
        student_request = {
            "subject_scope": SUBJECT_SCOPE_PER_STUDENT,
            "audience_mode": AUDIENCE_STUDENT,
            "signer_rule": SIGNER_RULE_STUDENT_SELF,
            "decision_mode": DECISION_MODE_APPROVE_DECLINE,
        }

        self.assertTrue(_request_is_executable(guardian_request, audience_mode=AUDIENCE_GUARDIAN))
        self.assertTrue(_request_is_executable(student_request, audience_mode=AUDIENCE_STUDENT))
        self.assertFalse(_request_is_executable(student_request, audience_mode=AUDIENCE_GUARDIAN))

    def test_decision_status_label_prefers_latest_decision_labels(self):
        self.assertEqual(
            _decision_status_label("completed", {"decision_status": "Approved"}),
            "Approved",
        )
        self.assertEqual(
            _decision_status_label("declined", {"decision_status": "Denied"}),
            "Denied",
        )
        self.assertEqual(_decision_status_label("overdue", None), "Overdue")

    def test_guardian_consent_home_summary_uses_action_needed_rows(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "School One"}]
        board_payload = {
            "counts": {"overdue": 1},
            "groups": {
                "action_needed": [
                    {
                        "request_key": "FCR-1",
                        "request_title": "Field trip consent",
                        "student": "STU-1",
                        "student_name": "Amina Example",
                        "due_on": "2026-04-25",
                        "current_status_label": "Overdue",
                    }
                ]
            },
        }

        with (
            patch(
                "ifitwala_ed.api.family_consent._children_with_signer_authority",
                return_value=children,
            ),
            patch(
                "ifitwala_ed.api.family_consent._build_board_payload",
                return_value=board_payload,
            ),
        ):
            summary = get_guardian_consent_home_summary(guardian_name="GRD-1", children=children)

        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["overdue_count"], 1)
        self.assertEqual(summary["items"][0]["href"]["name"], "guardian-consent-detail")

    def test_student_consent_home_summary_uses_action_needed_rows(self):
        board_payload = {
            "counts": {"overdue": 0},
            "groups": {
                "action_needed": [
                    {
                        "request_key": "FCR-1",
                        "request_title": "Lab participation consent",
                        "student": "STU-1",
                        "student_name": "Amina Example",
                        "due_on": "2026-04-25",
                        "current_status_label": "Action needed",
                    }
                ]
            },
        }

        with (
            patch(
                "ifitwala_ed.api.family_consent.frappe.db.get_value",
                return_value={"name": "STU-1", "student_full_name": "Amina Example", "anchor_school": "University One"},
            ),
            patch(
                "ifitwala_ed.api.family_consent._build_board_payload",
                return_value=board_payload,
            ),
        ):
            summary = get_student_consent_home_summary("STU-1")

        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["items"][0]["href"]["name"], "student-consent-detail")

    def test_get_or_create_student_contact_uses_student_identity_not_session_user(self):
        created_payloads: list[dict] = []

        class _FakeContactDoc:
            def __init__(self, payload):
                self.payload = payload
                self.name = "CONTACT-NEW"

            def insert(self, ignore_permissions=True):
                created_payloads.append(self.payload)
                return self

        with (
            patch("ifitwala_ed.api.family_consent.get_contact_linked_to_student", return_value=""),
            patch(
                "ifitwala_ed.api.family_consent.frappe.db.exists",
                side_effect=lambda doctype, name: doctype == "User" and name == "student@example.com",
            ),
            patch("ifitwala_ed.api.family_consent.frappe.db.get_value", return_value=None),
            patch(
                "ifitwala_ed.api.family_consent.frappe.get_doc",
                side_effect=lambda payload: _FakeContactDoc(payload),
            ),
            patch("ifitwala_ed.api.family_consent._ensure_contact_link"),
        ):
            student_row = {
                "student_full_name": "Amina Example",
                "student_preferred_name": "Amina",
                "student_email": "student@example.com",
                "student_mobile_number": "+66 812 345 678",
            }
            contact_name = _get_or_create_student_contact("STU-1", student_row)

        self.assertEqual(contact_name, "CONTACT-NEW")
        self.assertEqual(created_payloads[0]["user"], "student@example.com")
