# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed.api.org_communication_quick_create

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.api.student_groups import _instructor_group_names
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
AUDIENCE_TARGET_SEARCH_TTL_SECONDS = 60
MAX_AUDIENCE_TARGET_SEARCH_RESULTS = 12
SUGGESTED_AUDIENCE_TARGETS_LIMIT = 8
NULLISH_TEXT_VALUES = {"null", "undefined"}


def _clean_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in NULLISH_TEXT_VALUES:
        return None
    return text


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


def _set_row_value(row, fieldname: str, value) -> None:
    if isinstance(row, dict):
        row[fieldname] = value
        return
    setattr(row, fieldname, value)


def _request_includes_arg(fieldname: str) -> bool:
    form_dict = getattr(getattr(frappe, "local", None), "form_dict", None)
    if form_dict is None:
        return False
    try:
        return fieldname in form_dict
    except TypeError:
        return False


def _should_apply_arg(fieldname: str, value) -> bool:
    return value is not None or _request_includes_arg(fieldname)


def _normalize_audience_row_for_target_mode(row):
    target_mode = _clean_text((row.get("target_mode") if isinstance(row, dict) else getattr(row, "target_mode", None)))
    if target_mode == "Organization":
        _set_row_value(row, "school", None)
        _set_row_value(row, "team", None)
        _set_row_value(row, "student_group", None)
        _set_row_value(row, "include_descendants", 0)
    elif target_mode == "School Scope":
        _set_row_value(row, "team", None)
        _set_row_value(row, "student_group", None)
    elif target_mode == "Team":
        _set_row_value(row, "school", None)
        _set_row_value(row, "student_group", None)
        _set_row_value(row, "include_descendants", 0)
    elif target_mode == "Student Group":
        _set_row_value(row, "school", None)
        _set_row_value(row, "team", None)
        _set_row_value(row, "include_descendants", 0)
    return row


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


def _ensure_quick_create_access(user: str | None = None) -> dict[str, bool | str | None]:
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    capability = get_org_communication_quick_create_capability(user=user)
    if capability.get("enabled"):
        return capability

    blocked_reason = _clean_text(capability.get("blocked_reason"))
    frappe.throw(blocked_reason or _("You do not have permission to create communications."), frappe.PermissionError)


def _coerce_search_limit(value, *, default: int, maximum: int = MAX_AUDIENCE_TARGET_SEARCH_RESULTS) -> int:
    limit_value = cint(value) or default
    if limit_value < 1:
        return 1
    if limit_value > maximum:
        return maximum
    return limit_value


def _search_cache_key(
    *,
    kind: str,
    user: str,
    query: str,
    organization: str | None,
    school: str | None,
    limit: int,
) -> str:
    return (
        "ifitwala_ed:org_communication_quick_create:"
        f"{kind}:{user}:{query.lower()}:{organization or '-'}:{school or '-'}:{limit}"
    )


def get_org_communication_quick_create_capability(user: str | None = None) -> dict[str, bool | str | None]:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return {
            "enabled": False,
            "blocked_reason": _("You must be logged in."),
        }

    if not frappe.has_permission("Org Communication", ptype="create", user=user):
        return {
            "enabled": False,
            "blocked_reason": None,
        }

    context = get_org_communication_context(user=user)
    default_org = _clean_text(context.get("default_organization"))
    allowed_orgs: list[str] = []
    for raw_name in context.get("allowed_organizations") or []:
        org_name = _clean_text(raw_name)
        if org_name and org_name not in allowed_orgs:
            allowed_orgs.append(org_name)
    if default_org and default_org not in allowed_orgs:
        allowed_orgs.insert(0, default_org)

    if default_org or allowed_orgs:
        return {
            "enabled": True,
            "blocked_reason": None,
        }

    return {
        "enabled": False,
        "blocked_reason": _(
            "Set a default organization or ask an administrator to grant your organization scope before creating communications."
        ),
    }


