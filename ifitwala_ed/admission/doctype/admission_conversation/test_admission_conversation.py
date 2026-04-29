from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admissions_crm import (
    archive_inquiry_from_inbox,
    create_inquiry_from_admission_conversation,
    log_admission_message,
    mark_inquiry_contacted_from_inbox,
    qualify_inquiry_from_inbox,
    record_admission_crm_activity,
    update_admission_conversation_status,
)


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

    def test_create_inquiry_from_conversation_links_existing_crm_case(self):
        organization = self._make_organization("CRM Create Inquiry")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            inbound = log_admission_message(
                organization=organization,
                direction="Inbound",
                body="I would like admissions information.",
                client_request_id=f"crm-create-inquiry-msg-{frappe.generate_hash(length=8)}",
            )
            response = create_inquiry_from_admission_conversation(
                conversation=inbound["conversation"]["name"],
                client_request_id=f"crm-create-inquiry-{frappe.generate_hash(length=8)}",
            )
        finally:
            frappe.set_user(previous_user)

        inquiry_name = response["inquiry"]["name"]
        self.assertEqual(response["conversation"]["inquiry"], inquiry_name)
        inquiry = frappe.db.get_value(
            "Inquiry",
            inquiry_name,
            ["organization", "type_of_inquiry", "source", "message"],
            as_dict=True,
        )
        self.assertEqual(inquiry.organization, organization)
        self.assertEqual(inquiry.type_of_inquiry, "Admission")
        self.assertEqual(inquiry.source, "Other")
        self.assertEqual(inquiry.message, "I would like admissions information.")

    def test_update_conversation_status_archives_and_clears_reply_need(self):
        organization = self._make_organization("CRM Archive Conversation")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            inbound = log_admission_message(
                organization=organization,
                direction="Inbound",
                body="Please stop contacting me.",
                client_request_id=f"crm-archive-msg-{frappe.generate_hash(length=8)}",
            )
            response = update_admission_conversation_status(
                conversation=inbound["conversation"]["name"],
                status="Archived",
                note="Parent withdrew inquiry.",
                client_request_id=f"crm-archive-{frappe.generate_hash(length=8)}",
            )
        finally:
            frappe.set_user(previous_user)

        self.assertEqual(response["conversation"]["status"], "Archived")
        self.assertEqual(response["conversation"]["needs_reply"], 0)
        self.assertEqual(response["activity"]["activity_type"], "Archived")

    def test_inquiry_workflow_endpoints_reuse_existing_controller_methods(self):
        inquiry = self._make_inquiry()
        inquiry.db_set("workflow_state", "Assigned", update_modified=False)
        inquiry.reload()

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            contacted = mark_inquiry_contacted_from_inbox(
                inquiry=inquiry.name,
                client_request_id=f"crm-contacted-{frappe.generate_hash(length=8)}",
            )
            with patch(
                "ifitwala_ed.admission.doctype.inquiry.inquiry.ensure_admissions_permission",
                return_value="Administrator",
            ):
                qualified = qualify_inquiry_from_inbox(
                    inquiry=inquiry.name,
                    client_request_id=f"crm-qualified-{frappe.generate_hash(length=8)}",
                )
                archived = archive_inquiry_from_inbox(
                    inquiry=inquiry.name,
                    reason="Duplicate inquiry.",
                    client_request_id=f"crm-archive-inquiry-{frappe.generate_hash(length=8)}",
                )
        finally:
            frappe.set_user(previous_user)

        self.assertEqual(contacted["inquiry"]["workflow_state"], "Contacted")
        self.assertEqual(qualified["inquiry"]["workflow_state"], "Qualified")
        self.assertEqual(archived["inquiry"]["workflow_state"], "Archived")
        self.assertEqual(archived["inquiry"]["archive_reason"], "Duplicate inquiry.")

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

    def _make_inquiry(self):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "CRM",
                "last_name": f"Workflow-{frappe.generate_hash(length=6)}",
                "type_of_inquiry": "Admission",
                "message": "Admissions workflow test.",
            }
        )
        doc.insert(ignore_permissions=True)
        return doc
