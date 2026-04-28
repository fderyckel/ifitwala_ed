# ifitwala_ed/admission/access.py
# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

ADMISSIONS_APPLICANT_ROLE = "Admissions Applicant"
ADMISSIONS_FAMILY_ROLE = "Admissions Family"
ADMISSIONS_PORTAL_ROLES = frozenset({ADMISSIONS_APPLICANT_ROLE, ADMISSIONS_FAMILY_ROLE})

ADMISSIONS_ACCESS_MODE_SINGLE = "Single Applicant Workspace"
ADMISSIONS_ACCESS_MODE_FAMILY = "Family Workspace"

NON_PROMOTED_APPLICANT_STATUSES = frozenset(
    {
        "Draft",
        "Invited",
        "In Progress",
        "Submitted",
        "Under Review",
        "Missing Info",
        "Approved",
        "Rejected",
        "Withdrawn",
    }
)


def get_admissions_access_mode() -> str:
    try:
        value = (frappe.db.get_single_value("Admission Settings", "admissions_access_mode") or "").strip()
    except Exception:
        value = ""
    if value == ADMISSIONS_ACCESS_MODE_FAMILY:
        return ADMISSIONS_ACCESS_MODE_FAMILY
    return ADMISSIONS_ACCESS_MODE_SINGLE


def is_family_workspace_enabled() -> bool:
    return get_admissions_access_mode() == ADMISSIONS_ACCESS_MODE_FAMILY