def _get_audience_presets(*, can_target_wide_school_scope: bool) -> list[dict]:
    presets = [
        {
            "key": "whole_school_families",
            "label": _("Whole school families"),
            "description": _("Send to students and guardians in the selected school scope."),
            "target_mode": "School Scope",
            "default_fields": ["to_students", "to_guardians"],
            "picker_kind": None,
        },
        {
            "key": "one_team",
            "label": _("One team"),
            "description": _("Choose one team and send the communication to its staff members."),
            "target_mode": "Team",
            "default_fields": ["to_staff"],
            "picker_kind": "team",
        },
        {
            "key": "one_student_group",
            "label": _("One class or student group"),
            "description": _("Choose one class and send to students plus guardians by default."),
            "target_mode": "Student Group",
            "default_fields": ["to_students", "to_guardians"],
            "picker_kind": "student_group",
        },
    ]
    if can_target_wide_school_scope:
        presets.insert(
            1,
            {
                "key": "whole_school_staff",
                "label": _("Whole school staff"),
                "description": _("Reach staff across the selected school scope."),
                "target_mode": "School Scope",
                "default_fields": ["to_staff"],
                "picker_kind": None,
            },
        )
        presets.append(
            {
                "key": "organization_wide",
                "label": _("Organization-wide"),
                "description": _("Reach staff or guardians across the selected organization tree."),
                "target_mode": "Organization",
                "default_fields": ["to_staff"],
                "picker_kind": None,
            }
        )
    return presets


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
        cleaned_rows.append(_normalize_audience_row_for_target_mode(row))

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


def _get_team_suggestions(
    *,
    user: str,
    school_names: list[str],
    organization_names: list[str],
    preferred_school: str | None,
    limit: int,
) -> list[dict]:
    team_names = (
        frappe.get_all(
            "Team Member",
            filters={"parenttype": "Team", "member": user},
            pluck="parent",
            limit=limit,
        )
        or []
    )

    filters: dict = {"enabled": 1}
    if team_names:
        filters["name"] = ["in", tuple(sorted(set(team_names)))]
        if school_names:
            filters["school"] = ["in", tuple(sorted(set(school_names)))]
        elif organization_names:
            filters["organization"] = ["in", tuple(sorted(set(organization_names)))]
        return frappe.get_all(
            "Team",
            filters=filters,
            fields=["name", "team_name", "team_code", "school", "organization"],
            order_by="team_name asc, name asc",
            limit=limit,
        )

    if preferred_school:
        return frappe.get_all(
            "Team",
            filters={"enabled": 1, "school": preferred_school},
            fields=["name", "team_name", "team_code", "school", "organization"],
            order_by="team_name asc, name asc",
            limit=limit,
        )

    return []


def _get_student_group_suggestions(
    *,
    user: str,
    school_names: list[str],
    preferred_school: str | None,
    limit: int,
    prefill_student_group: str | None = None,
) -> list[dict]:
    filters: dict = {"status": "Active"}
    group_names = sorted(_instructor_group_names(user))
    if group_names:
        filters["name"] = ["in", tuple(group_names[: limit * 4])]
        if school_names:
            filters["school"] = ["in", tuple(sorted(set(school_names)))]
        rows = frappe.get_all(
            "Student Group",
            filters=filters,
            fields=["name", "student_group_name", "student_group_abbreviation", "school", "group_based_on"],
            order_by="student_group_abbreviation asc, student_group_name asc, name asc",
            limit=limit,
        )
    elif preferred_school:
        rows = frappe.get_all(
            "Student Group",
            filters={"school": preferred_school, "status": "Active"},
            fields=["name", "student_group_name", "student_group_abbreviation", "school", "group_based_on"],
            order_by="student_group_abbreviation asc, student_group_name asc, name asc",
            limit=limit,
        )
    else:
        rows = []

    prefill_name = _clean_text(prefill_student_group)
    if not prefill_name:
        return rows
    if any(row.get("name") == prefill_name for row in rows):
        return rows

    prefill_row = frappe.db.get_value(
        "Student Group",
        prefill_name,
        ["name", "student_group_name", "student_group_abbreviation", "school", "group_based_on"],
        as_dict=True,
    )
    if not prefill_row:
        return rows
    if school_names and _clean_text(prefill_row.get("school")) not in set(school_names):
        return rows
    return [prefill_row, *rows][:limit]


