from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import now_datetime, nowdate
from frappe.utils.password import update_password

from ifitwala_ed.tests.e2e import (
    E2E_LANGUAGE_CODE,
    E2E_LANGUAGE_NAME,
    E2E_ORGANIZATION_NAME,
    E2E_PACK_SCENARIOS,
    E2E_SCHOOL_NAME,
    E2E_USER_FIXTURES,
    scenario_names_for_pack,
)
from ifitwala_ed.tests.e2e.reset import clear_e2e_records


def _admission_settings_has_field(fieldname: str) -> bool:
    if not frappe.db.exists("DocType", "Admission Settings"):
        return False
    return bool(frappe.get_meta("Admission Settings").has_field(fieldname))


def _ensure_role(role_name: str) -> None:
    if frappe.db.exists("Role", role_name):
        return
    frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)


def _ensure_country_name() -> str:
    country_name = frappe.db.get_value("Country", {"name": "Thailand"}, "name")
    if country_name:
        return country_name

    first_country = frappe.get_all("Country", fields=["name"], limit=1)
    if first_country:
        return str(first_country[0].get("name") or "").strip()

    country = frappe.get_doc({"doctype": "Country", "country_name": "Thailand"}).insert(ignore_permissions=True)
    return country.name


def _ensure_language_code() -> str:
    if frappe.db.exists("Language Xtra", E2E_LANGUAGE_CODE):
        frappe.db.set_value("Language Xtra", E2E_LANGUAGE_CODE, "enabled", 1, update_modified=False)
        return E2E_LANGUAGE_CODE

    frappe.get_doc(
        {
            "doctype": "Language Xtra",
            "language_code": E2E_LANGUAGE_CODE,
            "language_name": E2E_LANGUAGE_NAME,
            "iso_name": E2E_LANGUAGE_NAME,
            "enabled": 1,
            "language_type": "Individual",
        }
    ).insert(ignore_permissions=True)
    return E2E_LANGUAGE_CODE


def _ensure_org_and_school() -> tuple[str, str]:
    organization_name = frappe.db.get_value(
        "Organization",
        {"organization_name": E2E_ORGANIZATION_NAME},
        "name",
    )
    if organization_name:
        school_name = frappe.db.get_value("School", {"school_name": E2E_SCHOOL_NAME}, "name")
        if school_name:
            return organization_name, school_name

    organization = frappe.get_doc(
        {
            "doctype": "Organization",
            "organization_name": E2E_ORGANIZATION_NAME,
            "abbr": "E2E",
        }
    ).insert(ignore_permissions=True)

    school = frappe.get_doc(
        {
            "doctype": "School",
            "school_name": E2E_SCHOOL_NAME,
            "abbr": "E2E-S",
            "organization": organization.name,
        }
    ).insert(ignore_permissions=True)
    return organization.name, school.name


def _set_password(email: str, password: str) -> None:
    update_password(email, password, logout_all_sessions=False)


def _create_user(
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    roles: list[str],
    user_type: str,
) -> str:
    for role in roles:
        _ensure_role(role)

    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "enabled": 1,
            "user_type": user_type,
            "roles": [{"role": role} for role in roles],
        }
    ).insert(ignore_permissions=True)
    _set_password(email, password)
    frappe.clear_cache(user=user.name)
    return user.name


def _create_employee_for_user(*, user_email: str, organization: str, school: str) -> str:
    employee = frappe.get_doc(
        {
            "doctype": "Employee",
            "employee_first_name": "Amina",
            "employee_last_name": "Staff",
            "employee_gender": "Prefer not to say",
            "employee_professional_email": user_email,
            "date_of_joining": nowdate(),
            "employment_status": "Active",
            "organization": organization,
            "school": school,
            "user_id": user_email,
        }
    ).insert(ignore_permissions=True)
    frappe.clear_cache(user=user_email)
    return employee.name


def _create_student(
    *,
    student_name: str,
    first_name: str,
    last_name: str,
    school: str,
    student_email: str,
    student_user_id: str | None = None,
) -> str:
    previous_in_import = bool(getattr(frappe.flags, "in_import", False))
    frappe.flags.in_import = True
    try:
        student = frappe.get_doc(
            {
                "doctype": "Student",
                "student_first_name": first_name,
                "student_last_name": last_name,
                "student_email": student_email,
                "student_user_id": student_user_id,
            }
        )
        student.allow_direct_creation = 1
        student.insert(ignore_permissions=True, set_name=student_name)
    finally:
        frappe.flags.in_import = previous_in_import

    if frappe.get_meta("Student").has_field("anchor_school"):
        student.db_set("anchor_school", school, update_modified=False)
    return student.name


