# ifitwala_ed/governance/policy_utils.py

import frappe
from frappe import _

from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    get_guardian_names_for_user,
    user_can_access_student_applicant,
)
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)

SYSTEM_MANAGER_ROLE = "System Manager"
ORG_ADMIN_ROLE = "Organization Admin"
ACCOUNTS_MANAGER_ROLE = "Accounts Manager"
ADMISSION_MANAGER_ROLE = "Admission Manager"
HR_MANAGER_ROLE = "HR Manager"
SCHOOL_ADMIN_ROLE = "School Admin"
ACADEMIC_ADMIN_ROLE = "Academic Admin"
ACADEMIC_STAFF_ROLE = "Academic Staff"
GUARDIAN_ROLE = "Guardian"
STUDENT_ROLE = "Student"
MEDIA_CONSENT_POLICY_KEY = "media_consent"
ADMISSIONS_POLICY_MODE_CHILD = "Child Acknowledgement"
ADMISSIONS_POLICY_MODE_FAMILY = "Family Acknowledgement"
ADMISSIONS_POLICY_MODE_OPTIONAL = "Child Optional Consent"
POLICY_CATEGORIES = (
    "Safeguarding",
    "Privacy & Data Protection",
    "Admissions",
    "Academic",
    "Conduct & Behaviour",
    "Health & Safety",
    "Operations",
    "Handbooks",
    "Employment",
)
POLICY_APPLIES_TO_OPTIONS = ("Applicant", "Student", "Guardian", "Staff")
POLICY_ADMIN_ROLES = frozenset(
    {
        SYSTEM_MANAGER_ROLE,
        ORG_ADMIN_ROLE,
        ACCOUNTS_MANAGER_ROLE,
        ADMISSION_MANAGER_ROLE,
        ACADEMIC_ADMIN_ROLE,
        HR_MANAGER_ROLE,
    }
)


def _user_roles(user: str | None = None) -> set[str]:
    user = user or frappe.session.user
    return set(frappe.get_roles(user))


def is_system_manager(user: str | None = None) -> bool:
    return SYSTEM_MANAGER_ROLE in _user_roles(user)


def ensure_policy_admin(user: str | None = None) -> None:
    roles = _user_roles(user)
    if roles & POLICY_ADMIN_ROLES:
        return
    frappe.throw(_("You do not have permission to manage policies."), frappe.PermissionError)


def is_policy_admin(user: str | None = None) -> bool:
    roles = _user_roles(user)
    return bool(roles & POLICY_ADMIN_ROLES)


def is_academic_admin(user: str | None = None) -> bool:
    return ACADEMIC_ADMIN_ROLE in _user_roles(user)


def has_guardian_role(user: str | None = None) -> bool:
    return GUARDIAN_ROLE in _user_roles(user)


def has_student_role(user: str | None = None) -> bool:
    return STUDENT_ROLE in _user_roles(user)


def has_admissions_applicant_role(user: str | None = None) -> bool:
    return ADMISSIONS_APPLICANT_ROLE in _user_roles(user)


def has_admissions_family_role(user: str | None = None) -> bool:
    return ADMISSIONS_FAMILY_ROLE in _user_roles(user)


def has_staff_role(user: str | None = None) -> bool:
    roles = _user_roles(user)
    return bool(
        roles
        & {
            ACADEMIC_STAFF_ROLE,
            "Employee",
        }
    )


def ensure_policy_applies_to_column(*, throw: bool = False, caller: str | None = None) -> dict:
    if frappe.db.has_column("Institutional Policy", "applies_to"):
        return {"ok": True}

    meta = frappe.get_meta("Institutional Policy")
    if meta and meta.has_field("applies_to"):
        return {"ok": True}

    debug_payload = {
        "doctype": "Institutional Policy",
        "missing_column": "applies_to",
        "caller": caller,
        "site": getattr(frappe.local, "site", None),
    }
    frappe.log_error(message=frappe.as_json(debug_payload), title="Policy schema mismatch")

    message = _("Institutional Policy is missing the applies_to field. Run migrations or reload the DocType.")
    if throw:
        frappe.throw(message)
    return {"ok": False, "message": message}


