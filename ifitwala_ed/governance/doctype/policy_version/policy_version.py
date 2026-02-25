# ifitwala_ed/governance/doctype/policy_version/policy_version.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_admin, is_system_manager

PRIVILEGED_POLICY_WRITE_ROLES = frozenset({"System Manager", "Administrator"})


def _parse_query_filters(filters) -> dict:
    raw_filters = filters or {}
    if isinstance(raw_filters, str):
        try:
            raw_filters = frappe.parse_json(raw_filters) or {}
        except Exception:
            raw_filters = {}
    return raw_filters if isinstance(raw_filters, dict) else {}


def _policy_version_write_roles() -> set[str]:
    meta = frappe.get_meta("Policy Version")
    roles: set[str] = set()
    for perm in meta.permissions or []:
        role = (getattr(perm, "role", "") or "").strip()
        if not role:
            continue
        if int(getattr(perm, "write", 0) or 0):
            roles.add(role)
    return roles


def _users_with_roles(roles: set[str] | frozenset[str]) -> set[str]:
    role_values = sorted({(role or "").strip() for role in roles if (role or "").strip()})
    if not role_values:
        return set()

    rows = frappe.get_all(
        "Has Role",
        filters={
            "parenttype": "User",
            "role": ["in", tuple(role_values)],
        },
        pluck="parent",
    )
    return {(row or "").strip() for row in rows if (row or "").strip()}


def _get_policy_scope(institutional_policy: str | None) -> tuple[str, str]:
    institutional_policy = (institutional_policy or "").strip()
    if not institutional_policy:
        return "", ""

    row = frappe.db.get_value(
        "Institutional Policy",
        institutional_policy,
        ["organization", "school"],
        as_dict=True,
    )
    if not row:
        return "", ""
    return (row.get("organization") or "").strip(), (row.get("school") or "").strip()


def _scope_employee_users(*, policy_organization: str | None, policy_school: str | None) -> set[str]:
    policy_organization = (policy_organization or "").strip()
    policy_school = (policy_school or "").strip()

    filters: dict = {
        "employment_status": "Active",
        "user_id": ["is", "set"],
    }
    if policy_school:
        school_scope = tuple(get_school_ancestors_including_self(policy_school))
        if not school_scope:
            return set()
        filters["school"] = ["in", school_scope]
    else:
        organization_scope = tuple(get_organization_ancestors_including_self(policy_organization))
        if not organization_scope:
            return set()
        filters["organization"] = ["in", organization_scope]

    rows = frappe.get_all("Employee", filters=filters, pluck="user_id")
    return {(row or "").strip() for row in rows if (row or "").strip()}


def _users_with_policy_version_write_access() -> set[str]:
    write_roles = _policy_version_write_roles() | set(PRIVILEGED_POLICY_WRITE_ROLES)
    return _users_with_roles(write_roles)


