from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from ifitwala_ed.api.admissions_crm import create_admissions_intake, log_admission_message
from ifitwala_ed.api.admissions_inbox import get_admissions_inbox_context


class TestAdmissionsInbox(FrappeTestCase):
    def test_context_returns_render_ready_inquiry_queues(self):
        organization = self._make_organization("Inbox Inquiry")
        inquiry = self._make_inquiry(organization=organization)
        frappe.db.set_value(
            "Inquiry",
            inquiry.name,
            {
                "first_contact_due_on": add_days(nowdate(), -1),
                "assigned_to": None,
            },
            update_modified=False,
        )

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            context = get_admissions_inbox_context(organization=organization, limit=10)
        finally:
            frappe.set_user(previous_user)

        unassigned = self._queue(context, "unassigned")
        overdue = self._queue(context, "overdue_first_contact")

        self.assertTrue(any(row["inquiry"] == inquiry.name for row in unassigned["rows"]))
        self.assertTrue(any(row["inquiry"] == inquiry.name for row in overdue["rows"]))

        row = next(row for row in unassigned["rows"] if row["inquiry"] == inquiry.name)
        self.assertEqual(row["kind"], "inquiry")
        self.assertEqual(row["open_url"], f"/desk/inquiry/{inquiry.name}")
        self.assertIn("log_message", {action["id"] for action in row["actions"]})
        self.assertIn("mark_contacted", {action["id"] for action in row["actions"]})

    def test_context_returns_needs_reply_conversation_queue(self):
        organization = self._make_organization("Inbox Conversation")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            logged = log_admission_message(
                organization=organization,
                direction="Inbound",
                body="Can someone call me about admissions?",
                client_request_id=f"inbox-msg-{frappe.generate_hash(length=8)}",
            )
            context = get_admissions_inbox_context(organization=organization, limit=10)
        finally:
            frappe.set_user(previous_user)

        needs_reply = self._queue(context, "needs_reply")
        self.assertTrue(any(row["conversation"] == logged["conversation"]["name"] for row in needs_reply["rows"]))

        row = next(row for row in needs_reply["rows"] if row["conversation"] == logged["conversation"]["name"])
        self.assertEqual(row["kind"], "conversation")
        self.assertEqual(row["open_url"], f"/desk/admission-conversation/{logged['conversation']['name']}")
        self.assertTrue(row["needs_reply"])
        self.assertIn("log_reply", {action["id"] for action in row["actions"]})
        self.assertEqual(row["last_message_preview"], "Can someone call me about admissions?")

    def test_context_uses_manual_intake_next_action_for_due_today(self):
        organization = self._make_organization("Inbox Intake")

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            intake = create_admissions_intake(
                organization=organization,
                type_of_inquiry="Admission",
                source="Community Fair",
                activity_channel="In Person",
                first_name="Fair",
                last_name="Family",
                message="Met family at the community fair.",
                activity_type="Reached",
                note="Call today to arrange a tour.",
                next_action_on=nowdate(),
                client_request_id=f"inbox-intake-{frappe.generate_hash(length=8)}",
            )
            context = get_admissions_inbox_context(organization=organization, limit=10)
        finally:
            frappe.set_user(previous_user)

        due_today = self._queue(context, "due_today")
        self.assertTrue(any(row["inquiry"] == intake["inquiry"]["name"] for row in due_today["rows"]))
        row = next(row for row in due_today["rows"] if row["inquiry"] == intake["inquiry"]["name"])
        self.assertEqual(row["kind"], "inquiry")
        self.assertEqual(row["conversation"], intake["conversation"]["name"])
        self.assertEqual(row["next_action_on"], nowdate())

    def test_context_returns_applicant_case_message_needing_reply(self):
        organization = self._make_organization("Inbox Applicant Message")
        school = self._make_school(organization=organization)
        applicant = self._make_applicant(organization=organization, school=school)

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            with patch(
                "ifitwala_ed.api.admissions_inbox.get_admissions_thread_summaries_for_applicants",
                return_value={
                    applicant.name: {
                        "thread_name": "COMM-0001",
                        "unread_count": 1,
                        "last_message_at": "2026-04-30 09:00:00",
                        "last_message_preview": "Can I upload the passport tomorrow?",
                        "last_message_from": "applicant",
                        "needs_reply": True,
                    }
                },
            ):
                context = get_admissions_inbox_context(organization=organization, limit=10)
        finally:
            frappe.set_user(previous_user)

        needs_reply = self._queue(context, "needs_reply")
        self.assertTrue(any(row["student_applicant"] == applicant.name for row in needs_reply["rows"]))
        row = next(row for row in needs_reply["rows"] if row["student_applicant"] == applicant.name)
        self.assertEqual(row["kind"], "applicant_message")
        self.assertEqual(row["org_communication"], "COMM-0001")
        self.assertEqual(row["unread_count"], 1)
        self.assertTrue(row["needs_reply"])
        self.assertIn("reply_applicant_case", {action["id"] for action in row["actions"]})

    def test_context_scope_filter_excludes_other_organizations(self):
        included_org = self._make_organization("Inbox Included")
        excluded_org = self._make_organization("Inbox Excluded")
        included_inquiry = self._make_inquiry(organization=included_org)
        excluded_inquiry = self._make_inquiry(organization=excluded_org)

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            context = get_admissions_inbox_context(organization=included_org, limit=10)
        finally:
            frappe.set_user(previous_user)

        names = {row["inquiry"] for queue in context["queues"] for row in queue["rows"] if row.get("inquiry")}
        self.assertIn(included_inquiry.name, names)
        self.assertNotIn(excluded_inquiry.name, names)

    def _queue(self, context: dict, queue_id: str) -> dict:
        for queue in context["queues"]:
            if queue["id"] == queue_id:
                return queue
        self.fail(f"Queue not found: {queue_id}")

    def _make_organization(self, prefix: str) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"{prefix} {frappe.generate_hash(length=6)}",
                "abbr": f"INB{frappe.generate_hash(length=4)}",
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
                "school_name": f"Inbox School {frappe.generate_hash(length=6)}",
                "abbr": f"IS{frappe.generate_hash(length=3)}",
                "organization": organization,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc.name

    def _make_applicant(self, *, organization: str, school: str):
        doc = frappe.get_doc(
            {
                "doctype": "Student Applicant",
                "first_name": "Inbox",
                "last_name": f"Applicant-{frappe.generate_hash(length=6)}",
                "organization": organization,
                "school": school,
                "application_status": "Draft",
            }
        )
        doc.insert(ignore_permissions=True)
        doc.db_set("applicant_user", f"applicant-{frappe.generate_hash(length=8)}@example.com", update_modified=False)
        doc.db_set("application_status", "In Progress", update_modified=False)
        doc.reload()
        return doc

    def _make_inquiry(self, *, organization: str):
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Inbox",
                "last_name": f"Lead-{frappe.generate_hash(length=6)}",
                "email": f"inbox-{frappe.generate_hash(length=8)}@example.com",
                "type_of_inquiry": "Admission",
                "source": "Website",
                "message": "We would like to ask about admissions.",
                "organization": organization,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc
