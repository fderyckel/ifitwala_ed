# ifitwala_ed/api/test_admissions_communication.py

from datetime import timedelta
from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from ifitwala_ed.api.admissions_communication import get_admissions_thread_summaries_for_applicants


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