def _resolve_team_search_scope(
    *,
    context: dict,
    organization: str | None,
    school: str | None,
) -> tuple[list[str], list[str]]:
    school_value = _clean_text(school)
    org_value = _clean_text(organization)
    allowed_schools = [name for name in (context.get("allowed_schools") or []) if _clean_text(name)]
    allowed_orgs = [name for name in (context.get("allowed_organizations") or []) if _clean_text(name)]

    if school_value:
        if allowed_schools and school_value not in set(allowed_schools):
            frappe.throw(_("You cannot target that school from your current scope."), frappe.PermissionError)
        if not allowed_schools and allowed_orgs:
            school_org = _clean_text(frappe.db.get_value("School", school_value, "organization"))
            if school_org and school_org not in set(allowed_orgs):
                frappe.throw(_("You cannot target that school from your current scope."), frappe.PermissionError)
        return [school_value], []

    if org_value:
        if allowed_orgs and org_value not in set(allowed_orgs):
            frappe.throw(_("You cannot target that organization from your current scope."), frappe.PermissionError)
        return [], [org_value]

    if allowed_schools:
        return allowed_schools, []
    if allowed_orgs:
        return [], allowed_orgs
    return [], []


def _resolve_student_group_search_scope(
    *,
    context: dict,
    organization: str | None,
    school: str | None,
) -> list[str]:
    school_value = _clean_text(school)
    org_value = _clean_text(organization)
    allowed_schools = [name for name in (context.get("allowed_schools") or []) if _clean_text(name)]
    allowed_orgs = [name for name in (context.get("allowed_organizations") or []) if _clean_text(name)]

    if school_value:
        if allowed_schools and school_value not in set(allowed_schools):
            frappe.throw(_("You cannot target that school from your current scope."), frappe.PermissionError)
        if not allowed_schools and allowed_orgs:
            school_org = _clean_text(frappe.db.get_value("School", school_value, "organization"))
            if school_org and school_org not in set(allowed_orgs):
                frappe.throw(_("You cannot target that school from your current scope."), frappe.PermissionError)
        return [school_value]

    if allowed_schools:
        return allowed_schools

    if org_value:
        if allowed_orgs and org_value not in set(allowed_orgs):
            frappe.throw(_("You cannot target that organization from your current scope."), frappe.PermissionError)
        return frappe.get_all(
            "School",
            filters={"organization": org_value},
            pluck="name",
            order_by="lft asc, name asc",
        )

    if allowed_orgs:
        return frappe.get_all(
            "School",
            filters={"organization": ["in", tuple(sorted(set(allowed_orgs)))]},
            pluck="name",
            order_by="lft asc, name asc",
        )

    return []


