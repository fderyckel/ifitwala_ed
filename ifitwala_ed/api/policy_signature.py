# ifitwala_ed/api/policy_signature.py

from __future__ import annotations

from html import escape
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import get_datetime, getdate, now_datetime

from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    is_policy_organization_applicable_to_context,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import (
    GUARDIAN_ACK_MODE_CHILD,
    get_policy_applies_to_token_map,
    get_policy_applies_to_tokens_for_policy,
    normalize_guardian_acknowledgement_mode,
    policy_applies_to,
)
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org
from ifitwala_ed.utilities.html_sanitizer import sanitize_html
from ifitwala_ed.utilities.school_tree import get_descendant_schools

POLICY_SIGNATURE_MANAGER_ROLES = frozenset(
    {
        "System Manager",
        "Administrator",
        "Organization Admin",
        "HR Manager",
        "HR User",
        "Academic Admin",
    }
)
POLICY_SIGNATURE_ANALYTICS_ROLES = POLICY_SIGNATURE_MANAGER_ROLES
POLICY_LIBRARY_STAFF_ROLES = frozenset({"Academic Staff", "Employee"})
POLICY_LIBRARY_ROLES = frozenset(set(POLICY_SIGNATURE_ANALYTICS_ROLES) | set(POLICY_LIBRARY_STAFF_ROLES))
POLICY_SIGNATURE_MARKER = "[policy_signature]"
POLICY_SIGNATURE_EMPLOYEE_KEY = "employee="
STAFF_POLICY_STATUS_SIGNED = "signed"
STAFF_POLICY_STATUS_PENDING = "pending"
STAFF_POLICY_STATUS_NEW_VERSION = "new_version"
STAFF_POLICY_STATUS_INFO = "informational"
POLICY_SIGNATURE_AUDIENCE_ORDER = ("Staff", "Guardian", "Student")
POLICY_SIGNATURE_AUDIENCE_LABELS = {
    "Staff": "Staff",
    "Guardian": "Guardians",
    "Student": "Students",
}
POLICY_SIGNATURE_AUDIENCE_WORKFLOW_DESCRIPTIONS = {
    "Staff": "Staff campaigns create internal signature tasks for eligible employees.",
    "Guardian": "Family campaigns publish guardian portal alerts; guardians acknowledge the policy in Guardian Portal.",
    "Student": "Family campaigns publish student portal alerts; students acknowledge the policy in Student Hub.",
}
POLICY_FAMILY_CAMPAIGN_AUDIENCE_ORDER = ("Guardian", "Student")
POLICY_SIGNATURE_REGISTER_STATUS_ALL = "all"
POLICY_SIGNATURE_REGISTER_STATUS_PENDING = "pending"
POLICY_SIGNATURE_REGISTER_STATUS_SIGNED = "signed"
POLICY_LIBRARY_AUDIENCE_ALL = "All"
POLICY_LIBRARY_AUDIENCES = (POLICY_LIBRARY_AUDIENCE_ALL, *POLICY_SIGNATURE_AUDIENCE_ORDER)
MULTIPLE_ORGANIZATIONS_LABEL = "Multiple organizations"
MULTIPLE_SCHOOLS_LABEL = "Multiple schools"


def _policy_applies_to_staff(applies_to: str | None) -> bool:
    return policy_applies_to(applies_to, "Staff")


def _supported_policy_signature_audiences(applies_to_tokens) -> list[str]:
    tokens = set(applies_to_tokens or [])
    return [audience for audience in POLICY_SIGNATURE_AUDIENCE_ORDER if audience in tokens]


def _supported_family_policy_campaign_audiences(applies_to_tokens) -> list[str]:
    tokens = set(applies_to_tokens or [])
    return [audience for audience in POLICY_FAMILY_CAMPAIGN_AUDIENCE_ORDER if audience in tokens]


def _normalize_policy_library_audience(*, value: str | None, can_manage_audiences: bool) -> str:
    normalized_map = {audience.lower(): audience for audience in POLICY_LIBRARY_AUDIENCES}
    normalized = normalized_map.get((value or "").strip().lower())
    if normalized == POLICY_LIBRARY_AUDIENCE_ALL and can_manage_audiences:
        return POLICY_LIBRARY_AUDIENCE_ALL
    if normalized in POLICY_SIGNATURE_AUDIENCE_ORDER:
        if can_manage_audiences or normalized == "Staff":
            return normalized
    return POLICY_LIBRARY_AUDIENCE_ALL if can_manage_audiences else "Staff"


def _require_roles(allowed_roles: set[str] | frozenset[str]) -> tuple[str, set[str]]:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & set(allowed_roles):
        return user, roles

    frappe.throw(_("You do not have permission for this policy signature action."), frappe.PermissionError)
    return user, roles


def _manager_scope_organizations(*, user: str, roles: set[str]) -> list[str]:
    if {"System Manager", "Administrator"} & roles:
        return sorted(frappe.get_all("Organization", pluck="name"))

    if "Organization Admin" in roles:
        return sorted(frappe.get_all("Organization", pluck="name"))

    base_org = (get_user_base_org(user) or "").strip()
    if not base_org:
        frappe.throw(_("No active Employee organization is linked to your account."), frappe.PermissionError)

    descendants = get_descendant_organizations(base_org)
    return sorted({(org or "").strip() for org in descendants if (org or "").strip()})


def _ensure_organization_in_scope(organization: str, scoped_orgs: list[str]) -> None:
    if not organization:
        frappe.throw(_("Organization is required."))
    if organization not in set(scoped_orgs):
        frappe.throw(_("Selected Organization is outside your policy signature scope."), frappe.PermissionError)


def _ensure_school_in_scope(*, school: str | None, organization_scope: list[str]) -> None:
    school = (school or "").strip()
    if not school:
        return
    school_org = frappe.db.get_value("School", school, "organization")
    if not school_org or school_org not in set(organization_scope):
        frappe.throw(_("Selected School is outside the selected Organization scope."), frappe.PermissionError)


def _policy_library_scope_organizations(*, user: str, roles: set[str], employee_row: dict | None) -> list[str]:
    if roles & set(POLICY_SIGNATURE_ANALYTICS_ROLES):
        return _manager_scope_organizations(user=user, roles=roles)

    base_org = ((employee_row or {}).get("organization") or "").strip()
    if not base_org:
        frappe.throw(_("No active Employee organization is linked to your account."), frappe.PermissionError)
    return [base_org]


def _school_options_for_scope(organization_scope: list[str]) -> list[str]:
    scoped_orgs = sorted({(org or "").strip() for org in organization_scope if (org or "").strip()})
    if not scoped_orgs:
        return []

    rows = frappe.get_all(
        "School",
        filters={"organization": ["in", tuple(scoped_orgs)]},
        pluck="name",
    )
    return sorted({(row or "").strip() for row in rows if (row or "").strip()})


def _school_scope_names(*, organization_scope: list[str], school: str | None) -> list[str]:
    school = (school or "").strip()
    if school:
        return sorted(
            {(name or "").strip() for name in (get_descendant_schools(school) or [school]) if (name or "").strip()}
        )
    return _school_options_for_scope(organization_scope)


def _employee_group_options_for_scope(
    *,
    organization_scope: list[str],
    school: str | None,
) -> list[str]:
    scoped_orgs = sorted({(org or "").strip() for org in organization_scope if (org or "").strip()})
    if not scoped_orgs:
        return []

    where_parts = [
        "employment_status = 'Active'",
        "ifnull(employee_group, '') != ''",
        "organization IN %(organizations)s",
    ]
    params: dict = {"organizations": tuple(scoped_orgs)}

    school = (school or "").strip()
    if school:
        school_scope = get_descendant_schools(school) or [school]
        if school_scope:
            where_parts.append("school IN %(schools)s")
            params["schools"] = tuple(school_scope)

    where_sql = " AND ".join(where_parts)
    rows = frappe.db.sql(
        f"""
        SELECT DISTINCT employee_group
        FROM `tabEmployee`
        WHERE {where_sql}
        ORDER BY employee_group ASC
        """,
        params,
        as_dict=True,
    )
    return sorted(
        {(row.get("employee_group") or "").strip() for row in rows if (row.get("employee_group") or "").strip()}
    )


def _policy_options_for_scope(
    *,
    organization: str | None,
    organization_scope: list[str],
    school: str | None,
) -> list[dict]:
    organization = (organization or "").strip() or None
    school = (school or "").strip() or None

    scoped_orgs = (
        get_organization_ancestors_including_self(organization)
        if organization
        else sorted({(org or "").strip() for org in organization_scope if (org or "").strip()})
    )
    if not scoped_orgs:
        return []

    params: dict = {"policy_organizations": tuple(scoped_orgs)}
    school_scope_clause = ""
    if organization:
        school_scope_clause = " AND (ifnull(ip.school, '') = '')"
        if school:
            school_ancestors = get_school_ancestors_including_self(school)
            if school_ancestors:
                params["school_ancestors"] = tuple(school_ancestors)
                school_scope_clause = " AND (ifnull(ip.school, '') = '' OR ip.school IN %(school_ancestors)s)"

    rows = frappe.db.sql(
        f"""
        SELECT
            pv.name AS policy_version,
            pv.version_label,
            pv.guardian_acknowledgement_mode,
            pv.effective_from,
            pv.effective_to,
            ip.name AS institutional_policy,
            ip.policy_title,
            ip.policy_key,
            ip.organization AS policy_organization,
            ip.school AS policy_school
        FROM `tabPolicy Version` pv
        JOIN `tabInstitutional Policy` ip
          ON ip.name = pv.institutional_policy
        WHERE pv.is_active = 1
          AND ip.is_active = 1
          AND ip.organization IN %(policy_organizations)s
          {school_scope_clause}
        ORDER BY ip.policy_title ASC, pv.modified DESC
        """,
        params,
        as_dict=True,
    )

    if organization:
        rows = select_nearest_policy_rows_by_key(
            rows=rows,
            context_organization=organization,
            context_school=school,
            policy_key_field="policy_key",
            policy_organization_field="policy_organization",
            policy_school_field="policy_school",
        )

    token_map = get_policy_applies_to_token_map(
        [row.get("institutional_policy") for row in rows if row.get("institutional_policy")]
    )

    options = []
    for row in rows:
        row["guardian_acknowledgement_mode"] = normalize_guardian_acknowledgement_mode(
            row.get("guardian_acknowledgement_mode")
        )
        tokens = list(token_map.get((row.get("institutional_policy") or "").strip(), ()))
        if not _supported_policy_signature_audiences(tokens):
            continue
        row["applies_to_tokens"] = tokens
        options.append(row)

    return options


def _family_policy_options_for_scope(
    *,
    organization: str | None,
    organization_scope: list[str],
    school: str | None,
) -> list[dict]:
    rows = _policy_options_for_scope(
        organization=organization,
        organization_scope=organization_scope,
        school=school,
    )
    return [row for row in rows if _supported_family_policy_campaign_audiences(row.get("applies_to_tokens"))]


