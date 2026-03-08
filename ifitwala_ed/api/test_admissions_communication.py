# ifitwala_ed/api/test_admissions_communication.py

from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from ifitwala_ed.api import admissions_communication
from ifitwala_ed.api.admission_cockpit import _ensure_cockpit_access
from ifitwala_ed.api.admissions_communication import (
    _require_actor_context,
    _session_user,
    get_admissions_thread_summaries_for_applicants,
)


class TestAdmissionsCommunicationSummaries(FrappeTestCase):
    def test_returns_empty_when_no_applicants(self):
        result = get_admissions_thread_summaries_for_applicants(applicant_rows=[], user="staff@example.com")
        self.assertEqual(result, {})

    def test_unread_applicant_reply_sets_needs_reply(self):
        applicant_rows = [{"name": "APP-0001", "applicant_user": "applicant@example.com"}]
        created_at = now_datetime() - timedelta(minutes=10)

        def fake_get_all(doctype, **kwargs):
            if doctype == "Org Communication":
                return [{"name": "COMM-0001", "admission_context_name": "APP-0001"}]
            if doctype == "Portal Read Receipt":
                return []
            return []

        with (
            patch("ifitwala_ed.api.admissions_communication.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.admissions_communication.frappe.db.table_exists", return_value=True),
            patch(
                "ifitwala_ed.api.admissions_communication.frappe.db.sql",
                return_value=[
                    {
                        "org_communication": "COMM-0001",
                        "user": "applicant@example.com",
                        "note": "We uploaded the passport copy.",
                        "visibility": "Private to school",
                        "creation": created_at,
                    }
                ],
            ),
        ):
            result = get_admissions_thread_summaries_for_applicants(
                applicant_rows=applicant_rows,
                user="staff@example.com",
            )

        row = result["APP-0001"]
        self.assertEqual(row["thread_name"], "COMM-0001")
        self.assertEqual(row["unread_count"], 1)
        self.assertEqual(row["last_message_from"], "applicant")
        self.assertTrue(bool(row["needs_reply"]))
        self.assertIn("passport", row["last_message_preview"])

    def test_read_receipt_clears_unread_but_preserves_last_message(self):
        applicant_rows = [{"name": "APP-0002", "applicant_user": "applicant@example.com"}]
        created_at = now_datetime() - timedelta(hours=2)
        read_at = now_datetime() - timedelta(minutes=15)

        def fake_get_all(doctype, **kwargs):
            if doctype == "Org Communication":
                return [{"name": "COMM-0002", "admission_context_name": "APP-0002"}]
            if doctype == "Portal Read Receipt":
                return [{"reference_name": "COMM-0002", "read_at": read_at}]
            return []

        with (
            patch("ifitwala_ed.api.admissions_communication.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.admissions_communication.frappe.db.table_exists", return_value=True),
            patch(
                "ifitwala_ed.api.admissions_communication.frappe.db.sql",
                return_value=[
                    {
                        "org_communication": "COMM-0002",
                        "user": "applicant@example.com",
                        "note": "Please confirm interview date.",
                        "visibility": "Private to school",
                        "creation": created_at,
                    }
                ],
            ),
        ):
            result = get_admissions_thread_summaries_for_applicants(
                applicant_rows=applicant_rows,
                user="staff@example.com",
            )

        row = result["APP-0002"]
        self.assertEqual(row["unread_count"], 0)
        self.assertEqual(row["last_message_from"], "applicant")
        self.assertFalse(bool(row["needs_reply"]))

    def test_staff_visible_message_marks_last_from_staff(self):
        applicant_rows = [{"name": "APP-0003", "applicant_user": "applicant@example.com"}]
        created_at = now_datetime() - timedelta(minutes=3)

        def fake_get_all(doctype, **kwargs):
            if doctype == "Org Communication":
                return [{"name": "COMM-0003", "admission_context_name": "APP-0003"}]
            if doctype == "Portal Read Receipt":
                return []
            return []

        with (
            patch("ifitwala_ed.api.admissions_communication.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.admissions_communication.frappe.db.table_exists", return_value=True),
            patch(
                "ifitwala_ed.api.admissions_communication.frappe.db.sql",
                return_value=[
                    {
                        "org_communication": "COMM-0003",
                        "user": "staff@example.com",
                        "note": "Please upload the translated birth certificate.",
                        "visibility": "Public to audience",
                        "creation": created_at,
                    }
                ],
            ),
        ):
            result = get_admissions_thread_summaries_for_applicants(
                applicant_rows=applicant_rows,
                user="staff@example.com",
            )

        row = result["APP-0003"]
        self.assertEqual(row["unread_count"], 0)
        self.assertEqual(row["last_message_from"], "staff")
        self.assertFalse(bool(row["needs_reply"]))


