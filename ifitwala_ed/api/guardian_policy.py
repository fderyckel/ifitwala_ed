# ifitwala_ed/api/guardian_policy.py

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.api.guardian_home import _resolve_guardian_scope
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_applies_to_storage, policy_applies_to_filter_sql


@frappe.whitelist()
def get_guardian_policy_overview() -> dict[str, Any]:
    user = frappe.session.user
    guardian_name, children = _resolve_guardian_scope(user)
    children = _children_with_signer_authority(guardian_name=guardian_name, children=children)
    rows = _get_guardian_policy_rows(guardian_name=guardian_name, children=children)

    acknowledged = sum(1 for row in rows if row.get("is_acknowledged"))
    total = len(rows)

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "guardian": {"name": guardian_name},
        },
        "family": {"children": children},
        "counts": {
            "total_policies": total,
            "acknowledged_policies": acknowledged,
            "pending_policies": total - acknowledged,
        },
        "rows": rows,
    }


@frappe.whitelist()
def acknowledge_guardian_policy(policy_version: str) -> dict[str, Any]:
    version = (policy_version or "").strip()
    if not version:
        frappe.throw(_("Policy Version is required."))

    user = frappe.session.user
    guardian_name, children = _resolve_guardian_scope(user)
    candidate_rows = _get_guardian_policy_rows(guardian_name=guardian_name, children=children)
    candidate_versions = {(row.get("policy_version") or "").strip() for row in candidate_rows}
    if version not in candidate_versions:
        frappe.throw(_("You do not have permission to acknowledge this policy."), frappe.PermissionError)

    existing_name = frappe.db.get_value(
        "Policy Acknowledgement",
        {
            "policy_version": version,
            "acknowledged_by": user,
            "acknowledged_for": "Guardian",
            "context_doctype": "Guardian",
            "context_name": guardian_name,
            "docstatus": 1,
        },
        "name",
    )
    if existing_name:
        return {
            "ok": True,
            "status": "already_acknowledged",
            "acknowledgement_name": existing_name,
            "policy_version": version,
        }

    acknowledgement = frappe.get_doc(
        {
            "doctype": "Policy Acknowledgement",
            "policy_version": version,
            "acknowledged_by": user,
            "acknowledged_for": "Guardian",
            "context_doctype": "Guardian",
            "context_name": guardian_name,
        }
    )
    acknowledgement.insert()

    return {
        "ok": True,
        "status": "acknowledged",
        "acknowledgement_name": acknowledgement.name,
        "policy_version": version,
    }