def _active_policy_rows_for_context(
    *,
    context_organization: str,
    context_school: str | None,
    audience: str | None = None,
) -> list[dict]:
    context_organization = (context_organization or "").strip()
    context_school = (context_school or "").strip()
    audience = (audience or "").strip() or None
    if not context_organization:
        return []

    ancestor_orgs = get_organization_ancestors_including_self(context_organization)
    if not ancestor_orgs:
        return []

    params: dict = {"policy_organizations": tuple(ancestor_orgs)}

    school_scope_clause = ""
    if context_school:
        school_ancestors = get_school_ancestors_including_self(context_school)
        if school_ancestors:
            params["school_ancestors"] = tuple(school_ancestors)
            school_scope_clause = " AND (ifnull(ip.school, '') = '' OR ip.school IN %(school_ancestors)s)"

    rows = frappe.db.sql(
        f"""
        SELECT
            pv.name AS policy_version,
            pv.version_label,
            pv.based_on_version,
            pv.change_summary,
            pv.guardian_acknowledgement_mode,
            pv.effective_from,
            pv.effective_to,
            pv.approved_on,
            ip.name AS institutional_policy,
            ip.policy_key,
            ip.policy_title,
            ip.policy_category,
            ip.description,
            ip.organization AS policy_organization,
            ip.school AS policy_school
        FROM `tabPolicy Version` pv
        JOIN `tabInstitutional Policy` ip
          ON ip.name = pv.institutional_policy
        WHERE pv.is_active = 1
          AND ip.is_active = 1
          AND ip.organization IN %(policy_organizations)s
          {school_scope_clause}
        ORDER BY ip.policy_title ASC, pv.modified DESC
        """,
        params,
        as_dict=True,
    )

    rows = select_nearest_policy_rows_by_key(
        rows=rows,
        context_organization=context_organization,
        context_school=context_school or None,
        policy_key_field="policy_key",
        policy_organization_field="policy_organization",
        policy_school_field="policy_school",
    )

    token_map = get_policy_applies_to_token_map(
        [row.get("institutional_policy") for row in rows if row.get("institutional_policy")]
    )

    out = []
    for row in rows:
        row["guardian_acknowledgement_mode"] = normalize_guardian_acknowledgement_mode(
            row.get("guardian_acknowledgement_mode")
        )
        tokens = _supported_policy_signature_audiences(
            token_map.get((row.get("institutional_policy") or "").strip(), ())
        )
        if not tokens:
            continue
        if audience and audience not in tokens:
            continue
        row["applies_to_tokens"] = list(tokens)
        out.append(row)
    return out


def get_active_employee_for_user(user: str | None = None) -> dict | None:
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    return frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": "Active"},
        [
            "name",
            "employee_full_name",
            "organization",
            "school",
            "employee_group",
            "user_id",
        ],
        as_dict=True,
    )


def get_policy_version_history_rows(institutional_policy: str | None) -> list[dict]:
    institutional_policy = (institutional_policy or "").strip()
    if not institutional_policy:
        return []

    rows = frappe.get_all(
        "Policy Version",
        filters={"institutional_policy": institutional_policy},
        fields=[
            "name",
            "version_label",
            "based_on_version",
            "effective_from",
            "effective_to",
            "approved_on",
            "is_active",
            "creation",
            "modified",
        ],
        order_by="creation desc, modified desc",
        limit=0,
    )
    out = []
    for row in rows:
        out.append(
            {
                "policy_version": (row.get("name") or "").strip(),
                "version_label": (row.get("version_label") or "").strip() or None,
                "based_on_version": (row.get("based_on_version") or "").strip() or None,
                "effective_from": str(row.get("effective_from")) if row.get("effective_from") else None,
                "effective_to": str(row.get("effective_to")) if row.get("effective_to") else None,
                "approved_on": str(row.get("approved_on")) if row.get("approved_on") else None,
                "is_active": bool(row.get("is_active")),
            }
        )
    return out


def _build_policy_library_counts(rows: list[dict]) -> dict:
    counts = {
        "total_policies": len(rows),
        "staff_policies": 0,
        "guardian_policies": 0,
        "student_policies": 0,
        "organization_scoped": 0,
        "school_scoped": 0,
        "multi_audience": 0,
        "signature_required": 0,
        "informational": 0,
        "signed": 0,
        "pending": 0,
        "new_version": 0,
    }

    for row in rows:
        tokens = set(row.get("applies_to_tokens") or [])
        if "Staff" in tokens:
            counts["staff_policies"] += 1
        if "Guardian" in tokens:
            counts["guardian_policies"] += 1
        if "Student" in tokens:
            counts["student_policies"] += 1
        if len(tokens) > 1:
            counts["multi_audience"] += 1
        if (row.get("policy_school") or "").strip():
            counts["school_scoped"] += 1
        else:
            counts["organization_scoped"] += 1

        if row.get("signature_required") is True:
            counts["signature_required"] += 1

        status = (row.get("acknowledgement_status") or "").strip()
        if status == STAFF_POLICY_STATUS_INFO:
            counts["informational"] += 1
        elif status == STAFF_POLICY_STATUS_SIGNED:
            counts["signed"] += 1
        elif status == STAFF_POLICY_STATUS_PENDING:
            counts["pending"] += 1
        elif status == STAFF_POLICY_STATUS_NEW_VERSION:
            counts["new_version"] += 1

    return counts


def _normalize_policy_names(policy_names: list[str]) -> list[str]:
    return sorted({(name or "").strip() for name in policy_names if (name or "").strip()})


def _signature_required_policy_names(policy_names: list[str]) -> set[str]:
    normalized_names = _normalize_policy_names(policy_names)
    if not normalized_names:
        return set()

    params = {"policy_names": tuple(normalized_names)}
    required_policies: set[str] = set()

    todo_rows = frappe.db.sql(
        """
        SELECT DISTINCT pv.institutional_policy
        FROM `tabToDo` todo
        JOIN `tabPolicy Version` pv
          ON pv.name = todo.reference_name
        WHERE todo.reference_type = 'Policy Version'
          AND pv.institutional_policy IN %(policy_names)s
          AND ifnull(todo.description, '') LIKE %(marker)s
        """,
        {**params, "marker": f"%{POLICY_SIGNATURE_MARKER}%"},
        as_dict=True,
    )
    for row in todo_rows:
        policy_name = (row.get("institutional_policy") or "").strip()
        if policy_name:
            required_policies.add(policy_name)

    ack_rows = frappe.db.sql(
        """
        SELECT DISTINCT pv.institutional_policy
        FROM `tabPolicy Acknowledgement` pa
        JOIN `tabPolicy Version` pv
          ON pv.name = pa.policy_version
        WHERE pa.acknowledged_for = 'Staff'
          AND pa.context_doctype = 'Employee'
          AND pv.institutional_policy IN %(policy_names)s
        """,
        params,
        as_dict=True,
    )
    for row in ack_rows:
        policy_name = (row.get("institutional_policy") or "").strip()
        if policy_name:
            required_policies.add(policy_name)

    return required_policies


def _user_acknowledgement_summary_for_policies(
    *,
    user: str,
    employee_name: str | None,
    policy_names: list[str],
) -> tuple[set[str], set[str], dict[str, str]]:
    employee_name = (employee_name or "").strip()
    normalized_names = _normalize_policy_names(policy_names)
    if not employee_name or not normalized_names:
        return set(), set(), {}

    rows = frappe.db.sql(
        """
        SELECT
            pa.policy_version,
            pa.acknowledged_at,
            pv.institutional_policy
        FROM `tabPolicy Acknowledgement` pa
        JOIN `tabPolicy Version` pv
          ON pv.name = pa.policy_version
        WHERE pa.acknowledged_by = %(user)s
          AND pa.acknowledged_for = 'Staff'
          AND pa.context_doctype = 'Employee'
          AND pa.context_name = %(employee_name)s
          AND pv.institutional_policy IN %(policy_names)s
        ORDER BY pa.acknowledged_at DESC
        """,
        {
            "user": user,
            "employee_name": employee_name,
            "policy_names": tuple(normalized_names),
        },
        as_dict=True,
    )

    signed_versions: set[str] = set()
    acknowledged_policies: set[str] = set()
    acknowledged_at_by_version: dict[str, str] = {}
    for row in rows:
        policy_version = (row.get("policy_version") or "").strip()
        policy_name = (row.get("institutional_policy") or "").strip()
        if policy_version:
            signed_versions.add(policy_version)
            if policy_version not in acknowledged_at_by_version and row.get("acknowledged_at"):
                acknowledged_at_by_version[policy_version] = str(row.get("acknowledged_at"))
        if policy_name:
            acknowledged_policies.add(policy_name)

    return signed_versions, acknowledged_policies, acknowledged_at_by_version


def _policy_status_for_user(
    *,
    policy_name: str,
    policy_version: str,
    required_policies: set[str],
    signed_versions: set[str],
    acknowledged_policies: set[str],
) -> str:
    if policy_name not in required_policies:
        return STAFF_POLICY_STATUS_INFO
    if policy_version in signed_versions:
        return STAFF_POLICY_STATUS_SIGNED
    if policy_name in acknowledged_policies:
        return STAFF_POLICY_STATUS_NEW_VERSION
    return STAFF_POLICY_STATUS_PENDING


def get_staff_policy_signature_state_for_user(
    *,
    policy_version: str,
    institutional_policy: str | None = None,
    user: str | None = None,
) -> dict:
    user = (user or frappe.session.user or "").strip()
    policy_version = (policy_version or "").strip()
    policy_name = (institutional_policy or "").strip()
    if not policy_name and policy_version:
        policy_name = (frappe.db.get_value("Policy Version", policy_version, "institutional_policy") or "").strip()

    if not user or not policy_name:
        return {
            "signature_required": False,
            "acknowledgement_status": STAFF_POLICY_STATUS_INFO,
            "acknowledged_at": None,
        }

    employee = get_active_employee_for_user(user)
    employee_name = (employee or {}).get("name")
    required_policies = _signature_required_policy_names([policy_name])
    signed_versions, acknowledged_policies, acknowledged_at_by_version = _user_acknowledgement_summary_for_policies(
        user=user,
        employee_name=employee_name,
        policy_names=[policy_name],
    )
    status = _policy_status_for_user(
        policy_name=policy_name,
        policy_version=policy_version,
        required_policies=required_policies,
        signed_versions=signed_versions,
        acknowledged_policies=acknowledged_policies,
    )
    return {
        "signature_required": policy_name in required_policies,
        "acknowledgement_status": status,
        "acknowledged_at": acknowledged_at_by_version.get(policy_version),
    }