def get_policy_applies_to_tokens(raw_value) -> tuple[str, ...]:
    if raw_value is None:
        return ()

    if isinstance(raw_value, (list, tuple, set)):
        source_values = raw_value
    else:
        source_values = str(raw_value).replace(",", "\n").splitlines()

    tokens: list[str] = []
    seen: set[str] = set()
    for value in source_values:
        token = (value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tuple(tokens)


def normalize_policy_applies_to(raw_value) -> str:
    return "\n".join(get_policy_applies_to_tokens(raw_value))


def policy_applies_to(raw_value, audience: str) -> bool:
    return (audience or "").strip() in set(get_policy_applies_to_tokens(raw_value))


def _has_policy_admissions_mode_column() -> bool:
    return frappe.db.has_column("Institutional Policy", "admissions_acknowledgement_mode")


def get_policy_admissions_acknowledgement_mode(
    *, policy_row: dict | None = None, policy_name: str | None = None
) -> str:
    raw_value = ""
    if policy_row and _has_policy_admissions_mode_column():
        raw_value = (policy_row.get("admissions_acknowledgement_mode") or "").strip()
    elif policy_name and _has_policy_admissions_mode_column():
        raw_value = (
            frappe.db.get_value("Institutional Policy", policy_name, "admissions_acknowledgement_mode") or ""
        ).strip()

    if raw_value == ADMISSIONS_POLICY_MODE_FAMILY:
        return ADMISSIONS_POLICY_MODE_FAMILY
    if raw_value == ADMISSIONS_POLICY_MODE_OPTIONAL:
        return ADMISSIONS_POLICY_MODE_OPTIONAL
    return ADMISSIONS_POLICY_MODE_CHILD


def _applicant_display_name(row: dict) -> str:
    parts = [
        (row.get("first_name") or "").strip(),
        (row.get("middle_name") or "").strip(),
        (row.get("last_name") or "").strip(),
    ]
    name = " ".join(part for part in parts if part).strip()
    return name or (row.get("name") or "").strip()


def _expected_family_signer_name(*, student_applicant: str, user: str) -> str:
    if not user_can_access_student_applicant(user=user, student_applicant=student_applicant):
        return (frappe.db.get_value("User", user, "full_name") or user or "").strip()

    guardian_names = get_guardian_names_for_user(user=user)
    if guardian_names:
        rows = frappe.get_all(
            "Student Applicant Guardian",
            filters={
                "parent": student_applicant,
                "parenttype": "Student Applicant",
                "parentfield": "guardians",
                "guardian": ["in", guardian_names],
                "can_consent": 1,
            },
            fields=["guardian", "guardian_full_name", "guardian_first_name", "guardian_last_name"],
            limit_page_length=5,
            order_by="is_primary desc, idx asc",
        )
        for row in rows:
            full_name = (row.get("guardian_full_name") or "").strip()
            if full_name:
                return full_name
            parts = [
                (row.get("guardian_first_name") or "").strip(),
                (row.get("guardian_last_name") or "").strip(),
            ]
            full_name = " ".join(part for part in parts if part).strip()
            if full_name:
                return full_name

    return (frappe.db.get_value("User", user, "full_name") or user or "").strip()


def get_expected_admissions_policy_signer_name(*, student_applicant: str, user: str) -> str:
    applicant_user = frappe.db.get_value("Student Applicant", student_applicant, "applicant_user")
    if (applicant_user or "").strip() == (user or "").strip():
        applicant_row = frappe.db.get_value(
            "Student Applicant",
            student_applicant,
            ["name", "first_name", "middle_name", "last_name"],
            as_dict=True,
        )
        if applicant_row:
            return _applicant_display_name(applicant_row)

    if has_admissions_family_role(user) and user_can_access_student_applicant(
        user=user, student_applicant=student_applicant
    ):
        return _expected_family_signer_name(student_applicant=student_applicant, user=user)

    applicant_row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        ["name", "first_name", "middle_name", "last_name"],
        as_dict=True,
    )
    if applicant_row:
        return _applicant_display_name(applicant_row)

    return (frappe.db.get_value("User", user, "full_name") or user or "").strip()


