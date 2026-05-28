from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.admissions_crm import create_admissions_intake, log_admission_message
from ifitwala_ed.api.admissions_timeline import get_admissions_timeline_context


class TestAdmissionsTimeline(FrappeTestCase):
    def test_inquiry_timeline_projects_existing_ledgers(self):
        organization = self._make_organization("Timeline Inquiry")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            intake = create_admissions_intake(
                organization=organization,
                type_of_inquiry="Admission",
                source="Website",
                activity_channel="In Person",
                first_name="Timeline",
                last_name="Family",
                email="timeline-family@example.com",
                phone_number="+15550001111",
                message="We would like to understand the admissions process.",
                activity_type="Reached",
                note="Family asked for a campus tour.",
                client_request_id=f"timeline-intake-{frappe.generate_hash(length=8)}",
            )
            log_admission_message(
                conversation=intake["conversation"]["name"],
                direction="Inbound",
                body="Can we visit the school next week?",
                client_request_id=f"timeline-message-{frappe.generate_hash(length=8)}",
            )
            context = get_admissions_timeline_context(
                context_doctype="Inquiry",
                context_name=intake["inquiry"]["name"],
                limit=20,
            )
        finally:
            frappe.set_user(previous_user)

        source_pairs = {(item["source_doctype"], item["kind"]) for item in context["items"]}
        self.assertIn(("Inquiry", "intake"), source_pairs)
        self.assertIn(("Admission Conversation", "touchpoint"), source_pairs)
        self.assertIn(("Admission CRM Activity", "touchpoint"), source_pairs)
        self.assertIn(("Admission Message", "message"), source_pairs)
        self.assertNotIn("Admissions Timeline", {item["source_doctype"] for item in context["items"]})

        self.assertEqual(context["context"]["doctype"], "Inquiry")
        self.assertEqual(context["context"]["name"], intake["inquiry"]["name"])
        self.assertEqual(context["context"]["organization"], organization)
        self.assertEqual(context["context"]["inquiry"], intake["inquiry"]["name"])
        self.assertIn("completion_ladder", context["summary"])

        action_ids = {action["id"] for action in context["actions"]}
        self.assertIn("log_activity", action_ids)
        self.assertIn("log_message", action_ids)
        self.assertIn("schedule_visit", action_ids)
        self.assertIn("invite_to_apply", action_ids)
        self.assertIn("archive", action_ids)

        payload = frappe.as_json(context)
        self.assertNotIn("timeline-family@example.com", payload)
        self.assertNotIn("+15550001111", payload)

    def test_timeline_is_bounded(self):
        organization = self._make_organization("Timeline Bounded")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            intake = create_admissions_intake(
                organization=organization,
                type_of_inquiry="Admission",
                source="Community Fair",
                activity_channel="In Person",
                first_name="Bounded",
                last_name="Family",
                message="We met at the community fair.",
                activity_type="Reached",
                note="Call back tomorrow.",
                client_request_id=f"timeline-bound-{frappe.generate_hash(length=8)}",
            )
            log_admission_message(
                conversation=intake["conversation"]["name"],
                direction="Inbound",
                body="Thank you for the information.",
                client_request_id=f"timeline-bound-msg-{frappe.generate_hash(length=8)}",
            )
            context = get_admissions_timeline_context(
                context_doctype="Inquiry",
                context_name=intake["inquiry"]["name"],
                limit=1,
            )
        finally:
            frappe.set_user(previous_user)

        self.assertEqual(len(context["items"]), 1)
        self.assertTrue(context["has_more"])
        self.assertEqual(context["context"]["limit"], 1)

    def test_applicant_timeline_includes_case_communication(self):
        organization = self._make_organization("Timeline Applicant")
        school = self._make_school(organization=organization)
        applicant = self._make_applicant(organization=organization, school=school)

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            with patch(
                "ifitwala_ed.admission.api.timeline.context.get_admissions_thread_summaries_for_applicants",
                return_value={
                    applicant.name: {
                        "thread_name": "COMM-TIMELINE-0001",
                        "unread_count": 1,
                        "last_message_at": "2026-05-22 09:00:00",
                        "last_message_preview": "Could we send the transcript tomorrow?",
                        "last_message_from": "applicant",
                        "needs_reply": True,
                    }
                },
            ):
                context = get_admissions_timeline_context(
                    context_doctype="Student Applicant",
                    context_name=applicant.name,
                    limit=20,
                )
        finally:
            frappe.set_user(previous_user)

        case_items = [item for item in context["items"] if item["source_doctype"] == "Org Communication"]
        self.assertEqual(len(case_items), 1)
        self.assertEqual(case_items[0]["kind"], "message")
        self.assertEqual(case_items[0]["source_name"], "COMM-TIMELINE-0001")
        self.assertTrue(context["summary"]["needs_reply"])

        action_by_id = {action["id"]: action for action in context["actions"]}
        self.assertTrue(action_by_id["message_family"]["enabled"])
        self.assertTrue(action_by_id["manage_offer"]["enabled"])
        self.assertFalse(action_by_id["log_activity"]["enabled"])
        self.assertIn("Log a message first", action_by_id["log_activity"]["disabled_reason"])
        self.assertFalse(action_by_id["check_deposit"]["enabled"])

    def _make_organization(self, prefix: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"TML{frappe.generate_hash(length=4)}",
                "is_group": 0,
            }
        )
        doc.flags.skip_coa_setup = True
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_school(self, *, organization: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"Timeline School {frappe.generate_hash(length=6)}",
                "abbr": f"TS{frappe.generate_hash(length=3)}",
                "organization": organization,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_applicant(self, *, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Timeline",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        )
        doc.insert(ignore_permissions=True)
        doc.db_set(
            "applicant_user",
            f"timeline-applicant-{frappe.generate_hash(length=8)}@example.com",
            update_modified=False,
        )
        doc.db_set("application_status", "In Progress", update_modified=False)
        doc.reload()
        return doc
