from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from ifitwala_ed.admission.api.crm.intake import create_admissions_intake_impl as create_admissions_intake
from ifitwala_ed.admission.api.crm.messages import log_admission_message_impl as log_admission_message
from ifitwala_ed.admission.api.inbox.assignees import (
    search_admissions_inbox_assignees_impl as search_admissions_inbox_assignees,
)
from ifitwala_ed.admission.api.inbox.context import (
    get_admissions_inbox_context_impl as get_admissions_inbox_context,
)
from ifitwala_ed.tests.factories.users import make_user


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

    def test_manual_intake_staff_lane_assigns_inquiry_to_employee_without_moving_crm_owner(self):
        organization = self._make_organization("Inbox Intake Staff Lane")
        school = self._make_school(organization=organization)
        staff_user = self._make_employee_user(organization=organization, school=school)

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            intake = create_admissions_intake(
                organization=organization,
                school=school,
                type_of_inquiry="Admission",
                source="Phone",
                activity_channel="Phone",
                first_name="Staff",
                last_name="Lane",
                message="Family needs academic staff follow-up.",
                activity_type="Reached",
                assigned_to=staff_user.name,
                assignment_lane="Staff",
                client_request_id=f"inbox-intake-staff-{frappe.generate_hash(length=8)}",
            )
        finally:
            frappe.set_user(previous_user)

        inquiry = frappe.db.get_value(
            "Inquiry",
            intake["inquiry"]["name"],
            ["assigned_to", "assignment_lane"],
            as_dict=True,
        )
        conversation_owner = frappe.db.get_value(
            "Admission Conversation",
            intake["conversation"]["name"],
            "assigned_to",
        )

        self.assertEqual(inquiry.assigned_to, staff_user.name)
        self.assertEqual(inquiry.assignment_lane, "Staff")
        self.assertNotEqual(conversation_owner, staff_user.name)

    def test_context_returns_applicant_case_message_needing_reply(self):
        organization = self._make_organization("Inbox Applicant Message")
        school = self._make_school(organization=organization)
        applicant = self._make_applicant(organization=organization, school=school)

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            with patch(
                "ifitwala_ed.admission.api.inbox.context.get_admissions_thread_summaries_for_applicants",
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

    def test_assignee_search_filters_staff_lane_to_employee_linked_staff_users(self):
        organization = self._make_organization("Inbox Assignee Staff")
        school = self._make_school(organization=organization)
        inquiry = self._make_inquiry(organization=organization, school=school)
        staff_user = self._make_employee_user(organization=organization, school=school)
        admission_user = self._make_employee_user(
            organization=organization,
            school=school,
            roles=["Admission Officer"],
        )

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            rows = search_admissions_inbox_assignees(
                context_doctype="Inquiry",
                context_name=inquiry.name,
                assignment_lane="Staff",
                limit=20,
            )
        finally:
            frappe.set_user(previous_user)

        values = {row["value"] for row in rows}
        self.assertIn(staff_user.name, values)
        self.assertNotIn(admission_user.name, values)
        self.assertTrue(all(row["lane"] == "Staff" for row in rows if row["value"] == staff_user.name))

    def test_assignee_search_filters_conversation_assignment_to_admissions_users(self):
        organization = self._make_organization("Inbox Assignee Conversation")
        school = self._make_school(organization=organization)
        staff_user = self._make_employee_user(organization=organization, school=school)
        admission_user = self._make_employee_user(
            organization=organization,
            school=school,
            roles=["Admission Officer"],
        )

        previous_user = frappe.session.user
        try:
            frappe.set_user("Administrator")
            conversation = frappe.get_doc(
                {
                    "doctype": "Admission Conversation",
                    "organization": organization,
                    "school": school,
                }
            )
            conversation.insert(ignore_permissions=True)

            rows = search_admissions_inbox_assignees(
                context_doctype="Admission Conversation",
                context_name=conversation.name,
                assignment_lane="Staff",
                limit=20,
            )
        finally:
            frappe.set_user(previous_user)

        values = {row["value"] for row in rows}
        self.assertIn(admission_user.name, values)
        self.assertNotIn(staff_user.name, values)

    def test_assignee_search_without_context_uses_resolved_user_scope(self):
        captured: dict = {}

        def fake_sql(query, params, as_dict=False):
            captured["query"] = query
            captured["params"] = dict(params)
            captured["as_dict"] = as_dict
            return []

        with (
            patch(
                "ifitwala_ed.admission.api.inbox.assignees.ensure_admissions_crm_permission",
                return_value="officer@example.com",
            ),
            patch(
                "ifitwala_ed.admission.api.inbox.assignees._resolve_scope",
                return_value={
                    "bypass": False,
                    "organization": None,
                    "school": None,
                    "org_scope": ["ORG-ALLOWED"],
                    "school_scope": ["SCH-ALLOWED"],
                },
            ) as resolve_scope,
            patch("ifitwala_ed.admission.api.inbox.assignees.frappe.db.sql", side_effect=fake_sql),
        ):
            rows = search_admissions_inbox_assignees(assignment_lane="Staff", limit=20)

        self.assertEqual(rows, [])
        resolve_scope.assert_called_once_with("officer@example.com", organization=None, school=None)
        self.assertIn("e.organization IN %(org_scope)s", captured["query"])
        self.assertIn("e.school IN %(school_scope)s", captured["query"])
        self.assertEqual(captured["params"]["org_scope"], ("ORG-ALLOWED",))
        self.assertEqual(captured["params"]["school_scope"], ("SCH-ALLOWED",))
        self.assertTrue(captured["as_dict"])

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

    def _make_inquiry(self, *, organization: str, school: str | None = None):
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
                "school": school,
            }
        )
        doc.insert(ignore_permissions=True)
        return doc

    def _ensure_role(self, role: str) -> None:
        if frappe.db.exists("Role", role):
            return
        frappe.get_doc({"doctype": "Role", "role_name": role}).insert(ignore_permissions=True)

    def _make_employee_user(
        self,
        *,
        organization: str,
        school: str | None = None,
        roles: list[str] | None = None,
    ):
        for role in roles or []:
            self._ensure_role(role)

        user = make_user(roles=roles)
        frappe.get_doc(
            {
                "doctype": "Employee",
                "employee_first_name": "Inbox",
                "employee_last_name": f"Assignee-{frappe.generate_hash(length=6)}",
                "employee_gender": "Prefer not to say",
                "employee_professional_email": user.name,
                "organization": organization,
                "school": school,
                "user_id": user.name,
                "date_of_joining": frappe.utils.nowdate(),
                "employment_status": "Active",
            }
        ).insert(ignore_permissions=True)
        return user
