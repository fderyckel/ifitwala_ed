# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import cstr

from ifitwala_ed.utilities.school_tree import get_descendant_schools

### THis creates quite a bit of issues in when we call the html card contact.
### Contact should be the primary way to deal with all contact information (tel, email, address)
## the doctype have link to doctype so it should be straight forward.


def update_profile_from_contact(doc, method=None):
    """Update the main doctype if changes made on Contact DocType.
    Called by hooks.py"""

    if frappe.flags.get("skip_contact_to_guardian_sync"):
        return

    # student = next((link.link_name for link in doc.links if link.link_doctype == "Student"), None)
    guardian = next((link.link_name for link in doc.links if link.link_doctype == "Guardian"), None)
    # employee = next((link.link_name for link in doc.links if link.link_doctype == "Employee"), None)
    primary_mobile = next((p.phone for p in doc.phone_nos if p.is_primary_mobile_no), None)

    if guardian:
        guardian_doc = frappe.get_doc("Guardian", guardian)
        changed = False

        salutation = (doc.salutation or "").strip()
        if salutation and salutation != (guardian_doc.salutation or "").strip():
            guardian_doc.salutation = salutation
            changed = True

        gender = (doc.gender or "").strip()
        if gender and gender != (guardian_doc.guardian_gender or "").strip():
            guardian_doc.guardian_gender = gender
            changed = True

        mobile = (primary_mobile or "").strip()
        if mobile and mobile != (guardian_doc.guardian_mobile_phone or "").strip():
            guardian_doc.guardian_mobile_phone = mobile
            changed = True

        if changed:
            guardian_doc.save(ignore_permissions=True)


from frappe.contacts.address_and_contact import has_permission as _core_has_permission  # noqa: E402

HR_CONTACT_ROLES = {"HR Manager", "HR User"}
ACADEMIC_CONTACT_ROLES = {"Academic Admin", "Academic Assistant"}


def _is_adminish(user: str) -> bool:
    return user == "Administrator" or "System Manager" in set(frappe.get_roles(user))


def _resolve_hr_contact_org_scope(user: str) -> list[str]:
    from ifitwala_ed.hr.doctype.employee.employee import _resolve_hr_org_scope

    return _resolve_hr_org_scope(user)


def _resolve_academic_contact_school_scope(user: str) -> list[str]:
    from ifitwala_ed.hr.doctype.employee.employee import (
        _get_user_default_from_db,
        _resolve_academic_admin_school_scope,
    )

    roles = set(frappe.get_roles(user))
    if "Academic Admin" in roles:
        school_scope = _resolve_academic_admin_school_scope(user)
    else:
        school_scope = _get_user_default_from_db(user, "school")

    if not school_scope:
        return []

    return list(dict.fromkeys(get_descendant_schools(school_scope) or [school_scope]))


def _resolve_academic_contact_org_scope(user: str) -> list[str]:
    from ifitwala_ed.hr.doctype.employee.employee import _resolve_academic_admin_org_scope

    return _resolve_academic_admin_org_scope(user)


def _resolve_self_employee_contact(user: str) -> str | None:
    from ifitwala_ed.hr.doctype.employee.employee import _resolve_self_employee

    return _resolve_self_employee(user)


def _employee_contact_scope_sql(user: str) -> str | None:
    roles = set(frappe.get_roles(user))

    if roles & HR_CONTACT_ROLES:
        orgs = _resolve_hr_contact_org_scope(user)
        if not orgs:
            return "IFNULL(emp.organization, '') = ''"

        vals = ", ".join(frappe.db.escape(org, percent=False) for org in orgs)
        return f"(emp.organization IN ({vals}) OR IFNULL(emp.organization, '') = '')"

    if roles & ACADEMIC_CONTACT_ROLES:
        schools = _resolve_academic_contact_school_scope(user)
        if schools:
            vals = ", ".join(frappe.db.escape(school, percent=False) for school in schools)
            return f"emp.school IN ({vals})"

        if "Academic Admin" not in roles:
            return "1=0"

        orgs = _resolve_academic_contact_org_scope(user)
        if not orgs:
            return "1=0"

        vals = ", ".join(frappe.db.escape(org, percent=False) for org in orgs)
        return f"emp.organization IN ({vals})"

    if "Employee" in roles:
        own_employee = _resolve_self_employee_contact(user)
        if not own_employee:
            return "1=0"

        return f"emp.name = {frappe.db.escape(own_employee, percent=False)}"

    return None


