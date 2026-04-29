from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

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
            _("Invalid workflow state: {workflow_state}").format(workflow_state=value),
            frappe.ValidationError,
        )
    return value


def normalize_optional_datetime(value):
    if value in (None, "", "Null"):
        return None
    return get_datetime(value)


def validate_publication_window(*, publish_at=None, expire_at=None):
    publish_dt = normalize_optional_datetime(publish_at)
    expire_dt = normalize_optional_datetime(expire_at)
    if publish_dt and expire_dt and publish_dt >= expire_dt:
        frappe.throw(
            _("Publish At must be earlier than Expire At."),
            frappe.ValidationError,
        )


def is_publication_window_open(*, publish_at=None, expire_at=None, now_dt=None) -> bool:
    current = now_dt or now_datetime()
    publish_dt = normalize_optional_datetime(publish_at)
    expire_dt = normalize_optional_datetime(expire_at)

    if publish_dt and current < publish_dt:
        return False
    if expire_dt and current >= expire_dt:
        return False
    return True


def compute_publication_flags(
    *, base_is_public: bool, workflow_state: str, publish_at=None, expire_at=None
) -> tuple[str, int]:
    state = normalize_workflow_state(workflow_state)
    is_live = bool(
        base_is_public
        and state == "Published"
        and is_publication_window_open(
            publish_at=publish_at,
            expire_at=expire_at,
        )
    )
    return ("Published" if is_live else "Draft", 1 if is_live else 0)


def compute_publication_status(*, base_is_public: bool, workflow_state: str, publish_at=None, expire_at=None) -> str:
    status, _is_published = compute_publication_flags(
        base_is_public=base_is_public,
        workflow_state=workflow_state,
        publish_at=publish_at,
        expire_at=expire_at,
    )
    return status


def _get_school_publication_map(school_names: list[str]) -> dict[str, bool]:
    if not school_names:
        return {}

    rows = frappe.get_all(
        "School",
        filters={"name": ["in", list(set(school_names))]},
        fields=["name", "website_slug", "is_published"],
        limit=max(len(set(school_names)), 50),
    )
    return {
        row["name"]: bool((row.get("website_slug") or "").strip() and int(row.get("is_published") or 0) == 1)
        for row in rows
        if row.get("name")
    }


def _sync_school_website_page_windows():
    rows = frappe.get_all(
        "School Website Page",
        filters=[
            ["School Website Page", "workflow_state", "in", ["Published"]],
        ],
        fields=["name", "school", "workflow_state", "publish_at", "expire_at", "status", "is_published"],
        limit=5000,
    )
    if not rows:
        return

    school_map = _get_school_publication_map([row.get("school") for row in rows if row.get("school")])
    for row in rows:
        status, is_published = compute_publication_flags(
            base_is_public=school_map.get(row.get("school"), False),
            workflow_state=row.get("workflow_state"),
            publish_at=row.get("publish_at"),
            expire_at=row.get("expire_at"),
        )
        updates = {}
        if row.get("status") != status:
            updates["status"] = status
        if int(row.get("is_published") or 0) != is_published:
            updates["is_published"] = is_published
        if updates:
            frappe.db.set_value("School Website Page", row.get("name"), updates, update_modified=False)


def _sync_website_story_windows():
    rows = frappe.get_all(
        "Website Story",
        filters=[
            ["Website Story", "workflow_state", "in", ["Published"]],
        ],
        fields=["name", "school", "workflow_state", "publish_at", "expire_at", "status"],
        limit=5000,
    )
    if not rows:
        return

    school_map = _get_school_publication_map([row.get("school") for row in rows if row.get("school")])
    changed = False
    for row in rows:
        status = compute_publication_status(
            base_is_public=school_map.get(row.get("school"), False),
            workflow_state=row.get("workflow_state"),
            publish_at=row.get("publish_at"),
            expire_at=row.get("expire_at"),
        )
        if row.get("status") != status:
            frappe.db.set_value("Website Story", row.get("name"), "status", status, update_modified=False)
            changed = True

    if changed:
        from ifitwala_ed.website.providers.story_feed import invalidate_story_feed_cache

        invalidate_story_feed_cache()


