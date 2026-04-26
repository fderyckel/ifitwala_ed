# ifitwala_ed/api/test_admissions_communication.py

from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from ifitwala_ed.api import admissions_communication
from ifitwala_ed.api.admission_cockpit import _ensure_cockpit_access, _get_roles_for_user
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
        with patch(
            "ifitwala_ed.api.admissions_communication.frappe.session",
            SimpleNamespace(user="None"),
        ):
            self.assertEqual(_session_user(), "")

    def test_require_actor_context_rejects_invalid_session_user(self):
        with patch(
            "ifitwala_ed.api.admissions_communication.frappe.session",
            SimpleNamespace(user="None"),
        ):
            with self.assertRaises(frappe.PermissionError):
                _require_actor_context(context_doctype="Student Applicant", context_name="APP-0001")

    def test_case_thread_endpoints_allow_guest_to_reach_auth_guard(self):
        self.assertIn(admissions_communication.send_admissions_case_message, frappe.whitelisted)
        self.assertIn(admissions_communication.get_admissions_case_thread, frappe.whitelisted)
        self.assertIn(admissions_communication.mark_admissions_case_thread_read, frappe.whitelisted)
        self.assertTrue(bool(getattr(admissions_communication.send_admissions_case_message, "allow_guest", False)))
        self.assertTrue(bool(getattr(admissions_communication.get_admissions_case_thread, "allow_guest", False)))
        self.assertTrue(bool(getattr(admissions_communication.mark_admissions_case_thread_read, "allow_guest", False)))


class TestAdmissionsCommunicationCanonicalWriters(FrappeTestCase):
    def test_create_thread_keeps_case_container_out_of_generic_audience_feeds(self):
        fake_doc = SimpleNamespace(name="COMM-0001", audiences=[])
        fake_doc.insert = MagicMock()

        with (
            patch("ifitwala_ed.api.admissions_communication.frappe.db.exists", return_value=False),
            patch("ifitwala_ed.api.admissions_communication.frappe.new_doc", return_value=fake_doc),
        ):
            thread_name = admissions_communication._create_thread(
                context_doctype="Student Applicant",
                context_name="APP-0001",
                context_row={"organization": "ORG-1", "school": "SCH-1"},
            )

        self.assertEqual(thread_name, "COMM-0001")
        self.assertEqual(fake_doc.status, "Draft")
        self.assertEqual(fake_doc.portal_surface, "Desk")
        self.assertEqual(fake_doc.admission_context_doctype, "Student Applicant")
        self.assertEqual(fake_doc.admission_context_name, "APP-0001")
        self.assertEqual(fake_doc.audiences, [])
        fake_doc.insert.assert_called_once_with(ignore_permissions=True)

    def test_send_message_uses_canonical_entry_writer(self):
        created_at = now_datetime()
        actor_ctx = {
            "actor": "applicant",
            "user": "applicant@example.com",
            "context": {"name": "APP-0001", "organization": "ORG-1", "school": "SCH-1"},
            "applicant_user": "applicant@example.com",
        }
        latest_row = {
            "name": "ENTRY-0001",
            "user": "applicant@example.com",
            "note": "Can I upload the passport tomorrow?",
            "visibility": "Private to school",
            "creation": created_at,
            "modified": created_at,
            "full_name": "Applicant One",
        }

        with (
            patch("ifitwala_ed.api.admissions_communication._require_actor_context", return_value=actor_ctx),
            patch("ifitwala_ed.api.admissions_communication._get_or_create_thread", return_value="COMM-0001"),
            patch(
                "ifitwala_ed.api.admissions_communication.create_interaction_entry",
                return_value=latest_row,
            ) as create_entry_mock,
            patch(
                "ifitwala_ed.api.admissions_communication.get_latest_org_communication_entry_for_user",
                return_value=latest_row,
            ),
        ):
            result = admissions_communication.send_admissions_case_message(
                context_doctype="Student Applicant",
                context_name="APP-0001",
                body="Can I upload the passport tomorrow?",
            )

        create_entry_mock.assert_called_once_with(
            org_communication="COMM-0001",
            user="applicant@example.com",
            intent_type="Question",
            note="Can I upload the passport tomorrow?",
            visibility="Private to school",
            surface="Other",
        )
        self.assertEqual(result["thread_name"], "COMM-0001")
        self.assertEqual(result["message"]["name"], "ENTRY-0001")
        self.assertEqual(result["message"]["direction"], "ApplicantToStaff")

    def test_mark_thread_read_delegates_to_shared_read_receipt(self):
        read_at = now_datetime()
        actor_ctx = {
            "actor": "applicant",
            "user": "applicant@example.com",
            "context": {"name": "APP-0001"},
            "applicant_user": "applicant@example.com",
        }

        with (
            patch("ifitwala_ed.api.admissions_communication._require_actor_context", return_value=actor_ctx),
            patch("ifitwala_ed.api.admissions_communication._get_thread_name", return_value="COMM-0001"),
            patch("ifitwala_ed.api.admissions_communication.now_datetime", return_value=read_at),
            patch("ifitwala_ed.api.admissions_communication.upsert_org_communication_read_receipt") as mark_read_mock,
        ):
            result = admissions_communication.mark_admissions_case_thread_read(
                context_doctype="Student Applicant",
                context_name="APP-0001",
            )

        mark_read_mock.assert_called_once_with(
            user="applicant@example.com",
            org_communication="COMM-0001",
            read_at=read_at,
        )
        self.assertEqual(result, {"ok": True, "thread_name": "COMM-0001", "read_at": read_at})


class TestAdmissionsCockpitAuthGuards(FrappeTestCase):
    def test_cockpit_access_rejects_none_literal_without_role_lookup(self):
        with (
            patch(
                "ifitwala_ed.api.admission_cockpit.frappe.session",
                SimpleNamespace(user="None"),
            ),
            patch("ifitwala_ed.api.admission_cockpit.frappe.get_roles") as get_roles_mock,
        ):
            with self.assertRaises(frappe.PermissionError):
                _ensure_cockpit_access()

        get_roles_mock.assert_not_called()

    def test_get_roles_for_user_rejects_none_user_not_found(self):
        with patch(
            "ifitwala_ed.api.admission_cockpit.frappe.get_roles",
            side_effect=RuntimeError("User None not found"),
        ):
            with self.assertRaises(frappe.PermissionError):
                _get_roles_for_user("None")
