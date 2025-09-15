# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import get_ancestors_of
from frappe.utils.nestedset import get_descendants_of

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
def get_school_descendants(doctype, txt, searchfield, start, page_len, filters):
	root = filters.get("root")
	if not root:
		return []
	chain = [root] + get_descendants_of("School", root)

	rows = frappe.db.get_list(
		"School",
		fields=["name", "school_name"],
		filters={"name": ["in", chain]},
		order_by="school_name",
		as_list=1
	)
	return rows


# Used to get a list of schools that are descendants of a given school
# Used in program enrollment. 
@frappe.whitelist()
def get_descendant_schools(user_school):
    # Defensive: Return [] if no school set
    if not user_school:
        return []
    # Use the NestedSet lft/rgt logic
    school_doc = frappe.get_doc("School", user_school)
    return [
        s.name
        for s in frappe.get_all(
            "School",
            filters={"lft": (">=", school_doc.lft), "rgt": ("<=", school_doc.rgt)},
            fields=["name"]
        )
    ]

# Used to get a list of schools that are ancestors of a given school
# Used in Term.
def get_ancestor_schools(user_school):
	# Defensive: Return [] if no school set
	if not user_school:
		return []
	# Use the NestedSet lft/rgt logic (find all ancestors including self)
	school_doc = frappe.get_doc("School", user_school)
	return [
		s.name
		for s in frappe.get_all(
			"School",
			filters={"lft": ("<=", school_doc.lft), "rgt": (">=", school_doc.rgt)},
			fields=["name"]
		)
	]

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
	row = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"}, ["school"], as_dict=True)
	return row.school if row and row.school else None