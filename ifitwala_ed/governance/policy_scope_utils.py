# ifitwala_ed/governance/policy_scope_utils.py

from __future__ import annotations

from collections.abc import Sequence

import frappe
from frappe.utils.nestedset import get_ancestors_of

CACHE_TTL = 600  # seconds


def _cache_key(kind: str, organization: str) -> str:
	return f"policy_scope:{kind}:{organization}"


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
	policy_key_field: str = "policy_key",
	policy_organization_field: str = "policy_organization",
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
	selected: dict[str, tuple[int, int, dict]] = {}

	for idx, row in enumerate(rows):
		key = (row.get(policy_key_field) or "").strip()
		org = (row.get(policy_organization_field) or "").strip()
		if not key or org not in rank:
			continue

		current_rank = rank[org]
		existing = selected.get(key)
		if not existing or current_rank < existing[0]:
			selected[key] = (current_rank, idx, row)

	return [entry[2] for entry in sorted(selected.values(), key=lambda item: (item[0], item[1]))]
