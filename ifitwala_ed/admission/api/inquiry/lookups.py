# ifitwala_ed/admission/api/inquiry/lookups.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.admission_utils import (
    get_admissions_file_staff_scope,
    get_public_inquiry_organization_scope,
)
from ifitwala_ed.admission.api.inquiry.access import _ensure_access
from ifitwala_ed.admission.api.inquiry.scope import _clean_values, _get_descendant_organizations
from ifitwala_ed.utilities.employee_utils import get_schools_for_organization_scope
from ifitwala_ed.utilities.school_tree import get_descendant_schools


def get_inquiry_organizations():
    user = _ensure_access()
    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        return []
    if not scope.get("bypass"):
        org_scope = _clean_values(scope.get("org_scope") or [])
        if not org_scope:
            return []
        rows = frappe.db.sql(
            """
            SELECT name
            FROM `tabOrganization`
            WHERE name IN %(organizations)s
            ORDER BY lft ASC, name ASC
            """,
            {"organizations": tuple(org_scope)},
            as_list=True,
        )
        return [r[0] for r in rows]

    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        ORDER BY lft ASC, name ASC
        """,
        as_list=True,
    )
    return [r[0] for r in rows]


def get_inquiry_schools():
    user = _ensure_access()
    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        return []
    if not scope.get("bypass"):
        school_scope = _clean_values(scope.get("school_scope") or [])
        if not school_scope:
            org_scope = _clean_values(scope.get("org_scope") or [])
            school_scope = _clean_values(get_schools_for_organization_scope(org_scope)) if org_scope else []
        if not school_scope:
            return []
        rows = frappe.db.sql(
            """
            SELECT name
            FROM `tabSchool`
            WHERE name IN %(schools)s
            ORDER BY lft ASC, name ASC
            """,
            {"schools": tuple(school_scope)},
            as_list=True,
        )
        return [r[0] for r in rows]

    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabSchool`
        ORDER BY lft ASC, name ASC
        """,
        as_list=True,
    )
    return [r[0] for r in rows]


def academic_year_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return frappe.db.sql(
        """
        SELECT name
        FROM `tabAcademic Year`
        WHERE name LIKE %(txt)s
        ORDER BY year_start_date DESC, name DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {"txt": f"%{txt or ''}%", "start": int(start or 0), "page_len": int(page_len or 20)},
    )


def inquiry_organization_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    return frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        WHERE name LIKE %(txt)s
            AND get_inquiry = 1
            AND COALESCE(archived, 0) = 0
        ORDER BY lft ASC, name ASC
        LIMIT %(start)s, %(page_len)s
        """,
        {"txt": f"%{txt or ''}%", "start": int(start or 0), "page_len": int(page_len or 20)},
    )


def inquiry_school_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    organization = (filters.get("organization") or "").strip()
    organization_scope = get_public_inquiry_organization_scope(organization)
    if not organization_scope:
        return []

    params = {
        "txt": f"%{txt or ''}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
        "organizations": tuple(organization_scope),
    }
    where = [
        "COALESCE(s.show_in_inquiry, 0) = 1",
        "COALESCE(o.archived, 0) = 0",
        "s.organization IN %(organizations)s",
        "(s.name LIKE %(txt)s OR s.school_name LIKE %(txt)s)",
    ]

    return frappe.db.sql(
        f"""
        SELECT
            s.name,
            COALESCE(NULLIF(s.school_name, ''), s.name) AS school_name
        FROM `tabSchool` s
        INNER JOIN `tabOrganization` o ON o.name = s.organization
        WHERE {" AND ".join(where)}
        ORDER BY s.lft ASC, s.school_name ASC, s.name ASC
        LIMIT %(start)s, %(page_len)s
        """,
        params,
    )


def get_inquiry_acknowledgement_context(organization=None, school=None, type_of_inquiry=None):
    from ifitwala_ed.admission.inquiry_acknowledgement import build_public_acknowledgement_context

    return build_public_acknowledgement_context(
        organization=organization,
        school=school,
        type_of_inquiry=type_of_inquiry,
    )


def admission_user_link_query(doctype=None, txt=None, searchfield=None, start=0, page_len=20, filters=None):
    """Enabled users linked to active Employee rows; match name/full_name/email."""
    filters = filters or {}
    organization = (filters.get("organization") or "").strip()
    school = (filters.get("school") or "").strip()

    org_scope = _get_descendant_organizations(organization) if organization else []
    if organization and not org_scope:
        return []
    school_scope = get_descendant_schools(school) if school else []
    if school and not school_scope:
        return []

    where = ["ifnull(e.employment_status, '') = 'Active'", "ifnull(e.user_id, '') <> ''"]
    params = {
        "txt": f"%{txt or ''}%",
        "start": int(start or 0),
        "page_len": int(page_len or 20),
    }
    if org_scope:
        where.append("e.organization IN %(org_scope)s")
        params["org_scope"] = tuple(org_scope)
    if school_scope:
        where.append("e.school IN %(school_scope)s")
        params["school_scope"] = tuple(school_scope)

    return frappe.db.sql(
        f"""
        SELECT
            u.name,
            COALESCE(NULLIF(u.full_name, ''), NULLIF(e.employee_full_name, ''), u.name) as full_name
        FROM `tabUser` u
        JOIN `tabEmployee` e ON e.user_id = u.name
        WHERE u.enabled = 1
            AND {" AND ".join(where)}
            AND (
            u.name LIKE %(txt)s
            OR u.full_name LIKE %(txt)s
            OR e.employee_full_name LIKE %(txt)s
            OR u.email LIKE %(txt)s
            )
        ORDER BY full_name ASC, u.creation DESC
        LIMIT %(start)s, %(page_len)s
        """,
        params,
    )


def get_inquiry_types():
    # Returns a simple list of distinct, non-empty types (alphabetical)
    rows = frappe.db.sql(
        """
        SELECT DISTINCT type_of_inquiry
        FROM `tabInquiry`
        WHERE COALESCE(type_of_inquiry, '') <> ''
        ORDER BY type_of_inquiry
        """,
        as_dict=False,
    )
    return [r[0] for r in rows]


def get_inquiry_sources():
    _ensure_access()
    meta = frappe.get_meta("Inquiry")
    source_field = meta.get_field("source")
    if not source_field:
        return []

    options = [option.strip() for option in (source_field.options or "").splitlines() if option.strip()]
    return options
