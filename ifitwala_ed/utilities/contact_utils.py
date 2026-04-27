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
ADMISSIONS_CONTACT_ROLES = {"Admission Manager", "Admission Officer"}
EDUCATION_CONTACT_ROLES = ACADEMIC_CONTACT_ROLES | ADMISSIONS_CONTACT_ROLES
READ_LIKE_CONTACT_PTYPES = {"read", "report", "export", "print", "email"}


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


def _resolve_education_contact_school_scope(user: str) -> list[str]:
    from ifitwala_ed.utilities.employee_utils import get_user_visible_schools

    return list(dict.fromkeys(get_user_visible_schools(user) or []))


def _student_scope_condition_sql(student_alias: str, school_values: str) -> str:
    return f"""
        IFNULL({student_alias}.enabled, 0) = 1
        AND (
            {student_alias}.anchor_school IN ({school_values})
            OR EXISTS (
                SELECT 1
                FROM `tabProgram Enrollment` pe
                WHERE pe.student = {student_alias}.name
                    AND IFNULL(pe.archived, 0) = 0
                    AND pe.school IN ({school_values})
            )
        )
    """


def _student_applicant_scope_condition_sql(applicant_alias: str, school_values: str) -> str:
    return f"""
        {applicant_alias}.school IN ({school_values})
        OR EXISTS (
            SELECT 1
            FROM `tabStudent` applicant_student
            WHERE applicant_student.name = {applicant_alias}.student
                AND {_student_scope_condition_sql("applicant_student", school_values)}
        )
    """


def _education_contact_scope_sql(user: str) -> str:
    schools = _resolve_education_contact_school_scope(user)
    if not schools:
        return "1=0"

    school_values = ", ".join(frappe.db.escape(school, percent=False) for school in schools)
    return f"""
        (
            scoped_education_link.link_doctype = 'Student Applicant'
            AND EXISTS (
                SELECT 1
                FROM `tabStudent Applicant` scoped_applicant
                WHERE scoped_applicant.name = scoped_education_link.link_name
                    AND ({_student_applicant_scope_condition_sql("scoped_applicant", school_values)})
            )
        )
        OR (
            scoped_education_link.link_doctype = 'Student'
            AND EXISTS (
                SELECT 1
                FROM `tabStudent` scoped_student
                WHERE scoped_student.name = scoped_education_link.link_name
                    AND {_student_scope_condition_sql("scoped_student", school_values)}
            )
        )
        OR (
            scoped_education_link.link_doctype = 'Guardian'
            AND EXISTS (
                SELECT 1
                FROM `tabStudent Guardian` student_guardian
                INNER JOIN `tabStudent` guardian_student
                    ON guardian_student.name = student_guardian.parent
                WHERE student_guardian.parenttype = 'Student'
                    AND student_guardian.parentfield = 'guardians'
                    AND student_guardian.guardian = scoped_education_link.link_name
                    AND {_student_scope_condition_sql("guardian_student", school_values)}
            )
        )
        OR (
            scoped_education_link.link_doctype = 'Guardian'
            AND EXISTS (
                SELECT 1
                FROM `tabGuardian Student` guardian_student_link
                INNER JOIN `tabStudent` guardian_link_student
                    ON guardian_link_student.name = guardian_student_link.student
                WHERE guardian_student_link.parenttype = 'Guardian'
                    AND guardian_student_link.parent = scoped_education_link.link_name
                    AND {_student_scope_condition_sql("guardian_link_student", school_values)}
            )
        )
    """


def _reverse_student_applicant_contact_scope_sql(user: str) -> str:
    schools = _resolve_education_contact_school_scope(user)
    if not schools:
        return "1=0"

    school_values = ", ".join(frappe.db.escape(school, percent=False) for school in schools)
    return f"""
        EXISTS (
            SELECT 1
            FROM `tabStudent Applicant` reverse_scoped_applicant
            WHERE reverse_scoped_applicant.applicant_contact = `tabContact`.name
                AND ({_student_applicant_scope_condition_sql("reverse_scoped_applicant", school_values)})
        )
    """


def _education_contact_scope_matches(contact_name: str | None, user: str, roles: set[str] | None = None) -> bool | None:
    if not contact_name:
        return None

    roles = roles if roles is not None else set(frappe.get_roles(user))
    if not roles & EDUCATION_CONTACT_ROLES:
        return None

    linked_rows = frappe.get_all(
        "Dynamic Link",
        filters={
            "parenttype": "Contact",
            "parent": contact_name,
            "link_doctype": ["in", ["Student Applicant", "Student", "Guardian"]],
        },
        fields=["link_doctype", "link_name"],
        limit=200,
    )
    linked_rows = [
        frappe._dict(
            link_doctype=cstr(row.get("link_doctype")).strip(),
            link_name=cstr(row.get("link_name")).strip(),
        )
        for row in linked_rows
        if cstr(row.get("link_doctype")).strip() and cstr(row.get("link_name")).strip()
    ]
    if not linked_rows:
        return _reverse_student_applicant_contact_scope_matches(contact_name, user)

    schools = set(_resolve_education_contact_school_scope(user))
    if not schools:
        return False

    applicant_names = [row.link_name for row in linked_rows if row.link_doctype == "Student Applicant"]
    student_names = [row.link_name for row in linked_rows if row.link_doctype == "Student"]
    guardian_names = [row.link_name for row in linked_rows if row.link_doctype == "Guardian"]

    if applicant_names and _any_scoped_student_applicant(applicant_names, schools):
        return True
    if student_names and _any_scoped_student(student_names, schools):
        return True
    if guardian_names and _any_scoped_guardian(guardian_names, schools):
        return True

    return False