def _get_guardian_policy_rows(*, guardian_name: str, children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schema_check = ensure_policy_applies_to_storage(caller="_get_guardian_policy_rows")
    if not schema_check.get("ok") or not children:
        return []

    candidate_rows: dict[str, dict[str, Any]] = {}
    for context in _resolve_policy_contexts(children):
        for row in _query_policy_candidates_for_context(
            organization=context["organization"],
            school=context["school"],
        ):
            version = (row.get("policy_version") or "").strip()
            if version and version not in candidate_rows:
                candidate_rows[version] = row

    rows = list(candidate_rows.values())
    if not rows:
        return []

    versions = [row["policy_version"] for row in rows if row.get("policy_version")]
    ack_rows = frappe.get_all(
        "Policy Acknowledgement",
        filters={
            "policy_version": ["in", versions],
            "acknowledged_for": "Guardian",
            "context_doctype": "Guardian",
            "context_name": guardian_name,
            "docstatus": 1,
        },
        fields=["name", "policy_version", "acknowledged_by", "acknowledged_at"],
        order_by="acknowledged_at desc",
    )
    ack_map = {}
    for row in ack_rows:
        version = (row.get("policy_version") or "").strip()
        if version and version not in ack_map:
            ack_map[version] = row

    out: list[dict[str, Any]] = []
    for row in rows:
        version = (row.get("policy_version") or "").strip()
        acknowledgement = ack_map.get(version, {})
        out.append(
            {
                "policy_name": row.get("policy_name"),
                "policy_key": row.get("policy_key"),
                "policy_title": row.get("policy_title"),
                "policy_category": row.get("policy_category"),
                "policy_version": version,
                "version_label": row.get("version_label"),
                "organization": row.get("policy_organization"),
                "school": row.get("policy_school"),
                "description": row.get("description") or "",
                "policy_text": row.get("policy_text") or "",
                "effective_from": str(row.get("effective_from") or ""),
                "effective_to": str(row.get("effective_to") or ""),
                "approved_on": str(row.get("approved_on") or ""),
                "ack_context_doctype": "Guardian",
                "ack_context_name": guardian_name,
                "is_acknowledged": bool(acknowledgement),
                "acknowledged_at": str(acknowledgement.get("acknowledged_at") or ""),
                "acknowledged_by": acknowledgement.get("acknowledged_by") or "",
            }
        )

    out.sort(
        key=lambda row: (
            0 if not row.get("is_acknowledged") else 1,
            row.get("policy_category") or "",
            row.get("policy_title") or "",
        )
    )
    return out


def _children_with_signer_authority(*, guardian_name: str, children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not guardian_name or not children:
        return []

    if not frappe.db.has_column("Student Guardian", "can_consent"):
        return children

    student_names = sorted(
        {(child.get("student") or "").strip() for child in children if (child.get("student") or "").strip()}
    )
    if not student_names:
        return []

    allowed_rows = frappe.get_all(
        "Student Guardian",
        filters={
            "guardian": guardian_name,
            "parent": ["in", tuple(student_names)],
            "parenttype": "Student",
            "parentfield": "guardians",
            "can_consent": 1,
        },
        fields=["parent"],
        limit=0,
    )
    allowed_students = {(row.get("parent") or "").strip() for row in allowed_rows if (row.get("parent") or "").strip()}
    if not allowed_students:
        return []

    return [child for child in children if (child.get("student") or "").strip() in allowed_students]


def _resolve_policy_contexts(children: list[dict[str, Any]]) -> list[dict[str, str]]:
    school_names = sorted(
        {(child.get("school") or "").strip() for child in children if (child.get("school") or "").strip()}
    )
    if not school_names:
        return []

    school_rows = frappe.get_all(
        "School",
        filters={"name": ["in", school_names]},
        fields=["name", "organization"],
    )
    school_map = {row.get("name"): row for row in school_rows if row.get("name")}

    contexts: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for child in children:
        school = (child.get("school") or "").strip()
        organization = (school_map.get(school, {}).get("organization") or "").strip()
        if not school or not organization:
            continue
        key = (organization, school)
        if key in seen:
            continue
        seen.add(key)
        contexts.append({"organization": organization, "school": school})
    return contexts


def _query_policy_candidates_for_context(*, organization: str, school: str) -> list[dict[str, Any]]:
    ancestor_orgs = get_organization_ancestors_including_self(organization)
    if not ancestor_orgs:
        return []

    school_ancestors = get_school_ancestors_including_self(school)
    org_placeholders = ", ".join(["%s"] * len(ancestor_orgs))
    params: list[str] = list(ancestor_orgs)
    school_params: list[str] = []

    school_scope_sql = " AND (ip.school IS NULL OR ip.school = '')"
    if school_ancestors:
        school_placeholders = ", ".join(["%s"] * len(school_ancestors))
        school_scope_sql = f" AND (ip.school IS NULL OR ip.school = '' OR ip.school IN ({school_placeholders}))"
        school_params.extend(school_ancestors)

    rows = frappe.db.sql(
        f"""
        SELECT ip.name AS policy_name,
               ip.policy_key AS policy_key,
               ip.policy_title AS policy_title,
               ip.policy_category AS policy_category,
               ip.description AS description,
               ip.organization AS policy_organization,
               ip.school AS policy_school,
               pv.name AS policy_version,
               pv.version_label AS version_label,
               pv.policy_text AS policy_text,
               pv.effective_from AS effective_from,
               pv.effective_to AS effective_to,
               pv.approved_on AS approved_on
          FROM `tabInstitutional Policy` ip
          JOIN `tabPolicy Version` pv
            ON pv.institutional_policy = ip.name
         WHERE ip.is_active = 1
           AND pv.is_active = 1
           AND ip.organization IN ({org_placeholders})
           {school_scope_sql}
           AND {policy_applies_to_filter_sql(policy_alias="ip", audience_placeholder="%s")}
        """,
        (*params, *school_params, "Guardian"),
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
