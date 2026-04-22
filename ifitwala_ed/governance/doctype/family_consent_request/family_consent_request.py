from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, getdate

from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
)

REQUEST_TYPE_ONE_OFF = "One-off Permission Request"
REQUEST_TYPE_MUTABLE = "Mutable Consent"
REQUEST_TYPE_ORDER = (REQUEST_TYPE_ONE_OFF, REQUEST_TYPE_MUTABLE)
REQUEST_TYPES = frozenset(REQUEST_TYPE_ORDER)

SUBJECT_SCOPE_PER_STUDENT = "Per Student"
SUBJECT_SCOPE_PER_FAMILY = "Per Family"
SUBJECT_SCOPES = frozenset({SUBJECT_SCOPE_PER_STUDENT, SUBJECT_SCOPE_PER_FAMILY})

AUDIENCE_GUARDIAN = "Guardian"
AUDIENCE_STUDENT = "Student"
AUDIENCE_GUARDIAN_AND_STUDENT = "Guardian + Student"
AUDIENCE_MODE_ORDER = (
    AUDIENCE_GUARDIAN,
    AUDIENCE_STUDENT,
    AUDIENCE_GUARDIAN_AND_STUDENT,
)
AUDIENCE_MODES = frozenset(AUDIENCE_MODE_ORDER)

SIGNER_RULE_ANY_GUARDIAN = "Any Authorized Guardian"
SIGNER_RULE_ALL_GUARDIANS = "All Authorized Guardians"
SIGNER_RULE_STUDENT_SELF = "Student Self"
SIGNER_RULE_GUARDIAN_AND_STUDENT = "Guardian And Student"
SIGNER_RULES = frozenset(
    {
        SIGNER_RULE_ANY_GUARDIAN,
        SIGNER_RULE_ALL_GUARDIANS,
        SIGNER_RULE_STUDENT_SELF,
        SIGNER_RULE_GUARDIAN_AND_STUDENT,
    }
)

DECISION_MODE_APPROVE_DECLINE = "Approve / Decline"
DECISION_MODE_GRANT_DENY = "Grant / Deny"
DECISION_MODE_ACKNOWLEDGE = "Acknowledge"
DECISION_MODES = frozenset(
    {
        DECISION_MODE_APPROVE_DECLINE,
        DECISION_MODE_GRANT_DENY,
        DECISION_MODE_ACKNOWLEDGE,
    }
)

COMPLETION_CHANNEL_PORTAL_ONLY = "Portal Only"
COMPLETION_CHANNEL_PORTAL_OR_PAPER = "Portal Or Paper"
COMPLETION_CHANNEL_PAPER_ONLY = "Paper Only"
COMPLETION_CHANNEL_MODE_ORDER = (
    COMPLETION_CHANNEL_PORTAL_ONLY,
    COMPLETION_CHANNEL_PORTAL_OR_PAPER,
    COMPLETION_CHANNEL_PAPER_ONLY,
)
COMPLETION_CHANNEL_MODES = frozenset(COMPLETION_CHANNEL_MODE_ORDER)

FIELD_TYPE_TEXT = "Text"
FIELD_TYPE_LONG_TEXT = "Long Text"
FIELD_TYPE_PHONE = "Phone"
FIELD_TYPE_EMAIL = "Email"
FIELD_TYPE_ADDRESS = "Address"
FIELD_TYPE_DATE = "Date"
FIELD_TYPE_CHECKBOX = "Checkbox"
FIELD_TYPES = frozenset(
    {
        FIELD_TYPE_TEXT,
        FIELD_TYPE_LONG_TEXT,
        FIELD_TYPE_PHONE,
        FIELD_TYPE_EMAIL,
        FIELD_TYPE_ADDRESS,
        FIELD_TYPE_DATE,
        FIELD_TYPE_CHECKBOX,
    }
)

