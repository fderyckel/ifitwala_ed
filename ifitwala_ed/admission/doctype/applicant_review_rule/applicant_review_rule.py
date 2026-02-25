# ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.governance.policy_scope_utils import is_policy_organization_applicable_to_context

REVIEWER_MODE_ROLE_ONLY = "Role Only"
REVIEWER_MODE_SPECIFIC_USER = "Specific User"


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
            reviewer_mode = self._normalize_reviewer_mode(row)
            reviewer_role = (row.reviewer_role or "").strip()
            reviewer_user = (row.reviewer_user or "").strip()
            row.reviewer_mode = reviewer_mode

            if reviewer_mode == REVIEWER_MODE_ROLE_ONLY:
                if not reviewer_role:
                    frappe.throw(_("Reviewer Role is required when Reviewer Mode is Role Only."))
                if reviewer_user:
                    frappe.throw(_("Reviewer User must be empty when Reviewer Mode is Role Only."))
                key = (None, reviewer_role)
            else:
                if not reviewer_user:
                    frappe.throw(_("Reviewer User is required when Reviewer Mode is Specific User."))
                if reviewer_role and not frappe.db.exists("Has Role", {"parent": reviewer_user, "role": reviewer_role}):
                    frappe.throw(_("Reviewer User must have the selected Reviewer Role."))
                key = (reviewer_user, None)

            if key in seen:
                frappe.throw(_("Duplicate reviewer rows are not allowed."))
            seen.add(key)

    def _normalize_reviewer_mode(self, row) -> str:
        mode = (row.reviewer_mode or "").strip()
        if mode in {REVIEWER_MODE_ROLE_ONLY, REVIEWER_MODE_SPECIFIC_USER}:
            return mode
        if (row.reviewer_user or "").strip():
            return REVIEWER_MODE_SPECIFIC_USER
        return REVIEWER_MODE_ROLE_ONLY
