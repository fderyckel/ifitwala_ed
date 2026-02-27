# ifitwala_ed/governance/policy_scope_utils.py

from __future__ import annotations

from collections.abc import Sequence

import frappe
from frappe.utils.nestedset import get_ancestors_of

from ifitwala_ed.utilities.employee_utils import get_user_base_org, get_user_base_school
from ifitwala_ed.utilities.school_tree import get_school_lineage

CACHE_TTL = 600  # seconds


def _cache_key(kind: str, organization: str) -> str:
    return f"policy_scope:{kind}:{organization}"


def _school_cache_key(kind: str, school: str) -> str:
    return f"policy_scope:{kind}:{school}"


def _get_user_default_value(user: str, key: str) -> str | None:
    row = frappe.db.get_value(
        "DefaultValue",
        {"parent": user, "defkey": key},
        "defvalue",
    )
    value = (row or "").strip()
    return value or None


def get_user_policy_scope(user: str | None = None) -> tuple[list[str], list[str]]:
    """
    Return user scope as (organization_ancestors_with_self, school_ancestors_with_self).

    Context resolution order:
    - Active Employee organization/school
    - User defaults (DefaultValue.organization / DefaultValue.school)
    """
    user = user or frappe.session.user
    if not user or user == "Guest":
        return [], []

    organization = (get_user_base_org(user) or "").strip() or (_get_user_default_value(user, "organization") or "")
    school = (get_user_base_school(user) or "").strip() or (_get_user_default_value(user, "school") or "")

    organization_scope = get_organization_ancestors_including_self(organization)
    school_scope = get_school_ancestors_including_self(school)
    return organization_scope, school_scope


def is_policy_within_user_scope(
    *,
    policy_organization: str | None,
    policy_school: str | None,
    user: str | None = None,
) -> bool:
    """
    True if the policy is visible for user scope:
    - organization must be in user's org ancestors
    - school-scoped policy additionally requires policy school in user's school ancestors
    """
    policy_organization = (policy_organization or "").strip()
    policy_school = (policy_school or "").strip()
    if not policy_organization:
        return False

    organization_scope, school_scope = get_user_policy_scope(user)
    if policy_organization not in set(organization_scope):
        return False

    if not policy_school:
        return True

    return policy_school in set(school_scope)


def get_organization_ancestors_including_self(organization: str | None) -> list[str]:
    """
    Return [organization, parent, ..., root] using Organization NestedSet ancestry.
    Order is nearest-first, which is required for nearest-only policy override.
    """
    organization = (organization or "").strip()
    if not organization:
        return []

    cache = frappe.cache()
    key = _cache_key("ancestors", organization)
    cached = cache.get_value(key)
    if cached is not None:
        try:
            parsed = frappe.parse_json(cached)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            if isinstance(cached, (list, tuple)):
                return list(cached)
        return []

    if not frappe.db.exists("Organization", organization):
        cache.set_value(key, "[]", expires_in_sec=CACHE_TTL)
        return []

    chain = [organization, *(get_ancestors_of("Organization", organization) or [])]
    seen = set()
    ordered_chain: list[str] = []
    for org in chain:
        org = (org or "").strip()
        if not org or org in seen:
            continue
        seen.add(org)
        ordered_chain.append(org)

    cache.set_value(key, frappe.as_json(ordered_chain), expires_in_sec=CACHE_TTL)
    return ordered_chain


def get_school_ancestors_including_self(school: str | None) -> list[str]:
    """
    Return [school, parent, ..., root] using School NestedSet ancestry.
    Order is nearest-first for nearest school scope matching.
    """
    school = (school or "").strip()
    if not school:
        return []

    cache = frappe.cache()
    key = _school_cache_key("ancestors", school)
    cached = cache.get_value(key)
    if cached is not None:
        try:
            parsed = frappe.parse_json(cached)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            if isinstance(cached, (list, tuple)):
                return list(cached)
        return []

    if not frappe.db.exists("School", school):
        cache.set_value(key, "[]", expires_in_sec=CACHE_TTL)
        return []

    chain = get_school_lineage(school) or [school]
    seen = set()
    ordered_chain: list[str] = []
    for row_school in chain:
        row_school = (row_school or "").strip()
        if not row_school or row_school in seen:
            continue
        seen.add(row_school)
        ordered_chain.append(row_school)

    cache.set_value(key, frappe.as_json(ordered_chain), expires_in_sec=CACHE_TTL)
    return ordered_chain


def is_policy_organization_applicable_to_context(
    *,
    policy_organization: str | None,
    context_organization: str | None,
) -> bool:
    """
    True when policy_organization is self/ancestor of context_organization.
    """
    policy_organization = (policy_organization or "").strip()
    context_organization = (context_organization or "").strip()
    if not policy_organization or not context_organization:
        return False
    return policy_organization in get_organization_ancestors_including_self(context_organization)


def is_school_within_policy_organization_scope(
    *,
    policy_organization: str | None,
    school: str | None,
) -> bool:
    """
    True when School.organization is self/descendant of policy_organization.
    """
    policy_organization = (policy_organization or "").strip()
    school = (school or "").strip()
    if not policy_organization or not school:
        return False
    school_org = frappe.db.get_value("School", school, "organization")
    return is_policy_organization_applicable_to_context(
        policy_organization=policy_organization,
        context_organization=school_org,
    )


def select_nearest_policy_rows_by_key(
    *,
    rows: Sequence[dict],
    context_organization: str | None,
    context_school: str | None = None,
    policy_key_field: str = "policy_key",
    policy_organization_field: str = "policy_organization",
    policy_school_field: str = "policy_school",
) -> list[dict]:
    """
    Nearest-only override by policy_key across ancestor policy candidates.
    """
    if not rows:
        return []

    ancestors = get_organization_ancestors_including_self(context_organization)
    if not ancestors:
        return []

    rank = {org: idx for idx, org in enumerate(ancestors)}
    school_chain = get_school_ancestors_including_self(context_school)
    school_rank = {school: idx for idx, school in enumerate(school_chain)}
    has_school_context = bool(school_rank)
    global_school_rank = len(school_rank) if has_school_context else 0
    selected: dict[str, tuple[int, int, int, dict]] = {}

    for idx, row in enumerate(rows):
        key = (row.get(policy_key_field) or "").strip()
        org = (row.get(policy_organization_field) or "").strip()
        if not key or org not in rank:
            continue

        current_rank = rank[org]
        current_school_rank = global_school_rank
        if has_school_context:
            row_school = (row.get(policy_school_field) or "").strip()
            if row_school:
                if row_school not in school_rank:
                    continue
                current_school_rank = school_rank[row_school]

        existing = selected.get(key)
        if not existing or (current_rank, current_school_rank, idx) < (
            existing[0],
            existing[1],
            existing[2],
        ):
            selected[key] = (current_rank, current_school_rank, idx, row)

    return [entry[3] for entry in sorted(selected.values(), key=lambda item: (item[0], item[1], item[2]))]