FIELD_MODE_DISPLAY_ONLY = "Display Only"
FIELD_MODE_CONFIRM_CURRENT = "Confirm Current"
FIELD_MODE_ALLOW_OVERRIDE = "Allow Override"
FIELD_MODES = frozenset(
    {
        FIELD_MODE_DISPLAY_ONLY,
        FIELD_MODE_CONFIRM_CURRENT,
        FIELD_MODE_ALLOW_OVERRIDE,
    }
)

REQUEST_STATUS_DRAFT = "Draft"
REQUEST_STATUS_PUBLISHED = "Published"
REQUEST_STATUS_CLOSED = "Closed"
REQUEST_STATUS_ARCHIVED = "Archived"
REQUEST_STATUS_ORDER = (
    REQUEST_STATUS_DRAFT,
    REQUEST_STATUS_PUBLISHED,
    REQUEST_STATUS_CLOSED,
    REQUEST_STATUS_ARCHIVED,
)
REQUEST_STATUSES = frozenset(REQUEST_STATUS_ORDER)

ALLOWED_STATUS_TRANSITIONS = {
    REQUEST_STATUS_DRAFT: {REQUEST_STATUS_DRAFT, REQUEST_STATUS_PUBLISHED},
    REQUEST_STATUS_PUBLISHED: {REQUEST_STATUS_PUBLISHED, REQUEST_STATUS_CLOSED, REQUEST_STATUS_ARCHIVED},
    REQUEST_STATUS_CLOSED: {REQUEST_STATUS_CLOSED, REQUEST_STATUS_ARCHIVED},
    REQUEST_STATUS_ARCHIVED: {REQUEST_STATUS_ARCHIVED},
}


