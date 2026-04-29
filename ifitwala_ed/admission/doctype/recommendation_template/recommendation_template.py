# ifitwala_ed/admission/doctype/recommendation_template/recommendation_template.py

import hashlib

import frappe
from frappe import _
from frappe.exceptions import DuplicateEntryError
from frappe.model.document import Document
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import get_applicant_scope_ancestors, is_applicant_document_type_in_scope
from ifitwala_ed.governance.policy_scope_utils import is_policy_organization_applicable_to_context

ALLOWED_FIELD_TYPES = {
    "Data",
    "Small Text",
    "Long Text",
    "Select",
    "Check",
    "Section Header",
    "Likert Scale",
}
DISPLAY_ONLY_FIELD_TYPES = {"Section Header"}
MANAGED_RECOMMENDATION_DOC_TYPE_CODE_PREFIX = "recommendation_letter"
MANAGED_RECOMMENDATION_DOC_TYPE_LABEL = "Recommendation Letter"


class RecommendationTemplate(Document):
    def validate(self):
        self._normalize_fields()
        self._validate_scope()
        self._validate_limits()
        self._validate_file_rules()
        self._ensure_target_document_type()
        self._validate_target_document_type()
        self._validate_template_fields()

    def _normalize_fields(self):
        self.template_name = (self.template_name or "").strip()
        self.organization = (self.organization or "").strip()
        self.school = (self.school or "").strip()
        self.target_document_type = (self.target_document_type or "").strip()
        self.description = (self.description or "").strip()
        self.minimum_required = cint(self.minimum_required or 0)
        self.maximum_allowed = cint(self.maximum_allowed or 1)

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

    def _ensure_target_document_type(self):
        if self.target_document_type:
            return

        target_row, created = self._resolve_or_create_managed_target_document_type()
        target_name = (target_row.get("name") or "").strip()
        if not target_name:
            frappe.throw(_("Unable to resolve a managed Recommendation target document type."))

        self.target_document_type = target_name
        if cint(frappe.flags.in_test):
            return

        if created:
            frappe.msgprint(
                _(
                    "Target Document Type was created in the background and linked: "
                    "{target_document_type} ({document_type_name})."
                ).format(
                    target_document_type=frappe.bold(target_name),
                    document_type_name=frappe.bold(target_row.get("document_type_name") or target_name),
                )
            )
            return

        frappe.msgprint(
            _("Target Document Type was linked automatically: {target_document_type}.").format(
                target_document_type=frappe.bold(target_name)
            )
        )

    def _managed_target_document_type_code(self) -> str:
        seed = f"{self.organization}|{self.school}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
        return f"{MANAGED_RECOMMENDATION_DOC_TYPE_CODE_PREFIX}_{digest}"

    def _resolve_or_create_managed_target_document_type(self) -> tuple[dict, bool]:
        code = self._managed_target_document_type_code()
        existing = frappe.db.get_value(
            "Applicant Document Type",
            {"code": code},
            ["name", "document_type_name"],
            as_dict=True,
        )
        if existing:
            return existing, False

        payload = {
            "doctype": "Applicant Document Type",
            "code": code,
            "document_type_name": MANAGED_RECOMMENDATION_DOC_TYPE_LABEL,
            "organization": self.organization,
            "school": self.school,
            "is_active": 1,
            "is_required": 0,
            "is_repeatable": 1,
            "min_items_required": 1,
            "classification_slot": "recommendation_letter",
            "classification_data_class": "academic",
            "classification_purpose": "academic_report",
            "classification_retention_policy": "until_program_end_plus_1y",
            "description": _("Managed automatically for external recommendation intake."),
        }

        try:
            created = frappe.get_doc(payload)
            created.insert(ignore_permissions=True)
            return {
                "name": created.name,
                "document_type_name": created.document_type_name,
            }, True
        except DuplicateEntryError:
            row = frappe.db.get_value(
                "Applicant Document Type",
                {"code": code},
                ["name", "document_type_name"],
                as_dict=True,
            )
            if row:
                return row, False
            raise

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

            if not row.field_key and row.label:
                row.field_key = frappe.scrub(row.label)[:80]
            if not row.field_key:
                frappe.throw(_("Template field key is required."))
            if not row.label:
                frappe.throw(_("Template field label is required."))
            if row.field_type not in ALLOWED_FIELD_TYPES:
                frappe.throw(
                    _("Invalid template field type: {field_type}.").format(field_type=row.field_type or _("(empty)"))
                )
            if row.field_key in seen:
                frappe.throw(_("Duplicate template field key: {field_key}.").format(field_key=row.field_key))
            seen.add(row.field_key)

            if row.field_type == "Select" and not row.options_json:
                frappe.throw(
                    _("Template select field {field_label} must define options.").format(field_label=row.label)
                )
            if row.field_type in DISPLAY_ONLY_FIELD_TYPES:
                row.is_required = 0
            if row.field_type == "Likert Scale":
                row.options_json = frappe.as_json(self._normalize_likert_options(row.label, row.options_json))

    def _normalize_likert_options(self, field_label: str, options_json: str) -> dict:
        if not options_json:
            frappe.throw(
                _("Likert Scale field {field_label} must define scale options and rows.").format(
                    field_label=field_label
                )
            )

        try:
            config = frappe.parse_json(options_json)
        except Exception:
            config = None
        if not isinstance(config, dict):
            frappe.throw(
                _("Likert Scale field {field_label} options must be valid JSON.").format(field_label=field_label)
            )

        columns = self._normalize_keyed_options(
            config.get("columns"),
            label=_("scale options for {field_label}").format(field_label=field_label),
            minimum=2,
        )
        rows = self._normalize_keyed_options(
            config.get("rows"),
            label=_("rows for {field_label}").format(field_label=field_label),
            minimum=1,
        )

        return {
            "version": 1,
            "columns": columns,
            "rows": rows,
        }

    def _normalize_keyed_options(self, values, *, label: str, minimum: int) -> list[dict]:
        if not isinstance(values, list) or len(values) < minimum:
            frappe.throw(_("{label} must include at least {minimum} entries.").format(label=label, minimum=minimum))

        normalized = []
        seen = set()
        for value in values:
            if isinstance(value, dict):
                option_label = (value.get("label") or value.get("key") or "").strip()
                key = frappe.scrub((value.get("key") or option_label).strip())[:80]
            else:
                option_label = str(value or "").strip()
                key = frappe.scrub(option_label)[:80]

            if not key or not option_label:
                frappe.throw(_("{label} cannot include blank entries.").format(label=label))
            if key in seen:
                frappe.throw(_("{label} cannot include duplicate key: {key}.").format(label=label, key=key))
            seen.add(key)
            normalized.append({"key": key, "label": option_label})

        return normalized