@frappe.whitelist()
def get_org_communication_quick_create_options(prefill_student_group: str | None = None) -> dict:
    user = frappe.session.user
    capability = get_org_communication_quick_create_capability(user=user)
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)
    if not capability.get("enabled") and not capability.get("blocked_reason"):
        frappe.throw(_("You do not have permission to create communications."), frappe.PermissionError)

    context = get_org_communication_context(user=user)
    org_names = list(context.get("allowed_organizations") or [])
    default_org = _clean_text(context.get("default_organization"))
    if default_org and default_org not in org_names:
        org_names.insert(0, default_org)

    school_names = list(context.get("allowed_schools") or [])
    reference_orgs = _get_reference_organizations(org_names)
    reference_schools = _get_reference_schools(school_names=school_names, organization_names=org_names)
    resolved_school_names = [row.get("name") for row in reference_schools if row.get("name")]
    can_target_wide_school_scope = _user_has_any_role(user, WIDE_AUDIENCE_RECIPIENT_ROLES)
    preferred_school = _clean_text(context.get("default_school"))
    available_target_modes = [
        target_mode
        for target_mode in AUDIENCE_TARGET_MODES
        if target_mode != "Organization" or can_target_wide_school_scope
    ]

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
            "audience_target_modes": available_target_modes,
        },
        "audience_presets": _get_audience_presets(can_target_wide_school_scope=can_target_wide_school_scope),
        "recipient_rules": {
            target_mode: {
                "allowed_fields": sorted(TARGET_MODE_ALLOWED_RECIPIENTS.get(target_mode, set())),
                "allowed_labels": [
                    RECIPIENT_TOGGLE_LABELS.get(fieldname, fieldname)
                    for fieldname in sorted(TARGET_MODE_ALLOWED_RECIPIENTS.get(target_mode, set()))
                ],
                "default_fields": (
                    ["to_staff"]
                    if target_mode == "Organization"
                    else ["to_staff"]
                    if target_mode == "Team"
                    else ["to_students", "to_guardians"]
                    if target_mode == "Student Group"
                    else []
                ),
            }
            for target_mode in available_target_modes
        },
        "references": {
            "organizations": reference_orgs,
            "schools": reference_schools,
        },
        "suggested_targets": {
            "teams": _get_team_suggestions(
                user=user,
                school_names=resolved_school_names,
                organization_names=[row.get("name") for row in reference_orgs if row.get("name")],
                preferred_school=preferred_school,
                limit=SUGGESTED_AUDIENCE_TARGETS_LIMIT,
            ),
            "student_groups": _get_student_group_suggestions(
                user=user,
                school_names=resolved_school_names,
                preferred_school=preferred_school,
                limit=SUGGESTED_AUDIENCE_TARGETS_LIMIT,
                prefill_student_group=prefill_student_group,
            ),
        },
        "permissions": {
            "can_create": bool(capability.get("enabled")),
            "blocked_reason": capability.get("blocked_reason"),
            "can_target_wide_school_scope": can_target_wide_school_scope,
        },
    }


@frappe.whitelist()
def search_org_communication_teams(
    query: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    limit: int | None = None,
) -> dict:
    user = frappe.session.user
    _ensure_quick_create_access(user=user)

    search_query = _clean_text(query) or ""
    if len(search_query) < 2:
        return {"results": []}

    context = get_org_communication_context(user=user)
    school_names, organization_names = _resolve_team_search_scope(
        context=context,
        organization=organization,
        school=school,
    )
    result_limit = _coerce_search_limit(
        limit,
        default=SUGGESTED_AUDIENCE_TARGETS_LIMIT,
        maximum=MAX_AUDIENCE_TARGET_SEARCH_RESULTS,
    )
    cache_key = _search_cache_key(
        kind="team_search",
        user=user,
        query=search_query,
        organization=_clean_text(organization),
        school=_clean_text(school),
        limit=result_limit,
    )
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    filters: dict = {"enabled": 1}
    if school_names:
        filters["school"] = ["in", tuple(sorted(set(school_names)))]
    elif organization_names:
        filters["organization"] = ["in", tuple(sorted(set(organization_names)))]
    else:
        return {"results": []}

    like_query = f"%{search_query}%"
    payload = {
        "results": frappe.get_all(
            "Team",
            filters=filters,
            or_filters=[
                ["Team", "name", "like", like_query],
                ["Team", "team_name", "like", like_query],
                ["Team", "team_code", "like", like_query],
            ],
            fields=["name", "team_name", "team_code", "school", "organization"],
            order_by="team_name asc, name asc",
            limit=result_limit,
        )
    }
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=AUDIENCE_TARGET_SEARCH_TTL_SECONDS)
    return payload


