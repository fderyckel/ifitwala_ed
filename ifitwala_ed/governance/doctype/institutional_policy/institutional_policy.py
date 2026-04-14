# ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.governance.policy_scope_utils import (
    get_user_policy_management_scope,
    get_user_policy_scope,
    is_policy_manageable_by_user,
    is_policy_within_user_scope,
)
from ifitwala_ed.governance.policy_utils import (
    POLICY_APPLIES_TO_CHILD_DOCTYPE,
    POLICY_APPLIES_TO_LINK_FIELD,
    POLICY_APPLIES_TO_OPTIONS,
    POLICY_CATEGORIES,
    ensure_policy_admin,
    get_policy_applies_to_tokens,
    is_policy_admin,
    is_system_manager,
)


class InstitutionalPolicy(Document):
    def before_insert(self):
        ensure_policy_admin()
        self._validate_policy_category()
        self._validate_applies_to()
        if not self.organization:
            frappe.throw(_("Organization is required."))
        self._validate_unique_policy_key()
        self._validate_school_organization()

    def before_save(self):
        ensure_policy_admin()
        self._validate_policy_category()
        self._validate_applies_to()
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
        school_org = (frappe.db.get_value("School", self.school, "organization") or "").strip()
        if school_org == (self.organization or "").strip():
            return

        frappe.throw(
            _(
                "Selected School belongs to Organization '{school_organization}', but this policy is scoped to "
                "Organization '{policy_organization}'. For school-scoped policies, the School must belong directly "
                "to the selected Organization. Leave School blank for an organization-wide policy."
            ).format(
                school_organization=school_org or _("Unknown"),
                policy_organization=self.organization,
            )
        )

    def _enforce_immutability(self, before):
        if before.get("policy_key") != self.get("policy_key"):
            frappe.throw(_("Policy Key is immutable once set."))

        before_organization = (before.get("organization") or "").strip()
        current_organization = (self.get("organization") or "").strip()
        if before_organization != current_organization:
            _raise_organization_transfer_permission_error(before_organization, current_organization)

        before_school = (before.get("school") or "").strip()
        current_school = (self.get("school") or "").strip()
        if before_school and before_school != current_school:
            frappe.throw(
                _(
                    "School cannot be changed or cleared after creation. This policy is currently scoped to "
                    "School '{current_school}'. Create a new Institutional Policy if you need a different school scope."
                ).format(current_school=before_school)
            )

    def _validate_policy_category(self):
        if not self.policy_category or self.policy_category not in POLICY_CATEGORIES:
            frappe.throw(
                _("Policy Category must be one of: {policy_categories}.").format(
                    policy_categories=", ".join(POLICY_CATEGORIES)
                )
            )

    def _validate_applies_to(self):
        tokens = get_policy_applies_to_tokens(self.applies_to)
        if not tokens:
            frappe.throw(_("Applies To must include at least one audience."))

        invalid = [token for token in tokens if token not in POLICY_APPLIES_TO_OPTIONS]
        if invalid:
            frappe.throw(
                _("Applies To must only use: {allowed_values}. Invalid values: {invalid_values}.").format(
                    allowed_values=", ".join(POLICY_APPLIES_TO_OPTIONS),
                    invalid_values=", ".join(invalid),
                )
            )

        self.set(
            "applies_to",
            [
                {
                    "doctype": POLICY_APPLIES_TO_CHILD_DOCTYPE,
                    POLICY_APPLIES_TO_LINK_FIELD: token,
                }
                for token in tokens
            ],
        )


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
    management_scope = get_user_policy_management_scope(user) if is_policy_admin(user) else []
    organizations_sql = _escaped_in(organization_scope)
    management_sql = _escaped_in(management_scope)

    clauses: list[str] = []
    if organizations_sql:
        school_sql = _escaped_in(school_scope)
        if school_sql:
            school_condition = (
                "(ifnull(`tabInstitutional Policy`.`school`, '') = '' "
                f"OR `tabInstitutional Policy`.`school` in ({school_sql}))"
            )
        else:
            school_condition = "ifnull(`tabInstitutional Policy`.`school`, '') = ''"
        clauses.append(f"(`tabInstitutional Policy`.`organization` in ({organizations_sql}) AND {school_condition})")

    if management_sql:
        clauses.append(f"`tabInstitutional Policy`.`organization` in ({management_sql})")

    if not clauses:
        return "1=0"

    return " OR ".join(clauses)


def _raise_organization_transfer_permission_error(previous_organization: str, next_organization: str) -> None:
    frappe.throw(
        _(
            "Organization cannot be changed after creation. This policy is currently scoped to '{previous_organization}'. "
            "To move it under '{next_organization}', create a new Institutional Policy for that organization and "
            "deactivate this one if needed."
        ).format(
            previous_organization=previous_organization,
            next_organization=next_organization,
        ),
        frappe.PermissionError,
    )


def _raise_policy_management_scope_permission_error(policy_organization: str, *, ptype: str | None = None) -> None:
    action = "manage"
    if ptype == "create":
        action = "create"
    elif ptype == "write":
        action = "edit"
    frappe.throw(
        _(
            "You can {0} policies only for your organization or its descendants. "
            "Organization '{1}' is outside your policy admin scope."
        ).format(action, policy_organization),
        frappe.PermissionError,
    )


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
        if ptype == "write" and getattr(doc, "name", None):
            existing = frappe.db.get_value(
                "Institutional Policy",
                doc.name,
                ["organization"],
                as_dict=True,
            )
            existing_organization = (existing.get("organization") or "").strip() if existing else ""
            if existing_organization and existing_organization != policy_organization:
                _raise_organization_transfer_permission_error(existing_organization, policy_organization)

    if is_policy_admin(user):
        if is_policy_manageable_by_user(policy_organization=policy_organization, user=user):
            return True
        if ptype in {"create", "write"} and policy_organization:
            _raise_policy_management_scope_permission_error(policy_organization, ptype=ptype)

    return is_policy_within_user_scope(
        policy_organization=policy_organization,
        policy_school=policy_school,
        user=user,
    )
