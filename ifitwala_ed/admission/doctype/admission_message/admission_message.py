from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.admission.admissions_crm_domain import clean, update_conversation_from_message
from ifitwala_ed.admission.admissions_crm_permissions import (
    conversation_has_permission,
    linked_conversation_has_permission,
    linked_conversation_permission_query_conditions,
)

IMMUTABLE_MESSAGE_FIELDS = (
    "conversation",
    "organization",
    "school",
    "direction",
    "message_type",
    "body",
    "message_at",
    "channel_account",
    "external_identity",
    "external_message_id",
    "external_conversation_id",
    "dedupe_key",
    "linked_inquiry",
    "linked_student_applicant",
    "media_provider_id",
    "media_mime_type",
    "media_file_name",
    "media_size",
)


class AdmissionMessage(Document):
    def before_insert(self):
        if not self.message_at:
            self.message_at = now_datetime()
        if not clean(self.delivery_status):
            self.delivery_status = "Received" if self.direction == "Inbound" else "Logged"

    def validate(self):
        self._validate_immutable_history()
        conversation = self._sync_conversation_context() if self.is_new() else self._load_conversation_context()
        self._validate_session_scope(conversation)
        self._validate_payload()

    def after_insert(self):
        update_conversation_from_message(self)

    def _sync_conversation_context(self) -> dict:
        conversation = self._load_conversation_context()
        self.organization = conversation.get("organization")
        self.school = conversation.get("school")
        self.linked_inquiry = conversation.get("inquiry")
        self.linked_student_applicant = conversation.get("student_applicant")
        if not clean(self.channel_account):
            self.channel_account = conversation.get("channel_account")
        if not clean(self.external_identity):
            self.external_identity = conversation.get("external_identity")
        return conversation

    def _load_conversation_context(self) -> dict:
        conversation = frappe.db.get_value(
            "Admission Conversation",
            self.conversation,
            [
                "organization",
                "school",
                "inquiry",
                "student_applicant",
                "channel_account",
                "external_identity",
                "assigned_to",
                "owner",
            ],
            as_dict=True,
        )
        if not conversation:
            frappe.throw(_("Admission Conversation not found: {conversation}").format(conversation=self.conversation))
        return conversation

    def _validate_session_scope(self, conversation: dict) -> None:
        user = clean(frappe.session.user)
        if user == "Administrator" or conversation_has_permission(conversation, ptype="write", user=user):
            return
        frappe.throw(
            _("You do not have permission to add messages to this admissions conversation."), frappe.PermissionError
        )

    def _validate_payload(self) -> None:
        if clean(self.body) or clean(self.media_provider_id):
            return
        frappe.throw(_("Message body or external media metadata is required."))

    def _validate_immutable_history(self) -> None:
        if self.is_new():
            return
        before = self.get_doc_before_save()
        if not before:
            return
        for fieldname in IMMUTABLE_MESSAGE_FIELDS:
            if self.get(fieldname) != before.get(fieldname):
                frappe.throw(_("Admission Message history is append-only. Create a new message instead."))


def get_permission_query_conditions(user: str | None = None) -> str | None:
    return linked_conversation_permission_query_conditions(doctype="Admission Message", user=user)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return linked_conversation_has_permission(doc, ptype=ptype, user=user)