def _reverse_student_applicant_contact_scope_matches(contact_name: str, user: str) -> bool | None:
    schools = set(_resolve_education_contact_school_scope(user))
    if not schools:
        return False

    applicant_rows = frappe.get_all(
        "Student Applicant",
        filters={"applicant_contact": contact_name},
        fields=["name", "school", "student"],
        limit=200,
    )
    if not applicant_rows:
        return None

    for row in applicant_rows:
        if cstr(row.get("school")).strip() in schools:
            return True

    linked_students = [cstr(row.get("student")).strip() for row in applicant_rows if cstr(row.get("student")).strip()]
    if linked_students and _any_scoped_student(linked_students, schools):
        return True

    return False


def _any_scoped_student_applicant(applicant_names: list[str], schools: set[str]) -> bool:
    rows = frappe.get_all(
        "Student Applicant",
        filters={"name": ["in", applicant_names]},
        fields=["name", "school", "student"],
        limit=len(applicant_names),
    )
    linked_students = []
    for row in rows:
        if cstr(row.get("school")).strip() in schools:
            return True
        student_name = cstr(row.get("student")).strip()
        if student_name:
            linked_students.append(student_name)

    return bool(linked_students and _any_scoped_student(linked_students, schools))


def _any_scoped_student(student_names: list[str], schools: set[str]) -> bool:
    rows = frappe.get_all(
        "Student",
        filters={"name": ["in", student_names], "enabled": 1},
        fields=["name", "anchor_school"],
        limit=len(student_names),
    )
    scoped_students = []
    for row in rows:
        student_name = cstr(row.get("name")).strip()
        if not student_name:
            continue
        if cstr(row.get("anchor_school")).strip() in schools:
            return True
        scoped_students.append(student_name)

    if not scoped_students:
        return False

    enrollment_rows = frappe.get_all(
        "Program Enrollment",
        filters={"student": ["in", scoped_students], "archived": 0, "school": ["in", list(schools)]},
        pluck="name",
        limit=1,
    )
    return bool(enrollment_rows)


def _any_scoped_guardian(guardian_names: list[str], schools: set[str]) -> bool:
    student_guardian_rows = frappe.get_all(
        "Student Guardian",
        filters={"parenttype": "Student", "parentfield": "guardians", "guardian": ["in", guardian_names]},
        pluck="parent",
        limit=1000,
    )
    guardian_student_rows = frappe.get_all(
        "Guardian Student",
        filters={"parenttype": "Guardian", "parent": ["in", guardian_names]},
        pluck="student",
        limit=1000,
    )
    student_names = [
        cstr(student).strip()
        for student in [*(student_guardian_rows or []), *(guardian_student_rows or [])]
        if cstr(student).strip()
    ]
    if not student_names:
        return False

    return _any_scoped_student(list(dict.fromkeys(student_names)), schools)


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

    roles = roles if roles is not None else set(frappe.get_roles(user))
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
    """Apply education and employee contact scope checks on top of the core Contact gate."""
    roles = set(frappe.get_roles(user))
    op = (ptype or "read").lower()

    if _is_adminish(user):
        return True

    education_allowed = _education_contact_scope_matches(getattr(doc, "name", None), user, roles)
    if education_allowed is False:
        return False
    if education_allowed is True and op in READ_LIKE_CONTACT_PTYPES:
        employee_allowed = _employee_contact_scope_matches(getattr(doc, "name", None), user, roles)
        if employee_allowed is False:
            return False
        return True

    core_allowed = _core_has_permission(doc, ptype, user)
    if not core_allowed:
        return core_allowed

    scope_allowed = _employee_contact_scope_matches(getattr(doc, "name", None), user, roles)
    if scope_allowed is None:
        return core_allowed

    return bool(scope_allowed)


# ------------------------------------------------------------------ #
#  List / report filter
# ------------------------------------------------------------------ #
def contact_permission_query_conditions(user):
    """Restrict scoped Contact links while leaving unrelated contacts to core rules."""
    if not user or user == "Guest" or _is_adminish(user):
        return ""

    roles = set(frappe.get_roles(user))
    conditions = []
    employee_scope_sql = _employee_contact_scope_sql(user)
    if employee_scope_sql:
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

        if roles & ACADEMIC_CONTACT_ROLES:
            conditions.append(f"((NOT {employee_link_exists}) OR {scoped_employee_link_exists})")
        else:
            conditions.append(f"({scoped_employee_link_exists})")

    if roles & EDUCATION_CONTACT_ROLES:
        education_scope_sql = _education_contact_scope_sql(user)
        reverse_student_applicant_scope_sql = _reverse_student_applicant_contact_scope_sql(user)
        education_link_exists = """
            (
                EXISTS (
                    SELECT 1
                    FROM `tabStudent Applicant` reverse_contact_applicant
                    WHERE reverse_contact_applicant.applicant_contact = `tabContact`.name
                )
                OR EXISTS (
                SELECT 1
                FROM `tabDynamic Link` contact_education_link
                WHERE contact_education_link.parenttype = 'Contact'
                    AND contact_education_link.parent = `tabContact`.name
                    AND contact_education_link.link_doctype IN ('Student Applicant', 'Student', 'Guardian')
                )
            )
        """
        scoped_education_link_exists = f"""
            (
                {reverse_student_applicant_scope_sql}
                OR EXISTS (
                    SELECT 1
                    FROM `tabDynamic Link` scoped_education_link
                    WHERE scoped_education_link.parenttype = 'Contact'
                        AND scoped_education_link.parent = `tabContact`.name
                        AND scoped_education_link.link_doctype IN ('Student Applicant', 'Student', 'Guardian')
                        AND ({education_scope_sql})
                )
            )
        """
        conditions.append(f"((NOT {education_link_exists}) OR {scoped_education_link_exists})")

    return " AND ".join(f"({condition})" for condition in conditions) if conditions else ""