def _employee_contact_scope_matches(contact_name: str | None, user: str, roles: set[str] | None = None) -> bool | None:
    if not contact_name:
        return None

    roles = roles or set(frappe.get_roles(user))
    linked_employees = frappe.get_all(
        "Dynamic Link",
        filters={"parenttype": "Contact", "parent": contact_name, "link_doctype": "Employee"},
        pluck="link_name",
    )
    linked_employees = [cstr(name).strip() for name in linked_employees if cstr(name).strip()]
    if not linked_employees:
        if roles & ACADEMIC_CONTACT_ROLES:
            return None
        if roles & HR_CONTACT_ROLES or "Employee" in roles:
            return False
        return None

    if roles & HR_CONTACT_ROLES:
        orgs = set(_resolve_hr_contact_org_scope(user))
        rows = frappe.get_all(
            "Employee",
            filters={"name": ["in", linked_employees]},
            fields=["organization"],
            limit=len(linked_employees),
        )
        return any(not cstr(row.get("organization")).strip() or row.get("organization") in orgs for row in rows)

    if roles & ACADEMIC_CONTACT_ROLES:
        schools = set(_resolve_academic_contact_school_scope(user))
        if schools:
            rows = frappe.get_all(
                "Employee",
                filters={"name": ["in", linked_employees]},
                fields=["school"],
                limit=len(linked_employees),
            )
            return any(cstr(row.get("school")).strip() in schools for row in rows)

        if "Academic Admin" not in roles:
            return False

        orgs = set(_resolve_academic_contact_org_scope(user))
        if not orgs:
            return False
        rows = frappe.get_all(
            "Employee",
            filters={"name": ["in", linked_employees]},
            fields=["organization"],
            limit=len(linked_employees),
        )
        return any(cstr(row.get("organization")).strip() in orgs for row in rows)

    if "Employee" in roles:
        own_employee = _resolve_self_employee_contact(user)
        return bool(own_employee and own_employee in linked_employees)

    return None


# ------------------------------------------------------------------ #
#  Doc‑level gate
# ------------------------------------------------------------------ #
def contact_has_permission(doc, ptype, user):
    """Apply employee-contact scope checks on top of the core Contact permission gate."""
    core_allowed = _core_has_permission(doc, ptype, user)
    if not core_allowed:
        return core_allowed

    if _is_adminish(user):
        return True

    scope_allowed = _employee_contact_scope_matches(getattr(doc, "name", None), user, set(frappe.get_roles(user)))
    if scope_allowed is None:
        return core_allowed

    return bool(scope_allowed)


# ------------------------------------------------------------------ #
#  List / report filter
# ------------------------------------------------------------------ #
def contact_permission_query_conditions(user):
    """Restrict employee-linked contacts by server-owned staff scope while leaving other contacts to core rules."""
    if not user or user == "Guest" or _is_adminish(user):
        return ""

    employee_scope_sql = _employee_contact_scope_sql(user)
    if not employee_scope_sql:
        return ""

    employee_link_exists = """
        EXISTS (
            SELECT 1
            FROM `tabDynamic Link` contact_employee_link
            WHERE contact_employee_link.parenttype = 'Contact'
                AND contact_employee_link.parent = `tabContact`.name
                AND contact_employee_link.link_doctype = 'Employee'
        )
    """
    scoped_employee_link_exists = f"""
        EXISTS (
            SELECT 1
            FROM `tabDynamic Link` scoped_contact_employee_link
            INNER JOIN `tabEmployee` emp ON emp.name = scoped_contact_employee_link.link_name
            WHERE scoped_contact_employee_link.parenttype = 'Contact'
                AND scoped_contact_employee_link.parent = `tabContact`.name
                AND scoped_contact_employee_link.link_doctype = 'Employee'
                AND {employee_scope_sql}
        )
    """

    roles = set(frappe.get_roles(user))
    if roles & ACADEMIC_CONTACT_ROLES:
        return f"((NOT {employee_link_exists}) OR {scoped_employee_link_exists})"

    return f"({scoped_employee_link_exists})"
