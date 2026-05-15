# ifitwala_ed/api/guardian_policy.py

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.api.guardian_home import _resolve_guardian_scope
from ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement import (
    get_policy_version_acknowledgement_clauses_map,
    populate_policy_acknowledgement_evidence,
)
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import (
    GUARDIAN_ACK_MODE_CHILD,
    ensure_policy_applies_to_storage,
    normalize_guardian_acknowledgement_mode,
    policy_applies_to_filter_sql,
)
from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def _as_bool(value) -> bool:
    return bool(frappe.utils.cint(value))


def _normalize_signature_name(value: str | None) -> str:
    return " ".join((value or "").strip().split()).casefold()


def _expected_guardian_signature_name(guardian_name: str) -> str:
    guardian_label = frappe.db.get_value("Guardian", guardian_name, "guardian_full_name")
    return (guardian_label or guardian_name or "").strip()


def _guardian_has_primary_signer_authority(guardian_name: str) -> bool:
    guardian_name = (guardian_name or "").strip()
    if not guardian_name:
        return False
    return bool(frappe.utils.cint(frappe.db.get_value("Guardian", guardian_name, "is_primary_guardian") or 0))


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


def get_guardian_policy_home_summary(*, guardian_name: str, children: list[dict[str, Any]]) -> dict[str, Any]:
    guardian_name = (guardian_name or "").strip()
    if not guardian_name:
        return {"pending_count": 0, "items": []}

    authorized_children = _children_with_signer_authority(guardian_name=guardian_name, children=children or [])
    rows = _get_guardian_policy_rows(guardian_name=guardian_name, children=authorized_children)
    pending_rows = [row for row in rows if not row.get("is_acknowledged")]
    return {
        "pending_count": len(pending_rows),
        "items": [
            {
                "policy_version": row.get("policy_version") or "",
                "policy_title": row.get("policy_title") or "",
                "version_label": row.get("version_label") or "",
                "description": _guardian_home_policy_description(row),
                "status_label": _("Pending acknowledgement"),
                "href": {
                    "name": "guardian-policies",
                    "query": {"policy_version": row.get("policy_version") or ""},
                },
            }
            for row in pending_rows[:3]
        ],
    }


def _guardian_home_policy_description(row: dict[str, Any]) -> str:
    description = (row.get("description") or "").strip()
    scope_label = (row.get("scope_label") or "").strip()
    if not scope_label or scope_label == _("Family acknowledgement"):
        return description
    if not description:
        return scope_label
    return _("{scope}: {description}").format(scope=scope_label, description=description)


