# ifitwala_ed/api/policy_signature.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import getdate

from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    is_policy_organization_applicable_to_context,
)
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations, get_user_base_org
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
POLICY_SIGNATURE_MARKER = "[policy_signature]"
POLICY_SIGNATURE_EMPLOYEE_KEY = "employee="


def _policy_applies_to_staff(applies_to: str | None) -> bool:
    text = (applies_to or "").strip()
    if not text:
        return False
    tokens = {token.strip() for raw in text.split("\n") for token in raw.split(",") if token and token.strip()}
    return "Staff" in tokens or text == "Staff"


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
            pv.amended_from,
            pv.change_summary,
            pv.diff_html,
            pv.change_stats,
            pv.effective_from,
            pv.effective_to,
            pv.is_active AS policy_version_is_active,
            ip.name AS institutional_policy,
            ip.policy_key,
            ip.policy_title,
            ip.applies_to,
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
    if require_active and (not row.get("policy_version_is_active") or not row.get("policy_is_active")):
        frappe.throw(_("Policy Version must be active under an active Institutional Policy."))

    if require_staff_applies and not _policy_applies_to_staff(row.get("applies_to")):
        frappe.throw(_("Selected Policy Version does not apply to Staff."))

    return row


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
        limit_page_length=200,
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
        limit_page_length=0,
    )

    out = []
    for row in rows:
        user_id = (row.get("user_id") or "").strip()
        if not user_id:
            continue
        out.append(row)
    return out


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
        limit_page_length=0,
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
        limit_page_length=0,
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

    school_options = []
    if org_scope:
        school_rows = frappe.get_all(
            "School",
            filters={"organization": ["in", tuple(org_scope)]},
            fields=["name"],
            limit_page_length=0,
        )
        school_options = sorted(
            {(row.get("name") or "").strip() for row in school_rows if (row.get("name") or "").strip()}
        )

    group_conditions = []
    group_params = {}
    if org_scope:
        group_conditions.append("organization IN %(organizations)s")
        group_params["organizations"] = tuple(org_scope)
    if school:
        school_scope = get_descendant_schools(school) or [school]
        group_conditions.append("school IN %(schools)s")
        group_params["schools"] = tuple(school_scope)
    group_where = " AND ".join(group_conditions) if group_conditions else "1=1"
    group_rows = frappe.db.sql(
        f"""
        SELECT DISTINCT employee_group
        FROM `tabEmployee`
        WHERE employment_status = 'Active'
          AND ifnull(employee_group, '') != ''
          AND {group_where}
        ORDER BY employee_group ASC
        """,
        group_params,
        as_dict=True,
    )
    employee_group_options = [
        row.get("employee_group") for row in group_rows if (row.get("employee_group") or "").strip()
    ]

    policy_options = []
    policy_params = {}
    if organization:
        ancestors = get_organization_ancestors_including_self(organization)
        policy_scope_orgs = ancestors or []
    else:
        policy_scope_orgs = org_scope

    if policy_scope_orgs:
        policy_params["policy_organizations"] = tuple(policy_scope_orgs)
        policy_options = frappe.db.sql(
            """
            SELECT
                pv.name AS policy_version,
                pv.version_label,
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
              AND ip.applies_to LIKE %(applies_to)s
            ORDER BY ip.policy_title ASC, pv.version_label DESC
            """,
            {**policy_params, "applies_to": "%Staff%"},
            as_dict=True,
        )

    preview = {
        "target_employee_rows": 0,
        "eligible_users": 0,
        "already_signed": 0,
        "already_open": 0,
        "to_create": 0,
        "skipped_scope": 0,
    }
    if organization and policy_version:
        policy_row = get_policy_version_context(
            policy_version,
            require_active=True,
            require_staff_applies=True,
        )
        preview = _campaign_preview(
            policy_row=policy_row,
            organization=organization,
            school=school,
            employee_group=employee_group,
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
        require_staff_applies=True,
    )

    scoped_orgs = _manager_scope_organizations(user=user, roles=roles)
    organization = (organization or "").strip() or (policy_row.get("policy_organization") or "").strip()
    school = (school or "").strip() or None
    employee_group = (employee_group or "").strip() or None
    limit = max(1, min(int(limit or 100), 500))

    _ensure_organization_in_scope(organization, scoped_orgs)
    org_scope = get_descendant_organizations(organization)
    _ensure_school_in_scope(school=school, organization_scope=org_scope)

    targets = _target_employees(
        organization=organization,
        school=school,
        employee_group=employee_group,
    )
    eligible, skipped_scope = _eligible_employee_rows(policy_row=policy_row, rows=targets)

    employee_names = [row.get("name") for row in eligible if row.get("name")]
    ack_rows = (
        frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": policy_version,
                "acknowledged_for": "Staff",
                "context_doctype": "Employee",
                "context_name": ["in", tuple(employee_names)],
            },
            fields=["context_name", "acknowledged_at", "acknowledged_by"],
            order_by="acknowledged_at desc",
            limit_page_length=0,
        )
        if employee_names
        else []
    )

    ack_by_employee: dict[str, dict] = {}
    for row in ack_rows:
        context_name = (row.get("context_name") or "").strip()
        if not context_name or context_name in ack_by_employee:
            continue
        ack_by_employee[context_name] = row

    rows = []
    for employee in eligible:
        employee_name = (employee.get("name") or "").strip()
        ack = ack_by_employee.get(employee_name)
        rows.append(
            {
                "employee": employee_name,
                "employee_name": employee.get("employee_full_name") or employee_name,
                "user_id": employee.get("user_id"),
                "organization": employee.get("organization"),
                "school": employee.get("school"),
                "employee_group": employee.get("employee_group"),
                "is_signed": bool(ack),
                "acknowledged_at": ack.get("acknowledged_at") if ack else None,
                "acknowledged_by": ack.get("acknowledged_by") if ack else None,
            }
        )

    signed_count = sum(1 for row in rows if row["is_signed"])
    pending_count = len(rows) - signed_count

    pending_rows = [row for row in rows if not row["is_signed"]][:limit]
    signed_rows = sorted(
        [row for row in rows if row["is_signed"]],
        key=lambda row: str(row.get("acknowledged_at") or ""),
        reverse=True,
    )[:limit]

    return {
        "summary": {
            "policy_version": policy_version,
            "institutional_policy": policy_row.get("institutional_policy"),
            "policy_key": policy_row.get("policy_key"),
            "policy_title": policy_row.get("policy_title"),
            "version_label": policy_row.get("version_label"),
            "effective_from": policy_row.get("effective_from"),
            "effective_to": policy_row.get("effective_to"),
            "organization": organization,
            "school": school,
            "employee_group": employee_group,
            "target_employee_rows": len(targets),
            "eligible_users": len(rows),
            "signed": signed_count,
            "pending": pending_count,
            "completion_pct": _completion_pct(signed_count, len(rows)),
            "skipped_scope": skipped_scope,
        },
        "breakdowns": {
            "by_organization": _build_breakdown(rows, field="organization"),
            "by_school": _build_breakdown(rows, field="school"),
            "by_employee_group": _build_breakdown(rows, field="employee_group"),
        },
        "rows": {
            "pending": pending_rows,
            "signed": signed_rows,
        },
    }
