# ifitwala_ed/admission/doctype/applicant_review_rule/applicant_review_rule.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.admission.admission_utils import (
    READ_LIKE_PERMISSION_TYPES,
    get_admissions_file_staff_scope,
)
from ifitwala_ed.governance.policy_scope_utils import is_policy_organization_applicable_to_context

REVIEWER_MODE_ROLE_ONLY = "Role Only"
REVIEWER_MODE_SPECIFIC_USER = "Specific User"
CONFIG_READ_ROLES = {"Admission Officer", "Admission Manager", "Academic Admin", "System Manager"}
CONFIG_MANAGER_ROLES = {"Admission Manager", "Academic Admin", "System Manager"}
WRITE_LIKE_PERMISSION_TYPES = {"write", "create", "delete", "submit", "cancel", "amend"}


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
        if target_type == "Applicant Document Item":
            return
        if document_type:
            frappe.throw(_("Document Type can only be set when Target Type is Applicant Document Item."))

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


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_reviewer_role_options(doctype, txt, searchfield, start, page_len, filters):
    """Role link query for Applicant Review Rule reviewer rows."""
    if not frappe.has_permission("Applicant Review Rule", ptype="write"):
        frappe.throw(_("Insufficient Permission for Applicant Review Rule"), frappe.PermissionError)

    start = int(start or 0)
    page_len = int(page_len or 20)
    txt = (txt or "").strip()

    role_filters = []
    if txt:
        role_filters.append(["name", "like", f"%{txt}%"])

    return frappe.get_all(
        "Role",
        filters=role_filters,
        fields=["name"],
        order_by="name asc",
        limit_start=start,
        limit=page_len,
        as_list=True,
    )


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    scope = get_admissions_file_staff_scope(resolved_user)
    if not scope.get("allowed"):
        return "1=0"
    if scope.get("bypass"):
        return None

    school_values = _scope_values_to_sql(scope.get("school_scope") or set())
    if school_values:
        return f"`tabApplicant Review Rule`.`school` IN ({school_values})"

    org_values = _scope_values_to_sql(scope.get("org_scope") or set())
    if org_values:
        return f"`tabApplicant Review Rule`.`organization` IN ({org_values})"

    return "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False

    roles = set(frappe.get_roles(resolved_user))
    if resolved_user != "Administrator" and not roles.intersection(CONFIG_READ_ROLES):
        return False
    if (
        op in WRITE_LIKE_PERMISSION_TYPES
        and resolved_user != "Administrator"
        and not roles.intersection(CONFIG_MANAGER_ROLES)
    ):
        return False
    if op not in READ_LIKE_PERMISSION_TYPES and op not in WRITE_LIKE_PERMISSION_TYPES:
        return False

    scope = get_admissions_file_staff_scope(resolved_user)
    if not scope.get("allowed"):
        return False
    if scope.get("bypass"):
        return True
    if not doc:
        return True

    organization, school = _resolve_rule_scope(doc)
    org_scope = set(scope.get("org_scope") or set())
    school_scope = set(scope.get("school_scope") or set())

    if school_scope:
        return school in school_scope
    if org_scope:
        return organization in org_scope
    return False


def _scope_values_to_sql(values) -> str:
    cleaned = sorted({(value or "").strip() for value in values if (value or "").strip()})
    return ", ".join(frappe.db.escape(value) for value in cleaned)


def _resolve_rule_scope(doc) -> tuple[str, str]:
    if isinstance(doc, str):
        row = frappe.db.get_value("Applicant Review Rule", doc, ["organization", "school"], as_dict=True) or {}
        return (row.get("organization") or "").strip(), (row.get("school") or "").strip()
    if isinstance(doc, dict):
        return (doc.get("organization") or "").strip(), (doc.get("school") or "").strip()
    return (getattr(doc, "organization", None) or "").strip(), (getattr(doc, "school", None) or "").strip()