@frappe.whitelist()
def acknowledge_guardian_policy(
    policy_version: str,
    context_name: str | None = None,
    typed_signature_name: str | None = None,
    attestation_confirmed: int | str | bool | None = None,
    checked_clause_names=None,
) -> dict[str, Any]:
    version = (policy_version or "").strip()
    if not version:
        frappe.throw(_("Policy Version is required."))

    user = frappe.session.user
    guardian_name, children = _resolve_guardian_scope(user)
    candidate_rows = _get_guardian_policy_rows(guardian_name=guardian_name, children=children)
    requested_context_name = (context_name or "").strip()
    selected_rows = [row for row in candidate_rows if (row.get("policy_version") or "").strip() == version]
    if requested_context_name:
        selected_rows = [
            row for row in selected_rows if (row.get("ack_context_name") or "").strip() == requested_context_name
        ]
    if not selected_rows:
        frappe.throw(_("You do not have permission to acknowledge this policy."), frappe.PermissionError)
    if len(selected_rows) > 1:
        frappe.throw(
            _("Choose the exact child acknowledgement row before signing this policy."),
            frappe.ValidationError,
        )
    selected_row = selected_rows[0]
    ack_context_doctype = (selected_row.get("ack_context_doctype") or "Guardian").strip()
    ack_context_name = (selected_row.get("ack_context_name") or guardian_name).strip()

    existing_name = frappe.db.get_value(
        "Policy Acknowledgement",
        {
            "policy_version": version,
            "acknowledged_for": "Guardian",
            "context_doctype": ack_context_doctype,
            "context_name": ack_context_name,
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

    expected_signature_name = _expected_guardian_signature_name(guardian_name)
    normalized_typed_name = _normalize_signature_name(typed_signature_name)
    expected_candidates = {
        normalized
        for normalized in {
            _normalize_signature_name(expected_signature_name),
            _normalize_signature_name(guardian_name),
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
            "acknowledged_for": "Guardian",
            "context_doctype": ack_context_doctype,
            "context_name": ack_context_name,
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


def _get_guardian_policy_rows(*, guardian_name: str, children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    schema_check = ensure_policy_applies_to_storage(caller="_get_guardian_policy_rows")
    if not schema_check.get("ok") or not children:
        return []

    child_contexts = _resolve_authorized_child_contexts(children)
    if not child_contexts:
        return []

    policy_contexts = _policy_contexts_from_authorized_children(child_contexts) or _resolve_policy_contexts(
        child_contexts
    )
    if not policy_contexts:
        return []

    candidate_rows: dict[str, dict[str, Any]] = {}
    applicable_children_by_version: dict[str, list[dict[str, Any]]] = {}
    scope_cache: dict[tuple[str, str], list[dict[str, Any]]] = {}
    seen_children_by_version: dict[str, set[str]] = {}

    for policy_context in policy_contexts:
        scope_key = (policy_context["organization"], policy_context["school"])
        policy_rows = scope_cache.get(scope_key)
        if policy_rows is None:
            policy_rows = _query_policy_candidates_for_context(
                organization=policy_context["organization"],
                school=policy_context["school"],
            )
            scope_cache[scope_key] = policy_rows
        for row in policy_rows:
            version = (row.get("policy_version") or "").strip()
            if version and version not in candidate_rows:
                candidate_rows[version] = row

    for child_context in child_contexts:
        scope_key = (child_context["organization"], child_context["school"])
        for row in scope_cache.get(scope_key) or []:
            version = (row.get("policy_version") or "").strip()
            if not version:
                continue
            seen_students = seen_children_by_version.setdefault(version, set())
            student_name = child_context["student"]
            if student_name in seen_students:
                continue
            seen_students.add(student_name)
            applicable_children_by_version.setdefault(version, []).append(child_context)

    rows = list(candidate_rows.values())
    if not rows:
        return []

    versions = [row["policy_version"] for row in rows if row.get("policy_version")]
    family_ack_rows = frappe.get_all(
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
    family_ack_map = {}
    for row in family_ack_rows:
        version = (row.get("policy_version") or "").strip()
        if version and version not in family_ack_map:
            family_ack_map[version] = row

    child_ack_rows = (
        frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": ["in", versions],
                "acknowledged_for": "Guardian",
                "context_doctype": "Student",
                "context_name": ["in", tuple([child["student"] for child in child_contexts])],
                "docstatus": 1,
            },
            fields=["name", "policy_version", "context_name", "acknowledged_by", "acknowledged_at"],
            order_by="acknowledged_at desc",
        )
        if child_contexts
        else []
    )
    child_ack_map: dict[tuple[str, str], dict[str, Any]] = {}
    for row in child_ack_rows:
        version = (row.get("policy_version") or "").strip()
        student_name = (row.get("context_name") or "").strip()
        key = (version, student_name)
        if version and student_name and key not in child_ack_map:
            child_ack_map[key] = row

    clauses_by_version = get_policy_version_acknowledgement_clauses_map(versions)
    expected_signature_name = _expected_guardian_signature_name(guardian_name)
    out: list[dict[str, Any]] = []
    for row in rows:
        version = (row.get("policy_version") or "").strip()
        guardian_mode = normalize_guardian_acknowledgement_mode(row.get("guardian_acknowledgement_mode"))
        if guardian_mode == GUARDIAN_ACK_MODE_CHILD:
            for child_context in applicable_children_by_version.get(version, []):
                acknowledgement = child_ack_map.get((version, child_context["student"]), {})
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
                        "guardian_acknowledgement_mode": guardian_mode,
                        "scope_label": child_context["student_label"],
                        "ack_context_doctype": "Student",
                        "ack_context_name": child_context["student"],
                        "is_acknowledged": bool(acknowledgement),
                        "acknowledged_at": str(acknowledgement.get("acknowledged_at") or ""),
                        "acknowledged_by": acknowledgement.get("acknowledged_by") or "",
                    }
                )
            continue

        acknowledgement = family_ack_map.get(version, {})
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
                "guardian_acknowledgement_mode": guardian_mode,
                "scope_label": _("Family acknowledgement"),
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
            row.get("scope_label") or "",
        )
    )
    return out


def _children_with_signer_authority(*, guardian_name: str, children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not guardian_name or not children:
        return []
    if not _guardian_has_primary_signer_authority(guardian_name):
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


def _policy_contexts_from_authorized_children(children: list[dict[str, Any]]) -> list[dict[str, str]]:
    contexts: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for child in children:
        organization = (child.get("organization") or "").strip()
        school = (child.get("school") or "").strip()
        if not organization or not school:
            continue
        key = (organization, school)
        if key in seen:
            continue
        seen.add(key)
        contexts.append({"organization": organization, "school": school})
    return contexts


def _resolve_policy_contexts(children: list[dict[str, Any]]) -> list[dict[str, str]]:
    if not children:
        return []

    direct_contexts: list[dict[str, str]] = []
    seen_direct: set[tuple[str, str]] = set()
    missing_school_context = False
    for child in children:
        school = (child.get("school") or "").strip()
        organization = (child.get("organization") or "").strip()
        if not school:
            continue
        if organization:
            key = (organization, school)
            if key in seen_direct:
                continue
            seen_direct.add(key)
            direct_contexts.append({"organization": organization, "school": school})
            continue
        missing_school_context = True
    if direct_contexts and not missing_school_context:
        return direct_contexts

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


def _resolve_authorized_child_contexts(children: list[dict[str, Any]]) -> list[dict[str, str]]:
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
    seen_students: set[str] = set()
    for child in children:
        student_name = (child.get("student") or "").strip()
        school = (child.get("school") or "").strip()
        organization = (school_map.get(school, {}).get("organization") or "").strip()
        if not student_name or not school or not organization or student_name in seen_students:
            continue
        seen_students.add(student_name)
        contexts.append(
            {
                "student": student_name,
                "student_label": (
                    child.get("full_name")
                    or child.get("student_name")
                    or child.get("student_full_name")
                    or student_name
                ).strip(),
                "organization": organization,
                "school": school,
            }
        )
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
               pv.guardian_acknowledgement_mode AS guardian_acknowledgement_mode,
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
