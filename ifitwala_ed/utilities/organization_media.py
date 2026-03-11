# ifitwala_ed/utilities/organization_media.py

from __future__ import annotations

from collections.abc import Iterable

import frappe
from frappe import _

from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
)
from ifitwala_ed.utilities.file_classification_contract import (
    ORGANIZATION_MEDIA_DATA_CLASS,
    ORGANIZATION_MEDIA_FILE_CATEGORY,
    ORGANIZATION_MEDIA_PURPOSE,
    ORGANIZATION_MEDIA_RETENTION_POLICY,
    ORGANIZATION_MEDIA_SUBJECT_TYPE,
)


def _normalize(value: str | None) -> str:
    return (value or "").strip()


def build_organization_media_slot(*, media_key: str) -> str:
    normalized = frappe.scrub(_normalize(media_key))
    if not normalized:
        frappe.throw(_("Organization media key is required."))
    return f"organization_media__{normalized}"


def build_school_logo_slot(*, school: str) -> str:
    normalized = frappe.scrub(_normalize(school))
    if not normalized:
        frappe.throw(_("School is required for the school logo slot."))
    return f"school_logo__{normalized}"


def build_school_gallery_slot(*, row_name: str) -> str:
    normalized = frappe.scrub(_normalize(row_name))
    if not normalized:
        frappe.throw(_("Gallery row name is required for the school gallery slot."))
    return f"school_gallery_image__{normalized}"


def validate_school_belongs_to_organization(*, organization: str, school: str | None = None) -> None:
    organization = _normalize(organization)
    school = _normalize(school)
    if not organization:
        frappe.throw(_("Organization is required for organization media."))
    if not school:
        return

    school_org = frappe.db.get_value("School", school, "organization")
    if not school_org:
        frappe.throw(_("School '{0}' was not found.").format(school))
    if school_org != organization:
        frappe.throw(
            _("School '{0}' belongs to '{1}', not '{2}'.").format(
                school,
                school_org,
                organization,
            )
        )


def build_organization_media_classification(
    *,
    organization: str,
    slot: str,
    school: str | None = None,
    upload_source: str = "Desk",
) -> dict:
    validate_school_belongs_to_organization(organization=organization, school=school)
    payload = {
        "primary_subject_type": ORGANIZATION_MEDIA_SUBJECT_TYPE,
        "primary_subject_id": organization,
        "data_class": ORGANIZATION_MEDIA_DATA_CLASS,
        "purpose": ORGANIZATION_MEDIA_PURPOSE,
        "retention_policy": ORGANIZATION_MEDIA_RETENTION_POLICY,
        "slot": slot,
        "organization": organization,
        "upload_source": upload_source,
    }
    if school:
        payload["school"] = school
    return payload


def build_organization_media_context(*, organization: str, slot: str, school: str | None = None) -> dict:
    validate_school_belongs_to_organization(organization=organization, school=school)
    organization = _normalize(organization)
    school = _normalize(school)
    if school:
        subfolder = f"{organization}/Schools/{school}/Media/Public"
    else:
        subfolder = f"{organization}/Media/Public"
    return {
        "root_folder": "Home/Organizations",
        "subfolder": subfolder,
        "file_category": ORGANIZATION_MEDIA_FILE_CATEGORY,
        "logical_key": slot,
    }


def _resolve_school_context(*, school: str) -> tuple[str, list[str], list[str]]:
    school = _normalize(school)
    if not school:
        frappe.throw(_("School is required."))

    organization = _normalize(frappe.db.get_value("School", school, "organization"))
    if not organization:
        frappe.throw(_("School '{0}' is missing its Organization.").format(school))

    return (
        organization,
        get_organization_ancestors_including_self(organization),
        get_school_ancestors_including_self(school),
    )


