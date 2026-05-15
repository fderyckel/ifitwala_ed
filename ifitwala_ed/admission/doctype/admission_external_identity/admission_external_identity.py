from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.admission.admissions_crm_domain import clean, get_channel_account_context
from ifitwala_ed.admission.admissions_crm_permissions import (
    doc_is_in_admissions_crm_scope,
    external_identity_has_permission,
    external_identity_permission_query_conditions,
)


class AdmissionExternalIdentity(Document):
    def validate(self):
        account = self._sync_channel_context()
        self._validate_session_scope(account)
        self._validate_identity_value()
        self._validate_confidence_score()
        self._validate_unique_external_identity()

    def _sync_channel_context(self) -> dict:
        account = get_channel_account_context(self.channel_account)
        channel_type = clean(account.get("channel_type"))
        if not channel_type:
            frappe.throw(_("Admission Channel Account is missing channel type."))
        if clean(self.channel_type) and self.channel_type != channel_type:
            frappe.throw(_("External identity channel type must match the channel account."))
        self.channel_type = channel_type
        return account

    def _validate_session_scope(self, account: dict) -> None:
        user = clean(frappe.session.user)
        if (
            user
            and user != "Guest"
            and doc_is_in_admissions_crm_scope(
                user=user,
                organization=account.get("organization"),
                school=account.get("school"),
            )
        ):
            return
        if user == "Administrator":
            return
        frappe.throw(_("You do not have permission for this external identity scope."), frappe.PermissionError)

    def _validate_identity_value(self) -> None:
        if clean(self.external_user_id) or clean(self.phone_number) or clean(self.email):
            return
        frappe.throw(_("External user ID, phone number, or email is required."))

    def _validate_confidence_score(self) -> None:
        if self.confidence_score is None:
            return
        if float(self.confidence_score) < 0 or float(self.confidence_score) > 100:
            frappe.throw(_("Confidence score must be between 0 and 100."))

    def _validate_unique_external_identity(self) -> None:
        external_user_id = clean(self.external_user_id)
        if not external_user_id:
            return
        duplicate = frappe.db.exists(
            "Admission External Identity",
            {
                "channel_account": self.channel_account,
                "external_user_id": external_user_id,
                "name": ["!=", self.name],
            },
        )
        if duplicate:
            frappe.throw(_("This external identity is already recorded for the selected channel account."))


def get_permission_query_conditions(user: str | None = None) -> str | None:
    return external_identity_permission_query_conditions(user)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return external_identity_has_permission(doc, ptype=ptype, user=user)