def get_policy_version_context(
    policy_version: str,
    *,
    require_active: bool = False,
    require_staff_applies: bool = False,
) -> dict:
    policy_version = (policy_version or "").strip()
    if not policy_version:
        frappe.throw(_("policy_version is required."))

    rows = frappe.db.sql(
        """
        SELECT
            pv.name AS policy_version,
            pv.version_label,
            pv.policy_text,
            pv.based_on_version,
            pv.change_summary,
            pv.diff_html,
            pv.change_stats,
            pv.guardian_acknowledgement_mode,
            pv.effective_from,
            pv.effective_to,
            pv.is_active AS policy_version_is_active,
            ip.name AS institutional_policy,
            ip.policy_key,
            ip.policy_title,
            ip.organization AS policy_organization,
            ip.school AS policy_school,
            ip.is_active AS policy_is_active
        FROM `tabPolicy Version` pv
        JOIN `tabInstitutional Policy` ip
          ON ip.name = pv.institutional_policy
        WHERE pv.name = %(policy_version)s
        LIMIT 1
        """,
        {"policy_version": policy_version},
        as_dict=True,
    )

    if not rows:
        frappe.throw(_("Policy Version not found."), frappe.DoesNotExistError)

    row = rows[0]
    row["policy_text"] = sanitize_html(row.get("policy_text") or "", allow_headings_from="h2")
    row["guardian_acknowledgement_mode"] = normalize_guardian_acknowledgement_mode(
        row.get("guardian_acknowledgement_mode")
    )
    row["applies_to_tokens"] = list(get_policy_applies_to_tokens_for_policy(row.get("institutional_policy")))
    if require_active and (not row.get("policy_version_is_active") or not row.get("policy_is_active")):
        frappe.throw(_("Policy Version must be active under an active Institutional Policy."))

    if require_staff_applies and not _policy_applies_to_staff(row.get("applies_to_tokens")):
        frappe.throw(_("Selected Policy Version does not apply to Staff."))

    return row


def _policy_supports_guardian_audience(policy_row: dict | None) -> bool:
    return "Guardian" in set((policy_row or {}).get("applies_to_tokens") or [])


def _guardian_acknowledgement_mode_is_locked(*, policy_version: str | None) -> bool:
    policy_version = (policy_version or "").strip()
    if not policy_version:
        return False
    return bool(
        frappe.db.exists(
            "Policy Acknowledgement",
            {
                "policy_version": policy_version,
                "acknowledged_for": "Guardian",
                "docstatus": 1,
            },
        )
    )


def _effective_guardian_acknowledgement_mode(
    *,
    policy_row: dict,
    requested_mode: str | None = None,
) -> tuple[str | None, bool]:
    if not _policy_supports_guardian_audience(policy_row):
        return None, False

    persisted_mode = normalize_guardian_acknowledgement_mode(policy_row.get("guardian_acknowledgement_mode"))
    locked = _guardian_acknowledgement_mode_is_locked(policy_version=policy_row.get("policy_version"))
    if locked:
        return persisted_mode, True

    return normalize_guardian_acknowledgement_mode(requested_mode or persisted_mode), False


def _policy_row_with_guardian_acknowledgement_mode(policy_row: dict, guardian_mode: str | None) -> dict:
    if guardian_mode is None:
        return dict(policy_row)
    return {
        **dict(policy_row),
        "guardian_acknowledgement_mode": normalize_guardian_acknowledgement_mode(guardian_mode),
    }


def _persist_guardian_acknowledgement_mode_if_needed(
    *,
    policy_row: dict,
    requested_mode: str | None,
) -> dict:
    effective_mode, locked = _effective_guardian_acknowledgement_mode(
        policy_row=policy_row,
        requested_mode=requested_mode,
    )
    if effective_mode is None:
        return dict(policy_row)

    persisted_mode = normalize_guardian_acknowledgement_mode(policy_row.get("guardian_acknowledgement_mode"))
    if effective_mode == persisted_mode:
        return _policy_row_with_guardian_acknowledgement_mode(policy_row, persisted_mode)
    if locked:
        frappe.throw(
            _(
                "Guardian acknowledgement scope is already locked for this Policy Version because guardian acknowledgements exist."
            ),
            frappe.ValidationError,
        )

    version_doc = frappe.get_doc("Policy Version", policy_row.get("policy_version"))
    version_doc.guardian_acknowledgement_mode = effective_mode
    version_doc.save(ignore_permissions=True)

    return {
        **dict(policy_row),
        "guardian_acknowledgement_mode": effective_mode,
    }


def _guardian_workflow_description(policy_row: dict) -> str:
    guardian_mode = normalize_guardian_acknowledgement_mode(policy_row.get("guardian_acknowledgement_mode"))
    if guardian_mode == GUARDIAN_ACK_MODE_CHILD:
        return _(
            "Guardians acknowledge this policy separately for each child in Guardian Portal; no staff tasks are created."
        )
    return _(
        "Guardians acknowledge this policy once in Guardian Portal for their family scope; no staff tasks are created."
    )


def validate_staff_policy_scope_for_employee(policy_row: dict, employee_row: dict) -> None:
    policy_org = (policy_row.get("policy_organization") or "").strip()
    employee_org = (employee_row.get("organization") or "").strip()
    if not is_policy_organization_applicable_to_context(
        policy_organization=policy_org,
        context_organization=employee_org,
    ):
        frappe.throw(_("Policy organization scope does not apply to this Employee."))

    policy_school = (policy_row.get("policy_school") or "").strip()
    if not policy_school:
        return

    employee_school = (employee_row.get("school") or "").strip()
    if not employee_school:
        frappe.throw(_("Policy is school-scoped, but Employee has no school context."))

    school_chain = get_school_ancestors_including_self(employee_school)
    if policy_school not in set(school_chain):
        frappe.throw(_("Policy school scope does not apply to this Employee school."))


def _policy_scope_applies_to_context(*, policy_row: dict, organization: str | None, school: str | None) -> bool:
    organization = (organization or "").strip()
    school = (school or "").strip()
    if not organization:
        return False

    if not is_policy_organization_applicable_to_context(
        policy_organization=policy_row.get("policy_organization"),
        context_organization=organization,
    ):
        return False

    policy_school = (policy_row.get("policy_school") or "").strip()
    if not policy_school:
        return True
    if not school:
        return False

    return policy_school in set(get_school_ancestors_including_self(school))


def find_open_staff_policy_todos(*, user: str, policy_version: str) -> list[dict]:
    user = (user or "").strip()
    policy_version = (policy_version or "").strip()
    if not user or not policy_version:
        return []

    return frappe.get_all(
        "ToDo",
        filters={
            "allocated_to": user,
            "reference_type": "Policy Version",
            "reference_name": policy_version,
            "status": "Open",
        },
        fields=["name", "date", "description", "assigned_by", "assigned_by_full_name"],
        order_by="modified desc",
        limit=200,
    )


def parse_employee_from_todo_description(description: str | None) -> str | None:
    text = (description or "").strip()
    if not text:
        return None
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith(POLICY_SIGNATURE_EMPLOYEE_KEY):
            continue
        value = line[len(POLICY_SIGNATURE_EMPLOYEE_KEY) :].strip()
        return value or None
    return None


def close_open_staff_policy_todos(*, user: str, policy_version: str) -> int:
    todos = find_open_staff_policy_todos(user=user, policy_version=policy_version)
    if not todos:
        return 0

    names = [row.get("name") for row in todos if row.get("name")]
    if not names:
        return 0

    frappe.db.sql(
        """
        UPDATE `tabToDo`
        SET status = 'Closed'
        WHERE name IN %(names)s
        """,
        {"names": tuple(names)},
    )
    return len(names)


def _todo_description(*, policy_row: dict, employee_name: str, message: str | None) -> str:
    title = (
        policy_row.get("policy_title") or policy_row.get("policy_key") or policy_row.get("institutional_policy") or ""
    ).strip()
    version = (policy_row.get("version_label") or policy_row.get("policy_version") or "").strip()

    lines = [
        POLICY_SIGNATURE_MARKER,
        f"{POLICY_SIGNATURE_EMPLOYEE_KEY}{employee_name}",
        f"policy_version={policy_row.get('policy_version')}",
    ]
    if title:
        lines.append(f"policy_title={title}")
    if version:
        lines.append(f"version_label={version}")
    if message:
        lines.append("")
        lines.append(message.strip())
    return "\n".join(lines)


def _target_employees(*, organization: str, school: str | None, employee_group: str | None) -> list[dict]:
    org_scope = get_descendant_organizations(organization)
    if not org_scope:
        return []

    filters: dict = {
        "employment_status": "Active",
        "organization": ["in", tuple(org_scope)],
    }

    school = (school or "").strip()
    if school:
        school_scope = get_descendant_schools(school) or [school]
        filters["school"] = ["in", tuple(school_scope)]

    employee_group = (employee_group or "").strip()
    if employee_group:
        filters["employee_group"] = employee_group

    rows = frappe.get_all(
        "Employee",
        filters=filters,
        fields=["name", "employee_full_name", "organization", "school", "employee_group", "user_id"],
        order_by="name asc",
        limit=0,
    )

    out = []
    for row in rows:
        user_id = (row.get("user_id") or "").strip()
        if not user_id:
            continue
        out.append(row)
    return out


def _target_students(*, organization: str, school: str | None) -> list[dict]:
    org_scope = get_descendant_organizations(organization)
    school_scope = _school_scope_names(organization_scope=org_scope, school=school)
    if not school_scope:
        return []

    return frappe.db.sql(
        """
        SELECT
            st.name,
            st.student_full_name,
            st.student_preferred_name,
            st.student_email,
            st.anchor_school AS school,
            sch.organization
        FROM `tabStudent` st
        JOIN `tabSchool` sch
          ON sch.name = st.anchor_school
        WHERE st.anchor_school IN %(schools)s
        ORDER BY st.student_full_name ASC, st.name ASC
        """,
        {"schools": tuple(school_scope)},
        as_dict=True,
    )


def _target_guardians(*, organization: str, school: str | None) -> list[dict]:
    org_scope = get_descendant_organizations(organization)
    school_scope = _school_scope_names(organization_scope=org_scope, school=school)
    if not school_scope:
        return []

    guardian_scope_sql = ""
    if frappe.db.has_column("Student Guardian", "can_consent"):
        guardian_scope_sql = " AND sg.can_consent = 1"

    rows = frappe.db.sql(
        f"""
        SELECT
            g.name AS guardian,
            g.guardian_full_name,
            g.guardian_email,
            g.user AS user_id,
            st.name AS student,
            st.student_full_name,
            st.anchor_school AS school,
            sch.organization
        FROM `tabStudent Guardian` sg
        JOIN `tabStudent` st
          ON st.name = sg.parent
        JOIN `tabGuardian` g
          ON g.name = sg.guardian
        JOIN `tabSchool` sch
          ON sch.name = st.anchor_school
        WHERE sg.parenttype = 'Student'
          AND sg.parentfield = 'guardians'
          AND ifnull(g.is_primary_guardian, 0) = 1
          AND st.anchor_school IN %(schools)s
          {guardian_scope_sql}
        ORDER BY g.guardian_full_name ASC, g.name ASC, st.student_full_name ASC
        """,
        {"schools": tuple(school_scope)},
        as_dict=True,
    )

    grouped: dict[str, dict] = {}
    for row in rows:
        guardian_name = (row.get("guardian") or "").strip()
        if not guardian_name:
            continue

        item = grouped.setdefault(
            guardian_name,
            {
                "name": guardian_name,
                "guardian_full_name": (row.get("guardian_full_name") or "").strip() or guardian_name,
                "guardian_email": (row.get("guardian_email") or "").strip() or None,
                "user_id": (row.get("user_id") or "").strip() or None,
                "contexts": [],
                "student_names": [],
            },
        )
        student_name = (row.get("student_full_name") or row.get("student") or "").strip()
        if student_name and student_name not in item["student_names"]:
            item["student_names"].append(student_name)
        item["contexts"].append(
            {
                "organization": (row.get("organization") or "").strip(),
                "school": (row.get("school") or "").strip(),
                "student": (row.get("student") or "").strip(),
                "student_name": student_name,
            }
        )

    return list(grouped.values())