def _eligible_approver_users(*, policy_organization: str | None, policy_school: str | None) -> set[str]:
    write_users = _users_with_policy_version_write_access()
    if not write_users:
        return set()

    privileged_users = _users_with_roles(PRIVILEGED_POLICY_WRITE_ROLES)
    scoped_users = _scope_employee_users(
        policy_organization=policy_organization,
        policy_school=policy_school,
    )
    return write_users & (scoped_users | privileged_users)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def approved_by_user_query(doctype, txt, searchfield, start, page_len, filters):
    query_filters = _parse_query_filters(filters)
    institutional_policy = (query_filters.get("institutional_policy") or "").strip()

    if institutional_policy:
        policy_organization, policy_school = _get_policy_scope(institutional_policy)
        candidates = _eligible_approver_users(
            policy_organization=policy_organization,
            policy_school=policy_school,
        )
    else:
        candidates = _users_with_policy_version_write_access()

    if not candidates:
        return []

    search_text = f"%{(txt or '').strip()}%"
    return frappe.db.sql(
        """
        SELECT
            u.name,
            COALESCE(NULLIF(u.full_name, ''), u.name) AS full_name
        FROM `tabUser` u
        WHERE u.enabled = 1
          AND u.user_type = 'System User'
          AND u.name IN %(candidates)s
          AND (
              u.name LIKE %(search_text)s
              OR COALESCE(u.full_name, '') LIKE %(search_text)s
          )
        ORDER BY COALESCE(NULLIF(u.full_name, ''), u.name) ASC, u.name ASC
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "candidates": tuple(sorted(candidates)),
            "search_text": search_text,
            "start": int(start or 0),
            "page_len": int(page_len or 20),
        },
    )


class PolicyVersion(Document):
    def before_insert(self):
        ensure_policy_admin()
        self._validate_parent_policy()
        self._validate_unique_version_label()
        if not (self.policy_text or "").strip():
            frappe.throw(_("Policy Text is required."))

    def before_save(self):
        ensure_policy_admin()
        before = self.get_doc_before_save() if not self.is_new() else None
        if before:
            self._enforce_immutability(before)
            self._enforce_ack_lock(before)
        self._validate_approved_by_write_access()
        self._validate_active_state()

    def before_delete(self):
        frappe.throw(_("Policy Versions cannot be deleted."))

    def _validate_parent_policy(self):
        if not self.institutional_policy:
            frappe.throw(_("Institutional Policy is required."))
        active = frappe.db.get_value("Institutional Policy", self.institutional_policy, "is_active")
        if not active:
            frappe.throw(_("Institutional Policy must be active."))

    def _validate_unique_version_label(self):
        if not self.institutional_policy or not self.version_label:
            return
        exists = frappe.db.exists(
            "Policy Version",
            {
                "institutional_policy": self.institutional_policy,
                "version_label": self.version_label,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(_("Version Label must be unique per Institutional Policy."))

    def _enforce_immutability(self, before):
        if before.institutional_policy != self.institutional_policy:
            frappe.throw(_("Institutional Policy is immutable once set."))

    def _enforce_ack_lock(self, before):
        has_ack = frappe.db.exists("Policy Acknowledgement", {"policy_version": self.name})
        if not has_ack:
            return

        locked_fields = ("policy_text", "version_label", "institutional_policy")
        if all(before.get(f) == self.get(f) for f in locked_fields):
            return

        override_reason = getattr(self.flags, "override_reason", None)
        if not is_system_manager() or not override_reason:
            frappe.throw(
                _(
                    "Policy Version is immutable after acknowledgements exist. "
                    "System Manager override with reason is required."
                )
            )

        self.add_comment(
            "Comment",
            text=_("System Manager override on Policy Version by {0} at {1}. Reason: {2}.").format(
                frappe.bold(frappe.session.user), now_datetime(), override_reason
            ),
        )

    def _validate_active_state(self):
        if not self.is_active:
            return
        active_parent = frappe.db.get_value("Institutional Policy", self.institutional_policy, "is_active")
        if not active_parent:
            frappe.throw(_("Cannot activate a Policy Version for an inactive Policy."))

        exists = frappe.db.exists(
            "Policy Version",
            {
                "institutional_policy": self.institutional_policy,
                "is_active": 1,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(_("Another active Policy Version already exists."))

    def _validate_approved_by_write_access(self):
        approver = (self.approved_by or "").strip()
        if not approver:
            return

        user_row = frappe.db.get_value(
            "User",
            approver,
            ["name", "enabled", "user_type"],
            as_dict=True,
        )
        if not user_row or not int(user_row.get("enabled") or 0):
            frappe.throw(_("Approved By must be an enabled user."))
        if (user_row.get("user_type") or "").strip() != "System User":
            frappe.throw(_("Approved By must be a system user."))

        if not frappe.has_permission("Policy Version", ptype="write", user=approver, doc=self):
            frappe.throw(_("Approved By must have write access to this Policy Version."), frappe.PermissionError)

        policy_organization, policy_school = _get_policy_scope(self.institutional_policy)
        eligible_users = _eligible_approver_users(
            policy_organization=policy_organization,
            policy_school=policy_school,
        )
        if approver in eligible_users:
            return

        if policy_school:
            frappe.throw(
                _("Approved By must belong to the selected school or one of its parent schools."),
                frappe.PermissionError,
            )
        frappe.throw(
            _("Approved By must belong to the policy organization or one of its parent organizations."),
            frappe.PermissionError,
        )
