# ifitwala_ed/governance/doctype/policy_version/policy_version.py

import json
import re
from difflib import SequenceMatcher
from html import escape, unescape

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, now_datetime

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


def _normalize_policy_paragraphs(policy_text: str | None) -> list[str]:
    html_text = (policy_text or "").strip()
    if not html_text:
        return []

    # Normalize common block delimiters before stripping markup.
    normalized = re.sub(r"(?is)<\s*br\s*/?\s*>", "\n", html_text)
    normalized = re.sub(r"(?is)</\s*(p|div|li|h[1-6]|blockquote|tr|table|ul|ol)\s*>", "\n\n", normalized)
    normalized = re.sub(r"(?is)<\s*li[^>]*>", "• ", normalized)
    normalized = re.sub(r"(?is)<[^>]+>", "", normalized)
    normalized = unescape(normalized).replace("\r\n", "\n").replace("\r", "\n")

    paragraphs = []
    for raw in re.split(r"\n\s*\n+", normalized):
        paragraph = re.sub(r"\s+", " ", (raw or "")).strip()
        if paragraph:
            paragraphs.append(paragraph)
    return paragraphs


def _render_added_paragraph(*, label: str, paragraph: str) -> str:
    return (
        '<article class="policy-diff-block policy-diff-block--added">'
        f'<div class="policy-diff-label">{escape(label)}</div>'
        f'<div class="policy-diff-body"><ins>{escape(paragraph)}</ins></div>'
        "</article>"
    )


def _render_removed_paragraph(*, label: str, paragraph: str) -> str:
    return (
        '<article class="policy-diff-block policy-diff-block--removed">'
        f'<div class="policy-diff-label">{escape(label)}</div>'
        '<details class="policy-diff-removed">'
        "<summary>Removed text (tap to view)</summary>"
        f'<div class="policy-diff-body"><del>{escape(paragraph)}</del></div>'
        "</details>"
        "</article>"
    )


def _render_modified_paragraph(*, label: str, old_paragraph: str, new_paragraph: str) -> str:
    return (
        '<article class="policy-diff-block policy-diff-block--modified">'
        f'<div class="policy-diff-label">{escape(label)}</div>'
        '<div class="policy-diff-body">'
        '<details class="policy-diff-previous">'
        "<summary>Previous text</summary>"
        f'<div class="policy-diff-body-old"><del>{escape(old_paragraph)}</del></div>'
        "</details>"
        f'<div class="policy-diff-body-new"><ins>{escape(new_paragraph)}</ins></div>'
        "</div>"
        "</article>"
    )


