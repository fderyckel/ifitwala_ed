# ifitwala_ed/school_site/doctype/course_website_profile/course_website_profile.py

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
from ifitwala_ed.website.validators import validate_page_blocks


def compute_course_profile_status(
    *,
    school_is_public: bool,
    course_is_published: bool,
    course_scope_matches_school: bool,
    has_course_slug: bool,
    workflow_state: str,
    publish_at=None,
    expire_at=None,
) -> str:
    return compute_publication_status(
        base_is_public=bool(
            school_is_public and course_is_published and course_scope_matches_school and has_course_slug
        ),
        workflow_state=workflow_state,
        publish_at=publish_at,
        expire_at=expire_at,
    )


class CourseWebsiteProfile(Document):
    def validate(self):
        self._ensure_workflow_state()
        self._sync_school_from_course()
        self._ensure_course_slug()
        validate_publication_window(publish_at=self.publish_at, expire_at=self.expire_at)
        self._sync_status_from_course()
        self._validate_unique_profile()
        self._validate_course_scope()
        self._validate_course_slug_unique()
        self._validate_blocks_props_json()
        validate_page_blocks(self)

    def on_update(self):
        self._sync_website_discoverability()

    def after_insert(self):
        self._sync_website_discoverability()

    def on_trash(self):
        self._invalidate_course_catalog_cache()

    def _ensure_workflow_state(self):
        self.workflow_state = normalize_workflow_state(self.workflow_state)

    def _sync_school_from_course(self):
        if self.school or not self.course:
            return
        course_school = frappe.db.get_value("Course", self.course, "school")
        if course_school:
            self.school = course_school

    def _ensure_course_slug(self):
        if (self.course_slug or "").strip() or not self.course or not self.school:
            return

        course_name = frappe.db.get_value("Course", self.course, "course_name") or self.course
        from ifitwala_ed.website.bootstrap import _next_available_course_slug

        self.course_slug = _next_available_course_slug(
            course_name,
            school_name=self.school,
            profile_name=self.name,
        )

    def _sync_status_from_course(self):
        course_scope_matches_school = False
        course_is_published = False
        if self.course:
            course_row = frappe.db.get_value(
                "Course",
                self.course,
                ["is_published", "school"],
                as_dict=True,
            )
            course_is_published = bool(course_row and int(course_row.is_published or 0) == 1)
            course_scope_matches_school = bool(course_row and course_row.school == self.school)
        self.status = compute_course_profile_status(
            school_is_public=self._get_school_publication_readiness(),
            course_is_published=course_is_published,
            course_scope_matches_school=course_scope_matches_school,
            has_course_slug=bool((self.course_slug or "").strip()),
            workflow_state=self.workflow_state,
            publish_at=self.publish_at,
            expire_at=self.expire_at,
        )

    def _validate_unique_profile(self):
        exists = frappe.db.exists(
            "Course Website Profile",
            {
                "course": self.course,
                "school": self.school,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(
                _("A Course Website Profile already exists for this Course and School."),
                frappe.ValidationError,
            )

    def _validate_course_scope(self):
        if not self.course or not self.school:
            return

        course_school = frappe.db.get_value("Course", self.course, "school")
        if not course_school:
            frappe.throw(
                _("Course must belong to a School before website publication."),
                frappe.ValidationError,
            )
        if course_school != self.school:
            frappe.throw(
                _("Course Website Profile school must match the Course school."),
                frappe.ValidationError,
            )

    def _validate_course_slug_unique(self):
        if not (self.course_slug or "").strip() or not self.school:
            return

        exists = frappe.db.exists(
            "Course Website Profile",
            {
                "school": self.school,
                "course_slug": self.course_slug,
                "name": ["!=", self.name],
            },
        )
        if exists:
            frappe.throw(
                _("A Course Website Profile with this slug already exists for this School."),
                frappe.ValidationError,
            )

    def _get_course_publication_readiness(self) -> bool:
        if not self.course or not self.school:
            return False
        row = frappe.db.get_value(
            "Course",
            self.course,
            ["is_published", "school"],
            as_dict=True,
        )
        if not row:
            return False
        return bool(int(row.is_published or 0) == 1 and row.school == self.school and self.course_slug)

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
        if target_state == "Published" and not (
            self._get_school_publication_readiness() and self._get_course_publication_readiness()
        ):
            frappe.throw(
                _(
                    "Cannot publish until the school website is published and the Course is published, assigned to this School, and has a course slug."
                ),
                frappe.ValidationError,
            )
        self.workflow_state = target_state
        self._sync_status_from_course()

    def _sync_website_discoverability(self):
        if self.status == "Published" and self.school:
            from ifitwala_ed.website.bootstrap import ensure_courses_index_page

            ensure_courses_index_page(school_name=self.school)

        self._invalidate_course_catalog_cache()

    def _invalidate_course_catalog_cache(self):
        from ifitwala_ed.website.providers.course_catalog import invalidate_course_catalog_cache

        invalidate_course_catalog_cache()

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
    doc = frappe.get_doc("Course Website Profile", name)
    if not frappe.has_permission(doc=doc, ptype="write"):
        frappe.throw(_("Not permitted."), frappe.PermissionError)

    doc.apply_workflow_action(action)
    doc.save()
    return {
        "name": doc.name,
        "workflow_state": doc.workflow_state,
        "status": doc.status,
    }
