# ifitwala_ed/api/student_policy.py

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement import (
    get_policy_version_acknowledgement_clauses_map,
    populate_policy_acknowledgement_evidence,
)
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_applies_to_storage, policy_applies_to_filter_sql
from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def _as_bool(value) -> bool:
    return bool(frappe.utils.cint(value))


def _normalize_signature_name(value: str | None) -> str:
    return " ".join((value or "").strip().split()).casefold()


def _require_student_name_for_session_user() -> str:
    user = frappe.session.user
    if user == "Guest":
        frappe.throw(_("You must be logged in to view this page."), frappe.AuthenticationError)

    roles = set(frappe.get_roles(user))
    if "Student" not in roles:
        frappe.throw(_("Student access is required."), frappe.PermissionError)

    student_name = frappe.db.get_value("Student", {"student_email": user}, "name")
    if not student_name:
        frappe.throw(_("No student profile linked to this login yet."), frappe.PermissionError)
    return str(student_name).strip()


def _expected_student_signature_name(student_name: str) -> str:
    row = frappe.db.get_value(
        "Student",
        student_name,
        ["student_preferred_name", "student_full_name"],
        as_dict=True,
    )
    return (
        (row or {}).get("student_preferred_name") or (row or {}).get("student_full_name") or student_name or ""
    ).strip()


@frappe.whitelist()
def get_student_policy_overview() -> dict[str, Any]:
    user = frappe.session.user
    student_name = _require_student_name_for_session_user()
    rows = _get_student_policy_rows(student_name=student_name)

    acknowledged = sum(1 for row in rows if row.get("is_acknowledged"))
    total = len(rows)

    return {
        "meta": {
            "generated_at": now_datetime().isoformat(),
            "student": {"name": student_name},
        },
        "counts": {
            "total_policies": total,
            "acknowledged_policies": acknowledged,
            "pending_policies": total - acknowledged,
        },
        "rows": rows,
        "identity": {
            "student": student_name,
            "user": user,
        },
    }


@frappe.whitelist()
def acknowledge_student_policy(
    policy_version: str,
    typed_signature_name: str | None = None,
    attestation_confirmed: int | str | bool | None = None,
    checked_clause_names=None,
) -> dict[str, Any]:
    version = (policy_version or "").strip()
    if not version:
        frappe.throw(_("Policy Version is required."))

    user = frappe.session.user
    student_name = _require_student_name_for_session_user()
    candidate_rows = _get_student_policy_rows(student_name=student_name)
    candidate_versions = {(row.get("policy_version") or "").strip() for row in candidate_rows}
    if version not in candidate_versions:
        frappe.throw(_("You do not have permission to acknowledge this policy."), frappe.PermissionError)

    existing_name = frappe.db.get_value(
        "Policy Acknowledgement",
        {
            "policy_version": version,
            "acknowledged_by": user,
            "acknowledged_for": "Student",
            "context_doctype": "Student",
            "context_name": student_name,
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

    expected_signature_name = _expected_student_signature_name(student_name)
    normalized_typed_name = _normalize_signature_name(typed_signature_name)
    expected_candidates = {
        normalized
        for normalized in {
            _normalize_signature_name(expected_signature_name),
            _normalize_signature_name(student_name),
        }
        if normalized
    }
    if not _as_bool(attestation_confirmed):
        frappe.throw(
            _("You must confirm the electronic signature attestation before signing."),
            frappe.ValidationError,
        )
    if not normalized_typed_name:
        frappe.throw(_("Type your full name as your electronic signature."), frappe.ValidationError)
    if expected_candidates and normalized_typed_name not in expected_candidates:
        frappe.throw(
            _("Typed signature must match exactly: {expected_name}").format(expected_name=expected_signature_name),
            frappe.ValidationError,
        )

    acknowledgement = frappe.get_doc(
        {
            "doctype": "Policy Acknowledgement",
            "policy_version": version,
            "acknowledged_by": user,
            "acknowledged_for": "Student",
            "context_doctype": "Student",
            "context_name": student_name,
        }
    )
    populate_policy_acknowledgement_evidence(
        acknowledgement,
        typed_signature_name=typed_signature_name,
        attestation_confirmed=attestation_confirmed,
        checked_clause_names=checked_clause_names,
    )
    acknowledgement.insert()

    return {
        "ok": True,
        "status": "acknowledged",
        "acknowledgement_name": acknowledgement.name,
        "policy_version": version,
    }


def get_student_policy_home_summary(student_name: str) -> dict[str, Any]:
    student_name = (student_name or "").strip()
    if not student_name:
        return {"pending_count": 0, "items": []}

    rows = _get_student_policy_rows(student_name=student_name)
    pending_rows = [row for row in rows if not row.get("is_acknowledged")]
    return {
        "pending_count": len(pending_rows),
        "items": [
            {
                "policy_version": row.get("policy_version") or "",
                "policy_title": row.get("policy_title") or "",
                "version_label": row.get("version_label") or "",
                "description": row.get("description") or "",
                "status_label": _("Pending acknowledgement"),
                "href": {
                    "name": "student-policies",
                    "query": {"policy_version": row.get("policy_version") or ""},
                },
            }
            for row in pending_rows[:3]
        ],
    }


def _get_student_policy_rows(*, student_name: str) -> list[dict[str, Any]]:
    schema_check = ensure_policy_applies_to_storage(caller="_get_student_policy_rows")
    if not schema_check.get("ok") or not student_name:
        return []

    student_row = frappe.db.get_value(
        "Student",
        student_name,
        ["anchor_school", "student_full_name", "student_preferred_name"],
        as_dict=True,
    )
    school = ((student_row or {}).get("anchor_school") or "").strip()
    if not school:
        return []

    organization = (frappe.db.get_value("School", school, "organization") or "").strip()
    if not organization:
        return []

    rows = _query_policy_candidates_for_context(organization=organization, school=school)
    if not rows:
        return []

    versions = [row["policy_version"] for row in rows if row.get("policy_version")]
    ack_rows = frappe.get_all(
        "Policy Acknowledgement",
        filters={
            "policy_version": ["in", versions],
            "acknowledged_for": "Student",
            "context_doctype": "Student",
            "context_name": student_name,
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

    clauses_by_version = get_policy_version_acknowledgement_clauses_map(versions)
    expected_signature_name = _expected_student_signature_name(student_name)
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
                "policy_text": sanitize_html(row.get("policy_text") or "", allow_headings_from="h2"),
                "effective_from": str(row.get("effective_from") or ""),
                "effective_to": str(row.get("effective_to") or ""),
                "approved_on": str(row.get("approved_on") or ""),
                "expected_signature_name": expected_signature_name,
                "acknowledgement_clauses": clauses_by_version.get(version, []),
                "ack_context_doctype": "Student",
                "ack_context_name": student_name,
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
        (*params, *school_params, "Student"),
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
