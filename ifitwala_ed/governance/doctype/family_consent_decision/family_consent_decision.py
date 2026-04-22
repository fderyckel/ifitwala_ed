from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.governance.doctype.family_consent_request.family_consent_request import (
    COMPLETION_CHANNEL_PAPER_ONLY,
    COMPLETION_CHANNEL_PORTAL_ONLY,
)

DECISION_BY_DOCTYPES = frozenset({"Guardian", "Student"})
DECISION_STATUSES = frozenset({"Approved", "Declined", "Granted", "Denied", "Withdrawn"})
SOURCE_CHANNELS = frozenset({"Guardian Portal", "Student Portal", "Desk Paper Capture"})
PROFILE_WRITEBACK_MODES = frozenset({"", "Form Only", "Update Profile"})


class FamilyConsentDecision(Document):
    def before_insert(self):
        self._normalize()
        self._validate_enums()
        self._validate_snapshot()
        self._validate_request_channel_compatibility()
        self.decision_at = get_datetime(self.decision_at) if self.decision_at else now_datetime()

    def before_save(self):
        if not self.is_new():
            frappe.throw(_("Family Consent Decisions are append-only and cannot be edited."))

    def before_delete(self):
        frappe.throw(_("Family Consent Decisions cannot be deleted."))

    def _normalize(self):
        self.family_consent_request = (self.family_consent_request or "").strip()
        self.student = (self.student or "").strip()
        self.decision_by_doctype = (self.decision_by_doctype or "").strip()
        self.decision_by = " ".join((self.decision_by or "").strip().split())
        self.decision_status = (self.decision_status or "").strip()
        self.typed_signature_name = " ".join((self.typed_signature_name or "").strip().split())
        self.attestation_confirmed = 1 if cint(self.attestation_confirmed) else 0
        self.source_channel = (self.source_channel or "").strip()
        self.source_file = (self.source_file or "").strip()
        self.response_snapshot = (self.response_snapshot or "").strip()
        self.profile_writeback_mode = (self.profile_writeback_mode or "").strip()
        self.supersedes_decision = (self.supersedes_decision or "").strip()

    def _validate_enums(self):
        if self.decision_by_doctype not in DECISION_BY_DOCTYPES:
            frappe.throw(_("Decision By DocType is invalid."))
        if self.decision_status not in DECISION_STATUSES:
            frappe.throw(_("Decision Status is invalid."))
        if self.source_channel not in SOURCE_CHANNELS:
            frappe.throw(_("Source Channel is invalid."))
        if self.profile_writeback_mode not in PROFILE_WRITEBACK_MODES:
            frappe.throw(_("Profile Writeback Mode is invalid."))

    def _validate_snapshot(self):
        if not self.response_snapshot:
            frappe.throw(_("Response Snapshot is required."))

        try:
            parsed = frappe.parse_json(self.response_snapshot)
        except Exception:
            parsed = None

        if not isinstance(parsed, dict):
            frappe.throw(_("Response Snapshot must be a JSON object."))

    def _validate_request_channel_compatibility(self):
        request_row = frappe.db.get_value(
            "Family Consent Request",
            self.family_consent_request,
            ["status", "completion_channel_mode"],
            as_dict=True,
        )
        if not request_row:
            frappe.throw(_("Family Consent Request is invalid."))

        request_status = (request_row.get("status") or "").strip()
        completion_channel_mode = (request_row.get("completion_channel_mode") or "").strip()
        if request_status == "Draft":
            frappe.throw(_("Family Consent Decisions cannot be recorded for draft requests."))

        if self.source_channel == "Guardian Portal" and self.decision_by_doctype != "Guardian":
            frappe.throw(_("Guardian Portal decisions must be recorded for Guardian signers."))
        if self.source_channel == "Student Portal" and self.decision_by_doctype != "Student":
            frappe.throw(_("Student Portal decisions must be recorded for Student signers."))
        if self.source_channel == "Desk Paper Capture" and self.profile_writeback_mode:
            frappe.throw(_("Desk paper capture cannot update profile data directly."))

        if completion_channel_mode == COMPLETION_CHANNEL_PAPER_ONLY and self.source_channel != "Desk Paper Capture":
            frappe.throw(_("This request accepts paper completion only."), frappe.ValidationError)
        if completion_channel_mode == COMPLETION_CHANNEL_PORTAL_ONLY and self.source_channel == "Desk Paper Capture":
            frappe.throw(_("This request accepts portal completion only."), frappe.ValidationError)