def _resolve_applicant_policy_candidates(
    *, student_applicant: str, organization: str | None = None, school: str | None = None
) -> list[dict]:
    if not organization or not school:
        row = frappe.db.get_value(
            "Student Applicant",
            student_applicant,
            ["organization", "school"],
            as_dict=True,
        )
        if not row:
            return []
        organization = organization or row.get("organization")
        school = school or row.get("school")

    if not organization:
        return []

    ancestor_orgs = get_organization_ancestors_including_self(organization)
    if not ancestor_orgs:
        return []
    school_ancestors = get_school_ancestors_including_self(school)

    schema_check = ensure_policy_applies_to_column(caller="_resolve_applicant_policy_candidates")
    if not schema_check.get("ok"):
        return []

    org_placeholders = ", ".join(["%s"] * len(ancestor_orgs))
    school_scope_sql = ""
    school_params: tuple[str, ...] = ()
    if school_ancestors:
        school_placeholders = ", ".join(["%s"] * len(school_ancestors))
        school_scope_sql = f" OR ip.school IN ({school_placeholders})"
        school_params = tuple(school_ancestors)

    mode_select_sql = (
        "ip.admissions_acknowledgement_mode AS admissions_acknowledgement_mode,"
        if _has_policy_admissions_mode_column()
        else f"'{ADMISSIONS_POLICY_MODE_CHILD}' AS admissions_acknowledgement_mode,"
    )

    rows = frappe.db.sql(
        f"""
        SELECT ip.name AS policy_name,
               ip.policy_key AS policy_key,
               ip.policy_title AS policy_title,
               ip.organization AS policy_organization,
               ip.school AS policy_school,
               {mode_select_sql}
               pv.name AS policy_version
          FROM `tabInstitutional Policy` ip
          JOIN `tabPolicy Version` pv
            ON pv.institutional_policy = ip.name
         WHERE ip.is_active = 1
           AND pv.is_active = 1
           AND ip.organization IN ({org_placeholders})
           AND (ip.school IS NULL OR ip.school = ''{school_scope_sql})
           AND ip.applies_to LIKE %s
        """,
        (*ancestor_orgs, *school_params, "%Applicant%"),
        as_dict=True,
    )

    return select_nearest_policy_rows_by_key(
        rows=rows,
        context_organization=organization,
        context_school=school,
        policy_key_field="policy_key",
        policy_organization_field="policy_organization",
        policy_school_field="policy_school",
    )


