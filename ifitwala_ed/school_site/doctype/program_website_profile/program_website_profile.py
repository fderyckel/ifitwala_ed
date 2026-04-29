# ifitwala_ed/school_site/doctype/program_website_profile/program_website_profile.py

import json

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.publication import (
    WORKFLOW_TRANSITIONS,
    compute_publication_status,
    normalize_workflow_state,
    validate_publication_window,
)
from ifitwala_ed.website.utils import apply_missing_block_enabled_defaults
from ifitwala_ed.website.validators import validate_page_blocks


def compute_program_profile_status(
    *,
    school_is_public: bool,
    program_is_published: bool,
    has_program_slug: bool,
    workflow_state: str,
    publish_at=None,
    expire_at=None,
) -> str:
    return compute_publication_status(
        base_is_public=bool(school_is_public and program_is_published and has_program_slug),
        workflow_state=workflow_state,
        publish_at=publish_at,
        expire_at=expire_at,
    )


class ProgramWebsiteProfile(Document):
    def validate(self):
        self._ensure_workflow_state()
        validate_publication_window(publish_at=self.publish_at, expire_at=self.expire_at)
        self._sync_status_from_program()
        self._validate_unique_profile()
        self._validate_program_slug()
        apply_missing_block_enabled_defaults(self.blocks)
        self._validate_blocks_props_json()
        validate_page_blocks(self)

    def on_update(self):
        self._sync_website_discoverability()

    def after_insert(self):
        self._sync_website_discoverability()

    def on_trash(self):
        self._invalidate_program_list_cache()

    def _sync_status_from_program(self):
        self.status = compute_program_profile_status(
            school_is_public=self._get_school_publication_readiness(),
            program_is_published=self._get_program_publication_readiness(),
            has_program_slug=bool((frappe.db.get_value("Program", self.program, "program_slug") or "").strip())
            if self.program
            else False,
            workflow_state=self.workflow_state,
            publish_at=self.publish_at,
            expire_at=self.expire_at,
        )

    def _ensure_workflow_state(self):
        self.workflow_state = normalize_workflow_state(self.workflow_state)

    def _get_program_publication_readiness(self) -> bool:
        if not self.program:
            return False
        row = frappe.db.get_value(
            "Program",
            self.program,
            ["is_published", "archive", "program_slug"],
            as_dict=True,
        )
        if not row:
            return False
        return bool(int(row.is_published or 0) == 1 and int(row.archive or 0) == 0 and row.program_slug)

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
        allowed_roles = set(transition["roles"])
        if not user_roles.intersection(allowed_roles):
            frappe.throw(
                _("You do not have permission to run workflow action: {action}.").format(action=action_key),
                frappe.PermissionError,
            )
        return action_key

    def apply_workflow_action(self, action: str):
        action_key = self._assert_transition_allowed(action)
        target_state = WORKFLOW_TRANSITIONS[action_key]["to_state"]
        if target_state == "Published" and not (
            self._get_school_publication_readiness() and self._get_program_publication_readiness()
        ):
            frappe.throw(
                _(
                    "Cannot publish until the school website is published and the Program is published, not archived, and has a program slug."
                ),
                frappe.ValidationError,
            )
        self.workflow_state = target_state
        self._sync_status_from_program()

    def _validate_unique_profile(self):
        exists = frappe.db.exists(
            "Program Website Profile",
            {
                "program": self.program,
                "school": self.school,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(
                _("A Program Website Profile already exists for this Program and School."),
                frappe.ValidationError,
            )

    def _validate_program_slug(self):
        if self.status != "Published":
            return
        program_slug = frappe.db.get_value("Program", self.program, "program_slug")
        if not program_slug:
            frappe.throw(
                _("Program slug is required before publishing a Program Website Profile."),
                frappe.ValidationError,
            )

    def _sync_website_discoverability(self):
        if self.status == "Published" and self.school:
            from ifitwala_ed.website.bootstrap import ensure_programs_index_page

            ensure_programs_index_page(school_name=self.school)

        self._invalidate_program_list_cache()

    def _invalidate_program_list_cache(self):
        from ifitwala_ed.website.providers.program_list import invalidate_program_list_cache

        invalidate_program_list_cache()

    def _validate_blocks_props_json(self):
        for row in self.blocks or []:
            raw_props = (row.props or "").strip()
            if not raw_props:
                continue
            try:
                json.loads(raw_props)
            except Exception as exc:
                frappe.throw(
                    _("Invalid block props JSON in row {row_index} ({block_type}): {error}").format(
                        row_index=row.idx or "?",
                        block_type=row.block_type or _("Unknown block"),
                        error=str(exc),
                    ),
                    frappe.ValidationError,
                )


@frappe.whitelist()
def transition_workflow_state(name: str, action: str) -> dict:
    doc = frappe.get_doc("Program Website Profile", name)
    if not frappe.has_permission(doc=doc, ptype="write"):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    doc.apply_workflow_action(action)
    doc.save()
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "status": doc.status,
    }
