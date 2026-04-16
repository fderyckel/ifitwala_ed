# ifitwala_ed/api/test_student_policy.py

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.student_policy import (
    _get_student_policy_rows,
    _query_policy_candidates_for_context,
    acknowledge_student_policy,
    get_student_policy_home_summary,
    get_student_policy_overview,
)


class TestStudentPolicy(FrappeTestCase):
    def test_get_student_policy_overview_returns_counts_from_rows(self):
        rows = [
            {"policy_version": "VER-1", "is_acknowledged": False},
            {"policy_version": "VER-2", "is_acknowledged": True},
        ]

        with (
            patch("ifitwala_ed.api.student_policy.frappe.session", frappe._dict({"user": "student@example.com"})),
            patch("ifitwala_ed.api.student_policy._require_student_name_for_session_user", return_value="STU-0001"),
            patch(
                "ifitwala_ed.api.student_policy.now_datetime",
                return_value=frappe.utils.get_datetime("2026-04-13 09:00:00"),
            ),
            patch("ifitwala_ed.api.student_policy._get_student_policy_rows", return_value=rows),
        ):
            payload = get_student_policy_overview()

        self.assertEqual(payload["meta"]["student"]["name"], "STU-0001")
        self.assertEqual(payload["counts"]["total_policies"], 2)
        self.assertEqual(payload["counts"]["acknowledged_policies"], 1)
        self.assertEqual(payload["counts"]["pending_policies"], 1)

    def test_get_student_policy_home_summary_returns_pending_items(self):
        with patch(
            "ifitwala_ed.api.student_policy._get_student_policy_rows",
            return_value=[
                {
                    "policy_version": "VER-1",
                    "policy_title": "Student Handbook",
                    "version_label": "2026",
                    "description": "Review handbook expectations.",
                    "is_acknowledged": False,
                },
                {
                    "policy_version": "VER-2",
                    "policy_title": "Academic Integrity",
                    "version_label": "v2",
                    "description": "",
                    "is_acknowledged": True,
                },
            ],
        ):
            summary = get_student_policy_home_summary("STU-0001")

        self.assertEqual(summary["pending_count"], 1)
        self.assertEqual(summary["items"][0]["href"]["name"], "student-policies")
        self.assertEqual(summary["items"][0]["policy_version"], "VER-1")

    def test_acknowledge_student_policy_is_idempotent_when_already_acknowledged(self):
        with (
            patch("ifitwala_ed.api.student_policy.frappe.session", frappe._dict({"user": "student@example.com"})),
            patch("ifitwala_ed.api.student_policy._require_student_name_for_session_user", return_value="STU-0001"),
            patch(
                "ifitwala_ed.api.student_policy._get_student_policy_rows",
                return_value=[{"policy_version": "VER-1"}],
            ),
            patch("ifitwala_ed.api.student_policy.frappe.db.get_value", return_value="ACK-1001"),
            patch("ifitwala_ed.api.student_policy.frappe.get_doc") as get_doc_mock,
        ):
            result = acknowledge_student_policy("VER-1")

        self.assertEqual(result["status"], "already_acknowledged")
        self.assertEqual(result["acknowledgement_name"], "ACK-1001")
        get_doc_mock.assert_not_called()

    def test_acknowledge_student_policy_requires_attestation(self):
        with (
            patch("ifitwala_ed.api.student_policy.frappe.session", frappe._dict({"user": "student@example.com"})),
            patch("ifitwala_ed.api.student_policy._require_student_name_for_session_user", return_value="STU-0001"),
            patch(
                "ifitwala_ed.api.student_policy._get_student_policy_rows",
                return_value=[{"policy_version": "VER-1"}],
            ),
            patch("ifitwala_ed.api.student_policy.frappe.db.get_value", return_value=None),
            patch("ifitwala_ed.api.student_policy._expected_student_signature_name", return_value="Amina Example"),
        ):
            with self.assertRaises(frappe.ValidationError):
                acknowledge_student_policy(
                    "VER-1",
                    typed_signature_name="Amina Example",
                    attestation_confirmed=0,
                )

    def test_acknowledge_student_policy_creates_acknowledgement_when_missing(self):
        acknowledgement_doc = Mock()
        acknowledgement_doc.name = "ACK-1002"

        with (
            patch("ifitwala_ed.api.student_policy.frappe.session", frappe._dict({"user": "student@example.com"})),
            patch("ifitwala_ed.api.student_policy._require_student_name_for_session_user", return_value="STU-0001"),
            patch(
                "ifitwala_ed.api.student_policy._get_student_policy_rows",
                return_value=[{"policy_version": "VER-1"}],
            ),
            patch("ifitwala_ed.api.student_policy.frappe.db.get_value", return_value=None),
            patch("ifitwala_ed.api.student_policy._expected_student_signature_name", return_value="Amina Example"),
            patch("ifitwala_ed.api.student_policy.populate_policy_acknowledgement_evidence") as evidence_mock,
            patch("ifitwala_ed.api.student_policy.frappe.get_doc", return_value=acknowledgement_doc) as get_doc_mock,
        ):
            result = acknowledge_student_policy(
                "VER-1",
                typed_signature_name="Amina Example",
                attestation_confirmed=1,
                checked_clause_names=["CLAUSE-1"],
            )

        self.assertEqual(result["status"], "acknowledged")
        self.assertEqual(result["acknowledgement_name"], "ACK-1002")
        acknowledgement_doc.insert.assert_called_once_with()
        evidence_mock.assert_called_once_with(
            acknowledgement_doc,
            typed_signature_name="Amina Example",
            attestation_confirmed=1,
            checked_clause_names=["CLAUSE-1"],
        )
        payload = get_doc_mock.call_args.args[0]
        self.assertEqual(payload["acknowledged_for"], "Student")
        self.assertEqual(payload["context_name"], "STU-0001")

    def test_query_policy_candidates_filters_student_rows_in_sql(self):
        with (
            patch(
                "ifitwala_ed.api.student_policy.get_organization_ancestors_including_self",
                return_value=["ORG-1"],
            ),
            patch(
                "ifitwala_ed.api.student_policy.get_school_ancestors_including_self",
                return_value=["SCHOOL-1"],
            ),
            patch(
                "ifitwala_ed.api.student_policy.frappe.db.sql",
                return_value=[
                    {
                        "policy_name": "POL-1",
                        "policy_key": "student_handbook",
                        "policy_title": "Student Handbook",
                        "policy_category": "Handbooks",
                        "description": "",
                        "policy_organization": "ORG-1",
                        "policy_school": "SCHOOL-1",
                        "policy_version": "VER-1",
                        "version_label": "v1",
                        "policy_text": "<p>Policy</p>",
                        "effective_from": None,
                        "effective_to": None,
                        "approved_on": None,
                    }
                ],
            ) as sql_mock,
            patch(
                "ifitwala_ed.api.student_policy.select_nearest_policy_rows_by_key",
                side_effect=lambda **kwargs: kwargs["rows"],
            ),
        ):
            rows = _query_policy_candidates_for_context(organization="ORG-1", school="SCHOOL-1")

        self.assertEqual([row["policy_name"] for row in rows], ["POL-1"])
        self.assertIn("tabInstitutional Policy Audience", sql_mock.call_args.args[0])
        self.assertEqual(sql_mock.call_args.args[1][-1], "Student")

    def test_get_student_policy_rows_sanitizes_policy_text(self):
        def fake_get_value(doctype, name_or_filters, fieldname, as_dict=False):
            if doctype == "Student":
                return {
                    "anchor_school": "SCHOOL-1",
                    "student_full_name": "Amina Example",
                    "student_preferred_name": "",
                }
            if doctype == "School":
                return "ORG-1"
            self.fail(f"Unexpected get_value call for {doctype}")

        with (
            patch("ifitwala_ed.api.student_policy.ensure_policy_applies_to_storage", return_value={"ok": True}),
            patch("ifitwala_ed.api.student_policy.frappe.db.get_value", side_effect=fake_get_value),
            patch(
                "ifitwala_ed.api.student_policy._query_policy_candidates_for_context",
                return_value=[
                    {
                        "policy_name": "POL-1",
                        "policy_key": "student_handbook",
                        "policy_title": "Student Handbook",
                        "policy_category": "Handbooks",
                        "policy_version": "VER-1",
                        "version_label": "v1",
                        "policy_organization": "ORG-1",
                        "policy_school": "SCHOOL-1",
                        "description": "Review this handbook.",
                        "policy_text": "<h1>Student Handbook</h1><p>Welcome</p><script>alert(1)</script>",
                        "effective_from": None,
                        "effective_to": None,
                        "approved_on": None,
                    }
                ],
            ),
            patch("ifitwala_ed.api.student_policy.frappe.get_all", return_value=[]),
            patch("ifitwala_ed.api.student_policy.get_policy_version_acknowledgement_clauses_map", return_value={}),
            patch("ifitwala_ed.api.student_policy._expected_student_signature_name", return_value="Amina Example"),
        ):
            rows = _get_student_policy_rows(student_name="STU-0001")

        self.assertEqual(len(rows), 1)
        self.assertIn("<h2>Student Handbook</h2>", rows[0]["policy_text"])
        self.assertIn("<p>Welcome</p>", rows[0]["policy_text"])
        self.assertNotIn("<script", rows[0]["policy_text"])
