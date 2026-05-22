# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

COMMUNICATION_CONTACT_POINT_DOCTYPE = "Communication Contact Point"

ALLOWED_OWNER_SUBJECT_DOCTYPES = frozenset({"Guardian", "Student", "Student Applicant", "Inquiry", "Employee"})
SCHOOL_REQUIRED_DOCTYPES = frozenset({"Guardian", "Student", "Student Applicant"})
ALLOWED_CHANNEL_TYPES = frozenset({"email", "phone", "address"})
ALLOWED_PURPOSES = frozenset(
    {
        "emergency",
        "billing",
        "admissions_followup",
        "family_consent",
        "school_communication",
        "hr",
        "relationship_crm",
        "export",
    }
)


def _clean_data(value) -> str:
    return str(value or "").strip()


def _as_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


class CommunicationContactPoint(Document):
    def _from_contact_point_service(self) -> bool:
        flags = getattr(self, "flags", None)
        if hasattr(flags, "get"):
            return bool(flags.get("from_contact_point_service"))
        return bool(getattr(flags, "from_contact_point_service", False))

    def before_insert(self):
        if not self._from_contact_point_service():
            frappe.throw(
                _("Communication Contact Point must be created by the contact privacy service."),
                frappe.PermissionError,
            )

    def before_save(self):
        if not self.is_new() and not self._from_contact_point_service():
            frappe.throw(
                _("Communication Contact Point must be changed through the contact privacy service."),
                frappe.PermissionError,
            )

    def validate(self):
        self._validate_owner_and_subject()
        self._validate_scope()
        self._validate_channel_and_purpose()
        self._validate_stored_values()
        self._validate_primary_uniqueness()

    def before_delete(self):
        frappe.throw(_("Communication Contact Point records cannot be deleted."))

    def _validate_owner_and_subject(self) -> None:
        owner_doctype = _clean_data(self.owner_doctype)
        owner_name = _clean_data(self.owner_name)
        subject_doctype = _clean_data(self.subject_doctype)
        subject_name = _clean_data(self.subject_name)

        if not owner_doctype or not owner_name:
            frappe.throw(_("Communication Contact Point requires an owner."))
        if not subject_doctype or not subject_name:
            frappe.throw(_("Communication Contact Point requires a subject."))
        if owner_doctype not in ALLOWED_OWNER_SUBJECT_DOCTYPES:
            frappe.throw(_("Communication Contact Point owner DocType is not approved."))
        if subject_doctype not in ALLOWED_OWNER_SUBJECT_DOCTYPES:
            frappe.throw(_("Communication Contact Point subject DocType is not approved."))

    def _validate_scope(self) -> None:
        if not _clean_data(self.organization):
            frappe.throw(_("Communication Contact Point requires an Organization."))

        scoped_doctypes = {_clean_data(self.owner_doctype), _clean_data(self.subject_doctype)}
        if scoped_doctypes & SCHOOL_REQUIRED_DOCTYPES and not _clean_data(self.school):
            frappe.throw(_("Communication Contact Point requires a School for this education record."))

    def _validate_channel_and_purpose(self) -> None:
        if _clean_data(self.channel_type) not in ALLOWED_CHANNEL_TYPES:
            frappe.throw(_("Communication Contact Point channel type is not approved."))
        if _clean_data(self.purpose) not in ALLOWED_PURPOSES:
            frappe.throw(_("Communication Contact Point purpose is not approved."))

    def _validate_stored_values(self) -> None:
        if _as_int(self.disabled):
            return

        if not _clean_data(self.value_encrypted):
            frappe.throw(_("Communication Contact Point requires an encrypted value."))
        if not _clean_data(self.normalized_hash):
            frappe.throw(_("Communication Contact Point requires a normalized hash."))
        if not _clean_data(self.masked_display):
            frappe.throw(_("Communication Contact Point requires a masked display value."))

    def _validate_primary_uniqueness(self) -> None:
        if not _as_int(self.is_primary) or _as_int(self.disabled):
            return

        filters = {
            "owner_doctype": self.owner_doctype,
            "owner_name": self.owner_name,
            "purpose": self.purpose,
            "channel_type": self.channel_type,
            "is_primary": 1,
            "disabled": 0,
        }
        if _clean_data(getattr(self, "name", None)):
            filters["name"] = ["!=", self.name]

        if frappe.db.exists(COMMUNICATION_CONTACT_POINT_DOCTYPE, filters):
            frappe.throw(_("Only one active primary Communication Contact Point is allowed for this owner, purpose, and channel."))


def on_doctype_update():
    frappe.db.add_index(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        fields=["owner_doctype", "owner_name", "channel_type", "disabled"],
        index_name="idx_ccp_owner_channel",
    )
    frappe.db.add_index(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        fields=["subject_doctype", "subject_name", "channel_type", "disabled"],
        index_name="idx_ccp_subject_channel",
    )
    frappe.db.add_index(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        fields=["organization", "school", "purpose", "channel_type", "disabled"],
        index_name="idx_ccp_scope_resolution",
    )
    frappe.db.add_index(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        fields=["normalized_hash", "organization", "school", "channel_type", "disabled"],
        index_name="idx_ccp_hash_scope",
    )
    frappe.db.add_index(
        COMMUNICATION_CONTACT_POINT_DOCTYPE,
        fields=["owner_doctype", "owner_name", "purpose", "channel_type", "is_primary", "disabled"],
        index_name="idx_ccp_owner_primary",
    )