def _create_guardian(*, user_email: str, first_name: str, last_name: str) -> str:
    guardian = frappe.get_doc(
        {
            "doctype": "Guardian",
            "guardian_first_name": first_name,
            "guardian_last_name": last_name,
            "guardian_email": user_email,
            "guardian_mobile_phone": "+14155550111",
            "user": user_email,
        }
    ).insert(ignore_permissions=True)
    return guardian.name


def _link_guardian_to_student(*, student_name: str, guardian_name: str) -> None:
    student = frappe.get_doc("Student", student_name)
    student.append(
        "guardians",
        {
            "guardian": guardian_name,
            "relation": "Mother",
            "can_consent": 1,
        },
    )
    student.save(ignore_permissions=True)


def _create_applicant(
    *,
    applicant_name: str,
    first_name: str,
    last_name: str,
    organization: str,
    school: str,
    applicant_user: str | None,
    application_status: str = "Invited",
    profile_complete: bool = False,
) -> str:
    country_name = _ensure_country_name()
    language_code = _ensure_language_code()

    applicant = frappe.get_doc(
        {
            "doctype": "Student Applicant",
            "first_name": first_name,
            "last_name": last_name,
            "organization": organization,
            "school": school,
            "application_status": "Draft",
        }
    )
    applicant.insert(ignore_permissions=True, set_name=applicant_name)
    applicant.db_set("application_status", application_status, update_modified=False)

    if applicant_user:
        applicant.db_set("applicant_user", applicant_user, update_modified=False)
        applicant.db_set("portal_account_email", applicant_user, update_modified=False)
        applicant.db_set("applicant_email", applicant_user, update_modified=False)

    if profile_complete:
        profile_updates = {
            "student_preferred_name": first_name,
            "student_date_of_birth": "2013-05-17",
            "student_gender": "Female",
            "student_mobile_number": "+14155550119",
            "student_first_language": language_code,
            "student_nationality": country_name,
            "residency_status": "Local Resident",
        }
        for fieldname, value in profile_updates.items():
            applicant.db_set(fieldname, value, update_modified=False)

    applicant.reload()
    return applicant.name


def _attach_family_guardian(*, applicant_name: str, guardian_name: str, user_email: str) -> None:
    applicant = frappe.get_doc("Student Applicant", applicant_name)
    applicant.append(
        "guardians",
        {
            "guardian": guardian_name,
            "user": user_email,
            "relationship": "Mother",
            "can_consent": 1,
            "is_primary": 1,
            "guardian_first_name": "Farah",
            "guardian_last_name": "Family",
            "guardian_email": user_email,
            "guardian_mobile_phone": "+14155550121",
        },
    )
    applicant.save(ignore_permissions=True)


def _create_ready_health_profile(*, applicant_name: str, declared_by: str) -> str:
    health = frappe.get_doc(
        {
            "doctype": "Applicant Health Profile",
            "student_applicant": applicant_name,
            "review_status": "Pending",
            "applicant_health_declared_complete": 1,
            "applicant_health_declared_by": declared_by,
            "applicant_health_declared_on": now_datetime(),
        }
    ).insert(ignore_permissions=True)
    return health.name


