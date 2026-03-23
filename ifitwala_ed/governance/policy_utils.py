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
POLICY_AUDIENCE_DOCTYPE = "Policy Audience"
POLICY_APPLIES_TO_CHILD_DOCTYPE = "Institutional Policy Audience"
POLICY_APPLIES_TO_LINK_FIELD = "policy_audience"
POLICY_APPLIES_TO_PARENTFIELD = "applies_to"
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


def institutional_policy_db_has_column(column_name: str) -> bool:
    column = (column_name or "").strip()
    if not column:
        return False

    cache_key = f"institutional_policy_db_column::{column}"
    cached = frappe.cache().get_value(cache_key)
    if cached is not None:
        return bool(cached)

    exists = False
    try:
        exists = bool(
            frappe.db.sql(
                """
                SELECT 1
                  FROM information_schema.columns
                 WHERE table_schema = DATABASE()
                   AND table_name = 'tabInstitutional Policy'
                   AND column_name = %s
                 LIMIT 1
                """,
                (column,),
            )
        )
    except Exception:
        exists = False

    frappe.cache().set_value(cache_key, 1 if exists else 0, expires_in_sec=300)
    return exists


def ensure_policy_audience_records() -> None:
    if not frappe.db.table_exists(POLICY_AUDIENCE_DOCTYPE):
        return

    for audience in POLICY_APPLIES_TO_OPTIONS:
        if frappe.db.exists(POLICY_AUDIENCE_DOCTYPE, audience):
            continue
        frappe.get_doc(
            {
                "doctype": POLICY_AUDIENCE_DOCTYPE,
                "policy_audience_name": audience,
            }
        ).insert(ignore_permissions=True)


def ensure_policy_applies_to_storage(*, throw: bool = False, caller: str | None = None) -> dict:
    meta = frappe.get_meta("Institutional Policy")
    applies_to_field = meta.get_field(POLICY_APPLIES_TO_PARENTFIELD) if meta else None
    child_table_ready = bool(
        frappe.db.table_exists(POLICY_APPLIES_TO_CHILD_DOCTYPE)
        and frappe.db.has_column(POLICY_APPLIES_TO_CHILD_DOCTYPE, POLICY_APPLIES_TO_LINK_FIELD)
        and frappe.db.table_exists(POLICY_AUDIENCE_DOCTYPE)
        and applies_to_field
        and applies_to_field.fieldtype == "Table MultiSelect"
        and applies_to_field.options == POLICY_APPLIES_TO_CHILD_DOCTYPE
    )
    if child_table_ready:
        return {"ok": True}

    debug_payload = {
        "doctype": "Institutional Policy",
        "caller": caller,
        "missing_table": POLICY_APPLIES_TO_CHILD_DOCTYPE,
        "missing_link_doctype": POLICY_AUDIENCE_DOCTYPE,
        "missing_link_field": POLICY_APPLIES_TO_LINK_FIELD,
        "site": getattr(frappe.local, "site", None),
        "meta_has_field": bool(meta and meta.has_field("applies_to")),
        "meta_fieldtype": getattr(applies_to_field, "fieldtype", None),
        "meta_options": getattr(applies_to_field, "options", None),
        "child_table_exists": frappe.db.table_exists(POLICY_APPLIES_TO_CHILD_DOCTYPE),
        "child_link_field_exists": frappe.db.has_column(POLICY_APPLIES_TO_CHILD_DOCTYPE, POLICY_APPLIES_TO_LINK_FIELD)
        if frappe.db.table_exists(POLICY_APPLIES_TO_CHILD_DOCTYPE)
        else False,
        "link_doctype_exists": frappe.db.table_exists(POLICY_AUDIENCE_DOCTYPE),
    }
    try:
        frappe.log_error(message=frappe.as_json(debug_payload), title="Policy schema mismatch")
    except Exception:
        pass

    message = _("Institutional Policy applies_to storage is not configured. Run migrations or reload the DocTypes.")
    if throw:
        frappe.throw(message)
    return {"ok": False, "message": message}