@frappe.whitelist()
def search_org_communication_student_groups(
    query: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    limit: int | None = None,
) -> dict:
    user = frappe.session.user
    _ensure_quick_create_access(user=user)

    search_query = _clean_text(query) or ""
    if len(search_query) < 2:
        return {"results": []}

    context = get_org_communication_context(user=user)
    school_names = _resolve_student_group_search_scope(
        context=context,
        organization=organization,
        school=school,
    )
    result_limit = _coerce_search_limit(
        limit,
        default=SUGGESTED_AUDIENCE_TARGETS_LIMIT,
        maximum=MAX_AUDIENCE_TARGET_SEARCH_RESULTS,
    )
    if not school_names:
        return {"results": []}

    cache_key = _search_cache_key(
        kind="student_group_search",
        user=user,
        query=search_query,
        organization=_clean_text(organization),
        school=_clean_text(school),
        limit=result_limit,
    )
    cache = frappe.cache()
    cached = cache.get_value(cache_key)
    if cached:
        parsed = frappe.parse_json(cached)
        if isinstance(parsed, dict):
            return parsed

    like_query = f"%{search_query}%"
    payload = {
        "results": frappe.get_all(
            "Student Group",
            filters={
                "school": ["in", tuple(sorted(set(school_names)))],
                "status": "Active",
            },
            or_filters=[
                ["Student Group", "name", "like", like_query],
                ["Student Group", "student_group_name", "like", like_query],
                ["Student Group", "student_group_abbreviation", "like", like_query],
            ],
            fields=["name", "student_group_name", "student_group_abbreviation", "school", "group_based_on"],
            order_by="student_group_abbreviation asc, student_group_name asc, name asc",
            limit=result_limit,
        )
    }
    cache.set_value(cache_key, frappe.as_json(payload), expires_in_sec=AUDIENCE_TARGET_SEARCH_TTL_SECONDS)
    return payload


@frappe.whitelist()
def create_org_communication_quick(
    name: str | None = None,
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
    doc_name = _clean_text(name)
    if not doc_name and not frappe.has_permission("Org Communication", ptype="create", user=user):
        frappe.throw(_("You do not have permission to create communications."), frappe.PermissionError)

    request_id = _clean_text(client_request_id)
    cache = frappe.cache()
    cache_key = _idempotency_key(user, request_id) if request_id and not doc_name else None

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

        if doc_name:
            doc = frappe.get_doc("Org Communication", doc_name)
            doc.check_permission("write")
        else:
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
        if _should_apply_arg("publish_from", publish_from):
            doc.publish_from = _clean_text(publish_from)
        if _should_apply_arg("publish_to", publish_to):
            doc.publish_to = _clean_text(publish_to)
        if _should_apply_arg("brief_start_date", brief_start_date):
            doc.brief_start_date = _clean_text(brief_start_date)
        if _should_apply_arg("brief_end_date", brief_end_date):
            doc.brief_end_date = _clean_text(brief_end_date)
        if _should_apply_arg("brief_order", brief_order):
            doc.brief_order = cint(brief_order) if brief_order not in (None, "") else None
        if _should_apply_arg("organization", organization):
            doc.organization = _clean_text(organization)
        if _should_apply_arg("school", school):
            doc.school = _clean_text(school)
        if _should_apply_arg("message", message):
            doc.message = message
        if _should_apply_arg("internal_note", internal_note):
            doc.internal_note = internal_note
        if _should_apply_arg("interaction_mode", interaction_mode):
            doc.interaction_mode = interaction_mode
        if allow_private_notes is not None:
            doc.allow_private_notes = _as_check(allow_private_notes)
        if allow_public_thread is not None:
            doc.allow_public_thread = _as_check(allow_public_thread)

        parsed_audiences = _parse_audiences(audiences)
        if any(row.get("target_mode") == "Organization" for row in parsed_audiences):
            doc.school = None

        doc.set("audiences", [])
        for row in parsed_audiences:
            child_row = doc.append("audiences", row)
            _normalize_audience_row_for_target_mode(child_row)
        for child_row in doc.get("audiences") or []:
            _normalize_audience_row_for_target_mode(child_row)

        if doc_name:
            doc.save()
        else:
            doc.insert()

        result = {
            "ok": True,
            "status": "updated" if doc_name else "created",
            "name": doc.name,
            "title": doc.title,
        }
        if cache_key:
            cache.set_value(cache_key, frappe.as_json(result), expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return result
