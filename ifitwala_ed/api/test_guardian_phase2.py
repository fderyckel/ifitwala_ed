# ifitwala_ed/api/test_guardian_phase2.py

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import guardian_communications
from ifitwala_ed.api.guardian_attendance import get_guardian_attendance_snapshot
from ifitwala_ed.api.guardian_communications import get_guardian_communication_center
from ifitwala_ed.api.guardian_finance import _resolve_finance_scope, get_guardian_finance_snapshot
from ifitwala_ed.api.guardian_monitoring import (
    _get_monitoring_logs,
    get_guardian_monitoring_published_results,
    get_guardian_monitoring_snapshot,
    get_guardian_monitoring_student_logs,
    mark_guardian_student_log_read,
)
from ifitwala_ed.api.guardian_policy import (
    _children_with_signer_authority,
    _get_guardian_policy_rows,
    _query_policy_candidates_for_context,
    acknowledge_guardian_policy,
    get_guardian_policy_overview,
)


class TestGuardianPolicyPhase2(FrappeTestCase):
    def test_get_guardian_policy_overview_returns_counts_from_rows(self):
        rows = [
            {"policy_version": "VER-1", "is_acknowledged": False},
            {"policy_version": "VER-2", "is_acknowledged": True},
        ]
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]

        with (
            patch("ifitwala_ed.api.guardian_policy.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_policy.now_datetime",
                return_value=frappe.utils.get_datetime("2026-03-13 09:00:00"),
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_guardian_scope",
                return_value=("GRD-0001", children),
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._children_with_signer_authority",
                return_value=children,
            ),
            patch("ifitwala_ed.api.guardian_policy._get_guardian_policy_rows", return_value=rows),
        ):
            payload = get_guardian_policy_overview()

        self.assertEqual(payload["meta"]["guardian"]["name"], "GRD-0001")
        self.assertEqual(payload["family"]["children"], children)
        self.assertEqual(payload["counts"]["total_policies"], 2)
        self.assertEqual(payload["counts"]["acknowledged_policies"], 1)
        self.assertEqual(payload["counts"]["pending_policies"], 1)

    def test_acknowledge_guardian_policy_is_idempotent_when_already_acknowledged(self):
        with (
            patch("ifitwala_ed.api.guardian_policy.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_guardian_scope",
                return_value=("GRD-0001", [{"student": "STU-1"}]),
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._get_guardian_policy_rows",
                return_value=[{"policy_version": "VER-1"}],
            ),
            patch("ifitwala_ed.api.guardian_policy.frappe.db.get_value", return_value="ACK-0001"),
            patch("ifitwala_ed.api.guardian_policy.frappe.get_doc") as get_doc_mock,
        ):
            result = acknowledge_guardian_policy("VER-1")

        self.assertEqual(result["status"], "already_acknowledged")
        self.assertEqual(result["acknowledgement_name"], "ACK-0001")
        get_doc_mock.assert_not_called()

    def test_acknowledge_guardian_policy_requires_attestation(self):
        with (
            patch("ifitwala_ed.api.guardian_policy.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_guardian_scope",
                return_value=("GRD-0001", [{"student": "STU-1"}]),
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._get_guardian_policy_rows",
                return_value=[{"policy_version": "VER-1"}],
            ),
            patch("ifitwala_ed.api.guardian_policy.frappe.db.get_value", return_value=None),
            patch(
                "ifitwala_ed.api.guardian_policy._expected_guardian_signature_name",
                return_value="Amina Example Guardian",
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                acknowledge_guardian_policy(
                    "VER-1",
                    typed_signature_name="Amina Example Guardian",
                    attestation_confirmed=0,
                )

    def test_acknowledge_guardian_policy_creates_acknowledgement_when_missing(self):
        acknowledgement_doc = Mock()
        acknowledgement_doc.name = "ACK-0002"

        with (
            patch("ifitwala_ed.api.guardian_policy.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_guardian_scope",
                return_value=("GRD-0001", [{"student": "STU-1"}]),
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._get_guardian_policy_rows",
                return_value=[{"policy_version": "VER-1"}],
            ),
            patch("ifitwala_ed.api.guardian_policy.frappe.db.get_value", return_value=None),
            patch(
                "ifitwala_ed.api.guardian_policy._expected_guardian_signature_name",
                return_value="Amina Example Guardian",
            ),
            patch("ifitwala_ed.api.guardian_policy.populate_policy_acknowledgement_evidence") as evidence_mock,
            patch("ifitwala_ed.api.guardian_policy.frappe.get_doc", return_value=acknowledgement_doc) as get_doc_mock,
        ):
            result = acknowledge_guardian_policy(
                "VER-1",
                typed_signature_name="Amina Example Guardian",
                attestation_confirmed=1,
                checked_clause_names=["CLAUSE-1"],
            )

        self.assertEqual(result["status"], "acknowledged")
        self.assertEqual(result["acknowledgement_name"], "ACK-0002")
        acknowledgement_doc.insert.assert_called_once_with()
        evidence_mock.assert_called_once_with(
            acknowledgement_doc,
            typed_signature_name="Amina Example Guardian",
            attestation_confirmed=1,
            checked_clause_names=["CLAUSE-1"],
        )
        payload = get_doc_mock.call_args.args[0]
        self.assertEqual(payload["acknowledged_for"], "Guardian")
        self.assertEqual(payload["context_name"], "GRD-0001")

    def test_acknowledge_guardian_policy_uses_student_context_for_child_mode(self):
        acknowledgement_doc = Mock()
        acknowledgement_doc.name = "ACK-CHILD-1"

        with (
            patch("ifitwala_ed.api.guardian_policy.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_guardian_scope",
                return_value=("GRD-0001", [{"student": "STU-1"}]),
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._get_guardian_policy_rows",
                return_value=[
                    {
                        "policy_version": "VER-1",
                        "ack_context_doctype": "Student",
                        "ack_context_name": "STU-1",
                    }
                ],
            ),
            patch("ifitwala_ed.api.guardian_policy.frappe.db.get_value", return_value=None),
            patch(
                "ifitwala_ed.api.guardian_policy._expected_guardian_signature_name",
                return_value="Amina Example Guardian",
            ),
            patch("ifitwala_ed.api.guardian_policy.populate_policy_acknowledgement_evidence"),
            patch("ifitwala_ed.api.guardian_policy.frappe.get_doc", return_value=acknowledgement_doc) as get_doc_mock,
        ):
            result = acknowledge_guardian_policy(
                "VER-1",
                context_name="STU-1",
                typed_signature_name="Amina Example Guardian",
                attestation_confirmed=1,
            )

        self.assertEqual(result["status"], "acknowledged")
        payload = get_doc_mock.call_args.args[0]
        self.assertEqual(payload["acknowledged_for"], "Guardian")
        self.assertEqual(payload["context_doctype"], "Student")
        self.assertEqual(payload["context_name"], "STU-1")

    def test_children_with_signer_authority_filters_to_consent_enabled_links(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-1"},
        ]

        with (
            patch("ifitwala_ed.api.guardian_policy._guardian_has_primary_signer_authority", return_value=True),
            patch("ifitwala_ed.api.guardian_policy.frappe.db.has_column", return_value=True),
            patch(
                "ifitwala_ed.api.guardian_policy.frappe.get_all",
                return_value=[{"parent": "STU-1"}],
            ),
        ):
            filtered = _children_with_signer_authority(guardian_name="GRD-0001", children=children)

        self.assertEqual(filtered, [children[0]])

    def test_children_with_signer_authority_rejects_non_primary_guardian(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]

        with patch("ifitwala_ed.api.guardian_policy._guardian_has_primary_signer_authority", return_value=False):
            filtered = _children_with_signer_authority(guardian_name="GRD-0001", children=children)

        self.assertEqual(filtered, [])

    def test_query_policy_candidates_filters_guardian_rows_in_sql(self):
        with (
            patch(
                "ifitwala_ed.api.guardian_policy.get_organization_ancestors_including_self",
                return_value=["ORG-1"],
            ),
            patch(
                "ifitwala_ed.api.guardian_policy.get_school_ancestors_including_self",
                return_value=["SCHOOL-1"],
            ),
            patch(
                "ifitwala_ed.api.guardian_policy.frappe.db.sql",
                return_value=[
                    {
                        "policy_name": "POL-1",
                        "policy_key": "family_handbook",
                        "policy_title": "Family Handbook",
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
                "ifitwala_ed.api.guardian_policy.select_nearest_policy_rows_by_key",
                side_effect=lambda **kwargs: kwargs["rows"],
            ),
        ):
            rows = _query_policy_candidates_for_context(organization="ORG-1", school="SCHOOL-1")

        self.assertEqual([row["policy_name"] for row in rows], ["POL-1"])
        self.assertIn("tabInstitutional Policy Audience", sql_mock.call_args.args[0])
        self.assertEqual(sql_mock.call_args.args[1][-1], "Guardian")

    def test_get_guardian_policy_rows_sanitizes_policy_text(self):
        children = [{"student": "STU-1", "school": "SCHOOL-1"}]

        with (
            patch("ifitwala_ed.api.guardian_policy.ensure_policy_applies_to_storage", return_value={"ok": True}),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_authorized_child_contexts",
                return_value=[
                    {
                        "student": "STU-1",
                        "student_label": "STU-1",
                        "organization": "ORG-1",
                        "school": "SCHOOL-1",
                    }
                ],
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_policy_contexts",
                return_value=[{"organization": "ORG-1", "school": "SCHOOL-1"}],
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._query_policy_candidates_for_context",
                return_value=[
                    {
                        "policy_name": "POL-1",
                        "policy_key": "family_handbook",
                        "policy_title": "Family Handbook",
                        "policy_category": "Handbooks",
                        "policy_version": "VER-1",
                        "version_label": "v1",
                        "policy_organization": "ORG-1",
                        "policy_school": "SCHOOL-1",
                        "description": "Review this handbook.",
                        "policy_text": "<h1>Family Handbook</h1><p>Welcome</p><script>alert(1)</script>",
                        "effective_from": None,
                        "effective_to": None,
                        "approved_on": None,
                    }
                ],
            ),
            patch("ifitwala_ed.api.guardian_policy.frappe.get_all", return_value=[]),
            patch("ifitwala_ed.api.guardian_policy.get_policy_version_acknowledgement_clauses_map", return_value={}),
            patch(
                "ifitwala_ed.api.guardian_policy._expected_guardian_signature_name",
                return_value="Mariam Example",
            ),
        ):
            rows = _get_guardian_policy_rows(guardian_name="GRD-0001", children=children)

        self.assertEqual(len(rows), 1)
        self.assertIn("<h2>Family Handbook</h2>", rows[0]["policy_text"])
        self.assertIn("<p>Welcome</p>", rows[0]["policy_text"])
        self.assertNotIn("<script", rows[0]["policy_text"])

    def test_get_guardian_policy_rows_expands_child_mode_to_one_row_per_student(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-1"},
        ]

        with (
            patch("ifitwala_ed.api.guardian_policy.ensure_policy_applies_to_storage", return_value={"ok": True}),
            patch(
                "ifitwala_ed.api.guardian_policy._resolve_authorized_child_contexts",
                return_value=[
                    {
                        "student": "STU-1",
                        "student_label": "Amina Example",
                        "organization": "ORG-1",
                        "school": "SCHOOL-1",
                    },
                    {
                        "student": "STU-2",
                        "student_label": "Noah Example",
                        "organization": "ORG-1",
                        "school": "SCHOOL-1",
                    },
                ],
            ),
            patch(
                "ifitwala_ed.api.guardian_policy._query_policy_candidates_for_context",
                return_value=[
                    {
                        "policy_name": "POL-1",
                        "policy_key": "family_handbook",
                        "policy_title": "Family Handbook",
                        "policy_category": "Handbooks",
                        "policy_version": "VER-1",
                        "version_label": "v1",
                        "guardian_acknowledgement_mode": "Child Acknowledgement",
                        "policy_organization": "ORG-1",
                        "policy_school": "SCHOOL-1",
                        "description": "Review this handbook.",
                        "policy_text": "<p>Policy text</p>",
                        "effective_from": None,
                        "effective_to": None,
                        "approved_on": None,
                    }
                ],
            ),
            patch("ifitwala_ed.api.guardian_policy.frappe.get_all", return_value=[]),
            patch("ifitwala_ed.api.guardian_policy.get_policy_version_acknowledgement_clauses_map", return_value={}),
            patch(
                "ifitwala_ed.api.guardian_policy._expected_guardian_signature_name",
                return_value="Mariam Example",
            ),
        ):
            rows = _get_guardian_policy_rows(guardian_name="GRD-0001", children=children)

        self.assertEqual(len(rows), 2)
        self.assertEqual({row["ack_context_doctype"] for row in rows}, {"Student"})
        self.assertEqual({row["ack_context_name"] for row in rows}, {"STU-1", "STU-2"})
        self.assertEqual({row["scope_label"] for row in rows}, {"Amina Example", "Noah Example"})


class TestGuardianFinancePhase2(FrappeTestCase):
    def test_finance_scope_authorizes_account_holder_by_email_match(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]

        def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=None):
            if doctype == "Student":
                return [
                    {
                        "name": "STU-1",
                        "student_full_name": "Amina Example",
                        "anchor_school": "SCHOOL-1",
                        "account_holder": "AH-1",
                    }
                ]
            if doctype == "Account Holder":
                return [
                    {
                        "name": "AH-1",
                        "account_holder_name": "Example Family",
                        "organization": "ORG-1",
                        "status": "Active",
                        "primary_email": "guardian@example.com",
                        "primary_phone": "",
                    }
                ]
            self.fail(f"Unexpected doctype lookup: {doctype}")

        with (
            patch(
                "ifitwala_ed.api.guardian_finance.frappe.db.get_value",
                return_value={"guardian_email": "guardian@example.com", "is_financial_guardian": 0},
            ),
            patch("ifitwala_ed.api.guardian_finance.frappe.get_all", side_effect=fake_get_all),
        ):
            scope = _resolve_finance_scope(
                user="guardian@example.com",
                guardian_name="GRD-0001",
                children=children,
            )

        self.assertEqual(scope["authorized_account_holders"], ["AH-1"])
        self.assertEqual(scope["account_holders"][0]["students"][0]["student"], "STU-1")
        self.assertEqual(scope["access_reason"], "")

    def test_finance_snapshot_returns_explicit_access_limited_meta(self):
        with (
            patch("ifitwala_ed.api.guardian_finance.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_finance.now_datetime",
                return_value=frappe.utils.get_datetime("2026-03-13 09:00:00"),
            ),
            patch(
                "ifitwala_ed.api.guardian_finance._resolve_guardian_scope",
                return_value=("GRD-0001", [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]),
            ),
            patch(
                "ifitwala_ed.api.guardian_finance._resolve_finance_scope",
                return_value={
                    "children": [],
                    "student_names": [],
                    "authorized_account_holders": [],
                    "account_holders": [],
                    "children_by_holder": {},
                    "access_reason": "no_authorized_account_holders",
                },
            ),
            patch("ifitwala_ed.api.guardian_finance._get_invoice_rows", return_value=[]),
            patch("ifitwala_ed.api.guardian_finance._get_payment_rows", return_value=[]),
        ):
            payload = get_guardian_finance_snapshot()

        self.assertFalse(payload["meta"]["finance_access"])
        self.assertEqual(payload["meta"]["access_reason"], "no_authorized_account_holders")
        self.assertEqual(payload["counts"]["total_invoices"], 0)


class TestGuardianMonitoringPhase2(FrappeTestCase):
    def test_monitoring_logs_return_full_guardian_visible_note_text(self):
        long_log_text = " ".join(["Detailed guardian-visible note"] * 24)
        row = {
            "name": "LOG-1",
            "student": "STU-1",
            "student_name": "Amina Example",
            "date": frappe.utils.getdate("2026-03-12"),
            "time": None,
            "follow_up_status": "Open",
            "log": f"<p>{long_log_text}</p>",
        }

        with (
            patch(
                "ifitwala_ed.api.guardian_monitoring.frappe.utils.getdate",
                return_value=frappe.utils.getdate("2026-03-13"),
            ),
            patch(
                "ifitwala_ed.api.guardian_monitoring.frappe.db.sql",
                return_value=[{**row, "is_unread": 1}],
            ),
            patch(
                "ifitwala_ed.students.doctype.student_log.evidence.get_student_log_evidence_map",
                return_value={},
            ),
        ):
            result = _get_monitoring_logs(
                user="guardian@example.com",
                student_names=["STU-1"],
                days=30,
                start=0,
                page_length=12,
            )

        self.assertEqual(result[0]["summary"], long_log_text)
        self.assertGreater(len(result[0]["summary"]), 220)
        self.assertTrue(result[0]["is_unread"])

    def test_monitoring_rejects_out_of_scope_student_filter(self):
        with (
            patch("ifitwala_ed.api.guardian_monitoring.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_monitoring._resolve_guardian_scope",
                return_value=("GRD-0001", [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]),
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                get_guardian_monitoring_snapshot(student="STU-404", days=30)

    def test_monitoring_snapshot_returns_familywide_counts(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-1"},
        ]
        student_logs = [
            {
                "student_log": "LOG-1",
                "student": "STU-1",
                "student_name": "Amina Example",
                "date": "2026-03-12",
                "summary": "Needs follow-up",
                "follow_up_status": "Open",
                "is_unread": True,
            }
        ]
        published_results = {
            "items": [
                {
                    "task_outcome": "OUT-1",
                    "student": "STU-2",
                    "student_name": "Noah Example",
                    "title": "Science assessment",
                    "published_on": "2026-03-11 09:00:00",
                }
            ],
            "total_count": 1,
            "unread_total_count": 0,
            "has_more": False,
            "start": 0,
            "page_length": 12,
        }
        student_log_page = {
            "items": student_logs,
            "total_count": 1,
            "unread_total_count": 1,
            "has_more": False,
            "start": 0,
            "page_length": 12,
        }

        with (
            patch("ifitwala_ed.api.guardian_monitoring.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_monitoring.now_datetime",
                return_value=frappe.utils.get_datetime("2026-03-13 09:00:00"),
            ),
            patch(
                "ifitwala_ed.api.guardian_monitoring._resolve_guardian_scope",
                return_value=("GRD-0001", children),
            ),
            patch("ifitwala_ed.api.guardian_monitoring._get_monitoring_logs_page", return_value=student_log_page),
            patch("ifitwala_ed.api.guardian_monitoring._get_monitoring_results_page", return_value=published_results),
        ):
            payload = get_guardian_monitoring_snapshot(days=30, page_length=12)

        self.assertEqual(payload["counts"]["visible_student_logs"], 1)
        self.assertEqual(payload["counts"]["unread_visible_student_logs"], 1)
        self.assertEqual(payload["counts"]["published_results"], 1)
        self.assertEqual(payload["family"]["children"], children)
        self.assertEqual(payload["student_logs"]["items"], student_logs)
        self.assertEqual(payload["published_results"]["total_count"], 1)

    def test_monitoring_student_logs_endpoint_returns_paged_payload(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]
        log_page = {
            "items": [
                {
                    "student_log": "LOG-1",
                    "student": "STU-1",
                    "student_name": "Amina Example",
                    "date": "2026-03-12",
                    "summary": "Needs follow-up",
                    "follow_up_status": "Open",
                    "is_unread": True,
                }
            ],
            "total_count": 3,
            "unread_total_count": 1,
            "has_more": True,
            "start": 1,
            "page_length": 12,
        }

        with (
            patch("ifitwala_ed.api.guardian_monitoring.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_monitoring._resolve_guardian_scope",
                return_value=("GRD-0001", children),
            ),
            patch("ifitwala_ed.api.guardian_monitoring._get_monitoring_logs_page", return_value=log_page),
        ):
            payload = get_guardian_monitoring_student_logs(start=1, page_length=12)

        self.assertEqual(payload["items"], log_page["items"])
        self.assertEqual(payload["total_count"], 3)
        self.assertTrue(payload["has_more"])

    def test_monitoring_published_results_endpoint_returns_paged_payload(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]
        result_page = {
            "items": [
                {
                    "task_outcome": "OUT-1",
                    "student": "STU-1",
                    "student_name": "Amina Example",
                    "title": "Science assessment",
                    "published_on": "2026-03-11 09:00:00",
                }
            ],
            "total_count": 2,
            "unread_total_count": 0,
            "has_more": True,
            "start": 1,
            "page_length": 12,
        }

        with (
            patch("ifitwala_ed.api.guardian_monitoring.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_monitoring._resolve_guardian_scope",
                return_value=("GRD-0001", children),
            ),
            patch("ifitwala_ed.api.guardian_monitoring._get_monitoring_results_page", return_value=result_page),
        ):
            payload = get_guardian_monitoring_published_results(start=1, page_length=12)

        self.assertEqual(payload["items"], result_page["items"])
        self.assertEqual(payload["total_count"], 2)
        self.assertTrue(payload["has_more"])

    def test_mark_guardian_student_log_read_persists_seen_state_for_linked_child(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]
        log_row = frappe._dict({"name": "LOG-1", "student": "STU-1", "visible_to_guardians": 1})
        read_at = frappe.utils.get_datetime("2026-03-15 11:45:00")

        with (
            patch("ifitwala_ed.api.guardian_monitoring.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_monitoring._resolve_guardian_scope",
                return_value=("GRD-0001", children),
            ),
            patch("ifitwala_ed.api.guardian_monitoring.now_datetime", return_value=read_at),
            patch("ifitwala_ed.api.guardian_monitoring.frappe.db.get_value", return_value=log_row),
            patch("ifitwala_ed.api.guardian_monitoring._upsert_student_log_read_receipt") as mark_read_mock,
        ):
            result = mark_guardian_student_log_read("LOG-1")

        self.assertEqual(result, {"ok": True, "student_log": "LOG-1", "read_at": read_at})
        mark_read_mock.assert_called_once_with(
            user="guardian@example.com",
            log_name="LOG-1",
            read_at=read_at,
        )

    def test_mark_guardian_student_log_read_rejects_out_of_scope_log(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]
        log_row = frappe._dict({"name": "LOG-404", "student": "STU-404", "visible_to_guardians": 1})

        with (
            patch("ifitwala_ed.api.guardian_monitoring.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_monitoring._resolve_guardian_scope",
                return_value=("GRD-0001", children),
            ),
            patch("ifitwala_ed.api.guardian_monitoring.frappe.db.get_value", return_value=log_row),
        ):
            with self.assertRaises(frappe.PermissionError):
                mark_guardian_student_log_read("LOG-404")


class TestGuardianCommunicationCenterPhase2(FrappeTestCase):
    def test_communication_center_rejects_out_of_scope_student_filter(self):
        with patch(
            "ifitwala_ed.api.guardian_communications._resolve_guardian_communication_context",
            return_value={
                "children": [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}],
                "student_names": ["STU-1"],
            },
        ):
            with self.assertRaises(frappe.PermissionError):
                get_guardian_communication_center(student="STU-404")

    def test_communication_center_returns_familywide_items_and_unread_counts(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-1"},
        ]
        org_items = [
            {
                "kind": "org_communication",
                "item_id": "org::COMM-1",
                "sort_at": "2026-04-14T08:00:00",
                "source_type": "school",
                "source_label": "School Update",
                "context_label": "School One",
                "matched_children": children,
                "is_unread": True,
                "org_communication": {
                    "name": "COMM-1",
                    "title": "Whole-school reminder",
                    "communication_type": "Reminder",
                    "status": "Published",
                    "priority": "Normal",
                    "portal_surface": "Guardian Portal",
                    "school": "SCHOOL-1",
                    "organization": "ORG-1",
                    "publish_from": "2026-04-14T08:00:00",
                    "publish_to": None,
                    "brief_start_date": None,
                    "brief_end_date": None,
                    "interaction_mode": "Student Q&A",
                    "allow_private_notes": 0,
                    "allow_public_thread": 1,
                    "snippet": "Bring the signed form tomorrow.",
                    "has_active_thread": 1,
                },
            },
            {
                "kind": "org_communication",
                "item_id": "org::COMM-2",
                "sort_at": "2026-04-13T10:00:00",
                "source_type": "course",
                "source_label": "Class Update",
                "context_label": "Biology A",
                "matched_children": [children[0]],
                "is_unread": False,
                "org_communication": {
                    "name": "COMM-2",
                    "title": "Biology checkpoint",
                    "communication_type": "Information",
                    "status": "Published",
                    "priority": "High",
                    "portal_surface": "Portal Feed",
                    "school": "SCHOOL-1",
                    "organization": "ORG-1",
                    "publish_from": "2026-04-13T10:00:00",
                    "publish_to": None,
                    "brief_start_date": None,
                    "brief_end_date": None,
                    "interaction_mode": "Student Q&A",
                    "allow_private_notes": 0,
                    "allow_public_thread": 1,
                    "snippet": "Study the microscope lab notes.",
                    "has_active_thread": 1,
                },
            },
        ]
        school_event_items = [
            {
                "kind": "school_event",
                "item_id": "event::EVENT-1",
                "sort_at": "2026-04-15T09:00:00",
                "source_type": "school",
                "source_label": "School Event",
                "context_label": "SCHOOL-1",
                "matched_children": children,
                "school_event": {
                    "name": "EVENT-1",
                    "subject": "Spring Showcase",
                    "school": "SCHOOL-1",
                    "location": "Main Hall",
                    "event_type": "Performance",
                    "event_category": "Other",
                    "description": "Families are welcome.",
                    "snippet": "Families are welcome.",
                    "starts_on": "2026-04-15T09:00:00",
                    "ends_on": "2026-04-15T11:00:00",
                    "all_day": 0,
                },
            }
        ]

        with (
            patch(
                "ifitwala_ed.api.guardian_communications.now_datetime",
                return_value=frappe.utils.get_datetime("2026-04-15 09:00:00"),
            ),
            patch(
                "ifitwala_ed.api.guardian_communications._resolve_guardian_communication_context",
                return_value={
                    "children": children,
                    "student_names": ["STU-1", "STU-2"],
                },
            ) as context_mock,
            patch(
                "ifitwala_ed.api.guardian_communications._fetch_guardian_org_communications",
                return_value=org_items,
            ) as fetch_org_mock,
            patch(
                "ifitwala_ed.api.guardian_communications._fetch_guardian_school_events",
                return_value=school_event_items,
            ) as fetch_event_mock,
        ):
            payload = get_guardian_communication_center(student="STU-1", page_length=10)

        fetch_org_mock.assert_called_once_with(context_mock.return_value, selected_student="STU-1")
        fetch_event_mock.assert_called_once_with(context_mock.return_value, selected_student="STU-1")
        self.assertEqual(payload["meta"]["student"], "STU-1")
        self.assertEqual(payload["summary"]["total_items"], 3)
        self.assertEqual(payload["summary"]["unread_items"], 1)
        self.assertEqual(payload["summary"]["source_counts"], {"school": 2, "course": 1})
        self.assertEqual(payload["family"]["children"], children)
        self.assertEqual(payload["items"], school_event_items + org_items)

    def test_fetch_candidate_rows_includes_organization_guardian_audiences(self):
        captured: dict[str, object] = {}

        def fake_sql(sql, values, as_dict=False):
            captured["sql"] = sql
            captured["values"] = values
            return []

        with (
            patch("ifitwala_ed.api.guardian_communications._recent_start_date", return_value="2026-01-10"),
            patch.object(guardian_communications.frappe.db, "sql", side_effect=fake_sql),
        ):
            rows = guardian_communications._fetch_candidate_rows(
                target_groups=set(),
                school_targets=set(),
                organization_targets={"ORG-ROOT"},
            )

        self.assertEqual(rows, [])
        self.assertIn("a.target_mode = 'Organization'", str(captured.get("sql") or ""))
        self.assertEqual((captured.get("values") or {}).get("organization_targets"), ("ORG-ROOT",))

    def test_matched_students_for_audience_allows_organization_targets(self):
        matched_students, matched_groups = guardian_communications._matched_students_for_audience(
            {
                "target_mode": "Organization",
                "to_guardians": 1,
            },
            context={
                "student_names": ["STU-1", "STU-2"],
                "eligible_organization_targets_by_student": {
                    "STU-1": {"ORG-CHILD", "ORG-ROOT"},
                    "STU-2": {"ORG-SIBLING"},
                },
            },
            selected_student=None,
            descendants_cache={},
            comm_organization="ORG-ROOT",
        )

        self.assertEqual(matched_students, {"STU-1"})
        self.assertEqual(matched_groups, set())

    def test_fetch_guardian_school_events_does_not_query_missing_event_type_column(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-2"},
        ]
        context = {
            "user": "guardian@example.com",
            "children": children,
            "child_by_student": {row["student"]: row for row in children},
            "student_names": ["STU-1", "STU-2"],
            "student_school_names": {
                "STU-1": {"SCHOOL-1"},
                "STU-2": {"SCHOOL-2"},
            },
            "membership_by_student": {
                "STU-1": {"GROUP-1"},
                "STU-2": {"GROUP-2"},
            },
        }
        captured: dict[str, object] = {}

        def fake_sql(sql, values, as_dict=False):
            captured["sql"] = sql
            captured["values"] = values
            return [
                {
                    "name": "SE-0001",
                    "subject": "Assembly",
                    "school": "SCHOOL-1",
                    "location": "Hall",
                    "event_category": "Other",
                    "description": "<p>Bring your planner.</p>",
                    "starts_on": "2026-04-10 08:00:00",
                    "ends_on": "2026-04-10 09:00:00",
                    "all_day": 0,
                    "creation": "2026-04-09 12:00:00",
                }
            ]

        def fake_get_all(doctype, filters=None, fields=None):
            if doctype == "School Event Audience":
                return [
                    {
                        "parent": "SE-0001",
                        "audience_type": "Students in Student Group",
                        "student_group": "GROUP-1",
                        "include_guardians": 1,
                        "include_students": 0,
                    }
                ]
            if doctype == "School Event Participant":
                return []
            self.fail(f"Unexpected doctype fetch: {doctype}")

        with (
            patch("ifitwala_ed.api.guardian_communications._recent_start_date", return_value="2026-01-10"),
            patch.object(guardian_communications.frappe.db, "sql", side_effect=fake_sql),
            patch.object(guardian_communications.frappe, "get_all", side_effect=fake_get_all),
        ):
            items = guardian_communications._fetch_guardian_school_events(context)

        self.assertNotIn("se.event_type", str(captured.get("sql") or ""))
        self.assertEqual(
            captured.get("values"),
            {
                "window_start": "2026-01-10",
                "user": "guardian@example.com",
                "target_schools": ("SCHOOL-1", "SCHOOL-2"),
            },
        )
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["school_event"]["subject"], "Assembly")
        self.assertIsNone(items[0]["school_event"]["event_type"])
        self.assertEqual(items[0]["matched_children"], [children[0]])

    def test_fetch_guardian_school_events_matches_parent_school_events_to_descendant_school_children(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "IHS"},
        ]
        context = {
            "user": "guardian@example.com",
            "children": children,
            "child_by_student": {row["student"]: row for row in children},
            "student_names": ["STU-1"],
            "student_school_names": {
                "STU-1": {"IHS"},
            },
            "eligible_school_targets_by_student": {
                "STU-1": {"IHS", "ISS"},
            },
            "membership_by_student": {
                "STU-1": {"GROUP-1"},
            },
        }
        captured: dict[str, object] = {}

        def fake_sql(sql, values, as_dict=False):
            captured["values"] = values
            return [
                {
                    "name": "SE-ISS-0001",
                    "subject": "ISS Parent Workshop",
                    "school": "ISS",
                    "location": "Hall",
                    "event_category": "Parent Engagement",
                    "description": "<p>Parents only.</p>",
                    "starts_on": "2026-04-10 08:00:00",
                    "ends_on": "2026-04-10 09:00:00",
                    "all_day": 0,
                    "creation": "2026-04-09 12:00:00",
                }
            ]

        def fake_get_all(doctype, filters=None, fields=None):
            if doctype == "School Event Audience":
                return [
                    {
                        "parent": "SE-ISS-0001",
                        "audience_type": "All Guardians",
                        "student_group": None,
                        "include_guardians": 0,
                        "include_students": 0,
                    }
                ]
            if doctype == "School Event Participant":
                return []
            self.fail(f"Unexpected doctype fetch: {doctype}")

        with (
            patch("ifitwala_ed.api.guardian_communications._recent_start_date", return_value="2026-01-10"),
            patch.object(guardian_communications.frappe.db, "sql", side_effect=fake_sql),
            patch.object(guardian_communications.frappe, "get_all", side_effect=fake_get_all),
        ):
            items = guardian_communications._fetch_guardian_school_events(context)

        self.assertEqual((captured.get("values") or {}).get("target_schools"), ("IHS", "ISS"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["school_event"]["school"], "ISS")
        self.assertEqual(items[0]["matched_children"], children)


class TestGuardianAttendancePhase2(FrappeTestCase):
    def test_attendance_rejects_out_of_scope_student_filter(self):
        with (
            patch("ifitwala_ed.api.guardian_attendance.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_attendance._resolve_guardian_scope",
                return_value=("GRD-0001", [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]),
            ),
        ):
            with self.assertRaises(frappe.PermissionError):
                get_guardian_attendance_snapshot(student="STU-404", days=60)

    def test_attendance_snapshot_returns_familywide_rows_and_counts(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-1"},
        ]
        attendance_rows = [
            {
                "student": "STU-1",
                "student_name": "Amina Example",
                "summary": {
                    "tracked_days": 2,
                    "present_days": 1,
                    "late_days": 1,
                    "absence_days": 0,
                },
                "days": [
                    {
                        "date": "2026-03-12",
                        "state": "late",
                        "details": [
                            {
                                "attendance": "ATT-1",
                                "time": "08:15",
                                "attendance_code": "L",
                                "attendance_code_name": "Late",
                                "whole_day": False,
                                "course": "Math",
                                "location": None,
                                "remark": "Late bus",
                            }
                        ],
                    }
                ],
            },
            {
                "student": "STU-2",
                "student_name": "Noah Example",
                "summary": {
                    "tracked_days": 1,
                    "present_days": 0,
                    "late_days": 0,
                    "absence_days": 1,
                },
                "days": [
                    {
                        "date": "2026-03-11",
                        "state": "absence",
                        "details": [
                            {
                                "attendance": "ATT-2",
                                "time": None,
                                "attendance_code": "A",
                                "attendance_code_name": "Absent",
                                "whole_day": True,
                                "course": None,
                                "location": "Nurse",
                                "remark": "Sent to nurse",
                            }
                        ],
                    }
                ],
            },
        ]
        counts = {
            "tracked_days": 3,
            "present_days": 1,
            "late_days": 1,
            "absence_days": 1,
        }

        with (
            patch("ifitwala_ed.api.guardian_attendance.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.guardian_attendance.now_datetime",
                return_value=frappe.utils.get_datetime("2026-03-13 09:00:00"),
            ),
            patch(
                "ifitwala_ed.api.guardian_attendance._resolve_guardian_scope",
                return_value=("GRD-0001", children),
            ),
            patch(
                "ifitwala_ed.api.guardian_attendance._build_attendance_students",
                return_value=(attendance_rows, counts),
            ),
        ):
            payload = get_guardian_attendance_snapshot(days=60)

        self.assertEqual(payload["meta"]["guardian"]["name"], "GRD-0001")
        self.assertEqual(payload["family"]["children"], children)
        self.assertEqual(payload["counts"], counts)
        self.assertEqual(payload["students"], attendance_rows)
        self.assertEqual(payload["meta"]["filters"]["days"], 60)
