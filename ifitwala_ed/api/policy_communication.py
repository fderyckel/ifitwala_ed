# ifitwala_ed/api/policy_communication.py

from __future__ import annotations

from html import escape
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, today

from ifitwala_ed.api.org_comm_utils import check_audience_match
from ifitwala_ed.api.policy_signature import (
    get_policy_version_history_rows,
    get_staff_policy_signature_state_for_user,
    launch_staff_policy_campaign,
)
from ifitwala_ed.governance.policy_scope_utils import is_policy_within_user_scope
from ifitwala_ed.governance.policy_utils import (
    ensure_policy_admin,
    get_policy_applies_to_tokens,
    get_policy_applies_to_tokens_for_policy,
)
from ifitwala_ed.utilities.employee_utils import get_descendant_organizations
from ifitwala_ed.utilities.html_sanitizer import sanitize_html
from ifitwala_ed.utilities.school_tree import get_descendant_schools

SCOPE_ORGANIZATION_STAFF = "organization_staff"
SCOPE_ORGANIZATION_ALL_SCHOOLS = "organization_all_schools"
SCOPE_SCHOOL = "school"
SCOPE_TEAM = "team"


def _normalize_scope(scope: str | None) -> str:
    raw = (scope or "").strip().lower()
    if raw in {SCOPE_ORGANIZATION_STAFF, "organization staff", "organization (all staff)"}:
        return SCOPE_ORGANIZATION_STAFF
    if raw in {SCOPE_ORGANIZATION_ALL_SCHOOLS, "organization (all schools)", "organization"}:
        return SCOPE_ORGANIZATION_ALL_SCHOOLS
    if raw == "schools in organization":
        return SCOPE_ORGANIZATION_ALL_SCHOOLS
    if raw == SCOPE_SCHOOL:
        return SCOPE_SCHOOL
    if raw == SCOPE_TEAM:
        return SCOPE_TEAM
    return ""


def _parse_change_stats(raw_stats) -> dict[str, int]:
    if not raw_stats:
        return {"added": 0, "removed": 0, "modified": 0}
    if isinstance(raw_stats, dict):
        source = raw_stats
    else:
        try:
            source = frappe.parse_json(raw_stats)
        except Exception:
            source = {}
    if not isinstance(source, dict):
        source = {}
    return {
        "added": int(source.get("added") or 0),
        "removed": int(source.get("removed") or 0),
        "modified": int(source.get("modified") or 0),
    }


def _default_recipient_flags(applies_to) -> dict[str, int]:
    tokens = set(get_policy_applies_to_tokens(applies_to))
    flags = {"to_staff": 1, "to_students": 0, "to_guardians": 0}
    if "Applicant" in tokens:
        flags["to_students"] = 1
        flags["to_guardians"] = 1
    if "Student" in tokens:
        flags["to_students"] = 1
    if "Guardian" in tokens:
        flags["to_guardians"] = 1
    return flags


def _is_staff_only_recipients(recipient_flags: dict[str, int]) -> bool:
    return bool(recipient_flags.get("to_staff")) and not any(
        recipient_flags.get(fieldname) for fieldname in ("to_students", "to_guardians")
    )


