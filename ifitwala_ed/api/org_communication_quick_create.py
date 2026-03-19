# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_communication_quick_create

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.setup.doctype.org_communication.org_communication import (
    AUDIENCE_TARGET_MODES,
    RECIPIENT_TOGGLE_FIELDS,
    RECIPIENT_TOGGLE_LABELS,
    TARGET_MODE_ALLOWED_RECIPIENTS,
    WIDE_AUDIENCE_RECIPIENT_ROLES,
    _user_has_any_role,
    get_org_communication_context,
)

IDEMPOTENCY_TTL_SECONDS = 900


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_json_arg(value, *, fallback):
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            parsed = frappe.parse_json(value)
        except Exception:
            parsed = None
        if parsed is None:
            return fallback
        return parsed
    return value


def _as_check(value) -> int:
    return 1 if cint(value or 0) else 0


def _field_options(doctype: str, fieldname: str) -> list[str]:
    field = frappe.get_meta(doctype).get_field(fieldname)
    if not field or not getattr(field, "options", None):
        return []
    return [row.strip() for row in str(field.options).splitlines() if row.strip()]


def _field_default(doctype: str, fieldname: str) -> str | None:
    field = frappe.get_meta(doctype).get_field(fieldname)
    if not field:
        return None
    return _clean_text(getattr(field, "default", None))


def _idempotency_key(user: str, client_request_id: str) -> str:
    return f"ifitwala_ed:org_communication_quick_create:{user}:{client_request_id}"


def _parse_audiences(audiences) -> list[dict]:
    rows = _parse_json_arg(audiences, fallback=[])
    if not isinstance(rows, list):
        frappe.throw(_("audiences must be a list."), frappe.ValidationError)

    cleaned_rows: list[dict] = []
    for raw_row in rows:
        if not isinstance(raw_row, dict):
            frappe.throw(_("Each audience row must be an object."), frappe.ValidationError)

        row = {
            "target_mode": _clean_text(raw_row.get("target_mode")),
            "school": _clean_text(raw_row.get("school")),
            "team": _clean_text(raw_row.get("team")),
            "student_group": _clean_text(raw_row.get("student_group")),
            "include_descendants": _as_check(raw_row.get("include_descendants")),
            "note": _clean_text(raw_row.get("note")),
        }
        for fieldname in RECIPIENT_TOGGLE_FIELDS:
            row[fieldname] = _as_check(raw_row.get(fieldname))
        cleaned_rows.append(row)

    return cleaned_rows


def _get_reference_organizations(org_names: list[str]) -> list[dict]:
    names = [_clean_text(name) for name in (org_names or [])]
    names = [name for name in names if name]
    if not names:
        return []
    return frappe.get_all(
        "Organization",
        filters={"name": ["in", names]},
        fields=["name", "organization_name", "abbr"],
        order_by="lft asc, name asc",
    )


def _get_reference_schools(*, school_names: list[str], organization_names: list[str]) -> list[dict]:
    names = [_clean_text(name) for name in (school_names or [])]
    names = [name for name in names if name]
    if not names and organization_names:
        names = frappe.get_all(
            "School",
            filters={"organization": ["in", tuple(organization_names)]},
            pluck="name",
            order_by="lft asc, name asc",
        )
    if not names:
        return []
    return frappe.get_all(
        "School",
        filters={"name": ["in", tuple(sorted(set(names)))]},
        fields=["name", "school_name", "abbr", "organization"],
        order_by="lft asc, school_name asc, name asc",
    )


def _get_reference_teams(*, school_names: list[str], organization_names: list[str]) -> list[dict]:
    or_filters = []
    if school_names:
        or_filters.append(["Team", "school", "in", tuple(sorted(set(school_names)))])
    if organization_names:
        or_filters.append(["Team", "organization", "in", tuple(sorted(set(organization_names)))])
    if not or_filters:
        return []
    return frappe.get_all(
        "Team",
        filters={"enabled": 1},
        or_filters=or_filters,
        fields=["name", "team_name", "team_code", "school", "organization"],
        order_by="team_name asc, name asc",
    )


def _get_reference_student_groups(*, school_names: list[str]) -> list[dict]:
    if not school_names:
        return []
    return frappe.get_all(
        "Student Group",
        filters={
            "school": ["in", tuple(sorted(set(school_names)))],
            "status": "Active",
        },
        fields=["name", "student_group_name", "student_group_abbreviation", "school", "group_based_on"],
        order_by="student_group_abbreviation asc, student_group_name asc, name asc",
    )