def _build_policy_diff_html(previous_text: str | None, current_text: str | None) -> tuple[str, dict[str, int]]:
    previous_paragraphs = _normalize_policy_paragraphs(previous_text)
    current_paragraphs = _normalize_policy_paragraphs(current_text)

    stats = {"added": 0, "removed": 0, "modified": 0}
    blocks: list[str] = []

    matcher = SequenceMatcher(None, previous_paragraphs, current_paragraphs, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        if tag == "insert":
            for idx in range(j1, j2):
                stats["added"] += 1
                blocks.append(
                    _render_added_paragraph(
                        label=f"Paragraph {idx + 1}",
                        paragraph=current_paragraphs[idx],
                    )
                )
            continue

        if tag == "delete":
            for idx in range(i1, i2):
                stats["removed"] += 1
                blocks.append(
                    _render_removed_paragraph(
                        label=f"Paragraph {idx + 1}",
                        paragraph=previous_paragraphs[idx],
                    )
                )
            continue

        if tag == "replace":
            paired = min(i2 - i1, j2 - j1)
            for paired_idx in range(paired):
                old_idx = i1 + paired_idx
                new_idx = j1 + paired_idx
                stats["modified"] += 1
                blocks.append(
                    _render_modified_paragraph(
                        label=f"Paragraph {new_idx + 1}",
                        old_paragraph=previous_paragraphs[old_idx],
                        new_paragraph=current_paragraphs[new_idx],
                    )
                )

            for idx in range(i1 + paired, i2):
                stats["removed"] += 1
                blocks.append(
                    _render_removed_paragraph(
                        label=f"Paragraph {idx + 1}",
                        paragraph=previous_paragraphs[idx],
                    )
                )

            for idx in range(j1 + paired, j2):
                stats["added"] += 1
                blocks.append(
                    _render_added_paragraph(
                        label=f"Paragraph {idx + 1}",
                        paragraph=current_paragraphs[idx],
                    )
                )

    if not blocks:
        blocks.append(
            '<article class="policy-diff-block policy-diff-block--none"><p>No textual changes detected.</p></article>'
        )

    return (
        '<section class="policy-diff">' + "".join(blocks) + "</section>",
        stats,
    )


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
        self._validate_policy_text_required()
        self._validate_amendment_chain(require_for_existing_policy=True)
        self._validate_change_summary_requirement()
        self._sync_text_lock_state(before=None, has_ack=False)
        self._sync_diff_artifacts(has_ack=False)

    def before_save(self):
        ensure_policy_admin()
        if self.is_new():
            self._validate_parent_policy()
        before = self.get_doc_before_save() if not self.is_new() else None
        has_ack = self._has_acknowledgements() if before else False

        self._validate_policy_text_required()
        self._validate_unique_version_label()
        self._validate_amendment_chain(require_for_existing_policy=self.is_new())
        self._validate_change_summary_requirement()

        if before:
            self._enforce_immutability(before)
            self._enforce_policy_text_lock(before, has_ack=has_ack)
            self._enforce_ack_lock(before, has_ack=has_ack)

        self._sync_text_lock_state(before=before, has_ack=has_ack)
        self._sync_diff_artifacts(has_ack=has_ack)
        self._validate_diff_artifacts_for_activation()

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

    def _validate_policy_text_required(self):
        if not (self.policy_text or "").strip():
            frappe.throw(_("Policy Text is required."))

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

    def _has_acknowledgements(self) -> bool:
        return bool(self.name and frappe.db.exists("Policy Acknowledgement", {"policy_version": self.name}))

    def _enforce_policy_text_lock(self, before, *, has_ack: bool):
        if before.get("policy_text") == self.get("policy_text"):
            return
        if has_ack or cint(before.get("is_active")) or cint(before.get("text_locked")):
            frappe.throw(
                _(
                    "Policy Text is immutable once a Policy Version is active or acknowledged. "
                    "Create a new Policy Version amendment."
                )
            )

    def _enforce_ack_lock(self, before, *, has_ack: bool):
        if not has_ack:
            return

        locked_fields = (
            "policy_text",
            "version_label",
            "institutional_policy",
            "amended_from",
            "change_summary",
            "diff_html",
            "change_stats",
            "text_locked",
        )
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

    def _validate_amendment_chain(self, *, require_for_existing_policy: bool):
        policy_name = (self.institutional_policy or "").strip()
        if not policy_name:
            return

        amended_from = (self.amended_from or "").strip()
        if amended_from:
            if amended_from == self.name:
                frappe.throw(_("Amended From cannot point to the same Policy Version."))

            amended_row = frappe.db.get_value(
                "Policy Version",
                amended_from,
                ["name", "institutional_policy"],
                as_dict=True,
            )
            if not amended_row:
                frappe.throw(_("Amended From must reference an existing Policy Version."))

            if (amended_row.get("institutional_policy") or "").strip() != policy_name:
                frappe.throw(_("Amended From must belong to the same Institutional Policy."))
            return

        if not require_for_existing_policy:
            return

        prior_version_exists = frappe.db.exists(
            "Policy Version",
            {
                "institutional_policy": policy_name,
                "name": ["!=", self.name],
            },
        )
        if prior_version_exists:
            frappe.throw(_("Amended From is required for every new Policy Version after the first one."))

    def _validate_change_summary_requirement(self):
        if not (self.amended_from or "").strip():
            return
        if not (self.change_summary or "").strip():
            frappe.throw(_("Change Summary is required when Amended From is set."))

    def _sync_text_lock_state(self, *, before, has_ack: bool):
        if cint(getattr(self, "text_locked", 0)):
            self.text_locked = 1
            return

        if before and (cint(before.get("text_locked")) or cint(before.get("is_active"))):
            self.text_locked = 1
            return

        if has_ack or cint(self.is_active):
            self.text_locked = 1
            return

        self.text_locked = 0

    def _sync_diff_artifacts(self, *, has_ack: bool):
        if has_ack:
            return

        amended_from = (self.amended_from or "").strip()
        if not amended_from:
            self.diff_html = ""
            self.change_stats = ""
            return

        previous_text = frappe.db.get_value("Policy Version", amended_from, "policy_text")
        if previous_text is None:
            frappe.throw(_("Amended From policy text could not be resolved."))

        diff_html, stats = _build_policy_diff_html(previous_text, self.policy_text)
        if not (diff_html or "").strip():
            frappe.throw(_("Unable to generate policy diff for this amendment."))

        self.diff_html = diff_html
        self.change_stats = json.dumps(stats, sort_keys=True, separators=(",", ":"))

    def _validate_diff_artifacts_for_activation(self):
        if not cint(self.is_active):
            return

        if not (self.amended_from or "").strip():
            return

        if not (self.change_summary or "").strip():
            frappe.throw(_("Change Summary is required before activating an amended Policy Version."))

        if not (self.diff_html or "").strip():
            frappe.throw(_("Diff output is required before activating an amended Policy Version."))

        if not (self.change_stats or "").strip():
            frappe.throw(_("Change statistics are required before activating an amended Policy Version."))

        try:
            parsed = frappe.parse_json(self.change_stats)
        except Exception:
            parsed = None
        if not isinstance(parsed, dict):
            frappe.throw(_("Change statistics payload is invalid. Regenerate the amendment diff."))

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
