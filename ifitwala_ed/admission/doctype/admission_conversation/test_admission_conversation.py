import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admissions_crm import log_admission_message, record_admission_crm_activity


class TestAdmissionConversation(FrappeTestCase):
    def test_crm_metadata_keeps_messages_and_media_separate_from_files(self):
        conversation_meta = frappe.get_meta("Admission Conversation")
        message_meta = frappe.get_meta("Admission Message")
        activity_meta = frappe.get_meta("Admission CRM Activity")

        self.assertEqual(conversation_meta.get_field("inquiry").options, "Inquiry")
        self.assertEqual(conversation_meta.get_field("student_applicant").options, "Student Applicant")
        self.assertEqual(message_meta.get_field("conversation").options, "Admission Conversation")
        self.assertIsNotNone(message_meta.get_field("media_provider_id"))
        self.assertIsNone(message_meta.get_field("media_file"))
        self.assertEqual(activity_meta.get_field("activity_type").fieldtype, "Select")

    def test_manual_message_logging_updates_needs_reply(self):
        organization = self._make_organization("CRM Manual")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            inbound = log_admission_message(
                organization=organization,
                direction="Inbound",
                body="We are interested in admissions for next year.",
                client_request_id=f"crm-inbound-{frappe.generate_hash(length=8)}",
            )
            conversation_name = inbound["conversation"]["name"]
            self.assertEqual(inbound["conversation"]["needs_reply"], 1)

            outbound = log_admission_message(
                conversation=conversation_name,
                direction="Outbound",
                body="Thanks. The admissions team will follow up with available tour dates.",
                client_request_id=f"crm-outbound-{frappe.generate_hash(length=8)}",
            )
        finally:
            frappe.set_user(previous_user)

        self.assertEqual(outbound["conversation"]["needs_reply"], 0)
        latest = frappe.db.get_value(
            "Admission Conversation",
            conversation_name,
            ["latest_inbound_message_at", "latest_outbound_message_at", "last_message_preview"],
            as_dict=True,
        )
        self.assertTrue(latest.latest_inbound_message_at)
        self.assertTrue(latest.latest_outbound_message_at)
        self.assertIn("Thanks.", latest.last_message_preview)

    def test_crm_activity_updates_next_action(self):
        organization = self._make_organization("CRM Activity")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            inbound = log_admission_message(
                organization=organization,
                direction="Inbound",
                body="Can we arrange a school visit?",
                client_request_id=f"crm-activity-msg-{frappe.generate_hash(length=8)}",
            )
            conversation_name = inbound["conversation"]["name"]
            response = record_admission_crm_activity(
                conversation=conversation_name,
                activity_type="Follow-up Scheduled",
                outcome="Call booked",
                next_action_on="2026-05-01",
                client_request_id=f"crm-activity-{frappe.generate_hash(length=8)}",
            )
        finally:
            frappe.set_user(previous_user)

        self.assertEqual(str(response["conversation"]["next_action_on"]), "2026-05-01")
        self.assertEqual(response["activity"]["activity_type"], "Follow-up Scheduled")

    def test_external_media_metadata_is_not_a_file_attachment(self):
        organization = self._make_organization("CRM Media")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            response = log_admission_message(
                organization=organization,
                direction="Inbound",
                message_type="Document",
                body="Uploaded a document in WhatsApp.",
                media_provider_id="provider-media-123",
                media_mime_type="application/pdf",
                media_file_name="passport.pdf",
                media_size=2048,
                media_status="Available",
                client_request_id=f"crm-media-{frappe.generate_hash(length=8)}",
            )
        finally:
            frappe.set_user(previous_user)

        message = frappe.db.get_value(
            "Admission Message",
            response["message"]["name"],
            ["media_provider_id", "media_status"],
            as_dict=True,
        )
        self.assertEqual(message.media_provider_id, "provider-media-123")
        self.assertEqual(message.media_status, "Available")
        self.assertFalse(
            frappe.db.exists(
                "File",
                {
                    "attached_to_doctype": "Admission Message",
                    "attached_to_name": response["message"]["name"],
                },
            )
        )

    def _make_organization(self, prefix: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"CRM{frappe.generate_hash(length=4)}",
                "is_group": 0,
            }
        )
        doc.flags.skip_coa_setup = True
        doc.insert(ignore_permissions=True)
        return doc.name
