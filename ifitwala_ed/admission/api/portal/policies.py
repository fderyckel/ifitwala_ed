# ifitwala_ed/admission/api/portal/policies.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission.access import (
    ADMISSIONS_ACCESS_MODE_FAMILY,
    ADMISSIONS_FAMILY_ROLE,
    get_admissions_access_mode,
    get_guardian_names_for_user,
)
from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE as ADMISSIONS_ROLE,
)
from ifitwala_ed.admission.api.common.request_payload import _as_bool
from ifitwala_ed.admission.api.portal.access import (
    _as_text,
    _ensure_applicant_match,
    _require_admissions_portal_user,
)
from ifitwala_ed.admission.api.portal.session import _build_applicant_display_name
from ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement import (
    get_policy_version_acknowledgement_clauses_map,
    populate_policy_acknowledgement_evidence,
)
from ifitwala_ed.governance.policy_utils import (
    ADMISSIONS_POLICY_MODE_FAMILY,
    get_applicant_policy_status,
)
from ifitwala_ed.utilities.html_sanitizer import sanitize_html


def _normalize_signature_name(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _find_family_guardian_context(*, student_applicant: str, user: str) -> str:
    direct_rows = frappe.get_all(
        "Student Applicant Guardian",
        filters={
            "parent": student_applicant,
            "parenttype": "Student Applicant",
            "parentfield": "guardians",
            "user": user,
            "can_consent": 1,
            "is_primary_guardian": 1,
        },
        fields=["guardian"],
        limit=5,
        order_by="is_primary desc, idx asc",
    )
    for row in direct_rows:
        guardian_name = (row.get("guardian") or "").strip()
        if guardian_name:
            return guardian_name

    guardian_names = get_guardian_names_for_user(user=user)
    if guardian_names:
        linked_rows = frappe.get_all(
            "Student Applicant Guardian",
            filters={
                "parent": student_applicant,
                "parenttype": "Student Applicant",
                "parentfield": "guardians",
                "guardian": ["in", guardian_names],
                "can_consent": 1,
                "is_primary_guardian": 1,
            },
            fields=["guardian"],
            limit=5,
            order_by="is_primary desc, idx asc",
        )
        for row in linked_rows:
            guardian_name = (row.get("guardian") or "").strip()
            if guardian_name:
                return guardian_name

    return ""


def _family_policy_blocked_reason(*, student_applicant: str, user: str) -> str:
    if _find_family_guardian_context(student_applicant=student_applicant, user=user):
        return ""

    roles = set(frappe.get_roles(user))
    if ADMISSIONS_ROLE in roles and ADMISSIONS_FAMILY_ROLE not in roles:
        if get_admissions_access_mode() != ADMISSIONS_ACCESS_MODE_FAMILY:
            return _(
                "This policy must be signed by an authorized family signer. Admissions is in single-applicant mode, "
                "so ask admissions staff to configure this policy as Child Acknowledgement or invite a family "
                "collaborator after enabling Family Workspace."
            )
        return _(
            "This policy must be signed by an authorized family collaborator. Ask admissions staff to invite your "
            "Admissions Family collaborator account for this applicant."
        )

    return _(
        "This policy must be signed by an authorized family collaborator. Ask admissions staff to check the "
        "Admissions Family collaborator signer link for this applicant."
    )


def _resolve_family_guardian_context(*, student_applicant: str, user: str) -> str:
    guardian_name = _find_family_guardian_context(student_applicant=student_applicant, user=user)
    if guardian_name:
        return guardian_name

    frappe.throw(
        _family_policy_blocked_reason(student_applicant=student_applicant, user=user),
        frappe.PermissionError,
    )


def get_applicant_policies_impl(student_applicant: str | None = None):
    user = _require_admissions_portal_user()
    row = _ensure_applicant_match(student_applicant, user)
    policy_status = get_applicant_policy_status(
        student_applicant=row.get("name"),
        organization=row.get("organization"),
        school=row.get("school"),
        user=user,
    )
    policy_rows = policy_status.get("rows") or []
    if not policy_rows:
        return {"policies": []}

    versions = [
        (row_policy.get("policy_version") or "").strip()
        for row_policy in policy_rows
        if row_policy.get("policy_version")
    ]
    version_rows = frappe.get_all(
        "Policy Version",
        filters={"name": ["in", versions]},
        fields=["name", "policy_text"],
        limit=max(20, len(versions)),
    )
    policy_text_by_version = {
        (row_version.get("name") or "").strip(): row_version.get("policy_text") or ""
        for row_version in version_rows
        if (row_version.get("name") or "").strip()
    }
    clauses_by_version = get_policy_version_acknowledgement_clauses_map(versions)
    family_guardian_context: str | None = None

    payload = []
    for row_policy in policy_rows:
        policy_version = row_policy.get("policy_version")
        acknowledgement_mode = row_policy.get("admissions_acknowledgement_mode")
        can_acknowledge = True
        blocked_reason = ""
        if acknowledgement_mode == ADMISSIONS_POLICY_MODE_FAMILY:
            if family_guardian_context is None:
                family_guardian_context = _find_family_guardian_context(student_applicant=row.get("name"), user=user)
            can_acknowledge = bool(family_guardian_context)
            if not can_acknowledge:
                blocked_reason = _family_policy_blocked_reason(student_applicant=row.get("name"), user=user)
        payload.append(
            {
                "name": row_policy.get("label"),
                "policy_version": policy_version,
                "content_html": sanitize_html(policy_text_by_version.get(policy_version, ""), allow_headings_from="h2"),
                "is_required": bool(row_policy.get("is_required")),
                "acknowledgement_mode": acknowledgement_mode,
                "is_acknowledged": bool(row_policy.get("is_acknowledged")),
                "acknowledged_at": row_policy.get("acknowledged_at"),
                "acknowledged_by": row_policy.get("acknowledged_by"),
                "can_acknowledge": can_acknowledge,
                "blocked_reason": blocked_reason,
                "expected_signature_name": row_policy.get("expected_signature_name") or "",
                "acknowledgement_clauses": clauses_by_version.get((policy_version or "").strip(), []),
            }
        )

    return {"policies": payload}


def acknowledge_policy_impl(
    *,
    policy_version: str | None = None,
    student_applicant: str | None = None,
    typed_signature_name: str | None = None,
    attestation_confirmed: int | str | bool | None = None,
    checked_clause_names=None,
):
    user = _require_admissions_portal_user()
    row = _ensure_applicant_match(student_applicant, user)

    if not policy_version:
        frappe.throw(_("policy_version is required."))

    policy_status = get_applicant_policy_status(
        student_applicant=row.get("name"),
        organization=row.get("organization"),
        school=row.get("school"),
        user=user,
    )
    selected_policy = next(
        (
            row_policy
            for row_policy in (policy_status.get("rows") or [])
            if (row_policy.get("policy_version") or "").strip() == (policy_version or "").strip()
        ),
        None,
    )
    if not selected_policy:
        frappe.throw(_("This policy is not assigned to the selected Applicant."), frappe.PermissionError)
    if selected_policy.get("is_acknowledged"):
        return {"ok": True, "acknowledged_at": selected_policy.get("acknowledged_at")}

    expected_signature_name = _as_text(
        selected_policy.get("expected_signature_name")
    ).strip() or _build_applicant_display_name(row)
    normalized_typed_name = _normalize_signature_name(typed_signature_name)
    expected_candidates = {
        normalized
        for normalized in {
            _normalize_signature_name(expected_signature_name),
            _normalize_signature_name(row.get("name")),
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

    acknowledged_for = "Applicant"
    context_doctype = "Student Applicant"
    context_name = row.get("name")
    if selected_policy.get("admissions_acknowledgement_mode") == ADMISSIONS_POLICY_MODE_FAMILY:
        acknowledged_for = "Guardian"
        context_doctype = "Guardian"
        context_name = _resolve_family_guardian_context(student_applicant=row.get("name"), user=user)

    doc = frappe.get_doc(
        {
            "doctype": "Policy Acknowledgement",
            "policy_version": policy_version,
            "acknowledged_by": user,
            "acknowledged_for": acknowledged_for,
            "context_doctype": context_doctype,
            "context_name": context_name,
        }
    )
    populate_policy_acknowledgement_evidence(
        doc,
        typed_signature_name=typed_signature_name,
        attestation_confirmed=attestation_confirmed,
        checked_clause_names=checked_clause_names,
    )
    doc.insert(ignore_permissions=True)

    return {"ok": True, "acknowledged_at": doc.acknowledged_at}
