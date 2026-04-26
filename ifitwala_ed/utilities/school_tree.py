# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# /Users/francois.de/Documents/ifitwala_ed/ifitwala_ed/utilities/school_tree.py

from __future__ import annotations

import frappe
from frappe.utils.nestedset import get_ancestors_of, get_descendants_of

from ifitwala_ed.utilities.tree_utils import get_ancestors_inclusive, get_descendants_inclusive

CACHE_TTL = 600  # seconds
SCHOOL_TREE_CACHE_PREFIXES = (
    "ifitwala_ed:school_tree:",
    "tree:School:",
)


class ParentRuleViolation(frappe.ValidationError):
    """Raised when a child record violates parent↔child inheritance rules."""


def invalidate_school_tree_cache(doc=None, _=None):
    cache = frappe.cache()
    for prefix in SCHOOL_TREE_CACHE_PREFIXES:
        for key in cache.get_keys(f"{prefix}*"):
            cache.delete_value(key)


def get_root_school() -> str | None:
    """Return the root School (lft == 1) if present, cached for reuse."""
    cache = frappe.cache()
    key = "ifitwala_ed:school_tree:root_school"
    cached = cache.get_value(key)
    if cached:
        return cached if cached != "__none__" else None

    root = frappe.db.get_value("School", {"lft": 1}, "name")
    if not root:
        root = frappe.db.get_value("School", {"parent_school": ["in", [None, ""]]}, "name")
    cache.set_value(key, root or "__none__", expires_in_sec=CACHE_TTL)
    return root


def _cache_key(doctype, school, extra):
    # Make a short, deterministic cache key
    return f"{doctype}:{school}:" + ":".join(f"{k}={v}" for k, v in sorted(extra.items()))


def _is_adminish(user: str) -> bool:
    """True if user is Administrator or has System Manager role."""
    return user == "Administrator" or ("System Manager" in frappe.get_roles(user))


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
            cache.set_value(key, record, expires_in_sec=CACHE_TTL)
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
                    cache.set_value(key, record, expires_in_sec=CACHE_TTL)
                    return record

    cache.set_value(key, "__none__", expires_in_sec=CACHE_TTL)
    return None


# an autocomplete/search function used in for js ui autocomplete
# in the school_calendar.js and in the school_schedule.js
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_school_descendants(doctype, txt, searchfield, start, page_len, filters):
    filters = filters or {}
    root = filters.get("root")

    # If no explicit root is provided, try user default; for admin/system manager, fallback to root school
    if not root:
        root = frappe.defaults.get_user_default("school") or (
            get_root_school() if _is_adminish(frappe.session.user) else None
        )
    if not root:
        return []

    chain = [root] + get_descendants_of("School", root)

    rows = frappe.db.get_list(
        "School", fields=["name", "school_name"], filters={"name": ["in", chain]}, order_by="school_name", as_list=1
    )
    return rows


# Used to get a list of schools that are descendants of a given school
# Used in program enrollment.
@frappe.whitelist()
def get_descendant_schools(user_school: str | None = None):
    """
    Return user_school + all of its descendants.
    - If user_school is None: use defaults, else for Administrator/System Manager, fall back to the root school.
    - Returns [] if nothing resolvable.
    """
    # Prefer explicit argument if provided
    if not user_school:
        # Try the user's default school first
        user_school = frappe.defaults.get_user_default("school")

    # Allow root fallback for admin/system manager when no default school
    if not user_school and _is_adminish(frappe.session.user):
        user_school = get_root_school()

    # Defensive: Return [] if still nothing
    if not user_school:
        return []

    return get_descendants_inclusive("School", user_school, cache_ttl=CACHE_TTL)


