# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import get_ancestors_of

CACHE_TTL = 300  # seconds

class ParentRuleViolation(frappe.ValidationError):
    """Raised when a child record violates parent↔child inheritance rules."""


def _cache_key(doctype, school, extra):
    # Make a short, deterministic cache key
    return f"{doctype}:{school}:" + ":".join(f"{k}={v}" for k, v in sorted(extra.items()))


def get_effective_record(
    doctype: str,
    school: str,
    link_field: str | None = "school",
    extra_filters: dict | None = None,
    use_org_fallback: bool = True,
) -> str | None:
    """
    Return the *nearest* ancestor's record of `doctype` that matches `extra_filters`.
    - If `link_field` is None, the doctype is treated as global (no school column).
    - Caches results for 5 minutes to keep DB load minimal.

    Example:
        ay = get_effective_record("Academic Year", "ISS",
                                   extra_filters={"status": 1})
    """
    extra_filters = extra_filters or {}
    cache = frappe.cache()
    key = _cache_key(doctype, school, extra_filters)
    cached = cache.get_value(key)
    if cached:
        return cached if cached != "__none__" else None

    # 1 ▪ climb school tree
    chain = [school] + get_ancestors_of("School", school)
    for sch in chain:
        filters = extra_filters.copy()
        if link_field:
            filters[link_field] = sch
        record = frappe.db.get_value(doctype, filters, "name")
        if record:
            cache.set_value(key, record, expires_in=CACHE_TTL)
            return record

    # 2 ▪ optional organisation fallback
    if use_org_fallback:
        org = frappe.db.get_value("School", school, "organization")
        if org:
            chain = [org] + get_ancestors_of("Organization", org)
            for org_node in chain:
                filters = extra_filters.copy()
                filters["organization"] = org_node
                record = frappe.db.get_value(doctype, filters, "name")
                if record:
                    cache.set_value(key, record, expires_in=CACHE_TTL)
                    return record

    cache.set_value(key, "__none__", expires_in=CACHE_TTL)
    return None
