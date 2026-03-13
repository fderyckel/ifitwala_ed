# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/utilities/tree_utils.py

import frappe

DEFAULT_TREE_CACHE_TTL = 300  # seconds


def _tree_cache_key(doctype: str, kind: str, node: str) -> str:
    return f"tree:{doctype}:{kind}:{node}"


def get_descendants_inclusive(doctype: str, node: str, cache_ttl: int = DEFAULT_TREE_CACHE_TTL) -> list[str]:
    """
    Return `node` plus all descendants for a NestedSet doctype.
    """
    if not doctype or not node:
        return []

    cache = frappe.cache()
    key = _tree_cache_key(doctype, "desc", node)
    cached = cache.get_value(key)
    if cached is not None:
        return cached

    doc = frappe.get_doc(doctype, node)
    rows = frappe.get_all(
        doctype,
        filters={"lft": (">=", doc.lft), "rgt": ("<=", doc.rgt)},
        pluck="name",
    )
    cache.set_value(key, rows, expires_in_sec=cache_ttl)
    return rows


def get_ancestors_inclusive(doctype: str, node: str, cache_ttl: int = DEFAULT_TREE_CACHE_TTL) -> list[str]:
    """
    Return `node` plus all ancestors for a NestedSet doctype.
    """
    if not doctype or not node:
        return []

    cache = frappe.cache()
    key = _tree_cache_key(doctype, "anc", node)
    cached = cache.get_value(key)
    if cached is not None:
        return cached

    doc = frappe.get_doc(doctype, node)
    rows = frappe.get_all(
        doctype,
        filters={"lft": ("<=", doc.lft), "rgt": (">=", doc.rgt)},
        pluck="name",
    )
    cache.set_value(key, rows, expires_in_sec=cache_ttl)
    return rows
