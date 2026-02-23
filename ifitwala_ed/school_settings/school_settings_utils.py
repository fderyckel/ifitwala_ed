# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/school_settings_utils.py

import frappe
from frappe.utils import getdate
from frappe.utils.nestedset import get_descendants_of


def get_allowed_schools(user=None, selected_school=None):
    """
    Visibility helper ONLY.

    Returns schools the user can SEE.
    Does NOT imply calendar inheritance or resolution.
    """
    user = user or frappe.session.user
    root_school = frappe.defaults.get_user_default("school", user)

    if not root_school:
        return []

    visible = [root_school] + get_descendants_of("School", root_school)

    if selected_school:
        return [selected_school] if selected_school in visible else []

    return visible


@frappe.whitelist()
def get_user_allowed_schools():
    user = frappe.session.user
    root_school = frappe.defaults.get_user_default("school", user)
    if not root_school:
        return []

    return [root_school] + get_descendants_of("School", root_school)


# ---------------------------------------------------------------------
# Option B helper (NEW, additive)
# ---------------------------------------------------------------------


def resolve_terms_for_school_calendar(school: str, academic_year: str):
    """
    Pattern B — Canonical term resolver.

    IMPORTANT:
    - This function does NOT decide inheritance.
    - It ONLY returns candidate terms that a School Calendar may use.
    - Final authority remains the School Calendar record.

    Resolution order:
    1. School-scoped terms for this school
    2. Ancestor-school terms (explicit, via school_tree)
    3. Global template terms (school IS NULL)

    No mutation. No silent inheritance.
    """

    if not school or not academic_year:
        return []

    from ifitwala_ed.utilities.school_tree import get_ancestor_schools

    candidates = []

    # 1 ▸ Exact school terms
    candidates += frappe.get_all(
        "Term",
        filters={
            "academic_year": academic_year,
            "school": school,
        },
        pluck="name",
        order_by="term_start_date",
    )

    # 2 ▸ Ancestor-scoped terms (explicit reuse, not inheritance)
    if not candidates:
        for ancestor in get_ancestor_schools(school):
            candidates += frappe.get_all(
                "Term",
                filters={
                    "academic_year": academic_year,
                    "school": ancestor,
                },
                pluck="name",
                order_by="term_start_date",
            )
            if candidates:
                break

    # 3 ▸ Global templates (opt-in via calendar only)
    if not candidates:
        candidates += frappe.get_all(
            "Term",
            filters={
                "academic_year": academic_year,
                "school": ["is", "not set"],
            },
            pluck="name",
            order_by="term_start_date",
        )

    return candidates


def resolve_school_calendars_for_window(
    school: str,
    start_date,
    end_date,
) -> list[dict]:
    """
    Pattern B calendar resolver for consumers (portal, attendance, analytics).

    Resolution rules:
    1. Match calendars by Academic Year overlap with the requested date window.
    2. Restrict candidates to the school lineage (self -> ancestors).
    3. For each Academic Year, keep the nearest school's calendar only.

    No mutation. No implicit auto-creation.
    """
    if not school or not start_date or not end_date:
        return []

    start_value = getdate(start_date)
    end_value = getdate(end_date)
    if end_value < start_value:
        start_value, end_value = end_value, start_value

    from ifitwala_ed.utilities.school_tree import get_school_lineage

    lineage = get_school_lineage(school)
    if not lineage:
        return []

    rows = frappe.db.sql(
        """
		SELECT
			sc.name AS name,
			sc.school AS school,
			sc.academic_year AS academic_year,
			ay.year_start_date AS year_start_date,
			ay.year_end_date AS year_end_date
		FROM `tabSchool Calendar` sc
		INNER JOIN `tabAcademic Year` ay
			ON ay.name = sc.academic_year
		WHERE sc.docstatus < 2
			AND sc.school IN %(lineage)s
			AND COALESCE(ay.archived, 0) = 0
			AND ay.year_start_date <= %(window_end)s
			AND ay.year_end_date >= %(window_start)s
		ORDER BY ay.year_start_date DESC, sc.modified DESC
		""",
        {
            "lineage": tuple(lineage),
            "window_start": start_value,
            "window_end": end_value,
        },
        as_dict=True,
    )
    if not rows:
        return []

    rank = {school_name: idx for idx, school_name in enumerate(lineage)}
    selected_by_ay: dict[str, dict] = {}

    for row in rows:
        academic_year = row.get("academic_year")
        if not academic_year:
            continue
        existing = selected_by_ay.get(academic_year)
        if not existing:
            selected_by_ay[academic_year] = row
            continue

        current_rank = rank.get(row.get("school"), 10**9)
        existing_rank = rank.get(existing.get("school"), 10**9)
        if current_rank < existing_rank:
            selected_by_ay[academic_year] = row

    selected = list(selected_by_ay.values())
    selected.sort(
        key=lambda row: (
            -getdate(row.get("year_start_date")).toordinal(),
            rank.get(row.get("school"), 10**9),
        )
    )
    return selected
