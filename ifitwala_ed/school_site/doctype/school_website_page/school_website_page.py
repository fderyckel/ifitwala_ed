# ifitwala_ed/school_site/doctype/school_website_page/school_website_page.py

import json

import frappe
from frappe import _
from frappe.model.document import Document

from ifitwala_ed.website.utils import normalize_route
from ifitwala_ed.website.validators import validate_page_blocks

WORKFLOW_DEFAULT_STATE = "Draft"
WORKFLOW_STATES = (
    "Draft",
    "In Review",
    "Approved",
    "Published",
)
WORKFLOW_TRANSITIONS = {
    "request_review": {
        "from_states": ("Draft",),
        "to_state": "In Review",
        "roles": ("Marketing User", "Website Manager", "System Manager"),
    },
    "approve": {
        "from_states": ("In Review",),
        "to_state": "Approved",
        "roles": ("Website Manager", "System Manager"),
    },
    "publish": {
        "from_states": ("Approved",),
        "to_state": "Published",
        "roles": ("Website Manager", "System Manager"),
    },
    "return_to_draft": {
        "from_states": ("In Review", "Approved", "Published"),
        "to_state": "Draft",
        "roles": ("Marketing User", "Website Manager", "System Manager"),
    },
}


def normalize_workflow_state(workflow_state: str | None) -> str:
    value = (workflow_state or "").strip() or WORKFLOW_DEFAULT_STATE
    if value not in WORKFLOW_STATES:
        frappe.throw(
            _("Invalid workflow state: {0}").format(value),
            frappe.ValidationError,
        )
    return value


def compute_school_page_publication_flags(*, school_is_public: bool, workflow_state: str) -> tuple[str, int]:
    state = normalize_workflow_state(workflow_state)
    is_published = 1 if school_is_public and state == "Published" else 0
    status = "Published" if is_published == 1 else "Draft"
    return status, is_published


class SchoolWebsitePage(Document):
    def before_insert(self):
        self._ensure_workflow_state()
        self._sync_status_flags()
        self._seed_admissions_blocks()

    def validate(self):
        self._ensure_workflow_state()
        self._sync_status_flags()
        school_slug = frappe.db.get_value("School", self.school, "website_slug")
        if not school_slug:
            frappe.throw(
                _("School website slug is required to build routes."),
                frappe.ValidationError,
            )

        raw_value = self.route or ""
        raw_route = raw_value.strip()
        if raw_value != raw_route:
            frappe.throw(
                _("Route cannot start or end with whitespace."),
                frappe.ValidationError,
            )
        if not raw_route:
            frappe.throw(
                _("Route is required. Use '/' for the school home page."),
                frappe.ValidationError,
            )

        if raw_route == "/":
            self.full_route = normalize_route(f"/schools/{school_slug}")
        else:
            if raw_route.startswith("/"):
                frappe.throw(
                    _("Route must not start with '/'. Use '/' only for the home page."),
                    frappe.ValidationError,
                )
            if raw_route.endswith("/"):
                frappe.throw(
                    _("Route must not end with '/'. Remove the trailing slash."),
                    frappe.ValidationError,
                )
            if "//" in raw_route:
                frappe.throw(
                    _("Route must not contain empty segments ('//')."),
                    frappe.ValidationError,
                )

            relative = raw_route
            segments = [seg for seg in relative.split("/") if seg]
            if not segments:
                frappe.throw(
                    _("Route is required. Use '/' for the school home page."),
                    frappe.ValidationError,
                )
            if segments[0] == school_slug:
                frappe.throw(
                    _("Do not include the school slug in the route."),
                    frappe.ValidationError,
                )

            self.full_route = normalize_route(f"/schools/{school_slug}/{relative}")

        exists = frappe.db.exists(
            "School Website Page",
            {
                "school": self.school,
                "full_route": self.full_route,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(
                _("A page already exists for this school and route."),
                frappe.ValidationError,
            )

        self._validate_blocks_props_json()
        validate_page_blocks(self)

    def _sync_status_flags(self):
        school_is_public = self._get_school_publication_readiness()
        status, is_published = compute_school_page_publication_flags(
            school_is_public=school_is_public,
            workflow_state=self.workflow_state,
        )
        self.status = status
        self.is_published = is_published

    def _ensure_workflow_state(self):
        self.workflow_state = normalize_workflow_state(self.workflow_state)

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
                _("Unknown workflow action: {0}").format(action_key or _("(empty)")),
                frappe.ValidationError,
            )

        current_state = normalize_workflow_state(self.workflow_state)
        if current_state not in transition["from_states"]:
            frappe.throw(
                _("Cannot run '{0}' from workflow state '{1}'.").format(action_key, current_state),
                frappe.ValidationError,
            )

        user_roles = set(frappe.get_roles())
        allowed_roles = set(transition["roles"])
        if not user_roles.intersection(allowed_roles):
            frappe.throw(
                _("You do not have permission to run workflow action: {0}.").format(action_key),
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
        self._sync_status_flags()

    def _seed_admissions_blocks(self):
        if not self.is_new() or self.page_type != "Admissions" or self.blocks:
            return

        steps_props = {
            "steps": [
                {"key": "inquire", "title": "Inquire", "description": "", "icon": "mail"},
                {"key": "visit", "title": "Visit", "description": "", "icon": "map"},
                {"key": "apply", "title": "Apply", "description": "", "icon": "file-text"},
            ],
            "layout": "horizontal",
        }

        faq_props = {
            "items": [{"question": "", "answer_html": ""}],
            "enable_schema": False,
            "collapsed_by_default": True,
        }

        self.append(
            "blocks",
            {
                "block_type": "admissions_overview",
                "order": 1,
                "props": json.dumps({"heading": "Admissions", "content_html": "", "max_width": "normal"}),
                "is_enabled": 1,
            },
        )
        self.append(
            "blocks",
            {
                "block_type": "admissions_steps",
                "order": 2,
                "props": json.dumps(steps_props),
                "is_enabled": 1,
            },
        )
        self.append(
            "blocks",
            {
                "block_type": "admission_cta",
                "order": 3,
                "props": json.dumps({"intent": "inquire", "style": "primary"}),
                "is_enabled": 1,
            },
        )
        self.append(
            "blocks",
            {
                "block_type": "admission_cta",
                "order": 4,
                "props": json.dumps({"intent": "visit", "style": "secondary"}),
                "is_enabled": 1,
            },
        )
        self.append(
            "blocks",
            {
                "block_type": "admission_cta",
                "order": 5,
                "props": json.dumps({"intent": "apply", "style": "outline"}),
                "is_enabled": 1,
            },
        )
        self.append(
            "blocks",
            {
                "block_type": "faq",
                "order": 6,
                "props": json.dumps(faq_props),
                "is_enabled": 1,
            },
        )

    def _validate_blocks_props_json(self):
        for row in self.blocks or []:
            raw_props = (row.props or "").strip()
            if not raw_props:
                continue
            try:
                json.loads(raw_props)
            except Exception as exc:
                frappe.throw(
                    _("Invalid block props JSON in row {0} ({1}): {2}").format(
                        row.idx or "?",
                        row.block_type or _("Unknown block"),
                        str(exc),
                    ),
                    frappe.ValidationError,
                )


@frappe.whitelist()
def transition_workflow_state(name: str, action: str) -> dict:
    doc = frappe.get_doc("School Website Page", name)
    if not frappe.has_permission(doc=doc, ptype="write"):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    doc.apply_workflow_action(action)
    doc.save()
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "status": doc.status,
        "is_published": doc.is_published,
    }
