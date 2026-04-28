from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.admission.admissions_crm_domain import clean, update_conversation_from_activity
from ifitwala_ed.admission.admissions_crm_permissions import (
    conversation_has_permission,
    linked_conversation_has_permission,
    linked_conversation_permission_query_conditions,
)


class AdmissionCRMActivity(Document):
    def before_insert(self):
        if not self.activity_at:
            self.activity_at = now_datetime()
        if not clean(self.staff_user):
            self.staff_user = frappe.session.user

    def validate(self):
        self._validate_append_only()
        conversation = self._sync_conversation_context()
        self._validate_session_scope(conversation)

    def after_insert(self):
        update_conversation_from_activity(self)

    def _sync_conversation_context(self) -> dict:
        conversation = frappe.db.get_value(
            "Admission Conversation",
            self.conversation,
            ["organization", "school", "inquiry", "student_applicant", "assigned_to", "owner"],
            as_dict=True,
        )
        if not conversation:
            frappe.throw(_("Admission Conversation not found: {0}").format(self.conversation))

        self.organization = conversation.get("organization")
        self.school = conversation.get("school")
        self.inquiry = conversation.get("inquiry")
        self.student_applicant = conversation.get("student_applicant")
        return conversation

    def _validate_session_scope(self, conversation: dict) -> None:
        user = clean(frappe.session.user)
        if user == "Administrator" or conversation_has_permission(conversation, ptype="write", user=user):
            return
        frappe.throw(
            _("You do not have permission to add CRM activity to this admissions conversation."), frappe.PermissionError
        )

    def _validate_append_only(self) -> None:
        if self.is_new():
            return
        frappe.throw(_("Admission CRM Activity is append-only. Create a new activity instead."))


def get_permission_query_conditions(user: str | None = None) -> str | None:
    return linked_conversation_permission_query_conditions(doctype="Admission CRM Activity", user=user)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return linked_conversation_has_permission(doc, ptype=ptype, user=user)
