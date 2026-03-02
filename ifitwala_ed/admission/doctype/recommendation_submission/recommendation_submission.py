# ifitwala_ed/admission/doctype/recommendation_submission/recommendation_submission.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admission_utils import normalize_email_value

IMMUTABLE_FIELDS = {
    "recommendation_request",
    "student_applicant",
    "recommendation_template",
    "applicant_document",
    "applicant_document_item",
    "recommender_name",
    "recommender_email",
    "answers_json",
    "attestation_confirmed",
    "has_file",
    "idempotency_key",
}


class RecommendationSubmission(Document):
    def validate(self):
        before = self.get_doc_before_save() if not self.is_new() else None
        self._normalize_fields()
        self._validate_links()
        self._validate_immutable(before)
        if not self.submitted_on:
            self.submitted_on = now_datetime()

    def _normalize_fields(self):
        self.recommendation_request = (self.recommendation_request or "").strip()
        self.student_applicant = (self.student_applicant or "").strip()
        self.recommendation_template = (self.recommendation_template or "").strip() or None
        self.applicant_document = (self.applicant_document or "").strip() or None
        self.applicant_document_item = (self.applicant_document_item or "").strip() or None
        self.recommender_name = (self.recommender_name or "").strip()
        self.recommender_email = normalize_email_value(self.recommender_email)
        self.answers_json = (self.answers_json or "").strip()
        self.source_ip = (self.source_ip or "").strip() or None
        self.user_agent = (self.user_agent or "").strip() or None
        self.idempotency_key = (self.idempotency_key or "").strip() or None
        self.attestation_confirmed = 1 if cint(self.attestation_confirmed) else 0
        self.has_file = 1 if cint(self.has_file) else 0

    def _validate_links(self):
        if not self.recommendation_request:
            frappe.throw(_("Recommendation Request is required."))
        if not frappe.db.exists("Recommendation Request", self.recommendation_request):
            frappe.throw(_("Invalid Recommendation Request: {0}.").format(self.recommendation_request))

        request_row = frappe.db.get_value(
            "Recommendation Request",
            self.recommendation_request,
            [
                "student_applicant",
                "recommendation_template",
                "recommender_name",
                "recommender_email",
            ],
            as_dict=True,
        )
        if not request_row:
            frappe.throw(_("Recommendation Request context is missing."))

        if self.student_applicant != (request_row.get("student_applicant") or "").strip():
            frappe.throw(_("Submission Student Applicant must match Recommendation Request."))
        if (
            self.recommendation_template
            and self.recommendation_template != (request_row.get("recommendation_template") or "").strip()
        ):
            frappe.throw(_("Submission template must match Recommendation Request template."))
        if self.recommender_name != (request_row.get("recommender_name") or "").strip():
            frappe.throw(_("Submission recommender name must match Recommendation Request."))
        if self.recommender_email != normalize_email_value(request_row.get("recommender_email")):
            frappe.throw(_("Submission recommender email must match Recommendation Request."))

        if not self.recommender_name or not self.recommender_email:
            frappe.throw(_("Recommender name and email are required."))
        if not self.answers_json:
            frappe.throw(_("Answers JSON is required."))

    def _validate_immutable(self, before):
        if not before:
            return
        for fieldname in IMMUTABLE_FIELDS:
            old_value = before.get(fieldname)
            new_value = self.get(fieldname)
            if (old_value or "") != (new_value or ""):
                frappe.throw(_("Recommendation submissions are immutable after insert."))