def _policy_row(policy_version: str) -> dict:
    row = frappe.db.sql(
        """
        SELECT
            pv.name AS policy_version,
            pv.version_label,
            pv.policy_text,
            pv.based_on_version,
            pv.change_summary,
            pv.diff_html,
            pv.change_stats,
            ip.name AS institutional_policy,
            ip.policy_key,
            ip.policy_title,
            ip.organization AS policy_organization,
            ip.school AS policy_school
        FROM `tabPolicy Version` pv
        JOIN `tabInstitutional Policy` ip
          ON ip.name = pv.institutional_policy
        WHERE pv.name = %(policy_version)s
        LIMIT 1
        """,
        {"policy_version": (policy_version or "").strip()},
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Policy Version was not found."))
    row_out = row[0]
    row_out["policy_text"] = sanitize_html(row_out.get("policy_text") or "", allow_headings_from="h2")
    row_out["applies_to_tokens"] = list(get_policy_applies_to_tokens_for_policy(row_out.get("institutional_policy")))
    return row_out


def _get_organization_schools(organization: str) -> list[str]:
    organization_scope = [org for org in (get_descendant_organizations(organization) or []) if org]
    if not organization_scope:
        organization_scope = [organization]
    schools = frappe.get_all(
        "School",
        filters={"organization": ["in", organization_scope]},
        fields=["name"],
        order_by="organization asc, lft asc, name asc",
        limit=0,
    )
    return [(row.get("name") or "").strip() for row in schools if (row.get("name") or "").strip()]


def _is_school_within_scope(root_school: str | None, target_school: str | None) -> bool:
    root_school = (root_school or "").strip()
    target_school = (target_school or "").strip()
    if not root_school or not target_school:
        return False
    if root_school == target_school:
        return True
    return target_school in set(get_descendant_schools(root_school) or [])


def _resolve_message_html(*, row: dict, override_html: str | None) -> str:
    if (override_html or "").strip():
        return override_html

    policy_label = (
        (row.get("policy_title") or "").strip()
        or (row.get("policy_key") or "").strip()
        or (row.get("institutional_policy") or "").strip()
        or (row.get("policy_version") or "").strip()
    )
    version_label = (row.get("version_label") or "").strip()
    summary = (row.get("change_summary") or "").strip()
    diff_html = (row.get("diff_html") or "").strip()
    stats = _parse_change_stats(row.get("change_stats"))
    policy_version = (row.get("policy_version") or "").strip()
    policy_url = f"#policy-inform?policy_version={quote(policy_version)}"
    desk_url = f"/app/policy-version/{quote(policy_version)}"
    inform_label = escape(_("Open Policy"))
    desk_label = escape(_("Version in Desk"))

    message_parts = [
        f"<h3>{escape(policy_label)}" + (f" - Version {escape(version_label)}" if version_label else "") + "</h3>",
    ]
    if summary:
        message_parts.append(f"<p><strong>What changed</strong><br>{escape(summary)}</p>")
    message_parts.append(
        f"<p>Added: {stats['added']}<br>Removed: {stats['removed']}<br>Modified: {stats['modified']}</p>"
    )
    if diff_html:
        message_parts.append("<hr><h4>Detailed changes</h4>")
        message_parts.append(diff_html)
    message_parts.append(
        "<hr>"
        + '<div class="mt-3 flex flex-wrap justify-end gap-2">'
        + f'<a href="{policy_url}" data-policy-inform="1" data-policy-version="{escape(policy_version)}" class="btn btn-primary">'
        + inform_label
        + "</a>"
        + f'<a href="{desk_url}" data-policy-inform="0" class="btn btn-quiet" target="_blank" rel="noopener">'
        + desk_label
        + "</a>"
        + "</div>"
    )
    return "".join(message_parts)


def _require_authenticated_user() -> str:
    user = (frappe.session.user or "").strip()
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)
    return user


def _get_active_employee_context(user: str) -> dict | None:
    return frappe.db.get_value(
        "Employee",
        {"user_id": user, "employment_status": "Active"},
        ["name", "school", "organization"],
        as_dict=True,
    )


def _get_policy_inform_employee_context(user: str, roles: list[str]) -> dict | None:
    employee = _get_active_employee_context(user)
    if not employee:
        return employee

    if "Academic Admin" not in (roles or []):
        return employee

    base_school = (employee.get("school") or "").strip()
    base_organization = (employee.get("organization") or "").strip()
    if base_school:
        school_names = [school for school in (get_descendant_schools(base_school) or []) if school]
        if school_names:
            employee["school_names"] = school_names
        return employee

    if not base_organization:
        return employee

    organization_names = [org for org in (get_descendant_organizations(base_organization) or []) if org]
    if organization_names:
        employee["organization_names"] = organization_names

    school_rows = frappe.get_all(
        "School",
        filters={"organization": ["in", organization_names]}
        if organization_names
        else {"organization": base_organization},
        pluck="name",
    )
    school_names = [school for school in (school_rows or []) if school]
    if school_names:
        employee["school_names"] = school_names

    return employee


