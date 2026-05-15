# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_descendants_including_self,
    is_school_within_policy_organization_scope,
)
from ifitwala_ed.website.utils import validate_cta_link

ACKNOWLEDGEMENT_PROFILE_CONFIG_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}


class AdmissionAcknowledgementProfile(Document):
    def validate(self):
        self._normalize_fields()
        self._validate_scope()
        self._validate_email_template()
        self._validate_ctas()
        self._validate_unique_active_scope()

    def _normalize_fields(self):
        self.profile_name = (self.profile_name or "").strip()
        self.organization = (self.organization or "").strip()
        self.school = (self.school or "").strip()
        self.email_template = (self.email_template or "").strip()
        self.thank_you_title = (self.thank_you_title or "").strip()
        self.thank_you_message = (self.thank_you_message or "").strip()
        self.timeline_intro = (self.timeline_intro or "").strip()
        self.visit_cta_label = (self.visit_cta_label or "").strip()
        self.visit_cta_route = (self.visit_cta_route or "").strip()
        self.application_cta_label = (self.application_cta_label or "").strip()
        self.application_cta_route = (self.application_cta_route or "").strip()
        self.footer_note = (self.footer_note or "").strip()

        if not self.profile_name:
            self.profile_name = self.school or self.organization or _("Admissions Acknowledgement")
        if not self.thank_you_title:
            self.thank_you_title = _("Inquiry received")
        if not self.thank_you_message:
            self.thank_you_message = _(
                "Thank you for contacting us. Our admissions team will review your inquiry and get back to you soon."
            )
        if not self.timeline_intro:
            self.timeline_intro = _("What happens next")
        if not self.visit_cta_label:
            self.visit_cta_label = _("Book a tour or open day")
        if not self.application_cta_label:
            self.application_cta_label = _("Start an application")

    def _validate_scope(self):
        if not self.organization:
            frappe.throw(_("Organization is required."))

        if not self.school:
            return

        if not is_school_within_policy_organization_scope(
            policy_organization=self.organization,
            school=self.school,
        ):
            frappe.throw(_("School must be within the selected Organization scope."))

    def _validate_email_template(self):
        if not self.email_template:
            frappe.throw(_("Email Template is required."))
        if not frappe.db.exists("Email Template", self.email_template):
            frappe.throw(_("Invalid Email Template: {email_template}.").format(email_template=self.email_template))

    def _validate_ctas(self):
        if self.visit_cta_route:
            self.visit_cta_route = validate_cta_link(self.visit_cta_route)

        if self.application_cta_route:
            self.application_cta_route = validate_cta_link(self.application_cta_route)
            if self.application_cta_route == "/admissions":
                frappe.throw(
                    _(
                        "Application CTA Route must be a public application route, not the authenticated Admissions Portal."
                    )
                )

        if cint(self.show_application_cta) and not self.application_cta_route:
            frappe.throw(_("Application CTA Route is required when Show Application CTA is enabled."))

    def _validate_unique_active_scope(self):
        if not cint(self.is_active):
            return

        params = {
            "organization": self.organization,
            "school": self.school,
            "name": self.name or "",
        }
        if self.school:
            duplicate = frappe.db.sql(
                """
                SELECT name
                FROM `tabAdmission Acknowledgement Profile`
                WHERE is_active = 1
                    AND organization = %(organization)s
                    AND school = %(school)s
                    AND name != %(name)s
                LIMIT 1
                """,
                params,
            )
        else:
            duplicate = frappe.db.sql(
                """
                SELECT name
                FROM `tabAdmission Acknowledgement Profile`
                WHERE is_active = 1
                    AND organization = %(organization)s
                    AND (school IS NULL OR school = '')
                    AND name != %(name)s
                LIMIT 1
                """,
                params,
            )
        if duplicate:
            frappe.throw(_("Only one active acknowledgement profile is allowed per Organization and School scope."))


def _ensure_acknowledgement_profile_config_access(user: str | None = None) -> str:
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to configure admissions acknowledgements."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if user == "Administrator" or roles & ACKNOWLEDGEMENT_PROFILE_CONFIG_ROLES:
        return user

    frappe.throw(_("You do not have permission to configure admissions acknowledgements."), frappe.PermissionError)
    return user


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def acknowledgement_school_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    _ensure_acknowledgement_profile_config_access()
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    organization = (filters.get("organization") or "").strip()
    if not organization:
        return []

    organization_scope = get_organization_descendants_including_self(organization)
    if not organization_scope:
        return []

    schools = frappe.get_all(
        "School",
        filters={
            "organization": ["in", organization_scope],
            "name": ["like", f"%{txt or ''}%"],
        },
        fields=["name", "school_name"],
        order_by="lft asc, school_name asc, name asc",
        limit_start=int(start or 0),
        limit=int(page_len or 20),
    )
    return [(row.get("name"), row.get("school_name") or row.get("name")) for row in schools]