def _sync_website_notice_windows():
    if not frappe.db.exists("DocType", "Website Notice"):
        return

    rows = frappe.get_all(
        "Website Notice",
        filters=[
            ["Website Notice", "workflow_state", "in", ["Published"]],
        ],
        fields=["name", "school", "workflow_state", "publish_at", "expire_at", "status"],
        limit=5000,
    )
    if not rows:
        return

    school_map = _get_school_publication_map([row.get("school") for row in rows if row.get("school")])
    changed = False
    for row in rows:
        status = compute_publication_status(
            base_is_public=school_map.get(row.get("school"), False),
            workflow_state=row.get("workflow_state"),
            publish_at=row.get("publish_at"),
            expire_at=row.get("expire_at"),
        )
        if row.get("status") != status:
            frappe.db.set_value("Website Notice", row.get("name"), "status", status, update_modified=False)
            changed = True

    if changed:
        from ifitwala_ed.website.site_notices import invalidate_site_notice_cache

        invalidate_site_notice_cache()


def _get_program_publication_map(program_names: list[str]) -> dict[str, bool]:
    if not program_names:
        return {}

    rows = frappe.get_all(
        "Program",
        filters={"name": ["in", list(set(program_names))]},
        fields=["name", "is_published", "archive", "program_slug"],
        limit=max(len(set(program_names)), 50),
    )
    return {
        row["name"]: bool(
            int(row.get("is_published") or 0) == 1
            and int(row.get("archive") or 0) == 0
            and (row.get("program_slug") or "").strip()
        )
        for row in rows
        if row.get("name")
    }


def _sync_program_profile_windows():
    rows = frappe.get_all(
        "Program Website Profile",
        filters=[
            ["Program Website Profile", "workflow_state", "in", ["Published"]],
        ],
        fields=["name", "school", "program", "workflow_state", "publish_at", "expire_at", "status"],
        limit=5000,
    )
    if not rows:
        return

    school_map = _get_school_publication_map([row.get("school") for row in rows if row.get("school")])
    program_map = _get_program_publication_map([row.get("program") for row in rows if row.get("program")])
    changed = False
    for row in rows:
        status = compute_publication_status(
            base_is_public=bool(
                school_map.get(row.get("school"), False) and program_map.get(row.get("program"), False)
            ),
            workflow_state=row.get("workflow_state"),
            publish_at=row.get("publish_at"),
            expire_at=row.get("expire_at"),
        )
        if row.get("status") != status:
            frappe.db.set_value("Program Website Profile", row.get("name"), "status", status, update_modified=False)
            changed = True

    if changed:
        from ifitwala_ed.website.providers.program_list import invalidate_program_list_cache

        invalidate_program_list_cache()


def _get_course_publication_map(course_names: list[str]) -> dict[str, dict[str, object]]:
    if not course_names:
        return {}

    rows = frappe.get_all(
        "Course",
        filters={"name": ["in", list(set(course_names))]},
        fields=["name", "is_published", "school"],
        limit=max(len(set(course_names)), 50),
    )
    return {
        row["name"]: {
            "is_published": int(row.get("is_published") or 0) == 1,
            "school": row.get("school"),
        }
        for row in rows
        if row.get("name")
    }


def _sync_course_profile_windows():
    rows = frappe.get_all(
        "Course Website Profile",
        filters=[
            ["Course Website Profile", "workflow_state", "in", ["Published"]],
        ],
        fields=["name", "school", "course", "workflow_state", "publish_at", "expire_at", "status", "course_slug"],
        limit=5000,
    )
    if not rows:
        return

    school_map = _get_school_publication_map([row.get("school") for row in rows if row.get("school")])
    course_map = _get_course_publication_map([row.get("course") for row in rows if row.get("course")])
    changed = False
    for row in rows:
        course = course_map.get(row.get("course")) or {}
        status = compute_publication_status(
            base_is_public=bool(
                school_map.get(row.get("school"), False)
                and course.get("is_published")
                and course.get("school") == row.get("school")
                and (row.get("course_slug") or "").strip()
            ),
            workflow_state=row.get("workflow_state"),
            publish_at=row.get("publish_at"),
            expire_at=row.get("expire_at"),
        )
        if row.get("status") != status:
            frappe.db.set_value("Course Website Profile", row.get("name"), "status", status, update_modified=False)
            changed = True

    if changed:
        from ifitwala_ed.website.providers.course_catalog import invalidate_course_catalog_cache

        invalidate_course_catalog_cache()


def run_hourly_website_publication_sync():
    _sync_school_website_page_windows()
    _sync_website_story_windows()
    _sync_website_notice_windows()
    _sync_program_profile_windows()
    _sync_course_profile_windows()