def _clean_text(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _clean_data(value: str | None) -> str:
    return (value or "").strip()


def _generate_request_key() -> str:
    for _attempt in range(10):
        candidate = f"FCR-{frappe.generate_hash(length=10).upper()}"
        if not frappe.db.exists("Family Consent Request", {"request_key": candidate}):
            return candidate
    frappe.throw(_("Unable to generate a unique request key. Please try again."))


class FamilyConsentRequest(Document):
    def before_insert(self):
        self.request_key = _clean_data(self.request_key) or _generate_request_key()
        self.status = _clean_data(self.status) or REQUEST_STATUS_DRAFT

    def validate(self):
        self._normalize_request()
        self._validate_request_enums()
        self._validate_scope()
        self._normalize_targets()
        self._normalize_fields()
        self._validate_date_window()
        self._validate_status_transition_and_freeze()

    def before_delete(self):
        if _clean_data(self.status) != REQUEST_STATUS_DRAFT:
            frappe.throw(_("Only draft Family Consent Requests can be deleted."))

    def _normalize_request(self):
        self.request_title = _clean_text(self.request_title)
        self.request_key = _clean_data(self.request_key)
        self.template_key = _clean_data(self.template_key)
        self.request_type = _clean_data(self.request_type)
        self.policy_version = _clean_data(self.policy_version)
        self.organization = _clean_data(self.organization)
        self.school = _clean_data(self.school)
        self.source_file = _clean_data(self.source_file)
        self.subject_scope = _clean_data(self.subject_scope)
        self.audience_mode = _clean_data(self.audience_mode)
        self.signer_rule = _clean_data(self.signer_rule)
        self.decision_mode = _clean_data(self.decision_mode)
        self.completion_channel_mode = _clean_data(self.completion_channel_mode)
        self.status = _clean_data(self.status) or REQUEST_STATUS_DRAFT
        self.requires_typed_signature = 1 if cint(self.requires_typed_signature) else 0
        self.requires_attestation = 1 if cint(self.requires_attestation) else 0

    def _validate_request_enums(self):
        if self.request_type not in REQUEST_TYPES:
            frappe.throw(_("Request Type is invalid."))
        if self.subject_scope not in SUBJECT_SCOPES:
            frappe.throw(_("Subject Scope is invalid."))
        if self.audience_mode not in AUDIENCE_MODES:
            frappe.throw(_("Audience Mode is invalid."))
        if self.signer_rule not in SIGNER_RULES:
            frappe.throw(_("Signer Rule is invalid."))
        if self.decision_mode not in DECISION_MODES:
            frappe.throw(_("Decision Mode is invalid."))
        if self.completion_channel_mode not in COMPLETION_CHANNEL_MODES:
            frappe.throw(_("Completion Channel Mode is invalid."))
        if self.status not in REQUEST_STATUSES:
            frappe.throw(_("Status is invalid."))

        allowed_signer_rules = {
            AUDIENCE_GUARDIAN: {SIGNER_RULE_ANY_GUARDIAN, SIGNER_RULE_ALL_GUARDIANS},
            AUDIENCE_STUDENT: {SIGNER_RULE_STUDENT_SELF},
            AUDIENCE_GUARDIAN_AND_STUDENT: {SIGNER_RULE_GUARDIAN_AND_STUDENT},
        }
        if self.signer_rule not in allowed_signer_rules.get(self.audience_mode, set()):
            frappe.throw(_("Signer Rule does not match the selected Audience Mode."))

    def _validate_scope(self):
        if not self.organization:
            frappe.throw(_("Organization is required."))
        if self.school:
            school_org = frappe.db.get_value("School", self.school, "organization")
            if not school_org:
                frappe.throw(_("Selected School is invalid."))
            school_ancestors = get_organization_ancestors_including_self(school_org)
            if self.organization not in school_ancestors:
                frappe.throw(_("Selected School is outside the selected Organization scope."))

    def _normalize_targets(self):
        seen_students: set[str] = set()
        for row in self.get("targets") or []:
            row.student = _clean_data(row.student)
            row.school = _clean_data(row.school)
            row.organization = _clean_data(row.organization)
            if not row.student:
                continue

            student_meta = frappe.db.get_value(
                "Student",
                row.student,
                ["anchor_school"],
                as_dict=True,
            )
            student_school = _clean_data((student_meta or {}).get("anchor_school"))
            if not student_school:
                frappe.throw(_("Student {student} must have an Anchor School.").format(student=row.student))
            student_org = _clean_data(frappe.db.get_value("School", student_school, "organization"))
            if not student_org:
                frappe.throw(_("Student {student} has an invalid school organization.").format(student=row.student))

            row.school = row.school or student_school
            row.organization = row.organization or student_org

            if row.organization != student_org:
                frappe.throw(_("Target Organization must match the student's school organization."))
            if row.school != student_school:
                frappe.throw(_("Target School must match the student's Anchor School."))

            org_ancestors = get_organization_ancestors_including_self(row.organization)
            if self.organization not in org_ancestors:
                frappe.throw(_("Target Student is outside the selected Organization scope."))
            if self.school:
                school_ancestors = get_school_ancestors_including_self(row.school)
                if self.school not in school_ancestors:
                    frappe.throw(_("Target Student is outside the selected School scope."))

            if row.student in seen_students:
                frappe.throw(_("Each Student may appear only once in Targets."))
            seen_students.add(row.student)

    def _normalize_fields(self):
        seen_keys: set[str] = set()
        for idx, row in enumerate(self.get("fields") or [], start=1):
            row.field_label = _clean_text(row.field_label)
            row.value_source = _clean_data(row.value_source)
            row.field_type = _clean_data(row.field_type)
            row.field_mode = _clean_data(row.field_mode)
            row.required = 1 if cint(row.required) else 0
            row.allow_profile_writeback = 1 if cint(row.allow_profile_writeback) else 0

            generated_key = frappe.scrub(row.field_key or row.value_source or row.field_label or f"field_{idx}")
            row.field_key = _clean_data(generated_key)

            if row.field_type not in FIELD_TYPES:
                frappe.throw(
                    _("Field Type is invalid for {field_label}.").format(
                        field_label=row.field_label or row.field_key or idx
                    )
                )
            if row.field_mode not in FIELD_MODES:
                frappe.throw(
                    _("Field Mode is invalid for {field_label}.").format(
                        field_label=row.field_label or row.field_key or idx
                    )
                )
            if row.field_mode == FIELD_MODE_DISPLAY_ONLY:
                row.required = 0
            if row.allow_profile_writeback and row.field_mode != FIELD_MODE_ALLOW_OVERRIDE:
                frappe.throw(_("Profile writeback is allowed only for override fields."))
            if row.allow_profile_writeback and not row.value_source:
                frappe.throw(_("Profile writeback requires a bound Value Source."))
            if not row.field_key:
                frappe.throw(_("Field Key is required."))
            if row.field_key in seen_keys:
                frappe.throw(_("Field Key must be unique within a request."))
            seen_keys.add(row.field_key)

    def _validate_date_window(self):
        effective_from = getdate(self.effective_from) if self.effective_from else None
        effective_to = getdate(self.effective_to) if self.effective_to else None
        due_on = getdate(self.due_on) if self.due_on else None

        if effective_from and effective_to and effective_from > effective_to:
            frappe.throw(_("Effective To cannot be before Effective From."))
        if due_on and effective_to and due_on > effective_to:
            frappe.throw(_("Due On cannot be after Effective To."))

    def _validate_status_transition_and_freeze(self):
        before = self.get_doc_before_save()
        if not before:
            if self.status != REQUEST_STATUS_DRAFT:
                frappe.throw(_("New Family Consent Requests must start in Draft."))
            return

        previous_status = _clean_data(before.get("status")) or REQUEST_STATUS_DRAFT
        next_status = self.status
        if next_status not in ALLOWED_STATUS_TRANSITIONS.get(previous_status, set()):
            frappe.throw(_("Invalid Family Consent Request status transition."))

        if previous_status == REQUEST_STATUS_DRAFT:
            return

        if self._freeze_snapshot(before) != self._freeze_snapshot(self):
            frappe.throw(_("Published Family Consent Requests are frozen. Close or archive the request instead."))

    def _freeze_snapshot(self, doc) -> dict:
        return {
            "request_title": _clean_text(doc.get("request_title")),
            "request_key": _clean_data(doc.get("request_key")),
            "template_key": _clean_data(doc.get("template_key")),
            "request_type": _clean_data(doc.get("request_type")),
            "policy_version": _clean_data(doc.get("policy_version")),
            "organization": _clean_data(doc.get("organization")),
            "school": _clean_data(doc.get("school")),
            "request_text": doc.get("request_text") or "",
            "source_file": _clean_data(doc.get("source_file")),
            "subject_scope": _clean_data(doc.get("subject_scope")),
            "audience_mode": _clean_data(doc.get("audience_mode")),
            "signer_rule": _clean_data(doc.get("signer_rule")),
            "decision_mode": _clean_data(doc.get("decision_mode")),
            "completion_channel_mode": _clean_data(doc.get("completion_channel_mode")),
            "requires_typed_signature": cint(doc.get("requires_typed_signature")),
            "requires_attestation": cint(doc.get("requires_attestation")),
            "effective_from": str(doc.get("effective_from") or ""),
            "effective_to": str(doc.get("effective_to") or ""),
            "due_on": str(doc.get("due_on") or ""),
            "targets": [
                {
                    "organization": _clean_data(row.get("organization")),
                    "school": _clean_data(row.get("school")),
                    "student": _clean_data(row.get("student")),
                }
                for row in (doc.get("targets") or [])
            ],
            "fields": [
                {
                    "field_key": _clean_data(row.get("field_key")),
                    "field_label": _clean_text(row.get("field_label")),
                    "field_type": _clean_data(row.get("field_type")),
                    "value_source": _clean_data(row.get("value_source")),
                    "field_mode": _clean_data(row.get("field_mode")),
                    "required": cint(row.get("required")),
                    "allow_profile_writeback": cint(row.get("allow_profile_writeback")),
                }
                for row in (doc.get("fields") or [])
            ],
        }