def _is_policy_visible_via_org_communication(
    *,
    user: str,
    roles: list[str],
    employee: dict | None,
    policy_organization: str,
    policy_school: str,
    org_communication: str,
) -> bool:
    if not check_audience_match(org_communication, user, roles, employee, allow_owner=True):
        return False

    communication_row = frappe.db.get_value(
        "Org Communication",
        org_communication,
        ["organization", "school"],
        as_dict=True,
    )
    if not communication_row:
        return False

    communication_organization = (communication_row.get("organization") or "").strip()
    communication_school = (communication_row.get("school") or "").strip()

    if communication_organization != policy_organization:
        return False

    if not policy_school:
        return True

    return _is_school_within_scope(policy_school, communication_school)


@frappe.whitelist()
def create_policy_amendment_communication(
    *,
    policy_version: str | None = None,
    title: str | None = None,
    message_html: str | None = None,
    target_scope: str | None = None,
    target_school: str | None = None,
    target_team: str | None = None,
    brief_start_date: str | None = None,
    brief_end_date: str | None = None,
    publish_from: str | None = None,
    publish_to: str | None = None,
    create_signature_campaign: int | str | bool | None = None,
    campaign_employee_group: str | None = None,
    to_staff: int | str | bool | None = None,
    to_students: int | str | bool | None = None,
    to_guardians: int | str | bool | None = None,
):
    ensure_policy_admin()

    policy_version = (policy_version or "").strip()
    if not policy_version:
        frappe.throw(_("policy_version is required."))

    row = _policy_row(policy_version)
    policy_organization = (row.get("policy_organization") or "").strip()
    policy_school = (row.get("policy_school") or "").strip()
    if not policy_organization:
        frappe.throw(_("Policy organization is required to create communication."))

    target_school = (target_school or "").strip() or None
    target_team = (target_team or "").strip() or None
    campaign_employee_group = (campaign_employee_group or "").strip() or None
    explicit_recipient_payload = any(value is not None for value in (to_staff, to_students, to_guardians))
    if explicit_recipient_payload:
        recipient_flags = {
            "to_staff": 1 if frappe.utils.cint(to_staff) else 0,
            "to_students": 1 if frappe.utils.cint(to_students) else 0,
            "to_guardians": 1 if frappe.utils.cint(to_guardians) else 0,
        }
    else:
        recipient_flags = _default_recipient_flags(row.get("applies_to_tokens"))
    if not any(recipient_flags.values()):
        frappe.throw(_("Select at least one recipient type."))

    scope = _normalize_scope(target_scope)
    if not scope:
        scope = (
            SCOPE_SCHOOL
            if policy_school
            else SCOPE_ORGANIZATION_STAFF
            if _is_staff_only_recipients(recipient_flags)
            else SCOPE_ORGANIZATION_ALL_SCHOOLS
        )

    team_row = None
    resolved_school = ""
    audience_rows: list[dict] = []

    if scope == SCOPE_TEAM:
        if not target_team:
            frappe.throw(_("Team is required for Team scope communication."))
        team_row = frappe.db.get_value(
            "Team",
            target_team,
            ["name", "school", "organization"],
            as_dict=True,
        )
        if not team_row:
            frappe.throw(_("Selected Team does not exist."))
        if (team_row.get("organization") or "").strip() and (
            team_row.get("organization") or ""
        ).strip() != policy_organization:
            frappe.throw(_("Selected Team must belong to the same policy organization."))

        resolved_school = ((target_school or "") or (team_row.get("school") or "")).strip()
        if policy_school and not resolved_school:
            frappe.throw(_("Team scope on a school-scoped policy requires a team inside the policy school scope."))
        if policy_school and not _is_school_within_scope(policy_school, resolved_school):
            frappe.throw(_("Selected Team must belong to the policy school scope."))
        if recipient_flags.get("to_students") or recipient_flags.get("to_guardians"):
            frappe.throw(_("Team scope supports Staff recipients only."))

        audience_rows = [
            {
                "target_mode": "Team",
                "team": target_team,
                **recipient_flags,
            }
        ]
    elif scope == SCOPE_ORGANIZATION_STAFF:
        if policy_school:
            frappe.throw(_("Organization Staff scope is only available for organization-wide policies."))
        if not _is_staff_only_recipients(recipient_flags):
            frappe.throw(_("Organization Staff scope supports Staff recipients only."))
        audience_rows = [
            {
                "target_mode": "Organization",
                **recipient_flags,
            }
        ]
    else:
        if scope == SCOPE_ORGANIZATION_ALL_SCHOOLS:
            if policy_school:
                frappe.throw(_("Schools in Organization scope is not available for school-scoped policies."))
            org_schools = _get_organization_schools(policy_organization)
            if not org_schools:
                frappe.throw(
                    _(
                        "Schools in Organization scope requires at least one School in this organization or its child organizations."
                    )
                )
            audience_rows = [
                {
                    "target_mode": "School Scope",
                    "school": school_name,
                    "include_descendants": 0,
                    **recipient_flags,
                }
                for school_name in org_schools
            ]
        else:
            resolved_school = (target_school or policy_school or "").strip()
            if not resolved_school:
                frappe.throw(_("School is required for School scope communication."))
            if policy_school and not _is_school_within_scope(policy_school, resolved_school):
                frappe.throw(_("Selected School must be within the policy school scope."))

        if scope == SCOPE_SCHOOL:
            audience_rows = [
                {
                    "target_mode": "School Scope",
                    "school": resolved_school,
                    "include_descendants": 1,
                    **recipient_flags,
                }
            ]

    now_value = now_datetime()
    brief_start = getdate(brief_start_date) if brief_start_date else getdate(today())
    brief_end = getdate(brief_end_date) if brief_end_date else add_days(brief_start, 6)
    if brief_end < brief_start:
        frappe.throw(_("Brief End Date cannot be before Brief Start Date."))

    publish_from_value = get_datetime(publish_from) if publish_from else now_value
    publish_to_value = get_datetime(publish_to) if publish_to else add_to_date(publish_from_value, days=7)
    if publish_to_value < publish_from_value:
        frappe.throw(_("Publish Until cannot be before Publish From."))

    communication_title = (title or "").strip()
    if not communication_title:
        policy_label = (
            (row.get("policy_title") or "").strip()
            or (row.get("policy_key") or "").strip()
            or (row.get("institutional_policy") or "").strip()
            or policy_version
        )
        version_label = (row.get("version_label") or "").strip()
        communication_title = (
            f"{policy_label} - Version {version_label} update" if version_label else f"{policy_label} update"
        )

    communication_doc = frappe.get_doc(
        {
            "doctype": "Org Communication",
            "title": communication_title,
            "communication_type": "Policy Procedure",
            "status": "Draft",
            "priority": "Normal",
            "portal_surface": "Morning Brief",
            "publish_from": publish_from_value,
            "publish_to": publish_to_value,
            "brief_start_date": brief_start,
            "brief_end_date": brief_end,
            "school": resolved_school,
            "organization": policy_organization,
            "message": _resolve_message_html(row=row, override_html=message_html),
            "internal_note": (
                f"Generated from Policy Version {policy_version}"
                + (f" (based on {row.get('based_on_version')})" if row.get("based_on_version") else "")
            ),
            "audiences": audience_rows,
        }
    )
    communication_doc.insert()

    campaign_result = None
    if frappe.utils.cint(create_signature_campaign):
        campaign_school = None
        if scope == SCOPE_SCHOOL:
            campaign_school = resolved_school
        elif scope == SCOPE_TEAM:
            campaign_school = (team_row or {}).get("school") or resolved_school

        campaign_result = launch_staff_policy_campaign(
            policy_version=policy_version,
            organization=policy_organization,
            school=campaign_school or None,
            employee_group=campaign_employee_group,
            due_date=str(brief_end),
            message=_("Please review and sign the amended policy communication."),
            client_request_id=f"policy_comm_{frappe.generate_hash(length=12)}",
        )

    return {
        "ok": True,
        "communication": communication_doc.name,
        "communication_title": communication_doc.title,
        "communication_status": communication_doc.status,
        "organization": policy_organization,
        "school": resolved_school,
        "target_scope": scope,
        "audience_count": len(audience_rows),
        "campaign": campaign_result,
    }


