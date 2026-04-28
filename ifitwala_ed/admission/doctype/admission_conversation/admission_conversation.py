from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.admission.admissions_crm_domain import apply_conversation_scope, clean, set_conversation_title
from ifitwala_ed.admission.admissions_crm_permissions import (
    conversation_has_permission,
    conversation_permission_query_conditions,
    doc_is_in_admissions_crm_scope,
)


class AdmissionConversation(Document):
    def validate(self):
        apply_conversation_scope(self)
        self._validate_session_scope()
        self._set_assignee_if_missing()
        set_conversation_title(self)

    def _set_assignee_if_missing(self) -> None:
        if clean(self.assigned_to):
            return

        self.assigned_to = frappe.session.user

    def _validate_session_scope(self) -> None:
        user = clean(frappe.session.user)
        if (
            user
            and user != "Guest"
            and doc_is_in_admissions_crm_scope(
                user=user,
                organization=self.organization,
                school=self.school,
            )
        ):
            return
        if user == "Administrator":
            return
        frappe.throw(_("You do not have permission for this admissions conversation scope."), frappe.PermissionError)


def get_permission_query_conditions(user: str | None = None) -> str | None:
    return conversation_permission_query_conditions(user)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return conversation_has_permission(doc, ptype=ptype, user=user)
