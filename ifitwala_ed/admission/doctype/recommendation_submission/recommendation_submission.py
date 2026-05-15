# ifitwala_ed/admission/doctype/recommendation_submission/recommendation_submission.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admission_utils import (
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    build_open_applicant_review_access_exists_sql,
    has_open_applicant_review_access,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
    normalize_email_value,
)

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
            frappe.throw(
                _("Invalid Recommendation Request: {recommendation_request}.").format(
                    recommendation_request=self.recommendation_request
                )
            )

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


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return "1=0"
    if not is_admissions_file_staff_user(resolved_user):
        return "1=0"

    staff_condition = build_admissions_file_scope_exists_sql(
        user=resolved_user,
        student_applicant_expr_sql="`tabRecommendation Submission`.`student_applicant`",
    )
    if staff_condition is None:
        return None

    conditions: list[str] = []
    if staff_condition != "1=0":
        conditions.append(f"({staff_condition})")

    reviewer_condition = build_open_applicant_review_access_exists_sql(
        user=resolved_user,
        student_applicant_expr_sql="`tabRecommendation Submission`.`student_applicant`",
    )
    if reviewer_condition != "1=0":
        conditions.append(f"({reviewer_condition})")

    return " OR ".join(conditions) if conditions else "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False
    if is_admissions_file_staff_user(resolved_user):
        staff_ops = READ_LIKE_PERMISSION_TYPES | {"write", "create", "delete", "submit", "cancel", "amend"}
        if op not in staff_ops:
            return False

        if op == "create":
            if not doc:
                return True
        if not doc:
            return True

        student_applicant = _resolve_recommendation_submission_student_applicant(doc)
        return has_scoped_staff_access_to_student_applicant(user=resolved_user, student_applicant=student_applicant)

    if op in READ_LIKE_PERMISSION_TYPES and doc:
        student_applicant = _resolve_recommendation_submission_student_applicant(doc)
        return has_open_applicant_review_access(user=resolved_user, student_applicant=student_applicant)

    return False


def _resolve_recommendation_submission_student_applicant(doc) -> str:
    if isinstance(doc, str):
        submission_name = (doc or "").strip()
        if not submission_name:
            return ""
        return (frappe.db.get_value("Recommendation Submission", submission_name, "student_applicant") or "").strip()

    if isinstance(doc, dict):
        student_applicant = (doc.get("student_applicant") or "").strip()
        if student_applicant:
            return student_applicant
        submission_name = (doc.get("name") or "").strip()
    else:
        student_applicant = (getattr(doc, "student_applicant", None) or "").strip()
        if student_applicant:
            return student_applicant
        submission_name = (getattr(doc, "name", None) or "").strip()

    if not submission_name:
        return ""
    return (frappe.db.get_value("Recommendation Submission", submission_name, "student_applicant") or "").strip()