def ensure_policy_applies_to_column(*, throw: bool = False, caller: str | None = None) -> dict:
    return ensure_policy_applies_to_storage(throw=throw, caller=caller)


def _extract_policy_audience_token(value) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        if isinstance(value.get("applies_to_tokens"), (list, tuple, set)):
            tokens = get_policy_applies_to_tokens(value.get("applies_to_tokens"))
            return tokens[0] if tokens else ""
        for key in (POLICY_APPLIES_TO_LINK_FIELD, "applies_to", "audience"):
            token = (value.get(key) or "").strip()
            if token:
                return token
        return ""
    if hasattr(value, POLICY_APPLIES_TO_LINK_FIELD):
        return (getattr(value, POLICY_APPLIES_TO_LINK_FIELD, None) or "").strip()
    return str(value or "").strip()


def get_policy_applies_to_tokens(raw_value) -> tuple[str, ...]:
    if raw_value is None:
        return ()

    if isinstance(raw_value, (list, tuple, set)):
        source_values = [_extract_policy_audience_token(value) for value in raw_value]
    elif isinstance(raw_value, dict) and isinstance(raw_value.get("applies_to_tokens"), (list, tuple, set)):
        source_values = list(raw_value.get("applies_to_tokens") or [])
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


def get_policy_applies_to_token_map(policy_names: list[str] | tuple[str, ...] | set[str]) -> dict[str, tuple[str, ...]]:
    names = sorted({(name or "").strip() for name in policy_names if (name or "").strip()})
    if not names or not frappe.db.table_exists(POLICY_APPLIES_TO_CHILD_DOCTYPE):
        return {}

    rows = frappe.get_all(
        POLICY_APPLIES_TO_CHILD_DOCTYPE,
        filters={
            "parent": ["in", names],
            "parenttype": "Institutional Policy",
            "parentfield": POLICY_APPLIES_TO_PARENTFIELD,
        },
        fields=["parent", POLICY_APPLIES_TO_LINK_FIELD, "idx"],
        order_by="parent asc, idx asc",
        limit=0,
    )
    out: dict[str, list[str]] = {}
    for row in rows:
        parent = (row.get("parent") or "").strip()
        token = (row.get(POLICY_APPLIES_TO_LINK_FIELD) or "").strip()
        if not parent or not token:
            continue
        out.setdefault(parent, []).append(token)
    return {name: get_policy_applies_to_tokens(values) for name, values in out.items()}


def get_policy_applies_to_tokens_for_policy(policy_name: str | None) -> tuple[str, ...]:
    policy_name = (policy_name or "").strip()
    if not policy_name:
        return ()
    return get_policy_applies_to_token_map([policy_name]).get(policy_name, ())


def policy_applies_to_filter_sql(
    *, policy_alias: str = "ip", audience_placeholder: str = "%s", child_alias: str = "ipa"
) -> str:
    return f"""
        EXISTS (
            SELECT 1
            FROM `tab{POLICY_APPLIES_TO_CHILD_DOCTYPE}` {child_alias}
            WHERE {child_alias}.parent = {policy_alias}.name
              AND {child_alias}.parenttype = 'Institutional Policy'
              AND {child_alias}.parentfield = '{POLICY_APPLIES_TO_PARENTFIELD}'
              AND {child_alias}.{POLICY_APPLIES_TO_LINK_FIELD} = {audience_placeholder}
        )
    """.strip()


def policy_applies_to(raw_value, audience: str) -> bool:
    return (audience or "").strip() in set(get_policy_applies_to_tokens(raw_value))


def _has_policy_admissions_mode_column() -> bool:
    return institutional_policy_db_has_column("admissions_acknowledgement_mode")


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
            limit=5,
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

    schema_check = ensure_policy_applies_to_storage(caller="_resolve_applicant_policy_candidates")
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
           AND {policy_applies_to_filter_sql(policy_alias="ip", audience_placeholder="%s")}
        """,
        (*ancestor_orgs, *school_params, "Applicant"),
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
    schema_check = ensure_policy_applies_to_storage(caller="get_applicant_policy_status")
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