def _prepare_staff_scenario(organization: str, school: str) -> dict[str, Any]:
    meta = E2E_USER_FIXTURES["hub_staff_basic"]
    _create_user(
        email=meta["email"],
        password=meta["password"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        roles=["Employee", "Academic Staff", "Instructor"],
        user_type="System User",
    )
    _create_employee_for_user(user_email=meta["email"], organization=organization, school=school)
    return {"user": meta["email"], "route": "/hub/staff"}


def _prepare_guardian_scenario(organization: str, school: str) -> dict[str, Any]:
    del organization  # school scope is enough for the seeded guardian journeys.
    meta = E2E_USER_FIXTURES["hub_guardian_one_child"]
    _create_user(
        email=meta["email"],
        password=meta["password"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        roles=["Guardian"],
        user_type="Website User",
    )
    guardian_name = _create_guardian(
        user_email=meta["email"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
    )
    _create_student(
        student_name=meta["student_name"],
        first_name="Amina",
        last_name="Guardian",
        school=school,
        student_email="e2e-guardian-child@ifitwala.test",
    )
    _create_student(
        student_name=meta["out_of_scope_student_name"],
        first_name="Noah",
        last_name="Outside",
        school=school,
        student_email="e2e-guardian-other@ifitwala.test",
    )
    _link_guardian_to_student(student_name=meta["student_name"], guardian_name=guardian_name)
    return {
        "user": meta["email"],
        "student_name": meta["student_name"],
        "out_of_scope_student_name": meta["out_of_scope_student_name"],
    }


def _prepare_family_workspace_scenario(organization: str, school: str) -> dict[str, Any]:
    meta = E2E_USER_FIXTURES["admissions_family_workspace"]
    _create_user(
        email=meta["email"],
        password=meta["password"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        roles=["Admissions Family"],
        user_type="Website User",
    )
    guardian_name = _create_guardian(
        user_email=meta["email"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
    )

    _create_applicant(
        applicant_name=meta["first_applicant_name"],
        first_name="Amina",
        last_name="Family",
        organization=organization,
        school=school,
        applicant_user=None,
    )
    _create_applicant(
        applicant_name=meta["second_applicant_name"],
        first_name="Noah",
        last_name="Family",
        organization=organization,
        school=school,
        applicant_user=None,
    )
    _attach_family_guardian(
        applicant_name=meta["first_applicant_name"],
        guardian_name=guardian_name,
        user_email=meta["email"],
    )
    _attach_family_guardian(
        applicant_name=meta["second_applicant_name"],
        guardian_name=guardian_name,
        user_email=meta["email"],
    )
    return {"user": meta["email"]}


def _prepare_profile_edit_scenario(organization: str, school: str) -> dict[str, Any]:
    meta = E2E_USER_FIXTURES["admissions_profile_edit"]
    _create_user(
        email=meta["email"],
        password=meta["password"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        roles=["Admissions Applicant"],
        user_type="Website User",
    )
    _create_applicant(
        applicant_name=meta["applicant_name"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        organization=organization,
        school=school,
        applicant_user=meta["email"],
    )
    return {"user": meta["email"], "applicant_name": meta["applicant_name"]}


def _prepare_blocked_submit_scenario(organization: str, school: str) -> dict[str, Any]:
    meta = E2E_USER_FIXTURES["admissions_submit_blocked"]
    _create_user(
        email=meta["email"],
        password=meta["password"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        roles=["Admissions Applicant"],
        user_type="Website User",
    )
    _create_applicant(
        applicant_name=meta["applicant_name"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        organization=organization,
        school=school,
        applicant_user=meta["email"],
    )
    return {"user": meta["email"], "applicant_name": meta["applicant_name"]}


def _prepare_ready_submit_scenario(organization: str, school: str) -> dict[str, Any]:
    meta = E2E_USER_FIXTURES["admissions_submit_ready"]
    _create_user(
        email=meta["email"],
        password=meta["password"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        roles=["Admissions Applicant"],
        user_type="Website User",
    )
    _create_applicant(
        applicant_name=meta["applicant_name"],
        first_name=meta["first_name"],
        last_name=meta["last_name"],
        organization=organization,
        school=school,
        applicant_user=meta["email"],
        profile_complete=True,
    )
    _create_ready_health_profile(applicant_name=meta["applicant_name"], declared_by=meta["email"])
    return {"user": meta["email"], "applicant_name": meta["applicant_name"]}


SCENARIO_BUILDERS = {
    "hub_staff_basic": _prepare_staff_scenario,
    "hub_guardian_one_child": _prepare_guardian_scenario,
    "admissions_family_workspace": _prepare_family_workspace_scenario,
    "admissions_profile_edit": _prepare_profile_edit_scenario,
    "admissions_submit_blocked": _prepare_blocked_submit_scenario,
    "admissions_submit_ready": _prepare_ready_submit_scenario,
}


def prepare_pack(pack: str = "critical", reset_first: int = 1) -> dict[str, Any]:
    """Prepare deterministic browser-E2E data for the requested pack."""
    normalized_pack = str(pack or "critical").strip().lower() or "critical"
    scenario_names = scenario_names_for_pack(normalized_pack)

    if int(reset_first or 0):
        clear_e2e_records()

    frappe.set_user("Administrator")
    organization, school = _ensure_org_and_school()
    _ensure_language_code()
    _ensure_country_name()

    if _admission_settings_has_field("admissions_access_mode"):
        frappe.db.set_single_value(
            "Admission Settings",
            "admissions_access_mode",
            "Family Workspace",
        )

    prepared: dict[str, Any] = {}
    for scenario_name in scenario_names:
        builder = SCENARIO_BUILDERS.get(scenario_name)
        if not builder:
            raise ValueError(f"No E2E builder registered for scenario: {scenario_name}")
        prepared[scenario_name] = builder(organization, school)

    frappe.db.commit()
    return {
        "pack": normalized_pack,
        "available_packs": sorted(E2E_PACK_SCENARIOS.keys()),
        "organization": organization,
        "school": school,
        "scenarios": prepared,
    }


def prepare_all(pack: str = "critical", reset_first: int = 1) -> dict[str, Any]:
    return prepare_pack(pack=pack, reset_first=reset_first)