def _acknowledged_employee_names(policy_version: str, employee_names: list[str]) -> set[str]:
    names = sorted({(name or "").strip() for name in employee_names if (name or "").strip()})
    if not names:
        return set()

    rows = frappe.get_all(
        "Policy Acknowledgement",
        filters={
            "policy_version": policy_version,
            "acknowledged_for": "Staff",
            "context_doctype": "Employee",
            "context_name": ["in", tuple(names)],
        },
        fields=["context_name"],
        limit=0,
    )
    return {(row.get("context_name") or "").strip() for row in rows if (row.get("context_name") or "").strip()}


def _open_todo_users(policy_version: str, users: list[str]) -> set[str]:
    user_ids = sorted({(user or "").strip() for user in users if (user or "").strip()})
    if not user_ids:
        return set()

    rows = frappe.get_all(
        "ToDo",
        filters={
            "allocated_to": ["in", tuple(user_ids)],
            "reference_type": "Policy Version",
            "reference_name": policy_version,
            "status": "Open",
        },
        fields=["allocated_to"],
        limit=0,
    )
    return {(row.get("allocated_to") or "").strip() for row in rows if (row.get("allocated_to") or "").strip()}


def _eligible_employee_rows(*, policy_row: dict, rows: list[dict]) -> tuple[list[dict], int]:
    eligible = []
    skipped_scope = 0
    for row in rows:
        try:
            validate_staff_policy_scope_for_employee(policy_row, row)
            eligible.append(row)
        except Exception:
            skipped_scope += 1
    return eligible, skipped_scope


def _eligible_student_rows(*, policy_row: dict, rows: list[dict]) -> tuple[list[dict], int]:
    eligible = []
    skipped_scope = 0
    for row in rows:
        if _policy_scope_applies_to_context(
            policy_row=policy_row,
            organization=row.get("organization"),
            school=row.get("school"),
        ):
            eligible.append(row)
            continue
        skipped_scope += 1
    return eligible, skipped_scope


def _eligible_guardian_rows(*, policy_row: dict, rows: list[dict]) -> tuple[list[dict], int]:
    eligible = []
    skipped_scope = 0
    for row in rows:
        contexts = row.get("contexts") or []
        if any(
            _policy_scope_applies_to_context(
                policy_row=policy_row,
                organization=context.get("organization"),
                school=context.get("school"),
            )
            for context in contexts
        ):
            eligible.append(row)
            continue
        skipped_scope += 1
    return eligible, skipped_scope


def _acknowledgement_rows_by_context(
    *,
    policy_version: str,
    acknowledged_for: str,
    context_doctype: str,
    context_names: list[str],
) -> dict[str, dict]:
    names = sorted({(name or "").strip() for name in context_names if (name or "").strip()})
    if not names:
        return {}

    rows = frappe.get_all(
        "Policy Acknowledgement",
        filters={
            "policy_version": policy_version,
            "acknowledged_for": acknowledged_for,
            "context_doctype": context_doctype,
            "context_name": ["in", tuple(names)],
            "docstatus": 1,
        },
        fields=["context_name", "acknowledged_at", "acknowledged_by"],
        order_by="acknowledged_at desc",
        limit=0,
    )
    ack_by_context: dict[str, dict] = {}
    for row in rows:
        context_name = (row.get("context_name") or "").strip()
        if not context_name or context_name in ack_by_context:
            continue
        ack_by_context[context_name] = row
    return ack_by_context


