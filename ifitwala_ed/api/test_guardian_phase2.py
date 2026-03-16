# ifitwala_ed/api/test_guardian_phase2.py

from unittest.mock import Mock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.guardian_attendance import get_guardian_attendance_snapshot
from ifitwala_ed.api.guardian_finance import _resolve_finance_scope, get_guardian_finance_snapshot
from ifitwala_ed.api.guardian_monitoring import (
    get_guardian_monitoring_snapshot,
    mark_guardian_student_log_read,
)
from ifitwala_ed.api.guardian_policy import (
    _children_with_signer_authority,
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
            patch("ifitwala_ed.api.guardian_policy.frappe.get_doc", return_value=acknowledgement_doc) as get_doc_mock,
        ):
            result = acknowledge_guardian_policy("VER-1")

        self.assertEqual(result["status"], "acknowledged")
        self.assertEqual(result["acknowledgement_name"], "ACK-0002")
        acknowledgement_doc.insert.assert_called_once_with()
        payload = get_doc_mock.call_args.args[0]
        self.assertEqual(payload["acknowledged_for"], "Guardian")
        self.assertEqual(payload["context_name"], "GRD-0001")

    def test_children_with_signer_authority_filters_to_consent_enabled_links(self):
        children = [
            {"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"},
            {"student": "STU-2", "full_name": "Noah Example", "school": "SCHOOL-1"},
        ]

        with (
            patch("ifitwala_ed.api.guardian_policy.frappe.db.has_column", return_value=True),
            patch(
                "ifitwala_ed.api.guardian_policy.frappe.get_all",
                return_value=[{"parent": "STU-1"}],
            ),
        ):
            filtered = _children_with_signer_authority(guardian_name="GRD-0001", children=children)

        self.assertEqual(filtered, [children[0]])

    def test_query_policy_candidates_accepts_multi_audience_guardian_rows(self):
        candidate_rows = [
            {
                "policy_name": "POL-1",
                "policy_key": "family_handbook",
                "policy_title": "Family Handbook",
                "policy_category": "Handbooks",
                "applies_to": "Guardian\nStudent",
                "description": "",
                "policy_organization": "ORG-1",
                "policy_school": "SCHOOL-1",
                "policy_version": "VER-1",
                "version_label": "v1",
                "policy_text": "<p>Policy</p>",
                "effective_from": None,
                "effective_to": None,
                "approved_on": None,
            },
            {
                "policy_name": "POL-2",
                "policy_key": "student_only",
                "policy_title": "Student Only",
                "policy_category": "Academic",
                "applies_to": "Student",
                "description": "",
                "policy_organization": "ORG-1",
                "policy_school": "SCHOOL-1",
                "policy_version": "VER-2",
                "version_label": "v1",
                "policy_text": "<p>Policy</p>",
                "effective_from": None,
                "effective_to": None,
                "approved_on": None,
            },
        ]

        with (
            patch(
                "ifitwala_ed.api.guardian_policy.get_organization_ancestors_including_self",
                return_value=["ORG-1"],
            ),
            patch(
                "ifitwala_ed.api.guardian_policy.get_school_ancestors_including_self",
                return_value=["SCHOOL-1"],
            ),
            patch("ifitwala_ed.api.guardian_policy.frappe.db.sql", return_value=candidate_rows),
            patch(
                "ifitwala_ed.api.guardian_policy.select_nearest_policy_rows_by_key",
                side_effect=lambda **kwargs: kwargs["rows"],
            ),
        ):
            rows = _query_policy_candidates_for_context(organization="ORG-1", school="SCHOOL-1")

        self.assertEqual([row["policy_name"] for row in rows], ["POL-1"])


class TestGuardianFinancePhase2(FrappeTestCase):
    def test_finance_scope_authorizes_account_holder_by_email_match(self):
        children = [{"student": "STU-1", "full_name": "Amina Example", "school": "SCHOOL-1"}]

        def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit_page_length=None):
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
        published_results = [
            {
                "task_outcome": "OUT-1",
                "student": "STU-2",
                "student_name": "Noah Example",
                "title": "Science assessment",
                "published_on": "2026-03-11 09:00:00",
            }
        ]

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
            patch("ifitwala_ed.api.guardian_monitoring._get_monitoring_logs", return_value=student_logs),
            patch("ifitwala_ed.api.guardian_monitoring._get_monitoring_results", return_value=published_results),
        ):
            payload = get_guardian_monitoring_snapshot(days=30)

        self.assertEqual(payload["counts"]["visible_student_logs"], 1)
        self.assertEqual(payload["counts"]["unread_visible_student_logs"], 1)
        self.assertEqual(payload["counts"]["published_results"], 1)
        self.assertEqual(payload["family"]["children"], children)

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