@frappe.whitelist()
def get_org_communication_quick_create_options() -> dict:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)
    if not frappe.has_permission("Org Communication", ptype="create", user=user):
        frappe.throw(_("You do not have permission to create communications."), frappe.PermissionError)

    context = get_org_communication_context()
    org_names = list(context.get("allowed_organizations") or [])
    default_org = _clean_text(context.get("default_organization"))
    if default_org and default_org not in org_names:
        org_names.insert(0, default_org)

    school_names = list(context.get("allowed_schools") or [])
    reference_orgs = _get_reference_organizations(org_names)
    reference_schools = _get_reference_schools(school_names=school_names, organization_names=org_names)
    resolved_school_names = [row.get("name") for row in reference_schools if row.get("name")]

    return {
        "context": context,
        "defaults": {
            "communication_type": _field_default("Org Communication", "communication_type") or "Information",
            "status": _field_default("Org Communication", "status") or "Draft",
            "priority": _field_default("Org Communication", "priority") or "Normal",
            "portal_surface": _field_default("Org Communication", "portal_surface") or "Everywhere",
            "interaction_mode": _field_default("Org Communication", "interaction_mode") or "None",
            "allow_private_notes": _as_check(_field_default("Org Communication", "allow_private_notes")),
            "allow_public_thread": _as_check(_field_default("Org Communication", "allow_public_thread")),
        },
        "fields": {
            "communication_types": _field_options("Org Communication", "communication_type"),
            "statuses": [value for value in _field_options("Org Communication", "status") if value != "Archived"],
            "priorities": _field_options("Org Communication", "priority"),
            "portal_surfaces": _field_options("Org Communication", "portal_surface"),
            "interaction_modes": _field_options("Org Communication", "interaction_mode"),
            "audience_target_modes": list(AUDIENCE_TARGET_MODES),
        },
        "recipient_rules": {
            target_mode: {
                "allowed_fields": sorted(TARGET_MODE_ALLOWED_RECIPIENTS.get(target_mode, set())),
                "allowed_labels": [
                    RECIPIENT_TOGGLE_LABELS.get(fieldname, fieldname)
                    for fieldname in sorted(TARGET_MODE_ALLOWED_RECIPIENTS.get(target_mode, set()))
                ],
                "default_fields": (
                    ["to_staff"]
                    if target_mode == "Team"
                    else ["to_students", "to_guardians"]
                    if target_mode == "Student Group"
                    else []
                ),
            }
            for target_mode in AUDIENCE_TARGET_MODES
        },
        "references": {
            "organizations": reference_orgs,
            "schools": reference_schools,
            "teams": _get_reference_teams(
                school_names=resolved_school_names,
                organization_names=[row.get("name") for row in reference_orgs if row.get("name")],
            ),
            "student_groups": _get_reference_student_groups(school_names=resolved_school_names),
        },
        "permissions": {
            "can_create": True,
            "can_target_wide_school_scope": _user_has_any_role(user, WIDE_AUDIENCE_RECIPIENT_ROLES),
        },
    }


@frappe.whitelist()
def create_org_communication_quick(
    title: str | None = None,
    communication_type: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    portal_surface: str | None = None,
    publish_from: str | None = None,
    publish_to: str | None = None,
    brief_start_date: str | None = None,
    brief_end_date: str | None = None,
    brief_order: int | None = None,
    organization: str | None = None,
    school: str | None = None,
    message: str | None = None,
    internal_note: str | None = None,
    interaction_mode: str | None = None,
    allow_private_notes: int | None = None,
    allow_public_thread: int | None = None,
    audiences=None,
    client_request_id: str | None = None,
) -> dict:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)
    if not frappe.has_permission("Org Communication", ptype="create", user=user):
        frappe.throw(_("You do not have permission to create communications."), frappe.PermissionError)

    request_id = _clean_text(client_request_id)
    cache = frappe.cache()
    cache_key = _idempotency_key(user, request_id) if request_id else None

    if cache_key:
        cached = cache.get_value(cache_key)
        if cached:
            result = frappe.parse_json(cached)
            if isinstance(result, dict):
                result["status"] = "already_processed"
                return result

    lock_name = f"{cache_key}:lock" if cache_key else f"ifitwala_ed:org_communication_quick_create:lock:{user}"
    with cache.lock(lock_name, timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                result = frappe.parse_json(cached)
                if isinstance(result, dict):
                    result["status"] = "already_processed"
                    return result

        doc = frappe.new_doc("Org Communication")
        if title is not None:
            doc.title = title
        if communication_type is not None:
            doc.communication_type = communication_type
        if status is not None:
            doc.status = status
        if priority is not None:
            doc.priority = priority
        if portal_surface is not None:
            doc.portal_surface = portal_surface
        if publish_from is not None:
            doc.publish_from = _clean_text(publish_from)
        if publish_to is not None:
            doc.publish_to = _clean_text(publish_to)
        if brief_start_date is not None:
            doc.brief_start_date = _clean_text(brief_start_date)
        if brief_end_date is not None:
            doc.brief_end_date = _clean_text(brief_end_date)
        if brief_order not in (None, ""):
            doc.brief_order = cint(brief_order)
        if organization is not None:
            doc.organization = _clean_text(organization)
        if school is not None:
            doc.school = _clean_text(school)
        if message is not None:
            doc.message = message
        if internal_note is not None:
            doc.internal_note = internal_note
        if interaction_mode is not None:
            doc.interaction_mode = interaction_mode
        if allow_private_notes is not None:
            doc.allow_private_notes = _as_check(allow_private_notes)
        if allow_public_thread is not None:
            doc.allow_public_thread = _as_check(allow_public_thread)

        for row in _parse_audiences(audiences):
            doc.append("audiences", row)

        doc.insert()

        result = {
            "ok": True,
            "status": "created",
            "name": doc.name,
            "title": doc.title,
        }
        if cache_key:
            cache.set_value(cache_key, frappe.as_json(result), expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return result
