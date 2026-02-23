# ifitwala_ed/admission/doctype/applicant_document_type/applicant_document_type.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from ifitwala_ed.governance.policy_scope_utils import is_policy_organization_applicable_to_context


class ApplicantDocumentType(Document):
    def validate(self):
        self._validate_scope_coherence()
        self._validate_classification_contract()

    def _validate_scope_coherence(self):
        school = (self.school or "").strip()
        organization = (self.organization or "").strip()
        if not school:
            return

        school_org = frappe.db.get_value("School", school, "organization")
        if not school_org:
            frappe.throw(_("Selected School must belong to an Organization."))

        if not organization:
            self.organization = school_org
            return

        if is_policy_organization_applicable_to_context(
            policy_organization=organization,
            context_organization=school_org,
        ):
            return

        frappe.throw(_("School must be within the selected Organization scope."))

    def _validate_classification_contract(self):
        values = {
            "classification_slot": (self.classification_slot or "").strip(),
            "classification_data_class": (self.classification_data_class or "").strip(),
            "classification_purpose": (self.classification_purpose or "").strip(),
            "classification_retention_policy": (self.classification_retention_policy or "").strip(),
        }

        provided = [fieldname for fieldname, value in values.items() if value]
        missing = [fieldname for fieldname, value in values.items() if not value]

        if not provided:
            if cint(self.is_active):
                frappe.throw(
                    _(
                        "Classification fields are required for active Applicant Document Types. "
                        "Provide slot, data class, purpose, and retention policy."
                    )
                )
            return

        if missing:
            labels = ", ".join(fieldname.replace("classification_", "").replace("_", " ") for fieldname in missing)
            frappe.throw(_("Incomplete classification settings. Missing: {0}.").format(labels))