def get_applicant_policy_status(
    *,
    student_applicant: str,
    organization: str | None = None,
    school: str | None = None,
    user: str | None = None,
) -> dict:
    schema_check = ensure_policy_applies_to_column(caller="get_applicant_policy_status")
    if not schema_check.get("ok"):
        return {
            "ok": False,
            "missing": [],
            "required": [],
            "rows": [],
            "schema_error": schema_check.get("message"),
        }

    rows = _resolve_applicant_policy_candidates(
        student_applicant=student_applicant,
        organization=organization,
        school=school,
    )
    if not rows:
        return {"ok": True, "missing": [], "required": [], "rows": []}

    versions = [row["policy_version"] for row in rows if row.get("policy_version")]
    applicant_ack_rows = frappe.get_all(
        "Policy Acknowledgement",
        filters={
            "policy_version": ["in", versions],
            "acknowledged_for": "Applicant",
            "context_doctype": "Student Applicant",
            "context_name": student_applicant,
        },
        fields=["policy_version", "acknowledged_by", "acknowledged_at", "context_name"],
        order_by="acknowledged_at desc",
    )
    applicant_ack_map: dict[str, list[dict]] = {}
    for row_ack in applicant_ack_rows:
        version = (row_ack.get("policy_version") or "").strip()
        if not version:
            continue
        applicant_ack_map.setdefault(version, []).append(
            {
                "acknowledged_by": row_ack.get("acknowledged_by"),
                "acknowledged_at": row_ack.get("acknowledged_at"),
                "context_name": row_ack.get("context_name"),
            }
        )

    guardian_ack_map: dict[str, list[dict]] = {}
    guardian_rows = frappe.get_all(
        "Student Applicant Guardian",
        filters={
            "parent": student_applicant,
            "parenttype": "Student Applicant",
            "parentfield": "guardians",
            "can_consent": 1,
        },
        fields=["guardian"],
    )
    resolved_guardian_names = sorted(
        {(row.get("guardian") or "").strip() for row in guardian_rows if (row.get("guardian") or "").strip()}
    )
    if resolved_guardian_names:
        guardian_ack_rows = frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": ["in", versions],
                "acknowledged_for": "Guardian",
                "context_doctype": "Guardian",
                "context_name": ["in", resolved_guardian_names],
            },
            fields=["policy_version", "acknowledged_by", "acknowledged_at", "context_name"],
            order_by="acknowledged_at desc",
        )
        for row_ack in guardian_ack_rows:
            version = (row_ack.get("policy_version") or "").strip()
            if not version:
                continue
            guardian_ack_map.setdefault(version, []).append(
                {
                    "acknowledged_by": row_ack.get("acknowledged_by"),
                    "acknowledged_at": row_ack.get("acknowledged_at"),
                    "context_name": row_ack.get("context_name"),
                }
            )

    required: list[str] = []
    missing: list[str] = []
    policy_rows: list[dict] = []
    for row_policy in rows:
        version = (row_policy.get("policy_version") or "").strip()
        if not version:
            continue
        label = row_policy.get("policy_key") or row_policy.get("policy_title") or row_policy.get("policy_name")
        mode = get_policy_admissions_acknowledgement_mode(policy_row=row_policy)
        signers = (
            guardian_ack_map.get(version, [])
            if mode == ADMISSIONS_POLICY_MODE_FAMILY
            else applicant_ack_map.get(version, [])
        )
        is_required = mode != ADMISSIONS_POLICY_MODE_OPTIONAL
        if is_required:
            required.append(label)
            if not signers:
                missing.append(label)
        primary_signer = signers[0] if signers else {}
        policy_rows.append(
            {
                "policy_name": row_policy.get("policy_name"),
                "policy_key": row_policy.get("policy_key"),
                "policy_title": row_policy.get("policy_title"),
                "policy_version": version,
                "label": label,
                "is_required": is_required,
                "admissions_acknowledgement_mode": mode,
                "ack_context_doctype": "Guardian" if mode == ADMISSIONS_POLICY_MODE_FAMILY else "Student Applicant",
                "is_acknowledged": bool(signers),
                "acknowledged_by": primary_signer.get("acknowledged_by"),
                "acknowledged_at": primary_signer.get("acknowledged_at"),
                "signers": signers,
                "expected_signature_name": (
                    get_expected_admissions_policy_signer_name(student_applicant=student_applicant, user=user)
                    if user
                    else ""
                ),
            }
        )

    return {"ok": not missing, "missing": missing, "required": required, "rows": policy_rows}


def has_applicant_policy_acknowledgement(
    *,
    policy_key: str,
    student_applicant: str,
    organization: str | None = None,
    school: str | None = None,
) -> bool:
    if not policy_key or not student_applicant:
        return False

    status = get_applicant_policy_status(
        student_applicant=student_applicant,
        organization=organization,
        school=school,
    )
    for row in status.get("rows") or []:
        if (row.get("policy_key") or "").strip() == policy_key:
            return bool(row.get("is_acknowledged"))
    return False
