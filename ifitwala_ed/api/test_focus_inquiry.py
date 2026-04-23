# ifitwala_ed/api/test_focus_inquiry.py
# Copyright (c) 2026, François de Ryckel and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.focus import (
    ACTION_INQUIRY_FIRST_CONTACT,
    build_focus_item_id,
    create_inquiry_contact,
    get_focus_context,
    mark_inquiry_contacted,
)
from ifitwala_ed.tests.factories.users import make_user

_REQUIRED_TEST_APPS = ("frappe", "ifitwala_ed")
_ORIGINAL_GET_INSTALLED_APPS = getattr(frappe, "get_installed_apps", None)


def _get_test_installed_apps(*args, **kwargs):
    apps = []
    if callable(_ORIGINAL_GET_INSTALLED_APPS):
        try:
            apps = list(_ORIGINAL_GET_INSTALLED_APPS(*args, **kwargs) or [])
        except Exception:
            apps = []
    for app_name in _REQUIRED_TEST_APPS:
        if app_name not in apps:
            apps.append(app_name)
    return apps


class TestFocusInquiry(FrappeTestCase):
    def setUp(self):
        super().setUp()
        self._installed_apps_patcher = patch.object(
            frappe,
            "get_installed_apps",
            side_effect=_get_test_installed_apps,
        )
        self._installed_apps_patcher.start()
        self._notification_states: list[tuple[str, int]] = []
        for notification_name in ("Inquiry Assigned", "Notify Admission Manager"):
            if not frappe.db.exists("Notification", notification_name):
                continue
            enabled = int(frappe.db.get_value("Notification", notification_name, "enabled") or 0)
            self._notification_states.append((notification_name, enabled))
            if enabled:
                frappe.db.set_value(
                    "Notification",
                    notification_name,
                    "enabled",
                    0,
                    update_modified=False,
                )
        if self._notification_states:
            frappe.clear_cache()

    def tearDown(self):
        frappe.set_user("Administrator")
        for notification_name, enabled in self._notification_states:
            if frappe.db.exists("Notification", notification_name):
                frappe.db.set_value(
                    "Notification",
                    notification_name,
                    "enabled",
                    enabled,
                    update_modified=False,
                )
        if self._notification_states:
            frappe.clear_cache()
        self._installed_apps_patcher.stop()
        super().tearDown()

    def _ensure_role(self, user: str, role: str) -> None:
        if not frappe.db.exists("Role", role):
            self.skipTest(f"Missing Role '{role}' in this site.")
        if frappe.db.exists("Has Role", {"parent": user, "role": role}):
            return
        frappe.get_doc(
            {
                "doctype": "Has Role",
                "parent": user,
                "parenttype": "User",
                "parentfield": "roles",
                "role": role,
            }
        ).insert(ignore_permissions=True)

    def _make_admissions_user(self, role: str = "Admission Officer") -> str:
        user = make_user()
        self._ensure_role(user.name, role)
        return user.name

    def _make_inquiry(self, assigned_to: str | None, workflow_state: str = "Assigned") -> str:
        doc = frappe.get_doc(
            {
                "doctype": "Inquiry",
                "first_name": "Focus",
                "last_name": "Inquiry",
                "email": f"focus-{frappe.generate_hash(length=8)}@example.com",
                "phone_number": "+6612345678",
                "message": "Parent asked about enrollment and transportation.",
            }
        )
        doc.insert(ignore_permissions=True)
        frappe.db.set_value(
            "Inquiry",
            doc.name,
            {
                "assigned_to": assigned_to,
                "workflow_state": workflow_state,
                "followup_due_on": frappe.utils.today(),
            },
            update_modified=False,
        )
        return doc.name

    def test_mark_inquiry_contacted_assignee_happy_path(self):
        assignee = self._make_admissions_user("Admission Officer")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            assignee,
        )

        frappe.set_user(assignee)
        result = mark_inquiry_contacted(
            focus_item_id=focus_item_id,
            complete_todo=1,
            client_request_id=f"focus-{frappe.generate_hash(length=8)}",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "processed")
        self.assertEqual(frappe.db.get_value("Inquiry", inquiry_name, "workflow_state"), "Contacted")

    def test_mark_inquiry_contacted_rejects_focus_user_mismatch(self):
        assignee = self._make_admissions_user("Admission Officer")
        other_user = self._make_admissions_user("Admission Manager")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            other_user,
        )

        frappe.set_user(assignee)
        with self.assertRaises(frappe.PermissionError):
            mark_inquiry_contacted(focus_item_id=focus_item_id, complete_todo=1)

    def test_mark_inquiry_contacted_rejects_non_assignee(self):
        assignee = self._make_admissions_user("Admission Officer")
        non_assignee = self._make_admissions_user("Admission Manager")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            non_assignee,
        )

        frappe.set_user(non_assignee)
        with self.assertRaises(frappe.PermissionError):
            mark_inquiry_contacted(focus_item_id=focus_item_id, complete_todo=1)

    def test_mark_inquiry_contacted_rejects_invalid_action_type(self):
        assignee = self._make_admissions_user("Admission Officer")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            "student_log.follow_up.act.submit",
            assignee,
        )

        frappe.set_user(assignee)
        with self.assertRaises(frappe.PermissionError):
            mark_inquiry_contacted(focus_item_id=focus_item_id, complete_todo=1)

    def test_mark_inquiry_contacted_rejects_non_assigned_state(self):
        assignee = self._make_admissions_user("Admission Officer")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="New")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            assignee,
        )

        frappe.set_user(assignee)
        with self.assertRaises(frappe.ValidationError):
            mark_inquiry_contacted(focus_item_id=focus_item_id, complete_todo=1)

    def test_mark_inquiry_contacted_is_idempotent_for_same_request_id(self):
        assignee = self._make_admissions_user("Admission Officer")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            assignee,
        )
        client_request_id = f"focus-{frappe.generate_hash(length=8)}"

        frappe.set_user(assignee)
        first = mark_inquiry_contacted(
            focus_item_id=focus_item_id,
            complete_todo=1,
            client_request_id=client_request_id,
        )
        second = mark_inquiry_contacted(
            focus_item_id=focus_item_id,
            complete_todo=1,
            client_request_id=client_request_id,
        )

        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "already_processed")
        self.assertTrue(second["idempotent"])

    def test_get_focus_context_includes_inquiry_message_and_contact_state(self):
        assignee = self._make_admissions_user("Admission Officer")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            assignee,
        )

        frappe.set_user(assignee)
        ctx = get_focus_context(focus_item_id=focus_item_id)

        self.assertEqual(ctx["reference_doctype"], "Inquiry")
        self.assertEqual(ctx["inquiry"]["message"], "Parent asked about enrollment and transportation.")
        self.assertFalse(bool(ctx["inquiry"]["contact"]))
        self.assertTrue(bool(ctx["inquiry"]["email"]))
        self.assertTrue(bool(ctx["inquiry"]["phone_number"]))

    def test_create_inquiry_contact_links_contact_for_assignee(self):
        assignee = self._make_admissions_user("Admission Officer")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            assignee,
        )

        frappe.set_user(assignee)
        result = create_inquiry_contact(focus_item_id=focus_item_id)

        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "processed")
        self.assertTrue(bool(result["contact_name"]))
        self.assertEqual(frappe.db.get_value("Inquiry", inquiry_name, "contact"), result["contact_name"])

    def test_create_inquiry_contact_is_idempotent_once_contact_exists(self):
        assignee = self._make_admissions_user("Admission Officer")
        inquiry_name = self._make_inquiry(assigned_to=assignee, workflow_state="Assigned")
        focus_item_id = build_focus_item_id(
            "inquiry",
            "Inquiry",
            inquiry_name,
            ACTION_INQUIRY_FIRST_CONTACT,
            assignee,
        )

        frappe.set_user(assignee)
        first = create_inquiry_contact(focus_item_id=focus_item_id)
        second = create_inquiry_contact(focus_item_id=focus_item_id)

        self.assertEqual(first["status"], "processed")
        self.assertEqual(second["status"], "already_linked")
        self.assertEqual(first["contact_name"], second["contact_name"])