@frappe.whitelist()
def get_policy_inform_payload(
    *,
    policy_version: str | None = None,
    org_communication: str | None = None,
):
    user = _require_authenticated_user()
    roles = frappe.get_roles(user)
    employee = _get_policy_inform_employee_context(user, roles)
    row = _policy_row((policy_version or "").strip())

    policy_organization = (row.get("policy_organization") or "").strip()
    policy_school = (row.get("policy_school") or "").strip()
    org_communication = (org_communication or "").strip()
    if not is_policy_within_user_scope(
        policy_organization=policy_organization,
        policy_school=policy_school,
        user=user,
    ):
        if not org_communication or not _is_policy_visible_via_org_communication(
            user=user,
            roles=roles,
            employee=employee,
            policy_organization=policy_organization,
            policy_school=policy_school,
            org_communication=org_communication,
        ):
            frappe.throw(_("You do not have permission to view this policy."), frappe.PermissionError)
    elif org_communication and not check_audience_match(org_communication, user, roles, employee, allow_owner=True):
        frappe.throw(_("You do not have permission to view this communication."), frappe.PermissionError)

    policy_label = (
        (row.get("policy_title") or "").strip()
        or (row.get("policy_key") or "").strip()
        or (row.get("institutional_policy") or "").strip()
        or (row.get("policy_version") or "").strip()
    )
    institutional_policy = (row.get("institutional_policy") or "").strip()
    signature_state = get_staff_policy_signature_state_for_user(
        policy_version=(row.get("policy_version") or "").strip(),
        institutional_policy=institutional_policy or None,
        user=user,
    )
    history_rows = get_policy_version_history_rows(institutional_policy)

    return {
        "policy_version": (row.get("policy_version") or "").strip(),
        "institutional_policy": institutional_policy or None,
        "policy_key": (row.get("policy_key") or "").strip() or None,
        "policy_title": (row.get("policy_title") or "").strip() or None,
        "policy_label": policy_label,
        "applies_to_tokens": list(row.get("applies_to_tokens") or []),
        "version_label": (row.get("version_label") or "").strip() or None,
        "policy_organization": policy_organization or None,
        "policy_school": policy_school or None,
        "based_on_version": (row.get("based_on_version") or "").strip() or None,
        "change_summary": (row.get("change_summary") or "").strip() or None,
        "change_stats": _parse_change_stats(row.get("change_stats")),
        "diff_html": row.get("diff_html") or "",
        "policy_text_html": sanitize_html(row.get("policy_text") or "", allow_headings_from="h2"),
        "history": history_rows,
        "signature_required": bool(signature_state.get("signature_required")),
        "acknowledgement_status": (signature_state.get("acknowledgement_status") or "").strip() or "informational",
        "acknowledged_at": signature_state.get("acknowledged_at"),
    }
