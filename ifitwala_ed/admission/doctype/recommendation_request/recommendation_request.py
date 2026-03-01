# ifitwala_ed/admission/doctype/recommendation_request/recommendation_request.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_datetime, now_datetime

from ifitwala_ed.admission.admission_utils import (
    get_applicant_scope_ancestors,
    is_applicant_document_type_in_scope,
    normalize_email_value,
)

IMMUTABLE_FIELDS = {
    "student_applicant",
    "recommendation_template",
    "target_document_type",
    "token_hash",
    "item_key",
}


class RecommendationRequest(Document):
    def validate(self):
        before = self.get_doc_before_save() if not self.is_new() else None
        self._normalize_fields()
        self._validate_links_and_scope()
        self._validate_status()
        self._validate_immutability(before)
        self._validate_item_key_uniqueness()

    def _normalize_fields(self):
        self.student_applicant = (self.student_applicant or "").strip()
        self.recommendation_template = (self.recommendation_template or "").strip()
        self.target_document_type = (self.target_document_type or "").strip() or None
        self.applicant_document = (self.applicant_document or "").strip() or None
        self.applicant_document_item = (self.applicant_document_item or "").strip() or None
        self.item_key = frappe.scrub((self.item_key or "").strip())[:80] or None
        self.item_label = (self.item_label or "").strip() or None
        self.recommender_name = (self.recommender_name or "").strip()
        self.recommender_relationship = (self.recommender_relationship or "").strip() or None
        self.recommender_email = normalize_email_value(self.recommender_email)
        self.request_status = (self.request_status or "Sent").strip()
        self.token_hash = (self.token_hash or "").strip() or None
        self.token_hint = (self.token_hint or "").strip() or None
        self.template_snapshot_json = (self.template_snapshot_json or "").strip() or None
        self.otp_enforced = 1 if cint(self.otp_enforced) else 0
        self.resend_count = max(0, cint(self.resend_count or 0))
        self.otp_send_count = max(0, cint(self.otp_send_count or 0))
        self.otp_failed_attempts = max(0, cint(self.otp_failed_attempts or 0))

    def _validate_links_and_scope(self):
        if not self.student_applicant:
            frappe.throw(_("Student Applicant is required."))
        if not frappe.db.exists("Student Applicant", self.student_applicant):
            frappe.throw(_("Invalid Student Applicant: {0}.").format(self.student_applicant))

        if not self.recommendation_template:
            frappe.throw(_("Recommendation Template is required."))
        template = frappe.db.get_value(
            "Recommendation Template",
            self.recommendation_template,
            [
                "name",
                "is_active",
                "organization",
                "school",
                "target_document_type",
                "otp_enforced",
            ],
            as_dict=True,
        )
        if not template:
            frappe.throw(_("Invalid Recommendation Template: {0}.").format(self.recommendation_template))
        if not cint(template.get("is_active")) and self.request_status in {"Sent", "Opened"}:
            frappe.throw(_("Recommendation Template must be active for open requests."))

        applicant_row = frappe.db.get_value(
            "Student Applicant",
            self.student_applicant,
            ["organization", "school"],
            as_dict=True,
        )
        applicant_org = (applicant_row.get("organization") or "").strip()
        applicant_school = (applicant_row.get("school") or "").strip()
        applicant_org_scope, applicant_school_scope = get_applicant_scope_ancestors(
            organization=applicant_org,
            school=applicant_school,
        )
        template_org = (template.get("organization") or "").strip()
        template_school = (template.get("school") or "").strip()
        if template_org and template_org not in set(applicant_org_scope):
            frappe.throw(_("Recommendation Template organization is outside Applicant scope."))
        if template_school and template_school not in set(applicant_school_scope):
            frappe.throw(_("Recommendation Template school is outside Applicant scope."))

        target_document_type = (template.get("target_document_type") or "").strip()
        if not target_document_type:
            frappe.throw(_("Recommendation Template target document type is required."))
        self.target_document_type = target_document_type
        self.otp_enforced = 1 if cint(template.get("otp_enforced")) else 0

        target_row = frappe.db.get_value(
            "Applicant Document Type",
            target_document_type,
            ["organization", "school", "is_active"],
            as_dict=True,
        )
        if not target_row:
            frappe.throw(_("Recommendation target document type no longer exists."))
        if not cint(target_row.get("is_active")):
            frappe.throw(_("Recommendation target document type must stay active for open requests."))
        if not is_applicant_document_type_in_scope(
            document_type_organization=target_row.get("organization"),
            document_type_school=target_row.get("school"),
            applicant_org_ancestors=set(applicant_org_scope),
            applicant_school_ancestors=set(applicant_school_scope),
        ):
            frappe.throw(_("Recommendation target document type is outside Applicant scope."))

        if not self.recommender_name:
            frappe.throw(_("Recommender Name is required."))
        if not self.recommender_email:
            frappe.throw(_("Recommender Email is required."))
        if not self.expires_on:
            frappe.throw(_("Expires On is required."))
        if not self.token_hash:
            frappe.throw(_("Token hash is required."))
        if not self.item_key:
            frappe.throw(_("Item Key is required."))

    def _validate_status(self):
        allowed = {"Sent", "Opened", "Submitted", "Revoked", "Expired"}
        if self.request_status not in allowed:
            frappe.throw(_("Invalid request status: {0}.").format(self.request_status or _("(empty)")))

        expires_on = get_datetime(self.expires_on)
        if self.request_status in {"Sent", "Opened"} and expires_on < now_datetime():
            # Auto-normalize stale open requests to expired.
            self.request_status = "Expired"

        if self.request_status == "Submitted" and not self.consumed_on:
            self.consumed_on = now_datetime()

    def _validate_immutability(self, before):
        if not before:
            return
        for fieldname in IMMUTABLE_FIELDS:
            old_value = (before.get(fieldname) or "").strip()
            new_value = (self.get(fieldname) or "").strip()
            if old_value != new_value:
                frappe.throw(_("{0} is immutable once set.").format(fieldname.replace("_", " ").title()))

    def _validate_item_key_uniqueness(self):
        if not self.student_applicant or not self.item_key:
            return
        exists = frappe.db.exists(
            "Recommendation Request",
            {
                "student_applicant": self.student_applicant,
                "item_key": self.item_key,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(_("Item Key must be unique per Student Applicant recommendation request."))
