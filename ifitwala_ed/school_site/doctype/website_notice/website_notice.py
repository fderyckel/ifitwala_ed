# ifitwala_ed/school_site/doctype/website_notice/website_notice.py

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.publication import (
    WORKFLOW_TRANSITIONS,
    compute_publication_status,
    normalize_workflow_state,
    validate_publication_window,
)
from ifitwala_ed.website.site_notices import invalidate_site_notice_cache
from ifitwala_ed.website.utils import validate_cta_link


class WebsiteNotice(Document):
    def validate(self):
        self._ensure_workflow_state()
        validate_publication_window(publish_at=self.publish_at, expire_at=self.expire_at)
        self.button_link = validate_cta_link(self.button_link)
        self._sync_status()

    def on_update(self):
        invalidate_site_notice_cache()

    def after_insert(self):
        invalidate_site_notice_cache()

    def on_trash(self):
        invalidate_site_notice_cache()

    def _ensure_workflow_state(self):
        self.workflow_state = normalize_workflow_state(self.workflow_state)

    def _sync_status(self):
        self.status = compute_publication_status(
            base_is_public=self._get_school_publication_readiness(),
            workflow_state=self.workflow_state,
            publish_at=self.publish_at,
            expire_at=self.expire_at,
        )

    def _get_school_publication_readiness(self) -> bool:
        if not self.school:
            return False
        row = frappe.db.get_value(
            "School",
            self.school,
            ["website_slug", "is_published"],
            as_dict=True,
        )
        return bool(row and row.website_slug and int(row.is_published or 0) == 1)

    def _assert_transition_allowed(self, action: str) -> str:
        action_key = (action or "").strip()
        transition = WORKFLOW_TRANSITIONS.get(action_key)
        if not transition:
            frappe.throw(
                _("Unknown workflow action: {action}").format(action=action_key or _("(empty)")),
                frappe.ValidationError,
            )

        current_state = normalize_workflow_state(self.workflow_state)
        if current_state not in transition["from_states"]:
            frappe.throw(
                _("Cannot run '{action}' from workflow state '{state}'.").format(
                    action=action_key,
                    state=current_state,
                ),
                frappe.ValidationError,
            )

        user_roles = set(frappe.get_roles())
        if not user_roles.intersection(set(transition["roles"])):
            frappe.throw(
                _("You do not have permission to run workflow action: {action}.").format(action=action_key),
                frappe.PermissionError,
            )
        return action_key

    def apply_workflow_action(self, action: str):
        action_key = self._assert_transition_allowed(action)
        target_state = WORKFLOW_TRANSITIONS[action_key]["to_state"]
        if target_state == "Published" and not self._get_school_publication_readiness():
            frappe.throw(
                _("Cannot publish until the school has a website slug and Is Published enabled."),
                frappe.ValidationError,
            )
        self.workflow_state = target_state
        self._sync_status()


@frappe.whitelist()
def transition_workflow_state(name: str, action: str) -> dict:
    doc = frappe.get_doc("Website Notice", name)
    if not frappe.has_permission(doc=doc, ptype="write"):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    doc.apply_workflow_action(action)
    doc.save()
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "status": doc.status,
    }
