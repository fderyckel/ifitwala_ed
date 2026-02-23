# ifitwala_ed/governance/doctype/policy_version/policy_version.py

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from ifitwala_ed.governance.policy_utils import ensure_policy_admin, is_system_manager


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