def get_descendant_school_scope(user_school: str | None, *, max_depth: int | None = None) -> list[str]:
    """
    Return user_school + descendants, optionally bounded to N child levels.

    `max_depth=None` means the full descendant subtree.
    `max_depth=1` means self + direct children only.
    """
    if not user_school:
        return []

    subtree = [school for school in (get_descendant_schools(user_school) or []) if school]
    if not subtree:
        return [user_school]

    if max_depth is None:
        return subtree

    depth_limit = max(int(max_depth), 0)
    if depth_limit == 0:
        return [user_school]

    rows = frappe.get_all(
        "School",
        filters={"name": ["in", subtree]},
        fields=["name", "parent_school"],
        limit=max(len(subtree), 1),
    )

    children_by_parent: dict[str, list[str]] = {}
    for row in rows:
        parent_school = (row.get("parent_school") or "").strip()
        school_name = (row.get("name") or "").strip()
        if not parent_school or not school_name:
            continue
        children_by_parent.setdefault(parent_school, []).append(school_name)

    allowed = {user_school}
    frontier = [user_school]
    remaining_depth = depth_limit
    while remaining_depth:
        next_frontier: list[str] = []
        for school_name in frontier:
            next_frontier.extend(children_by_parent.get(school_name, []))
        if not next_frontier:
            break
        allowed.update(next_frontier)
        frontier = next_frontier
        remaining_depth -= 1

    return [school for school in subtree if school in allowed]


# Used to get a list of schools that are ancestors of a given school
# Used in Term.
def get_ancestor_schools(user_school):
    # Defensive: Return [] if no school set
    if not user_school:
        return []
    return get_ancestors_inclusive("School", user_school, cache_ttl=CACHE_TTL)


def get_school_lineage(school: str | None) -> list[str]:
    """
    Return school lineage from nearest to farthest ancestor: [self, parent, grandparent...].
    """
    if not school:
        return []
    return [school, *(get_ancestors_of("School", school) or [])]


def get_first_ancestor_with_doc(doctype, school, filters=None):
    """
    Returns the first ancestor (including self) up the school tree that has a matching doctype.
    """
    if not school:
        return []
    chain = [school] + get_ancestors_of("School", school)
    for sch in chain:
        flt = dict(filters) if filters else {}
        flt["school"] = sch
        if frappe.db.exists(doctype, flt):
            return [sch]
    return []


def get_school_scope_for_academic_year(school: str | None) -> list[str]:
    """
    Return the school scope used for Academic Year visibility:
    - Prefer self + descendants when that subtree has visible, unarchived Academic Years
    - Otherwise fallback to nearest ancestor with visible, unarchived Academic Years
    Cached by school for 5 minutes.
    """
    if not school:
        return []

    cache = frappe.cache()
    key = f"ifitwala_ed:school_tree:ay_scope:{school}"
    cached = cache.get_value(key)
    if cached is not None:
        return cached

    subtree_scope = get_descendant_schools(school) or [school]
    if frappe.db.exists(
        "Academic Year",
        {"school": ["in", subtree_scope], "archived": 0, "visible_to_admission": 1},
    ):
        scope = subtree_scope
    else:
        scope = (
            get_first_ancestor_with_doc(
                "Academic Year",
                school,
                filters={"archived": 0, "visible_to_admission": 1},
            )
            or subtree_scope
        )

    cache.set_value(key, scope, expires_in_sec=CACHE_TTL)
    return scope


# Usage Scenarios:
#   - Used in permission logic (e.g., Term, Program Enrollment) to determine
#     whether a user should see ancestor schools' data (for leaf schools) or all descendant data (for parent schools).
#   - Helps to differentiate between access rules for child campuses and main/parent campuses.
def is_leaf_school(school):
    """Return True if the school has no children (descendants), else False."""
    if not school:
        return False
    descendants = get_descendant_schools(school)
    return len(descendants) == 1  # Only itself in the list


@frappe.whitelist()
def get_user_default_school():
    """
    Return the effective default school for the current user:
    1) frappe.defaults user default
    2) Employee.school (active), if any
    3) For Administrator/System Manager: root school
    """
    user = frappe.session.user

    # 1) explicit user default
    school = frappe.defaults.get_user_default("school", user=user)
    if school:
        return school

    # 2) linked Employee (common for staff)
    row = frappe.db.get_value("Employee", {"user_id": user, "employment_status": "Active"}, ["school"], as_dict=True)
    if row and row.school:
        return row.school

    # 3) admin/system manager fallback to root
    if _is_adminish(user):
        return get_root_school()

    return None
