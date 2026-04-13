from __future__ import annotations

import frappe

from ifitwala_ed.tests.e2e import E2E_ORGANIZATION_NAME, E2E_SCHOOL_NAME, E2E_USER_FIXTURES


def clear_e2e_records() -> dict[str, int]:
    """Delete known browser-E2E records from the current site."""
    frappe.set_user("Administrator")

    user_emails = sorted({meta["email"] for meta in E2E_USER_FIXTURES.values()})
    student_names = sorted(
        {meta["student_name"] for meta in E2E_USER_FIXTURES.values() if meta.get("student_name")}
        | {
            meta["out_of_scope_student_name"]
            for meta in E2E_USER_FIXTURES.values()
            if meta.get("out_of_scope_student_name")
        }
    )
    applicant_names = sorted(
        {meta["applicant_name"] for meta in E2E_USER_FIXTURES.values() if meta.get("applicant_name")}
        | {meta["first_applicant_name"] for meta in E2E_USER_FIXTURES.values() if meta.get("first_applicant_name")}
        | {meta["second_applicant_name"] for meta in E2E_USER_FIXTURES.values() if meta.get("second_applicant_name")}
    )

    counts = {
        "applicant_health_profiles": 0,
        "student_applicants": 0,
        "student_guardians": 0,
        "guardian_students": 0,
        "guardians": 0,
        "students": 0,
        "employees": 0,
        "users": 0,
        "schools": 0,
        "organizations": 0,
    }

    if applicant_names:
        health_names = (
            frappe.get_all(
                "Applicant Health Profile",
                filters={"student_applicant": ["in", applicant_names]},
                pluck="name",
            )
            or []
        )
        for name in health_names:
            frappe.delete_doc("Applicant Health Profile", name, force=1, ignore_permissions=True)
            counts["applicant_health_profiles"] += 1

        for applicant_name in applicant_names:
            if frappe.db.exists("Student Applicant", applicant_name):
                frappe.delete_doc("Student Applicant", applicant_name, force=1, ignore_permissions=True)
                counts["student_applicants"] += 1

    if student_names:
        counts["student_guardians"] = frappe.db.count(
            "Student Guardian",
            {"parent": ["in", student_names], "parenttype": "Student"},
        )
        frappe.db.delete(
            "Student Guardian",
            {"parent": ["in", student_names], "parenttype": "Student"},
        )

        counts["guardian_students"] = frappe.db.count(
            "Guardian Student",
            {"student": ["in", student_names], "parenttype": "Guardian"},
        )
        frappe.db.delete(
            "Guardian Student",
            {"student": ["in", student_names], "parenttype": "Guardian"},
        )

    guardian_names = (
        frappe.get_all(
            "Guardian",
            filters={"user": ["in", user_emails]},
            pluck="name",
        )
        or []
    )
    for guardian_name in guardian_names:
        if frappe.db.exists("Guardian", guardian_name):
            frappe.delete_doc("Guardian", guardian_name, force=1, ignore_permissions=True)
            counts["guardians"] += 1

    for student_name in student_names:
        if frappe.db.exists("Student", student_name):
            frappe.delete_doc("Student", student_name, force=1, ignore_permissions=True)
            counts["students"] += 1

    employee_names = (
        frappe.get_all(
            "Employee",
            filters={"user_id": ["in", user_emails]},
            pluck="name",
        )
        or []
    )
    for employee_name in employee_names:
        if frappe.db.exists("Employee", employee_name):
            frappe.delete_doc("Employee", employee_name, force=1, ignore_permissions=True)
            counts["employees"] += 1

    for email in user_emails:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=1, ignore_permissions=True)
            counts["users"] += 1

    school_name = frappe.db.get_value("School", {"school_name": E2E_SCHOOL_NAME}, "name")
    if school_name and frappe.db.exists("School", school_name):
        frappe.delete_doc("School", school_name, force=1, ignore_permissions=True)
        counts["schools"] += 1

    organization_name = frappe.db.get_value(
        "Organization",
        {"organization_name": E2E_ORGANIZATION_NAME},
        "name",
    )
    if organization_name and frappe.db.exists("Organization", organization_name):
        frappe.delete_doc("Organization", organization_name, force=1, ignore_permissions=True)
        counts["organizations"] += 1

    frappe.db.commit()
    return counts