class TestAdmissionsCommunicationAuthGuards(FrappeTestCase):
    def test_session_user_treats_none_literal_as_unauthenticated(self):
        with patch("ifitwala_ed.api.admissions_communication.frappe.session.user", "None"):
            self.assertEqual(_session_user(), "")

    def test_require_actor_context_rejects_invalid_session_user(self):
        with patch("ifitwala_ed.api.admissions_communication.frappe.session.user", "None"):
            with self.assertRaises(frappe.PermissionError):
                _require_actor_context(context_doctype="Student Applicant", context_name="APP-0001")

    def test_case_thread_endpoints_allow_guest_to_reach_auth_guard(self):
        self.assertTrue(bool(getattr(admissions_communication.send_admissions_case_message, "allow_guest", False)))
        self.assertTrue(bool(getattr(admissions_communication.get_admissions_case_thread, "allow_guest", False)))
        self.assertTrue(bool(getattr(admissions_communication.mark_admissions_case_thread_read, "allow_guest", False)))


class TestAdmissionsCockpitAuthGuards(FrappeTestCase):
    def test_cockpit_access_rejects_none_literal_without_role_lookup(self):
        with (
            patch("ifitwala_ed.api.admission_cockpit.frappe.session.user", "None"),
            patch("ifitwala_ed.api.admission_cockpit.frappe.get_roles") as get_roles_mock,
        ):
            with self.assertRaises(frappe.PermissionError):
                _ensure_cockpit_access()

        get_roles_mock.assert_not_called()


class TestAdmissionsCaseReadReceiptUpsert(FrappeTestCase):
    def test_upsert_retries_deadlock_and_succeeds(self):
        class QueryDeadlockError(Exception):
            pass

        read_at = now_datetime()
        with (
            patch("ifitwala_ed.api.admissions_communication.frappe.cache") as cache_mock,
            patch(
                "ifitwala_ed.api.admissions_communication.frappe.db.sql",
                side_effect=[QueryDeadlockError("deadlock"), None],
            ) as sql_mock,
            patch(
                "ifitwala_ed.api.admissions_communication.frappe.generate_hash",
                side_effect=["receipt-a", "receipt-b", "receipt-c"],
            ),
            patch("ifitwala_ed.api.admissions_communication.time.sleep") as sleep_mock,
        ):
            cache_mock.return_value.lock.return_value = nullcontext()
            admissions_communication._upsert_portal_read_receipt(
                user="applicant@example.com",
                thread_name="COMM-0001",
                read_at=read_at,
            )

        self.assertEqual(sql_mock.call_count, 2)
        sleep_mock.assert_called_once_with(admissions_communication.READ_RECEIPT_RETRY_BASE_DELAY_SEC)

    def test_upsert_raises_non_deadlock_errors(self):
        read_at = now_datetime()
        with (
            patch("ifitwala_ed.api.admissions_communication.frappe.cache") as cache_mock,
            patch(
                "ifitwala_ed.api.admissions_communication.frappe.db.sql",
                side_effect=RuntimeError("db failure"),
            ),
            patch(
                "ifitwala_ed.api.admissions_communication.frappe.generate_hash",
                return_value="receipt-a",
            ),
        ):
            cache_mock.return_value.lock.return_value = nullcontext()
            with self.assertRaises(RuntimeError):
                admissions_communication._upsert_portal_read_receipt(
                    user="applicant@example.com",
                    thread_name="COMM-0001",
                    read_at=read_at,
                )
