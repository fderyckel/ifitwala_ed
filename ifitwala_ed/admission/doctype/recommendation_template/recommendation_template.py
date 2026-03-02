# ifitwala_ed/admission/doctype/recommendation_template/recommendation_template.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import get_applicant_scope_ancestors, is_applicant_document_type_in_scope
from ifitwala_ed.governance.policy_scope_utils import is_policy_organization_applicable_to_context

ALLOWED_FIELD_TYPES = {"Data", "Small Text", "Long Text", "Select", "Check"}


class RecommendationTemplate(Document):
    def validate(self):
        self._normalize_fields()
        self._validate_scope()
        self._validate_limits()
        self._validate_file_rules()
        self._validate_target_document_type()
        self._validate_template_fields()

    def _normalize_fields(self):
        self.template_name = (self.template_name or "").strip()
        self.organization = (self.organization or "").strip()
        self.school = (self.school or "").strip()
        self.target_document_type = (self.target_document_type or "").strip()
        self.description = (self.description or "").strip()
        self.minimum_required = max(0, cint(self.minimum_required or 0))
        self.maximum_allowed = max(1, cint(self.maximum_allowed or 1))

    def _validate_scope(self):
        if not self.organization or not self.school:
            frappe.throw(_("Organization and School are required."))

        school_org = (frappe.db.get_value("School", self.school, "organization") or "").strip()
        if not school_org:
            frappe.throw(_("Selected School must belong to an Organization."))

        if not is_policy_organization_applicable_to_context(
            policy_organization=self.organization,
            context_organization=school_org,
        ):
            frappe.throw(_("School must be within the selected Organization scope."))

    def _validate_limits(self):
        if self.maximum_allowed < 1:
            frappe.throw(_("Maximum Allowed must be at least 1."))
        if self.minimum_required < 0:
            frappe.throw(_("Minimum Required cannot be negative."))
        if self.minimum_required > self.maximum_allowed:
            frappe.throw(_("Minimum Required cannot be greater than Maximum Allowed."))

    def _validate_file_rules(self):
        if cint(self.file_upload_required) and not cint(self.allow_file_upload):
            frappe.throw(_("File Upload Required cannot be enabled when Allow File Upload is disabled."))

    def _validate_target_document_type(self):
        if not self.target_document_type:
            frappe.throw(_("Target Document Type is required."))

        row = frappe.db.get_value(
            "Applicant Document Type",
            self.target_document_type,
            [
                "name",
                "is_active",
                "is_repeatable",
                "organization",
                "school",
            ],
            as_dict=True,
        )
        if not row:
            frappe.throw(_("Invalid Target Document Type."))
        if not cint(row.get("is_active")):
            frappe.throw(_("Target Document Type must be active."))

        org_scope, school_scope = get_applicant_scope_ancestors(
            organization=self.organization,
            school=self.school,
        )
        if not is_applicant_document_type_in_scope(
            document_type_organization=row.get("organization"),
            document_type_school=row.get("school"),
            applicant_org_ancestors=set(org_scope),
            applicant_school_ancestors=set(school_scope),
        ):
            frappe.throw(_("Target Document Type is outside the template school scope."))

        if self.maximum_allowed > 1 and not cint(row.get("is_repeatable")):
            frappe.throw(_("Target Document Type must be repeatable when Maximum Allowed is greater than 1."))

    def _validate_template_fields(self):
        seen = set()
        for row in self.template_fields or []:
            row.field_key = frappe.scrub((row.field_key or "").strip())[:80]
            row.label = (row.label or "").strip()
            row.field_type = (row.field_type or "").strip()
            row.options_json = (row.options_json or "").strip()
            row.help_text = (row.help_text or "").strip()

            if not row.field_key:
                frappe.throw(_("Template field key is required."))
            if not row.label:
                frappe.throw(_("Template field label is required."))
            if row.field_type not in ALLOWED_FIELD_TYPES:
                frappe.throw(_("Invalid template field type: {0}.").format(row.field_type or _("(empty)")))
            if row.field_key in seen:
                frappe.throw(_("Duplicate template field key: {0}.").format(row.field_key))
            seen.add(row.field_key)

            if row.field_type == "Select" and not row.options_json:
                frappe.throw(_("Template select field {0} must define options.").format(row.label))