def _dedupe_by_user(rows: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for row in rows:
        user_id = (row.get("user_id") or "").strip()
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        deduped.append(row)
    return deduped


def _campaign_preview(
    *,
    policy_row: dict,
    organization: str,
    school: str | None,
    employee_group: str | None,
) -> dict:
    targets = _target_employees(organization=organization, school=school, employee_group=employee_group)
    eligible, skipped_scope = _eligible_employee_rows(policy_row=policy_row, rows=targets)
    eligible = _dedupe_by_user(eligible)

    acknowledged_names = _acknowledged_employee_names(
        policy_version=policy_row["policy_version"],
        employee_names=[row.get("name") for row in eligible],
    )
    open_todo_user_ids = _open_todo_users(
        policy_version=policy_row["policy_version"],
        users=[row.get("user_id") for row in eligible],
    )

    already_signed = 0
    already_open = 0
    to_create = 0
    for row in eligible:
        employee_name = (row.get("name") or "").strip()
        user_id = (row.get("user_id") or "").strip()
        if employee_name in acknowledged_names:
            already_signed += 1
            continue
        if user_id in open_todo_user_ids:
            already_open += 1
            continue
        to_create += 1

    return {
        "target_employee_rows": len(targets),
        "eligible_users": len(eligible),
        "already_signed": already_signed,
        "already_open": already_open,
        "to_create": to_create,
        "skipped_scope": skipped_scope,
    }


@frappe.whitelist()
def get_staff_policy_campaign_options(
    *,
    organization: str | None = None,
    school: str | None = None,
    employee_group: str | None = None,
    policy_version: str | None = None,
):
    user, roles = _require_roles(POLICY_SIGNATURE_ANALYTICS_ROLES)
    scoped_orgs = _manager_scope_organizations(user=user, roles=roles)

    organization = (organization or "").strip() or None
    school = (school or "").strip() or None
    employee_group = (employee_group or "").strip() or None
    policy_version = (policy_version or "").strip() or None

    if organization:
        _ensure_organization_in_scope(organization, scoped_orgs)

    org_scope = get_descendant_organizations(organization) if organization else scoped_orgs
    _ensure_school_in_scope(school=school, organization_scope=org_scope)

    organization_options = sorted(scoped_orgs)
    school_options = _school_options_for_scope(org_scope)
    employee_group_options = _employee_group_options_for_scope(
        organization_scope=org_scope,
        school=school,
    )
    policy_options = _policy_options_for_scope(
        organization=organization,
        organization_scope=org_scope,
        school=school,
    )

    preview = {
        "target_employee_rows": 0,
        "eligible_users": 0,
        "already_signed": 0,
        "already_open": 0,
        "to_create": 0,
        "skipped_scope": 0,
        "policy_audiences": [],
        "audience_previews": [],
    }
    if organization and policy_version:
        policy_row = get_policy_version_context(
            policy_version,
            require_active=True,
        )
        dashboard_payload = _build_policy_signature_dashboard_payload(
            policy_row=policy_row,
            organization=organization,
            school=school,
            employee_group=employee_group,
            limit=25,
        )
        preview["policy_audiences"] = list((dashboard_payload.get("summary") or {}).get("applies_to_tokens") or [])
        preview["audience_previews"] = [
            {
                "audience": section.get("audience"),
                "audience_label": section.get("audience_label"),
                "workflow_description": section.get("workflow_description"),
                "supports_campaign_launch": bool(section.get("supports_campaign_launch")),
                **(section.get("summary") or {}),
            }
            for section in dashboard_payload.get("audiences") or []
        ]
        staff_preview = next(
            (section for section in (dashboard_payload.get("audiences") or []) if section.get("audience") == "Staff"),
            None,
        )
        if staff_preview:
            staff_summary = staff_preview.get("summary") or {}
            preview.update(
                {
                    "target_employee_rows": staff_summary.get("target_rows", 0),
                    "eligible_users": staff_summary.get("eligible_targets", 0),
                    "already_signed": staff_summary.get("signed", 0),
                    "already_open": staff_summary.get("already_open", 0),
                    "to_create": staff_summary.get("to_create", 0),
                    "skipped_scope": staff_summary.get("skipped_scope", 0),
                }
            )

    return {
        "options": {
            "organizations": organization_options,
            "schools": school_options,
            "employee_groups": employee_group_options,
            "policies": policy_options,
        },
        "preview": preview,
    }


def _idempotency_key(*, user: str, scope: str, client_request_id: str, suffix: str) -> str:
    return f"ifitwala_ed:policy_signature:{user}:{suffix}:{scope}:{client_request_id}"


def _lock_key(*, user: str, scope: str, suffix: str) -> str:
    return f"ifitwala_ed:lock:policy_signature:{user}:{suffix}:{scope}"


def _family_campaign_school_targets(*, organization: str, school: str | None) -> list[str]:
    organization = (organization or "").strip()
    school = (school or "").strip()
    if not organization:
        return []

    if school:
        school_scope = {
            (school_name or "").strip() for school_name in (get_descendant_schools(school) or []) if school_name
        }
        school_scope.add(school)
        return sorted(school_scope)

    organization_scope = {
        (organization_name or "").strip()
        for organization_name in (get_descendant_organizations(organization) or [])
        if organization_name
    }
    organization_scope.add(organization)
    if not organization_scope:
        return []

    school_rows = frappe.get_all(
        "School",
        filters={"organization": ["in", tuple(sorted(organization_scope))]},
        pluck="name",
    )
    return sorted({(school_name or "").strip() for school_name in school_rows if (school_name or "").strip()})


def _family_campaign_audience_rows(*, audience: str, school: str | None, school_targets: list[str]) -> list[dict]:
    flags = {
        "to_staff": 0,
        "to_students": 1 if audience == "Student" else 0,
        "to_guardians": 1 if audience == "Guardian" else 0,
    }
    selected_school = (school or "").strip()
    if selected_school:
        return [
            {
                "target_mode": "School Scope",
                "school": selected_school,
                "include_descendants": 1,
                **flags,
            }
        ]

    return [
        {
            "target_mode": "School Scope",
            "school": school_name,
            "include_descendants": 0,
            **flags,
        }
        for school_name in school_targets
    ]


def _family_policy_portal_href(*, audience: str, policy_version: str) -> str:
    policy_version = quote((policy_version or "").strip())
    if audience == "Guardian":
        return f"/hub/guardian/policies?policy_version={policy_version}"
    return f"/hub/student/policies?policy_version={policy_version}"


def _family_policy_campaign_title(*, policy_row: dict, audience: str, override_title: str | None = None) -> str:
    custom_title = (override_title or "").strip()
    if custom_title:
        return custom_title

    audience_label = _("Guardian") if audience == "Guardian" else _("Student")
    policy_label = (
        (policy_row.get("policy_title") or "").strip()
        or (policy_row.get("policy_key") or "").strip()
        or (policy_row.get("institutional_policy") or "").strip()
        or (policy_row.get("policy_version") or "").strip()
    )
    version_label = (policy_row.get("version_label") or "").strip()
    if version_label:
        return _("{audience_label} policy acknowledgement: {policy_label} ({version_label})").format(
            audience_label=audience_label,
            policy_label=policy_label,
            version_label=version_label,
        )
    return _("{audience_label} policy acknowledgement: {policy_label}").format(
        audience_label=audience_label,
        policy_label=policy_label,
    )


def _family_policy_campaign_custom_message_html(message: str | None) -> str:
    text = (message or "").strip()
    if not text:
        return ""
    return f"<p>{escape(text).replace(chr(10), '<br>')}</p>"


def _family_policy_campaign_message_html(*, policy_row: dict, audience: str, message: str | None = None) -> str:
    policy_label = (
        (policy_row.get("policy_title") or "").strip()
        or (policy_row.get("policy_key") or "").strip()
        or (policy_row.get("institutional_policy") or "").strip()
        or (policy_row.get("policy_version") or "").strip()
    )
    version_label = (policy_row.get("version_label") or "").strip()
    change_summary = (policy_row.get("change_summary") or "").strip()
    portal_label = _("Guardian Portal") if audience == "Guardian" else _("Student Hub")
    action_label = _("Open Guardian Policies") if audience == "Guardian" else _("Open Student Policies")
    action_href = _family_policy_portal_href(
        audience=audience,
        policy_version=(policy_row.get("policy_version") or "").strip(),
    )

    parts = [
        f"<h3>{escape(policy_label)}" + (f" - {escape(version_label)}" if version_label else "") + "</h3>",
    ]
    custom_message_html = _family_policy_campaign_custom_message_html(message)
    if custom_message_html:
        parts.append(custom_message_html)
    if change_summary:
        parts.append(f"<p><strong>{escape(_('Summary'))}</strong><br>{escape(change_summary)}</p>")
    if audience == "Guardian":
        guardian_mode = normalize_guardian_acknowledgement_mode(policy_row.get("guardian_acknowledgement_mode"))
        guidance = (
            _("Please review the full policy text and acknowledge it separately for each child in {portal_label}.")
            if guardian_mode == GUARDIAN_ACK_MODE_CHILD
            else _("Please review the full policy text and acknowledge it in {portal_label}.")
        )
    else:
        guidance = _("Please review the full policy text and acknowledge it in {portal_label}.")
    parts.append(f"<p>{escape(guidance.format(portal_label=portal_label))}</p>")
    parts.append(
        '<div class="mt-3 flex flex-wrap justify-end gap-2">'
        + f'<a href="{action_href}" data-policy-version="{escape((policy_row.get("policy_version") or "").strip())}" class="btn btn-primary">'
        + escape(action_label)
        + "</a>"
        + "</div>"
    )
    return "".join(parts)


def _normalize_family_policy_campaign_audiences(
    audiences, *, supported_audiences: list[str] | None = None
) -> list[str]:
    values = audiences
    if isinstance(values, str):
        raw = values.strip()
        if raw.startswith("["):
            try:
                values = frappe.parse_json(raw)
            except Exception:
                values = [raw]
        elif raw:
            values = [value.strip() for value in raw.split(",")]
        else:
            values = []

    if not isinstance(values, (list, tuple, set)):
        frappe.throw(_("Select at least one family audience."))

    normalized_map = {
        "guardian": "Guardian",
        "guardians": "Guardian",
        "student": "Student",
        "students": "Student",
    }
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        audience = normalized_map.get((str(value or "")).strip().lower())
        if not audience or audience in seen:
            continue
        normalized.append(audience)
        seen.add(audience)

    if not normalized:
        frappe.throw(_("Select at least one family audience."))

    if supported_audiences is not None:
        supported = set(supported_audiences or [])
        unsupported = [audience for audience in normalized if audience not in supported]
        if unsupported:
            frappe.throw(_("Selected Policy Version does not apply to the requested family audience."))

    return normalized


def _family_campaign_preview_payload(
    *,
    policy_row: dict,
    organization: str,
    school: str | None,
    guardian_acknowledgement_mode: str | None = None,
) -> dict:
    effective_guardian_mode, guardian_mode_locked = _effective_guardian_acknowledgement_mode(
        policy_row=policy_row,
        requested_mode=guardian_acknowledgement_mode,
    )
    preview_policy_row = _policy_row_with_guardian_acknowledgement_mode(policy_row, effective_guardian_mode)
    dashboard_payload = _build_policy_signature_dashboard_payload(
        policy_row=preview_policy_row,
        organization=organization,
        school=school,
        employee_group=None,
        limit=25,
    )
    sections = [
        section
        for section in (dashboard_payload.get("audiences") or [])
        if (section.get("audience") or "").strip() in set(POLICY_FAMILY_CAMPAIGN_AUDIENCE_ORDER)
    ]
    return {
        "family_audiences": _supported_family_policy_campaign_audiences(preview_policy_row.get("applies_to_tokens")),
        "guardian_acknowledgement_mode": effective_guardian_mode,
        "guardian_acknowledgement_mode_locked": guardian_mode_locked,
        "school_target_count": len(_family_campaign_school_targets(organization=organization, school=school)),
        "audience_previews": [
            {
                "audience": section.get("audience"),
                "audience_label": section.get("audience_label"),
                "workflow_description": section.get("workflow_description"),
                "eligible_targets": int((section.get("summary") or {}).get("eligible_targets") or 0),
                "signed": int((section.get("summary") or {}).get("signed") or 0),
                "pending": int((section.get("summary") or {}).get("pending") or 0),
                "completion_pct": float((section.get("summary") or {}).get("completion_pct") or 0),
                "skipped_scope": int((section.get("summary") or {}).get("skipped_scope") or 0),
            }
            for section in sections
        ],
    }


@frappe.whitelist()
def get_family_policy_campaign_options(
    *,
    organization: str | None = None,
    school: str | None = None,
    policy_version: str | None = None,
    guardian_acknowledgement_mode: str | None = None,
):
    user, roles = _require_roles(POLICY_SIGNATURE_MANAGER_ROLES)
    scoped_orgs = _manager_scope_organizations(user=user, roles=roles)

    organization = (organization or "").strip() or None
    school = (school or "").strip() or None
    policy_version = (policy_version or "").strip() or None
    guardian_acknowledgement_mode = (guardian_acknowledgement_mode or "").strip() or None

    if organization:
        _ensure_organization_in_scope(organization, scoped_orgs)

    org_scope = get_descendant_organizations(organization) if organization else scoped_orgs
    if organization and organization not in set(org_scope or []):
        org_scope = sorted({organization, *(org_scope or [])})
    _ensure_school_in_scope(school=school, organization_scope=org_scope)

    organization_options = sorted(scoped_orgs)
    school_options = _school_options_for_scope(org_scope)
    policy_options = _family_policy_options_for_scope(
        organization=organization,
        organization_scope=org_scope,
        school=school,
    )

    preview = {
        "family_audiences": [],
        "guardian_acknowledgement_mode": None,
        "guardian_acknowledgement_mode_locked": False,
        "school_target_count": len(_family_campaign_school_targets(organization=organization, school=school))
        if organization
        else 0,
        "audience_previews": [],
    }
    if organization and policy_version:
        policy_row = get_policy_version_context(
            policy_version,
            require_active=True,
        )
        if _policy_scope_applies_to_context(policy_row=policy_row, organization=organization, school=school):
            preview = _family_campaign_preview_payload(
                policy_row=policy_row,
                organization=organization,
                school=school,
                guardian_acknowledgement_mode=guardian_acknowledgement_mode,
            )

    return {
        "options": {
            "organizations": organization_options,
            "schools": school_options,
            "policies": policy_options,
        },
        "preview": preview,
    }


@frappe.whitelist()
def publish_family_policy_campaign(
    *,
    policy_version: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    audiences=None,
    guardian_acknowledgement_mode: str | None = None,
    title: str | None = None,
    message: str | None = None,
    publish_to: str | None = None,
    client_request_id: str | None = None,
):
    user, roles = _require_roles(POLICY_SIGNATURE_MANAGER_ROLES)

    policy_version = (policy_version or "").strip()
    organization = (organization or "").strip()
    school = (school or "").strip() or None
    guardian_acknowledgement_mode = (guardian_acknowledgement_mode or "").strip() or None
    title = (title or "").strip() or None
    message = (message or "").strip() or None
    client_request_id = (client_request_id or "").strip() or None

    if not policy_version:
        frappe.throw(_("policy_version is required."))
    if not organization:
        frappe.throw(_("organization is required."))

    publish_to_value = get_datetime(publish_to) if publish_to else None

    scoped_orgs = _manager_scope_organizations(user=user, roles=roles)
    _ensure_organization_in_scope(organization, scoped_orgs)
    org_scope = get_descendant_organizations(organization)
    if organization not in set(org_scope or []):
        org_scope = sorted({organization, *(org_scope or [])})
    _ensure_school_in_scope(school=school, organization_scope=org_scope)

    policy_row = get_policy_version_context(
        policy_version,
        require_active=True,
    )
    if not _policy_scope_applies_to_context(policy_row=policy_row, organization=organization, school=school):
        frappe.throw(_("Selected policy scope does not apply to the selected Organization or School."))

    supported_audiences = _supported_family_policy_campaign_audiences(policy_row.get("applies_to_tokens"))
    if not supported_audiences:
        frappe.throw(_("Selected Policy Version does not apply to Students or Guardians."))

    selected_audiences = _normalize_family_policy_campaign_audiences(
        audiences,
        supported_audiences=supported_audiences,
    )

    school_targets = _family_campaign_school_targets(organization=organization, school=school)
    if not school_targets:
        frappe.throw(_("No schools are available in the selected family campaign scope."))

    preview = _family_campaign_preview_payload(
        policy_row=policy_row,
        organization=organization,
        school=school,
        guardian_acknowledgement_mode=guardian_acknowledgement_mode if "Guardian" in set(selected_audiences) else None,
    )
    preview_by_audience = {
        (row.get("audience") or "").strip(): row
        for row in (preview.get("audience_previews") or [])
        if (row.get("audience") or "").strip()
    }
    selected_pending = sum(
        int((preview_by_audience.get(audience) or {}).get("pending") or 0) for audience in selected_audiences
    )
    if selected_pending <= 0:
        frappe.throw(_("Selected family audiences are already fully acknowledged in this scope."))

    campaign_scope = "|".join(
        [
            policy_version,
            organization,
            school or "",
            ",".join(selected_audiences),
            normalize_guardian_acknowledgement_mode(
                guardian_acknowledgement_mode or policy_row.get("guardian_acknowledgement_mode")
            )
            if "Guardian" in set(selected_audiences)
            else "",
            title or "",
            message or "",
            publish_to_value.isoformat() if publish_to_value else "",
        ]
    )

    cache = frappe.cache()
    if client_request_id:
        existing = cache.get_value(
            _idempotency_key(
                user=user,
                scope=campaign_scope,
                client_request_id=client_request_id,
                suffix="family_publish",
            )
        )
        if existing:
            try:
                parsed = frappe.parse_json(existing)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                return {
                    **parsed,
                    "status": "already_processed",
                    "idempotent": True,
                }

    with cache.lock(
        _lock_key(user=user, scope=campaign_scope, suffix="family_publish"),
        timeout=15,
    ):
        if client_request_id:
            existing = cache.get_value(
                _idempotency_key(
                    user=user,
                    scope=campaign_scope,
                    client_request_id=client_request_id,
                    suffix="family_publish",
                )
            )
            if existing:
                try:
                    parsed = frappe.parse_json(existing)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    return {
                        **parsed,
                        "status": "already_processed",
                        "idempotent": True,
                    }

        if "Guardian" in set(selected_audiences):
            policy_row = _persist_guardian_acknowledgement_mode_if_needed(
                policy_row=policy_row,
                requested_mode=guardian_acknowledgement_mode,
            )

        publish_from_value = now_datetime()
        created_communications: list[dict] = []
        for audience in selected_audiences:
            audience_label = POLICY_SIGNATURE_AUDIENCE_LABELS.get(audience) or audience
            communication_title = _family_policy_campaign_title(
                policy_row=policy_row,
                audience=audience,
                override_title=title,
            )
            communication_doc = frappe.get_doc(
                {
                    "doctype": "Org Communication",
                    "title": communication_title,
                    "communication_type": "Policy Procedure",
                    "status": "Published",
                    "priority": "Normal",
                    "portal_surface": "Portal Feed",
                    "publish_from": publish_from_value,
                    "publish_to": publish_to_value,
                    "school": school or "",
                    "organization": organization,
                    "message": _family_policy_campaign_message_html(
                        policy_row=policy_row,
                        audience=audience,
                        message=message,
                    ),
                    "internal_note": _(
                        "Family policy campaign from Policy Version {policy_version} for {audience_label}."
                    ).format(
                        policy_version=policy_version,
                        audience_label=audience_label,
                    ),
                    "audiences": _family_campaign_audience_rows(
                        audience=audience,
                        school=school,
                        school_targets=school_targets,
                    ),
                }
            )
            communication_doc.insert()
            created_communications.append(
                {
                    "audience": audience,
                    "audience_label": audience_label,
                    "org_communication": communication_doc.name,
                    "title": communication_doc.title,
                    "href": _family_policy_portal_href(audience=audience, policy_version=policy_version),
                    "pending": int((preview_by_audience.get(audience) or {}).get("pending") or 0),
                }
            )

        result = {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "policy_version": policy_version,
            "organization": organization,
            "school": school,
            "audiences": selected_audiences,
            "guardian_acknowledgement_mode": (
                normalize_guardian_acknowledgement_mode(policy_row.get("guardian_acknowledgement_mode"))
                if "Guardian" in set(selected_audiences)
                else None
            ),
            "counts": {
                "published": len(created_communications),
                "pending": selected_pending,
                "school_targets": len(school_targets),
            },
            "communications": created_communications,
        }

        if client_request_id:
            cache.set_value(
                _idempotency_key(
                    user=user,
                    scope=campaign_scope,
                    client_request_id=client_request_id,
                    suffix="family_publish",
                ),
                frappe.as_json(result),
                expires_in_sec=60 * 15,
            )

        return result


@frappe.whitelist()
def launch_staff_policy_campaign(
    *,
    policy_version: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    employee_group: str | None = None,
    due_date: str | None = None,
    message: str | None = None,
    client_request_id: str | None = None,
):
    user, roles = _require_roles(POLICY_SIGNATURE_MANAGER_ROLES)

    policy_version = (policy_version or "").strip()
    organization = (organization or "").strip()
    school = (school or "").strip() or None
    employee_group = (employee_group or "").strip() or None
    message = (message or "").strip() or None
    client_request_id = (client_request_id or "").strip() or None

    if not policy_version:
        frappe.throw(_("policy_version is required."))
    if not organization:
        frappe.throw(_("organization is required."))

    due_date_value = None
    if due_date:
        due_date_value = getdate(due_date)

    scoped_orgs = _manager_scope_organizations(user=user, roles=roles)
    _ensure_organization_in_scope(organization, scoped_orgs)
    org_scope = get_descendant_organizations(organization)
    _ensure_school_in_scope(school=school, organization_scope=org_scope)

    policy_row = get_policy_version_context(
        policy_version,
        require_active=True,
        require_staff_applies=True,
    )
    if not is_policy_organization_applicable_to_context(
        policy_organization=policy_row.get("policy_organization"),
        context_organization=organization,
    ):
        frappe.throw(_("Selected policy scope does not apply to the selected Organization."))

    campaign_scope = "|".join(
        [
            policy_version,
            organization,
            school or "",
            employee_group or "",
            str(due_date_value or ""),
        ]
    )

    cache = frappe.cache()
    if client_request_id:
        existing = cache.get_value(
            _idempotency_key(
                user=user,
                scope=campaign_scope,
                client_request_id=client_request_id,
                suffix="launch",
            )
        )
        if existing:
            try:
                parsed = frappe.parse_json(existing)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                return {
                    **parsed,
                    "status": "already_processed",
                    "idempotent": True,
                }

    with cache.lock(
        _lock_key(user=user, scope=campaign_scope, suffix="launch"),
        timeout=15,
    ):
        if client_request_id:
            existing = cache.get_value(
                _idempotency_key(
                    user=user,
                    scope=campaign_scope,
                    client_request_id=client_request_id,
                    suffix="launch",
                )
            )
            if existing:
                try:
                    parsed = frappe.parse_json(existing)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    return {
                        **parsed,
                        "status": "already_processed",
                        "idempotent": True,
                    }

        targets = _target_employees(
            organization=organization,
            school=school,
            employee_group=employee_group,
        )
        eligible, skipped_scope = _eligible_employee_rows(policy_row=policy_row, rows=targets)
        eligible = _dedupe_by_user(eligible)

        acknowledged_names = _acknowledged_employee_names(
            policy_version=policy_version,
            employee_names=[row.get("name") for row in eligible],
        )
        open_todo_user_ids = _open_todo_users(
            policy_version=policy_version,
            users=[row.get("user_id") for row in eligible],
        )

        created_todos = []
        already_signed = 0
        already_open = 0
        created = 0
        created_users = []
        for row in eligible:
            employee_name = (row.get("name") or "").strip()
            user_id = (row.get("user_id") or "").strip()
            if not employee_name or not user_id:
                continue

            if employee_name in acknowledged_names:
                already_signed += 1
                continue

            if user_id in open_todo_user_ids:
                already_open += 1
                continue

            todo = frappe.get_doc(
                {
                    "doctype": "ToDo",
                    "allocated_to": user_id,
                    "assigned_by": user,
                    "reference_type": "Policy Version",
                    "reference_name": policy_version,
                    "status": "Open",
                    "description": _todo_description(
                        policy_row=policy_row,
                        employee_name=employee_name,
                        message=message,
                    ),
                }
            )
            if due_date_value:
                todo.date = due_date_value
            todo.insert(ignore_permissions=True)

            created_todos.append(todo.name)
            created_users.append(user_id)
            open_todo_user_ids.add(user_id)
            created += 1

        for target_user in sorted(set(created_users)):
            frappe.publish_realtime(
                event="focus:invalidate",
                message={"policy_version": policy_version, "source": "policy_signature_campaign"},
                user=target_user,
            )

        result = {
            "ok": True,
            "idempotent": False,
            "status": "processed",
            "policy_version": policy_version,
            "organization": organization,
            "school": school,
            "employee_group": employee_group,
            "counts": {
                "target_employee_rows": len(targets),
                "eligible_users": len(eligible),
                "created": created,
                "already_open": already_open,
                "already_signed": already_signed,
                "skipped_scope": skipped_scope,
            },
            "created_todos": created_todos,
        }

        if client_request_id:
            cache.set_value(
                _idempotency_key(
                    user=user,
                    scope=campaign_scope,
                    client_request_id=client_request_id,
                    suffix="launch",
                ),
                frappe.as_json(result),
                expires_in_sec=60 * 15,
            )

        return result


def _completion_pct(signed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((signed / total) * 100, 2)


def _build_breakdown(rows: list[dict], *, field: str) -> list[dict]:
    buckets: dict[str, dict[str, int]] = {}
    for row in rows:
        key = (row.get(field) or "").strip() or _("Unspecified")
        bucket = buckets.setdefault(key, {"signed": 0, "pending": 0, "total": 0})
        bucket["total"] += 1
        if row.get("is_signed"):
            bucket["signed"] += 1
        else:
            bucket["pending"] += 1

    out = []
    for label, bucket in buckets.items():
        out.append(
            {
                "label": label,
                "signed": bucket["signed"],
                "pending": bucket["pending"],
                "total": bucket["total"],
                "completion_pct": _completion_pct(bucket["signed"], bucket["total"]),
            }
        )
    out.sort(key=lambda row: (-row["pending"], row["label"]))
    return out


def _compact_scope_label(values: list[str], *, multiple_label: str) -> str | None:
    cleaned = sorted({(value or "").strip() for value in values if (value or "").strip()})
    if not cleaned:
        return None
    if len(cleaned) == 1:
        return cleaned[0]
    return multiple_label


def _sorted_signed_rows(rows: list[dict], limit: int) -> list[dict]:
    return sorted(
        [row for row in rows if row.get("is_signed")],
        key=lambda row: str(row.get("acknowledged_at") or ""),
        reverse=True,
    )[:limit]


def _build_staff_audience_dataset(
    *,
    policy_row: dict,
    organization: str,
    school: str | None,
    employee_group: str | None,
) -> dict:
    targets = _target_employees(organization=organization, school=school, employee_group=employee_group)
    eligible, skipped_scope = _eligible_employee_rows(policy_row=policy_row, rows=targets)
    eligible = _dedupe_by_user(eligible)

    acknowledged_names = _acknowledged_employee_names(
        policy_version=policy_row["policy_version"],
        employee_names=[row.get("name") for row in eligible],
    )
    open_todo_user_ids = _open_todo_users(
        policy_version=policy_row["policy_version"],
        users=[row.get("user_id") for row in eligible],
    )
    ack_by_employee = _acknowledgement_rows_by_context(
        policy_version=policy_row["policy_version"],
        acknowledged_for="Staff",
        context_doctype="Employee",
        context_names=[row.get("name") for row in eligible],
    )

    already_signed = 0
    already_open = 0
    to_create = 0
    rows = []
    for employee in eligible:
        employee_name = (employee.get("name") or "").strip()
        user_id = (employee.get("user_id") or "").strip()
        ack = ack_by_employee.get(employee_name)
        if employee_name in acknowledged_names:
            already_signed += 1
        elif user_id in open_todo_user_ids:
            already_open += 1
        else:
            to_create += 1

        rows.append(
            {
                "record_id": employee_name,
                "subject_name": employee.get("employee_full_name") or employee_name,
                "subject_subtitle": (employee.get("employee_group") or "").strip() or None,
                "context_label": None,
                "organization": employee.get("organization"),
                "school": employee.get("school"),
                "is_signed": bool(ack),
                "acknowledged_at": ack.get("acknowledged_at") if ack else None,
                "acknowledged_by": ack.get("acknowledged_by") if ack else None,
            }
        )

    signed_count = sum(1 for row in rows if row["is_signed"])
    pending_count = len(rows) - signed_count
    return {
        "audience": "Staff",
        "audience_label": POLICY_SIGNATURE_AUDIENCE_LABELS["Staff"],
        "workflow_description": POLICY_SIGNATURE_AUDIENCE_WORKFLOW_DESCRIPTIONS["Staff"],
        "supports_campaign_launch": True,
        "summary": {
            "target_rows": len(targets),
            "eligible_targets": len(rows),
            "signed": signed_count,
            "pending": pending_count,
            "completion_pct": _completion_pct(signed_count, len(rows)),
            "skipped_scope": skipped_scope,
            "already_open": already_open,
            "to_create": to_create,
        },
        "breakdowns": {
            "by_organization": _build_breakdown(rows, field="organization"),
            "by_school": _build_breakdown(rows, field="school"),
            "by_context": _build_breakdown(rows, field="subject_subtitle"),
            "context_label": _("Employee Group"),
        },
        "rows": rows,
    }


def _build_student_audience_dataset(
    *,
    policy_row: dict,
    organization: str,
    school: str | None,
) -> dict:
    targets = _target_students(organization=organization, school=school)
    eligible, skipped_scope = _eligible_student_rows(policy_row=policy_row, rows=targets)
    ack_by_student = _acknowledgement_rows_by_context(
        policy_version=policy_row["policy_version"],
        acknowledged_for="Student",
        context_doctype="Student",
        context_names=[row.get("name") for row in eligible],
    )

    rows = []
    for student in eligible:
        student_name = (student.get("name") or "").strip()
        preferred_name = (student.get("student_preferred_name") or "").strip()
        full_name = (student.get("student_full_name") or "").strip() or student_name
        ack = ack_by_student.get(student_name)
        rows.append(
            {
                "record_id": student_name,
                "subject_name": preferred_name or full_name,
                "subject_subtitle": full_name if preferred_name and preferred_name != full_name else None,
                "context_label": (student.get("student_email") or "").strip() or None,
                "organization": student.get("organization"),
                "school": student.get("school"),
                "is_signed": bool(ack),
                "acknowledged_at": ack.get("acknowledged_at") if ack else None,
                "acknowledged_by": ack.get("acknowledged_by") if ack else None,
            }
        )

    signed_count = sum(1 for row in rows if row["is_signed"])
    pending_count = len(rows) - signed_count
    return {
        "audience": "Student",
        "audience_label": POLICY_SIGNATURE_AUDIENCE_LABELS["Student"],
        "workflow_description": POLICY_SIGNATURE_AUDIENCE_WORKFLOW_DESCRIPTIONS["Student"],
        "supports_campaign_launch": False,
        "summary": {
            "target_rows": len(targets),
            "eligible_targets": len(rows),
            "signed": signed_count,
            "pending": pending_count,
            "completion_pct": _completion_pct(signed_count, len(rows)),
            "skipped_scope": skipped_scope,
            "already_open": 0,
            "to_create": 0,
        },
        "breakdowns": {
            "by_organization": _build_breakdown(rows, field="organization"),
            "by_school": _build_breakdown(rows, field="school"),
            "by_context": [],
            "context_label": _("Portal Email"),
        },
        "rows": rows,
    }


def _build_guardian_audience_dataset(
    *,
    policy_row: dict,
    organization: str,
    school: str | None,
) -> dict:
    targets = _target_guardians(organization=organization, school=school)
    eligible, skipped_scope = _eligible_guardian_rows(policy_row=policy_row, rows=targets)
    guardian_mode = normalize_guardian_acknowledgement_mode(policy_row.get("guardian_acknowledgement_mode"))

    if guardian_mode == GUARDIAN_ACK_MODE_CHILD:
        child_target_rows = []
        for guardian in eligible:
            for context in guardian.get("contexts") or []:
                if not _policy_scope_applies_to_context(
                    policy_row=policy_row,
                    organization=context.get("organization"),
                    school=context.get("school"),
                ):
                    continue
                student_name = (context.get("student") or "").strip()
                if not student_name:
                    continue
                child_target_rows.append(
                    {
                        "guardian_name": (guardian.get("name") or "").strip(),
                        "guardian_full_name": guardian.get("guardian_full_name"),
                        "guardian_email": guardian.get("guardian_email"),
                        "guardian_user_id": guardian.get("user_id"),
                        "student_name": student_name,
                        "student_label": (context.get("student_name") or student_name).strip(),
                        "organization": (context.get("organization") or "").strip(),
                        "school": (context.get("school") or "").strip(),
                    }
                )

        ack_by_student = _acknowledgement_rows_by_context(
            policy_version=policy_row["policy_version"],
            acknowledged_for="Guardian",
            context_doctype="Student",
            context_names=[row.get("student_name") for row in child_target_rows],
        )
        rows = []
        for target in child_target_rows:
            ack = ack_by_student.get((target.get("student_name") or "").strip())
            context_bits = [_("For {student}").format(student=target.get("student_label"))]
            if not target.get("guardian_user_id"):
                context_bits.append(_("No guardian portal user linked yet"))
            rows.append(
                {
                    "record_id": f"{target.get('guardian_name')}::{target.get('student_name')}",
                    "subject_name": target.get("guardian_full_name") or target.get("guardian_name"),
                    "subject_subtitle": target.get("guardian_email"),
                    "context_label": " · ".join(bit for bit in context_bits if bit),
                    "organization": target.get("organization") or None,
                    "school": target.get("school") or None,
                    "is_signed": bool(ack),
                    "acknowledged_at": ack.get("acknowledged_at") if ack else None,
                    "acknowledged_by": ack.get("acknowledged_by") if ack else None,
                }
            )

        signed_count = sum(1 for row in rows if row["is_signed"])
        pending_count = len(rows) - signed_count
        workflow_description = _guardian_workflow_description(policy_row)
        return {
            "audience": "Guardian",
            "audience_label": POLICY_SIGNATURE_AUDIENCE_LABELS["Guardian"],
            "workflow_description": workflow_description,
            "supports_campaign_launch": False,
            "summary": {
                "target_rows": len(child_target_rows),
                "eligible_targets": len(rows),
                "signed": signed_count,
                "pending": pending_count,
                "completion_pct": _completion_pct(signed_count, len(rows)),
                "skipped_scope": skipped_scope,
                "already_open": 0,
                "to_create": 0,
            },
            "breakdowns": {
                "by_organization": _build_breakdown(rows, field="organization"),
                "by_school": _build_breakdown(rows, field="school"),
                "by_context": [],
                "context_label": _("Guardian Child Scope"),
            },
            "rows": rows,
        }

    ack_by_guardian = _acknowledgement_rows_by_context(
        policy_version=policy_row["policy_version"],
        acknowledged_for="Guardian",
        context_doctype="Guardian",
        context_names=[row.get("name") for row in eligible],
    )

    rows = []
    for guardian in eligible:
        guardian_name = (guardian.get("name") or "").strip()
        contexts = guardian.get("contexts") or []
        ack = ack_by_guardian.get(guardian_name)
        linked_students = guardian.get("student_names") or []
        context_bits = []
        if linked_students:
            context_bits.append(_("Linked students: {students}").format(students=", ".join(linked_students)))
        if not guardian.get("user_id"):
            context_bits.append(_("No guardian portal user linked yet"))
        rows.append(
            {
                "record_id": guardian_name,
                "subject_name": guardian.get("guardian_full_name") or guardian_name,
                "subject_subtitle": guardian.get("guardian_email"),
                "context_label": " · ".join(context_bits) if context_bits else None,
                "organization": _compact_scope_label(
                    [context.get("organization") for context in contexts],
                    multiple_label=MULTIPLE_ORGANIZATIONS_LABEL,
                ),
                "school": _compact_scope_label(
                    [context.get("school") for context in contexts],
                    multiple_label=MULTIPLE_SCHOOLS_LABEL,
                ),
                "is_signed": bool(ack),
                "acknowledged_at": ack.get("acknowledged_at") if ack else None,
                "acknowledged_by": ack.get("acknowledged_by") if ack else None,
            }
        )

    signed_count = sum(1 for row in rows if row["is_signed"])
    pending_count = len(rows) - signed_count
    return {
        "audience": "Guardian",
        "audience_label": POLICY_SIGNATURE_AUDIENCE_LABELS["Guardian"],
        "workflow_description": _guardian_workflow_description(policy_row),
        "supports_campaign_launch": False,
        "summary": {
            "target_rows": len(targets),
            "eligible_targets": len(rows),
            "signed": signed_count,
            "pending": pending_count,
            "completion_pct": _completion_pct(signed_count, len(rows)),
            "skipped_scope": skipped_scope,
            "already_open": 0,
            "to_create": 0,
        },
        "breakdowns": {
            "by_organization": _build_breakdown(rows, field="organization"),
            "by_school": _build_breakdown(rows, field="school"),
            "by_context": [],
            "context_label": _("Guardian Email"),
        },
        "rows": rows,
    }


def _finalize_audience_section(*, dataset: dict, limit: int) -> dict:
    rows = list(dataset.get("rows") or [])
    pending_rows = [row for row in rows if not row.get("is_signed")][:limit]
    signed_rows = _sorted_signed_rows(rows, limit)

    return {
        "audience": dataset.get("audience"),
        "audience_label": dataset.get("audience_label"),
        "workflow_description": dataset.get("workflow_description"),
        "supports_campaign_launch": bool(dataset.get("supports_campaign_launch")),
        "summary": dataset.get("summary") or {},
        "breakdowns": dataset.get("breakdowns") or {},
        "rows": {
            "pending": pending_rows,
            "signed": signed_rows,
        },
    }


def _build_policy_signature_audience_dataset(
    *,
    audience: str,
    policy_row: dict,
    organization: str,
    school: str | None,
    employee_group: str | None,
) -> dict:
    if audience == "Staff":
        return _build_staff_audience_dataset(
            policy_row=policy_row,
            organization=organization,
            school=school,
            employee_group=employee_group,
        )
    if audience == "Guardian":
        return _build_guardian_audience_dataset(
            policy_row=policy_row,
            organization=organization,
            school=school,
        )
    if audience == "Student":
        return _build_student_audience_dataset(
            policy_row=policy_row,
            organization=organization,
            school=school,
        )
    frappe.throw(_("Unsupported policy signature audience."))
    return {}


def _normalize_policy_signature_audience(audience: str | None) -> str:
    audience_key = (audience or "").strip().casefold()
    mapping = {
        "staff": "Staff",
        "guardian": "Guardian",
        "student": "Student",
    }
    normalized = mapping.get(audience_key)
    if normalized:
        return normalized
    frappe.throw(_("Unsupported policy signature audience."))
    return ""


def _normalize_register_status(status: str | None) -> str:
    normalized = (status or POLICY_SIGNATURE_REGISTER_STATUS_ALL).strip().casefold()
    allowed = {
        POLICY_SIGNATURE_REGISTER_STATUS_ALL,
        POLICY_SIGNATURE_REGISTER_STATUS_PENDING,
        POLICY_SIGNATURE_REGISTER_STATUS_SIGNED,
    }
    if normalized in allowed:
        return normalized
    frappe.throw(_("Unsupported policy signature register status."))
    return POLICY_SIGNATURE_REGISTER_STATUS_ALL


def _register_row_matches_query(row: dict, query: str | None) -> bool:
    query = (query or "").strip().casefold()
    if not query:
        return True

    haystack = " ".join(
        [
            row.get("record_id") or "",
            row.get("subject_name") or "",
            row.get("subject_subtitle") or "",
            row.get("context_label") or "",
            row.get("organization") or "",
            row.get("school") or "",
            row.get("acknowledged_by") or "",
        ]
    ).casefold()
    return query in haystack


def _filter_policy_signature_register_rows(
    *,
    rows: list[dict],
    status: str,
    query: str | None,
) -> list[dict]:
    filtered: list[dict] = []
    for row in rows:
        is_signed = bool(row.get("is_signed"))
        if status == POLICY_SIGNATURE_REGISTER_STATUS_PENDING and is_signed:
            continue
        if status == POLICY_SIGNATURE_REGISTER_STATUS_SIGNED and not is_signed:
            continue
        if not _register_row_matches_query(row, query):
            continue
        filtered.append(row)

    filtered.sort(
        key=lambda row: (
            (row.get("subject_name") or row.get("record_id") or "").casefold(),
            (row.get("record_id") or "").casefold(),
        )
    )
    return filtered


def _paginate_policy_signature_register_rows(*, rows: list[dict], page: int, limit: int) -> tuple[list[dict], dict]:
    total_rows = len(rows)
    total_pages = max(1, (total_rows + limit - 1) // limit)
    page = max(1, min(page, total_pages))
    start = (page - 1) * limit
    end = start + limit

    return rows[start:end], {
        "page": page,
        "limit": limit,
        "total_rows": total_rows,
        "total_pages": total_pages,
    }


def _build_policy_signature_dashboard_payload(
    *,
    policy_row: dict,
    organization: str,
    school: str | None,
    employee_group: str | None,
    limit: int,
) -> dict:
    audiences = _supported_policy_signature_audiences(policy_row.get("applies_to_tokens"))
    if not audiences:
        frappe.throw(_("Selected Policy Version does not apply to Staff, Guardians, or Students."))

    audience_sections = []
    for audience in audiences:
        dataset = _build_policy_signature_audience_dataset(
            audience=audience,
            policy_row=policy_row,
            organization=organization,
            school=school,
            employee_group=employee_group,
        )
        audience_sections.append(_finalize_audience_section(dataset=dataset, limit=limit))

    total_eligible = sum((section.get("summary") or {}).get("eligible_targets", 0) for section in audience_sections)
    total_signed = sum((section.get("summary") or {}).get("signed", 0) for section in audience_sections)
    total_pending = sum((section.get("summary") or {}).get("pending", 0) for section in audience_sections)
    total_skipped = sum((section.get("summary") or {}).get("skipped_scope", 0) for section in audience_sections)
    return {
        "summary": {
            "policy_version": policy_row.get("policy_version"),
            "institutional_policy": policy_row.get("institutional_policy"),
            "policy_key": policy_row.get("policy_key"),
            "policy_title": policy_row.get("policy_title"),
            "version_label": policy_row.get("version_label"),
            "effective_from": policy_row.get("effective_from"),
            "effective_to": policy_row.get("effective_to"),
            "organization": organization,
            "school": school,
            "employee_group": employee_group,
            "applies_to_tokens": audiences,
            "eligible_targets": total_eligible,
            "signed": total_signed,
            "pending": total_pending,
            "completion_pct": _completion_pct(total_signed, total_eligible),
            "skipped_scope": total_skipped,
        },
        "audiences": audience_sections,
    }


@frappe.whitelist()
def get_staff_policy_signature_audience_rows(
    *,
    policy_version: str | None = None,
    audience: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    employee_group: str | None = None,
    status: str | None = None,
    query: str | None = None,
    page: int = 1,
    limit: int = 25,
):
    user, roles = _require_roles(POLICY_SIGNATURE_ANALYTICS_ROLES)

    policy_version = (policy_version or "").strip()
    if not policy_version:
        frappe.throw(_("policy_version is required."))

    audience_name = _normalize_policy_signature_audience(audience)
    register_status = _normalize_register_status(status)
    query = (query or "").strip() or None
    page = max(1, int(page or 1))
    limit = max(1, min(int(limit or 25), 100))

    policy_row = get_policy_version_context(
        policy_version,
        require_active=False,
    )
    if audience_name not in _supported_policy_signature_audiences(policy_row.get("applies_to_tokens")):
        frappe.throw(_("Selected Policy Version does not apply to the requested audience."))

    scoped_orgs = _manager_scope_organizations(user=user, roles=roles)
    organization = (organization or "").strip() or (policy_row.get("policy_organization") or "").strip()
    school = (school or "").strip() or None
    employee_group = (employee_group or "").strip() or None

    _ensure_organization_in_scope(organization, scoped_orgs)
    org_scope = get_descendant_organizations(organization)
    _ensure_school_in_scope(school=school, organization_scope=org_scope)

    dataset = _build_policy_signature_audience_dataset(
        audience=audience_name,
        policy_row=policy_row,
        organization=organization,
        school=school,
        employee_group=employee_group,
    )
    filtered_rows = _filter_policy_signature_register_rows(
        rows=list(dataset.get("rows") or []),
        status=register_status,
        query=query,
    )
    paged_rows, pagination = _paginate_policy_signature_register_rows(
        rows=filtered_rows,
        page=page,
        limit=limit,
    )

    return {
        "audience": dataset.get("audience"),
        "audience_label": dataset.get("audience_label"),
        "workflow_description": dataset.get("workflow_description"),
        "supports_campaign_launch": bool(dataset.get("supports_campaign_launch")),
        "status": register_status,
        "query": query,
        "rows": paged_rows,
        "pagination": pagination,
    }


@frappe.whitelist()
def get_staff_policy_signature_dashboard(
    *,
    policy_version: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    employee_group: str | None = None,
    limit: int = 100,
):
    user, roles = _require_roles(POLICY_SIGNATURE_ANALYTICS_ROLES)

    policy_version = (policy_version or "").strip()
    if not policy_version:
        frappe.throw(_("policy_version is required."))

    policy_row = get_policy_version_context(
        policy_version,
        require_active=False,
    )

    scoped_orgs = _manager_scope_organizations(user=user, roles=roles)
    organization = (organization or "").strip() or (policy_row.get("policy_organization") or "").strip()
    school = (school or "").strip() or None
    employee_group = (employee_group or "").strip() or None
    limit = max(1, min(int(limit or 100), 500))

    _ensure_organization_in_scope(organization, scoped_orgs)
    org_scope = get_descendant_organizations(organization)
    _ensure_school_in_scope(school=school, organization_scope=org_scope)

    return _build_policy_signature_dashboard_payload(
        policy_row=policy_row,
        organization=organization,
        school=school,
        employee_group=employee_group,
        limit=limit,
    )


@frappe.whitelist()
def get_policy_library(
    *,
    organization: str | None = None,
    school: str | None = None,
    audience: str | None = None,
):
    user, roles = _require_roles(POLICY_LIBRARY_ROLES)
    employee_row = get_active_employee_for_user(user)
    can_manage_audiences = bool(roles & set(POLICY_SIGNATURE_ANALYTICS_ROLES))

    scoped_orgs = _policy_library_scope_organizations(
        user=user,
        roles=roles,
        employee_row=employee_row,
    )
    organization_options = sorted({(org or "").strip() for org in scoped_orgs if (org or "").strip()})
    if not organization_options:
        return {
            "meta": {
                "generated_at": now_datetime().isoformat(),
                "user": user,
                "employee": employee_row,
                "can_manage_audiences": can_manage_audiences,
            },
            "filters": {
                "organization": None,
                "school": None,
                "audience": _normalize_policy_library_audience(
                    value=audience,
                    can_manage_audiences=can_manage_audiences,
                ),
            },
            "options": {
                "organizations": [],
                "schools": [],
                "audiences": list(POLICY_LIBRARY_AUDIENCES if can_manage_audiences else ("Staff",)),
            },
            "counts": _build_policy_library_counts([]),
            "rows": [],
        }

    selected_organization = (organization or "").strip() or (employee_row or {}).get("organization") or ""
    selected_organization = (selected_organization or "").strip()
    if not selected_organization:
        selected_organization = organization_options[0]
    _ensure_organization_in_scope(selected_organization, organization_options)

    selected_organization_scope = [selected_organization]
    school_options = _school_options_for_scope(selected_organization_scope)

    employee_school = ((employee_row or {}).get("school") or "").strip()
    selected_school = (school or "").strip()
    school_option_set = set(school_options)

    if selected_school and selected_school not in school_option_set:
        selected_school = ""

    if not can_manage_audiences and not selected_school and school_options:
        selected_school = employee_school if employee_school in school_option_set else school_options[0]

    if selected_school:
        _ensure_school_in_scope(school=selected_school, organization_scope=selected_organization_scope)

    selected_audience = _normalize_policy_library_audience(
        value=audience,
        can_manage_audiences=can_manage_audiences,
    )

    policy_rows = _active_policy_rows_for_context(
        context_organization=selected_organization,
        context_school=selected_school or None,
        audience=None if selected_audience == POLICY_LIBRARY_AUDIENCE_ALL else selected_audience,
    )
    policy_names = [(row.get("institutional_policy") or "").strip() for row in policy_rows]

    required_policy_names: set[str] = set()
    signed_versions: set[str] = set()
    acknowledged_policies: set[str] = set()
    acknowledged_at_by_version: dict[str, str] = {}
    if selected_audience == "Staff":
        required_policy_names = _signature_required_policy_names(policy_names)
        (
            signed_versions,
            acknowledged_policies,
            acknowledged_at_by_version,
        ) = _user_acknowledgement_summary_for_policies(
            user=user,
            employee_name=(employee_row or {}).get("name"),
            policy_names=policy_names,
        )

    rows = []
    for row in policy_rows:
        policy_name = (row.get("institutional_policy") or "").strip()
        policy_version = (row.get("policy_version") or "").strip()
        status = None
        signature_required = None
        acknowledged_at = None
        if selected_audience == "Staff":
            status = _policy_status_for_user(
                policy_name=policy_name,
                policy_version=policy_version,
                required_policies=required_policy_names,
                signed_versions=signed_versions,
                acknowledged_policies=acknowledged_policies,
            )
            signature_required = policy_name in required_policy_names
            acknowledged_at = acknowledged_at_by_version.get(policy_version)
        rows.append(
            {
                "institutional_policy": policy_name,
                "policy_version": policy_version,
                "policy_key": (row.get("policy_key") or "").strip() or None,
                "policy_title": (row.get("policy_title") or "").strip() or None,
                "policy_category": (row.get("policy_category") or "").strip() or None,
                "version_label": (row.get("version_label") or "").strip() or None,
                "description": (row.get("description") or "").strip() or "",
                "policy_organization": (row.get("policy_organization") or "").strip() or None,
                "policy_school": (row.get("policy_school") or "").strip() or None,
                "effective_from": str(row.get("effective_from")) if row.get("effective_from") else None,
                "effective_to": str(row.get("effective_to")) if row.get("effective_to") else None,
                "approved_on": str(row.get("approved_on")) if row.get("approved_on") else None,
                "based_on_version": (row.get("based_on_version") or "").strip() or None,
                "change_summary": (row.get("change_summary") or "").strip() or None,
                "applies_to_tokens": list(row.get("applies_to_tokens") or []),
                "signature_required": signature_required,
                "acknowledgement_status": status,
                "acknowledged_at": acknowledged_at,
            }
        )

    counts = _build_policy_library_counts(rows)

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "user": user,
            "employee": employee_row,
            "can_manage_audiences": can_manage_audiences,
        },
        "filters": {
            "organization": selected_organization or None,
            "school": selected_school or None,
            "audience": selected_audience,
        },
        "options": {
            "organizations": organization_options,
            "schools": school_options,
            "audiences": list(POLICY_LIBRARY_AUDIENCES if can_manage_audiences else ("Staff",)),
        },
        "counts": counts,
        "rows": rows,
    }
