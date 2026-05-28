from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.admission_utils import get_admissions_file_staff_scope
from ifitwala_ed.admission.admissions_crm_domain import clean, get_school_organization
from ifitwala_ed.admission.admissions_crm_permissions import doc_is_in_admissions_crm_scope
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_descendants_including_self,
    get_school_descendants_including_self,
)


def _scope_values(values) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = clean(value)
        if not text or text in seen:
            continue
        cleaned.append(text)
        seen.add(text)
    return cleaned


def _descendant_organizations(organization: str | None) -> list[str]:
    organization_name = clean(organization)
    if not organization_name:
        return []
    return _scope_values(get_organization_descendants_including_self(organization_name))


def _descendant_schools(school: str | None) -> list[str]:
    school_name = clean(school)
    if not school_name:
        return []
    return _scope_values(get_school_descendants_including_self(school_name))


def _resolve_scope(user: str, *, organization: str | None = None, school: str | None = None) -> dict:
    organization_name = clean(organization)
    school_name = clean(school)

    if school_name and not organization_name:
        organization_name = get_school_organization(school_name)
    if school_name and organization_name:
        school_org = get_school_organization(school_name)
        if school_org and school_org != organization_name:
            if school_org not in _descendant_organizations(organization_name):
                frappe.throw(_("Selected School does not belong to the selected Organization."))

    if organization_name or school_name:
        if not doc_is_in_admissions_crm_scope(user=user, organization=organization_name, school=school_name):
            frappe.throw(_("You do not have permission for this admissions inbox scope."), frappe.PermissionError)

    staff_scope = get_admissions_file_staff_scope(user)
    if not staff_scope.get("allowed"):
        frappe.throw(_("You do not have permission to access Admissions Inbox."), frappe.PermissionError)

    return {
        "bypass": bool(staff_scope.get("bypass")),
        "organization": organization_name,
        "school": school_name,
        "org_scope": _scope_values(staff_scope.get("org_scope") or []),
        "school_scope": _scope_values(staff_scope.get("school_scope") or []),
        "filter_orgs": _descendant_organizations(organization_name) if organization_name else [],
        "filter_schools": _descendant_schools(school_name) if school_name else [],
    }
