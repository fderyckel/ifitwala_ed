from __future__ import annotations

E2E_PASSWORD = "Ifitwala-E2E-2026!"
E2E_ORGANIZATION_NAME = "E2E Browser Testing Org"
E2E_SCHOOL_NAME = "E2E Browser Testing School"
E2E_LANGUAGE_CODE = "e2e_en"
E2E_LANGUAGE_NAME = "English"

E2E_USER_FIXTURES = {
    "hub_staff_basic": {
        "email": "e2e-staff@ifitwala.test",
        "password": E2E_PASSWORD,
        "first_name": "Amina",
        "last_name": "Staff",
    },
    "hub_guardian_one_child": {
        "email": "e2e-guardian@ifitwala.test",
        "password": E2E_PASSWORD,
        "first_name": "Grace",
        "last_name": "Guardian",
        "student_name": "E2E-STU-GUARDIAN-1",
        "student_label": "Amina Guardian",
        "out_of_scope_student_name": "E2E-STU-GUARDIAN-OTHER",
    },
    "admissions_family_workspace": {
        "email": "e2e-family@ifitwala.test",
        "password": E2E_PASSWORD,
        "first_name": "Farah",
        "last_name": "Family",
        "first_applicant_name": "E2E-APPL-FAMILY-1",
        "first_applicant_label": "Amina Family",
        "second_applicant_name": "E2E-APPL-FAMILY-2",
        "second_applicant_label": "Noah Family",
    },
    "admissions_profile_edit": {
        "email": "e2e-applicant-profile@ifitwala.test",
        "password": E2E_PASSWORD,
        "first_name": "Amina",
        "last_name": "Profile",
        "applicant_name": "E2E-APPL-PROFILE",
    },
    "admissions_submit_blocked": {
        "email": "e2e-applicant-blocked@ifitwala.test",
        "password": E2E_PASSWORD,
        "first_name": "Binta",
        "last_name": "Blocked",
        "applicant_name": "E2E-APPL-BLOCKED",
    },
    "admissions_submit_ready": {
        "email": "e2e-applicant-ready@ifitwala.test",
        "password": E2E_PASSWORD,
        "first_name": "Rania",
        "last_name": "Ready",
        "applicant_name": "E2E-APPL-READY",
    },
}

E2E_PACK_SCENARIOS = {
    "smoke": (
        "hub_staff_basic",
        "hub_guardian_one_child",
        "admissions_profile_edit",
        "admissions_submit_blocked",
    ),
    "critical": tuple(E2E_USER_FIXTURES.keys()),
}


def scenario_names_for_pack(pack: str) -> tuple[str, ...]:
    normalized = str(pack or "critical").strip().lower() or "critical"
    if normalized not in E2E_PACK_SCENARIOS:
        raise ValueError(f"Unsupported E2E pack: {pack}")
    return tuple(E2E_PACK_SCENARIOS[normalized])
