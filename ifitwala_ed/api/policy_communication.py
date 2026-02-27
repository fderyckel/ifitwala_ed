# ifitwala_ed/api/policy_communication.py

from __future__ import annotations

from html import escape
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_days, add_to_date, get_datetime, getdate, now_datetime, today

from ifitwala_ed.api.policy_signature import launch_staff_policy_campaign
from ifitwala_ed.governance.policy_utils import ensure_policy_admin

SCOPE_ORGANIZATION_ALL_SCHOOLS = "organization_all_schools"
SCOPE_SCHOOL = "school"
SCOPE_TEAM = "team"


def _normalize_scope(scope: str | None) -> str:
    raw = (scope or "").strip().lower()
    if raw in {SCOPE_ORGANIZATION_ALL_SCHOOLS, "organization (all schools)", "organization"}:
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


def _default_recipient_flags(applies_to: str | None) -> dict[str, int]:
    token = (applies_to or "").strip()
    if token == "Student":
        return {"to_staff": 1, "to_students": 1, "to_guardians": 0, "to_community": 0}
    if token == "Guardian":
        return {"to_staff": 1, "to_students": 0, "to_guardians": 1, "to_community": 0}
    if token == "Applicant":
        return {"to_staff": 1, "to_students": 1, "to_guardians": 1, "to_community": 0}
    return {"to_staff": 1, "to_students": 0, "to_guardians": 0, "to_community": 0}


def _policy_row(policy_version: str) -> dict:
    row = frappe.db.sql(
        """
        SELECT
            pv.name AS policy_version,
            pv.version_label,
            pv.policy_text,
            pv.amended_from,
            pv.change_summary,
            pv.diff_html,
            pv.change_stats,
            ip.name AS institutional_policy,
            ip.policy_key,
            ip.policy_title,
            ip.applies_to,
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
    return row[0]


def _resolve_org_root_school(organization: str) -> str:
    schools = frappe.get_all(
        "School",
        filters={"organization": organization},
        fields=["name", "lft", "rgt"],
        order_by="lft asc",
        limit_page_length=0,
    )
    if not schools:
        frappe.throw(_("No schools were found for this organization."))

    root = schools[0]
    root_lft = int(root.get("lft") or 0)
    root_rgt = int(root.get("rgt") or 0)
    if root_lft <= 0 or root_rgt <= 0:
        frappe.throw(_("School hierarchy is not initialized. Please rebuild School tree."))

    for school in schools:
        lft = int(school.get("lft") or 0)
        rgt = int(school.get("rgt") or 0)
        if lft < root_lft or rgt > root_rgt:
            frappe.throw(
                _("Organization has multiple school roots. Choose School or Team scope for this communication.")
            )

    return (root.get("name") or "").strip()


def _get_organization_schools(organization: str) -> list[str]:
    schools = frappe.get_all(
        "School",
        filters={"organization": organization},
        fields=["name"],
        order_by="lft asc, name asc",
        limit_page_length=0,
    )
    return [(row.get("name") or "").strip() for row in schools if (row.get("name") or "").strip()]


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
    policy_url = f"/app/policy-version/{quote((row.get('policy_version') or '').strip())}"

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
    message_parts.append(f'<hr><p><a href="{policy_url}">Open policy version in Desk</a></p>')
    return "".join(message_parts)


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
    to_community: int | str | bool | None = None,
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

    scope = _normalize_scope(target_scope)
    if not scope:
        scope = SCOPE_SCHOOL if policy_school else SCOPE_ORGANIZATION_ALL_SCHOOLS

    target_school = (target_school or "").strip() or None
    target_team = (target_team or "").strip() or None
    campaign_employee_group = (campaign_employee_group or "").strip() or None
    explicit_recipient_payload = any(value is not None for value in (to_staff, to_students, to_guardians, to_community))
    if explicit_recipient_payload:
        recipient_flags = {
            "to_staff": 1 if frappe.utils.cint(to_staff) else 0,
            "to_students": 1 if frappe.utils.cint(to_students) else 0,
            "to_guardians": 1 if frappe.utils.cint(to_guardians) else 0,
            "to_community": 1 if frappe.utils.cint(to_community) else 0,
        }
    else:
        recipient_flags = _default_recipient_flags(row.get("applies_to"))
    if not any(recipient_flags.values()):
        frappe.throw(_("Select at least one recipient type."))

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

        resolved_school = (
            (target_school or "")
            or (team_row.get("school") or "")
            or policy_school
            or _resolve_org_root_school(policy_organization)
        ).strip()
        if not resolved_school:
            frappe.throw(_("Could not resolve Issuing School for Team scope communication."))
        if (
            recipient_flags.get("to_students")
            or recipient_flags.get("to_guardians")
            or recipient_flags.get("to_community")
        ):
            frappe.throw(_("Team scope supports Staff recipients only."))

        audience_rows = [
            {
                "target_mode": "Team",
                "team": target_team,
                **recipient_flags,
            }
        ]
    else:
        if scope == SCOPE_ORGANIZATION_ALL_SCHOOLS:
            resolved_school = _resolve_org_root_school(policy_organization)
            org_schools = _get_organization_schools(policy_organization)
            if not org_schools:
                frappe.throw(_("No schools were found for this organization."))
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
                + (f" (amended from {row.get('amended_from')})" if row.get("amended_from") else "")
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
