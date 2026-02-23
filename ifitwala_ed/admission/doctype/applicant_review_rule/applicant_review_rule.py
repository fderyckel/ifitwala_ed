# ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.governance.policy_scope_utils import is_policy_organization_applicable_to_context


class ApplicantReviewRule(Document):
    def validate(self):
        self._validate_scope_coherence()
        self._validate_target_fields()
        self._validate_reviewers()

    def _validate_scope_coherence(self):
        organization = (self.organization or "").strip()
        school = (self.school or "").strip()
        if not organization or not school:
            frappe.throw(_("Organization and School are required."))

        school_org = frappe.db.get_value("School", school, "organization")
        if not school_org:
            frappe.throw(_("Selected School must belong to an Organization."))

        if is_policy_organization_applicable_to_context(
            policy_organization=organization,
            context_organization=school_org,
        ):
            return

        frappe.throw(_("School must be within the selected Organization scope."))

    def _validate_target_fields(self):
        target_type = (self.target_type or "").strip()
        document_type = (self.document_type or "").strip()
        if target_type == "Applicant Document":
            return
        if document_type:
            frappe.throw(_("Document Type can only be set when Target Type is Applicant Document."))

    def _validate_reviewers(self):
        reviewers = self.reviewers or []
        if not reviewers:
            frappe.throw(_("At least one reviewer row is required."))

        seen: set[tuple[str | None, str | None]] = set()
        for row in reviewers:
            reviewer_role = (row.reviewer_role or "").strip()
            reviewer_user = (row.reviewer_user or "").strip()

            if bool(reviewer_role) == bool(reviewer_user):
                frappe.throw(_("Each reviewer row must set exactly one of Reviewer Role or Reviewer User."))

            key = (reviewer_user or None, reviewer_role or None)
            if key in seen:
                frappe.throw(_("Duplicate reviewer rows are not allowed."))
            seen.add(key)