def has_admissions_family_role(user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user:
        return False
    return ADMISSIONS_FAMILY_ROLE in set(frappe.get_roles(resolved_user))


def has_admissions_applicant_role(user: str | None = None) -> bool:
    resolved_user = (user or frappe.session.user or "").strip()
    if not resolved_user:
        return False
    return ADMISSIONS_APPLICANT_ROLE in set(frappe.get_roles(resolved_user))


def get_guardian_names_for_user(*, user: str) -> list[str]:
    resolved_user = (user or "").strip()
    if not resolved_user:
        return []
    rows = frappe.get_all(
        "Guardian",
        filters={"user": resolved_user},
        pluck="name",
    )
    return sorted({(row or "").strip() for row in rows if (row or "").strip()})


def _non_promoted_name_filters(*, names: list[str]) -> dict:
    filters: dict = {"name": ["in", names]}
    filters["application_status"] = ["in", sorted(NON_PROMOTED_APPLICANT_STATUSES)]
    return filters


def get_family_applicant_names_for_user(*, user: str, include_promoted: bool = False) -> list[str]:
    resolved_user = (user or "").strip()
    if not resolved_user or not is_family_workspace_enabled():
        return []

    filters = {
        "parenttype": "Student Applicant",
        "parentfield": "guardians",
        "can_consent": 1,
        "user": resolved_user,
    }
    direct_rows = frappe.get_all("Student Applicant Guardian", filters=filters, pluck="parent") or []

    guardian_names = get_guardian_names_for_user(user=resolved_user)
    guardian_rows: list[str] = []
    if guardian_names:
        guardian_rows = (
            frappe.get_all(
                "Student Applicant Guardian",
                filters={
                    "parenttype": "Student Applicant",
                    "parentfield": "guardians",
                    "can_consent": 1,
                    "guardian": ["in", guardian_names],
                },
                pluck="parent",
            )
            or []
        )

    names = sorted({(row or "").strip() for row in [*direct_rows, *guardian_rows] if (row or "").strip()})
    if include_promoted or not names:
        return names

    rows = frappe.get_all(
        "Student Applicant",
        filters=_non_promoted_name_filters(names=names),
        pluck="name",
    )
    return sorted({(row or "").strip() for row in rows if (row or "").strip()})


def get_admissions_portal_applicant_names_for_user(*, user: str, include_promoted: bool = False) -> list[str]:
    resolved_user = (user or "").strip()
    if not resolved_user:
        return []

    roles = set(frappe.get_roles(resolved_user))
    names: set[str] = set()

    if ADMISSIONS_APPLICANT_ROLE in roles:
        filters: dict = {"applicant_user": resolved_user}
        if not include_promoted:
            filters["application_status"] = ["in", sorted(NON_PROMOTED_APPLICANT_STATUSES)]
        applicant_rows = frappe.get_all("Student Applicant", filters=filters, pluck="name") or []
        names.update((row or "").strip() for row in applicant_rows if (row or "").strip())

    if ADMISSIONS_FAMILY_ROLE in roles:
        names.update(get_family_applicant_names_for_user(user=resolved_user, include_promoted=include_promoted))

    return sorted(names)


def build_admissions_portal_access_exists_sql(*, user: str, student_applicant_expr_sql: str) -> str:
    resolved_user = (user or "").strip()
    expr_sql = (student_applicant_expr_sql or "").strip()
    if not resolved_user or not expr_sql:
        return "1=0"

    escaped_user = frappe.db.escape(resolved_user)
    conditions: list[str] = []
    roles = set(frappe.get_roles(resolved_user))

    if ADMISSIONS_APPLICANT_ROLE in roles:
        conditions.append(
            "("
            "EXISTS ("
            "SELECT 1 FROM `tabStudent Applicant` sa "
            f"WHERE sa.name = {expr_sql} "
            f"AND sa.applicant_user = {escaped_user}"
            ")"
            ")"
        )

    if ADMISSIONS_FAMILY_ROLE in roles and is_family_workspace_enabled():
        conditions.append(
            "("
            "EXISTS ("
            "SELECT 1 "
            "FROM `tabStudent Applicant Guardian` sag "
            "LEFT JOIN `tabGuardian` g ON g.name = sag.guardian "
            f"WHERE sag.parent = {expr_sql} "
            "AND sag.parenttype = 'Student Applicant' "
            "AND sag.parentfield = 'guardians' "
            "AND ifnull(sag.can_consent, 0) = 1 "
            f"AND (ifnull(sag.user, '') = {escaped_user} OR ifnull(g.user, '') = {escaped_user})"
            ")"
            ")"
        )

    return " OR ".join(conditions) if conditions else "1=0"


def user_can_access_student_applicant(*, user: str, student_applicant: str) -> bool:
    resolved_user = (user or "").strip()
    applicant_name = (student_applicant or "").strip()
    if not resolved_user or not applicant_name:
        return False

    roles = set(frappe.get_roles(resolved_user))
    if ADMISSIONS_APPLICANT_ROLE in roles:
        applicant_user = frappe.db.get_value("Student Applicant", applicant_name, "applicant_user")
        if (applicant_user or "").strip() == resolved_user:
            return True

    if ADMISSIONS_FAMILY_ROLE in roles and is_family_workspace_enabled():
        if frappe.db.exists(
            "Student Applicant Guardian",
            {
                "parent": applicant_name,
                "parenttype": "Student Applicant",
                "parentfield": "guardians",
                "user": resolved_user,
                "can_consent": 1,
            },
        ):
            return True

        guardian_names = get_guardian_names_for_user(user=resolved_user)
        if guardian_names and frappe.db.exists(
            "Student Applicant Guardian",
            {
                "parent": applicant_name,
                "parenttype": "Student Applicant",
                "parentfield": "guardians",
                "guardian": ["in", guardian_names],
                "can_consent": 1,
            },
        ):
            return True

    return False


def has_open_admissions_portal_access(*, user: str, roles: set[str] | None = None) -> bool:
    resolved_user = (user or "").strip()
    resolved_roles = roles or set(frappe.get_roles(resolved_user))
    if not resolved_user or not (resolved_roles & ADMISSIONS_PORTAL_ROLES):
        return False
    return bool(get_admissions_portal_applicant_names_for_user(user=resolved_user, include_promoted=False))