def get_visible_organization_media_for_school(*, school: str) -> list[dict]:
    school_organization, org_chain, school_chain = _resolve_school_context(school=school)
    if not org_chain:
        return []

    rows = frappe.get_all(
        "File Classification",
        filters={
            "primary_subject_type": ORGANIZATION_MEDIA_SUBJECT_TYPE,
            "purpose": ORGANIZATION_MEDIA_PURPOSE,
            "organization": ["in", org_chain],
            "is_current_version": 1,
        },
        fields=[
            "name",
            "file",
            "organization",
            "school",
            "slot",
            "attached_doctype",
            "attached_name",
        ],
    )
    if not school_organization:
        return []
    if not rows:
        return []

    allowed_schools = set(school_chain)
    filtered: list[dict] = []
    for row in rows:
        row_school = _normalize(row.get("school"))
        if row_school and row_school not in allowed_schools:
            continue
        filtered.append(row)

    if not filtered:
        return []

    file_rows = frappe.get_all(
        "File",
        filters={"name": ["in", [row["file"] for row in filtered if row.get("file")]]},
        fields=["name", "file_url", "file_name", "is_private"],
    )
    file_map = {row["name"]: row for row in file_rows}
    org_rank = {name: idx for idx, name in enumerate(org_chain)}
    school_rank = {name: idx for idx, name in enumerate(school_chain)}
    default_school_rank = len(school_chain) + 1

    for row in filtered:
        file_row = file_map.get(row.get("file")) or {}
        row["file_url"] = file_row.get("file_url")
        row["file_name"] = file_row.get("file_name")
        row["is_private"] = file_row.get("is_private")

    return sorted(
        filtered,
        key=lambda row: (
            org_rank.get(_normalize(row.get("organization")), len(org_chain) + 1),
            school_rank.get(_normalize(row.get("school")), default_school_rank),
            _normalize(row.get("slot")),
            _normalize(row.get("name")),
        ),
    )


def get_visible_organization_media_files_for_school(*, school: str) -> dict[str, dict]:
    return {
        row["file"]: row
        for row in get_visible_organization_media_for_school(school=school)
        if _normalize(row.get("file"))
    }


def find_visible_organization_media_by_url(*, school: str, file_url: str | None) -> dict | None:
    target = _normalize(file_url)
    if not target:
        return None
    for row in get_visible_organization_media_for_school(school=school):
        if _normalize(row.get("file_url")) == target:
            return row
    return None


def get_governed_organization_media(file_name: str | None) -> dict | None:
    file_name = _normalize(file_name)
    if not file_name:
        return None
    row = frappe.db.get_value(
        "File Classification",
        {
            "file": file_name,
            "primary_subject_type": ORGANIZATION_MEDIA_SUBJECT_TYPE,
            "purpose": ORGANIZATION_MEDIA_PURPOSE,
            "is_current_version": 1,
        },
        [
            "name",
            "file",
            "organization",
            "school",
            "slot",
            "attached_doctype",
            "attached_name",
        ],
        as_dict=True,
    )
    if not row:
        return None

    file_row = frappe.db.get_value("File", file_name, ["file_url", "file_name", "is_private"], as_dict=True) or {}
    row["file_url"] = file_row.get("file_url")
    row["file_name"] = file_row.get("file_name")
    row["is_private"] = file_row.get("is_private")
    return row


def ensure_organization_media_files_visible_to_school(*, school: str, file_names: Iterable[str]) -> dict[str, dict]:
    visible = get_visible_organization_media_files_for_school(school=school)
    normalized = [_normalize(name) for name in file_names if _normalize(name)]
    missing = [name for name in normalized if name not in visible]
    if missing:
        frappe.throw(
            _("Organization media is not visible to School '{0}': {1}").format(
                school,
                ", ".join(missing),
            )
        )
    return {name: visible[name] for name in normalized}


def ensure_organization_media_visible_to_school_by_url(*, school: str, file_url: str | None) -> dict | None:
    row = find_visible_organization_media_by_url(school=school, file_url=file_url)
    if not row:
        return None
    return row
