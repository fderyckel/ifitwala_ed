from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.admission.admission_utils import _validate_admissions_assignee
from ifitwala_ed.admission.admissions_crm_domain import assert_school_in_organization_scope, clean
from ifitwala_ed.admission.admissions_crm_permissions import (
    channel_account_has_permission,
    channel_account_permission_query_conditions,
    doc_is_in_admissions_crm_scope,
)


class AdmissionChannelAccount(Document):
    def validate(self):
        self._validate_school_scope()
        self._validate_session_scope()
        self._validate_default_owner()
        self._validate_secret_references()

    def _validate_school_scope(self) -> None:
        if clean(self.school):
            assert_school_in_organization_scope(school=self.school, organization=self.organization)

    def _validate_default_owner(self) -> None:
        if clean(self.default_owner):
            _validate_admissions_assignee(self.default_owner)

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
        frappe.throw(_("You do not have permission for this admissions channel account scope."), frappe.PermissionError)

    def _validate_secret_references(self) -> None:
        for fieldname in ("webhook_secret_ref", "access_token_secret_ref"):
            value = clean(self.get(fieldname))
            if value and any(marker in value.lower() for marker in ("token=", "secret=", "bearer ")):
                frappe.throw(_("Store only a secret reference, not the provider secret value."))


def get_permission_query_conditions(user: str | None = None) -> str | None:
    return channel_account_permission_query_conditions(user)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    return channel_account_has_permission(doc, ptype=ptype, user=user)
