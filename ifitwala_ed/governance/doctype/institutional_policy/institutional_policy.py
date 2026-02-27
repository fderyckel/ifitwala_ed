# ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.governance.policy_scope_utils import (
    get_user_policy_scope,
    is_policy_within_user_scope,
    is_school_within_policy_organization_scope,
)
from ifitwala_ed.governance.policy_utils import POLICY_CATEGORIES, ensure_policy_admin, is_system_manager


class InstitutionalPolicy(Document):
    def before_insert(self):
        ensure_policy_admin()
        self._validate_policy_category()
        if not self.organization:
            frappe.throw(_("Organization is required."))
        self._validate_unique_policy_key()
        self._validate_school_organization()

    def before_save(self):
        ensure_policy_admin()
        self._validate_policy_category()
        self._validate_school_organization()
        if self.is_new():
            return
        before = self.get_doc_before_save()
        if not before:
            return
        self._enforce_immutability(before)

    def before_delete(self):
        frappe.throw(_("Institutional Policies cannot be deleted. Deactivate instead."))

    def _validate_unique_policy_key(self):
        if not self.policy_key or not self.organization:
            return
        exists = frappe.db.exists(
            "Institutional Policy",
            {
                "policy_key": self.policy_key,
                "organization": self.organization,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(_("Policy Key must be unique within the Organization."))

    def _validate_school_organization(self):
        if not self.school:
            return
        if not self.organization:
            return
        if is_school_within_policy_organization_scope(
            policy_organization=self.organization,
            school=self.school,
        ):
            return

        school_org = frappe.db.get_value("School", self.school, "organization")
        frappe.throw(
            _(
                "School Organization '{0}' is outside Policy Organization scope '{1}'. "
                "Scope includes the Policy Organization and its descendants."
            ).format(school_org or _("Unknown"), self.organization)
        )

    def _enforce_immutability(self, before):
        for field in ("policy_key", "organization"):
            if before.get(field) != self.get(field):
                frappe.throw(_("{0} is immutable once set.").format(field.replace("_", " ").title()))

        before_school = (before.get("school") or "").strip()
        current_school = (self.get("school") or "").strip()
        if before_school and before_school != current_school:
            frappe.throw(_("School is immutable once set."))

    def _validate_policy_category(self):
        if not self.policy_category or self.policy_category not in POLICY_CATEGORIES:
            frappe.throw(_("Policy Category must be one of: {0}.").format(", ".join(POLICY_CATEGORIES)))


def _escaped_in(values: list[str]) -> str:
    cleaned = [(value or "").strip() for value in values if (value or "").strip()]
    if not cleaned:
        return ""
    return ", ".join(frappe.db.escape(value) for value in cleaned)


def get_permission_query_conditions(user: str | None = None) -> str | None:
    user = user or frappe.session.user
    if user == "Administrator" or is_system_manager(user):
        return None

    organization_scope, school_scope = get_user_policy_scope(user)
    organizations_sql = _escaped_in(organization_scope)
    if not organizations_sql:
        return "1=0"

    school_sql = _escaped_in(school_scope)
    if school_sql:
        school_condition = (
            "(ifnull(`tabInstitutional Policy`.`school`, '') = '' "
            f"OR `tabInstitutional Policy`.`school` in ({school_sql}))"
        )
    else:
        school_condition = "ifnull(`tabInstitutional Policy`.`school`, '') = ''"

    return f"`tabInstitutional Policy`.`organization` in ({organizations_sql}) AND {school_condition}"


def has_permission(doc: "InstitutionalPolicy", user: str | None = None, ptype: str | None = None) -> bool:
    user = user or frappe.session.user
    if user == "Administrator" or is_system_manager(user):
        return True

    if not doc:
        return True

    if isinstance(doc, str):
        row = frappe.db.get_value(
            "Institutional Policy",
            doc,
            ["organization", "school"],
            as_dict=True,
        )
        if not row:
            return False
        policy_organization = (row.get("organization") or "").strip()
        policy_school = (row.get("school") or "").strip()
    else:
        policy_organization = (getattr(doc, "organization", None) or "").strip()
        policy_school = (getattr(doc, "school", None) or "").strip()

    return is_policy_within_user_scope(
        policy_organization=policy_organization,
        policy_school=policy_school,
        user=user,
    )
