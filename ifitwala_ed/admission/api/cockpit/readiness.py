# ifitwala_ed/admission/api/cockpit/readiness.py

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.api.cockpit.access import _to_text
from ifitwala_ed.admission.api.recommendation_intake import get_recommendation_status_batch_for_applicants
from ifitwala_ed.admission.applicant_document_readiness import build_document_review_payload_batch
from ifitwala_ed.admission.doctype.student_applicant.student_applicant import STUDENT_PROFILE_REQUIRED_FIELD_LABELS
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import (
    ADMISSIONS_POLICY_MODE_FAMILY,
    ADMISSIONS_POLICY_MODE_OPTIONAL,
    ensure_policy_applies_to_storage,
    get_policy_admissions_acknowledgement_mode,
    institutional_policy_db_has_column,
    policy_applies_to_filter_sql,
)


def _value_present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(str(value).strip())


def _empty_readiness_snapshot() -> dict:
    return {
        "ready": False,
        "issues": [_("Readiness data unavailable")],
        "policies": {"ok": False, "missing": [], "required": [], "missing_rows": []},
        "documents": {
            "ok": False,
            "missing": [],
            "unapproved": [],
            "required": [],
            "missing_rows": [],
            "unapproved_rows": [],
        },
        "health": {
            "ok": False,
            "required_for_approval": True,
            "status": "missing",
            "profile_name": None,
            "review_status": None,
            "reviewed_by": None,
            "reviewed_on": None,
            "declared_complete": False,
            "declared_by": None,
            "declared_on": None,
        },
        "profile": {"ok": False, "missing": [], "required": []},
        "recommendations": {
            "ok": True,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [],
            "rows": [],
            "state": "optional",
            "counts": {},
            "review_rows": [],
            "pending_review_count": 0,
            "first_pending_review": None,
            "latest_submitted_on": None,
        },
    }


def _build_profile_state(applicant_row: dict) -> dict:
    missing_labels: list[str] = []
    required_labels: list[str] = []

    for fieldname, label in STUDENT_PROFILE_REQUIRED_FIELD_LABELS:
        required_labels.append(label)
        if not _value_present(applicant_row.get(fieldname)):
            missing_labels.append(label)

    return {
        "ok": not missing_labels,
        "missing": missing_labels,
        "required": required_labels,
    }


def _build_health_state(applicant_names: list[str]) -> dict[str, dict]:
    health_state_by_applicant: dict[str, dict] = {}

    if not applicant_names:
        return health_state_by_applicant

    rows = frappe.get_all(
        "Applicant Health Profile",
        filters={"student_applicant": ["in", applicant_names]},
        fields=[
            "name",
            "student_applicant",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "applicant_health_declared_complete",
            "applicant_health_declared_by",
            "applicant_health_declared_on",
            "modified",
        ],
        order_by="modified desc",
        limit=10000,
    )

    latest_by_applicant: dict[str, dict] = {}
    for row in rows:
        applicant_name = _to_text(row.get("student_applicant"))
        if not applicant_name or applicant_name in latest_by_applicant:
            continue
        latest_by_applicant[applicant_name] = row

    for applicant_name in applicant_names:
        profile_row = latest_by_applicant.get(applicant_name)
        if not profile_row:
            health_state_by_applicant[applicant_name] = {
                "ok": False,
                "required_for_approval": True,
                "status": "missing",
                "profile_name": None,
                "review_status": None,
                "reviewed_by": None,
                "reviewed_on": None,
                "declared_complete": False,
                "declared_by": None,
                "declared_on": None,
            }
            continue

        review_status = _to_text(profile_row.get("review_status"))
        if review_status == "Cleared":
            status = "complete"
            is_ok = True
        elif review_status == "Needs Follow-Up":
            status = "needs_follow_up"
            is_ok = False
        else:
            status = "pending"
            is_ok = False

        health_state_by_applicant[applicant_name] = {
            "ok": is_ok,
            "required_for_approval": True,
            "status": status,
            "profile_name": _to_text(profile_row.get("name")) or None,
            "review_status": review_status or None,
            "reviewed_by": _to_text(profile_row.get("reviewed_by")) or None,
            "reviewed_on": profile_row.get("reviewed_on"),
            "declared_complete": bool(cint(profile_row.get("applicant_health_declared_complete"))),
            "declared_by": _to_text(profile_row.get("applicant_health_declared_by")) or None,
            "declared_on": profile_row.get("applicant_health_declared_on"),
        }

    return health_state_by_applicant


def _build_documents_state(applicant_rows: list[dict], applicant_names: list[str]) -> dict[str, dict]:
    payload_by_applicant = build_document_review_payload_batch(applicant_rows)
    return {
        applicant_name: payload_by_applicant.get(applicant_name)
        or {
            "ok": False,
            "missing": [],
            "unapproved": [],
            "required": [],
            "required_rows": [],
            "uploaded_rows": [],
            "missing_rows": [],
            "unapproved_rows": [],
        }
        for applicant_name in applicant_names
    }


def _build_policy_state(applicant_rows: list[dict], applicant_names: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}

    schema_check = ensure_policy_applies_to_storage(caller="admission_cockpit.get_admissions_cockpit_data")
    if not schema_check.get("ok"):
        schema_message = _to_text(schema_check.get("message")) or _("Policy schema is not configured.")
        for applicant_name in applicant_names:
            out[applicant_name] = {
                "ok": False,
                "missing": [],
                "required": [],
                "missing_rows": [],
                "schema_error": schema_message,
            }
        return out

    org_ancestors_cache: dict[str, list[str]] = {}
    school_ancestors_cache: dict[str, list[str]] = {}
    all_ancestor_orgs: set[str] = set()
    all_school_ancestors: set[str] = set()

    for applicant_row in applicant_rows:
        organization = _to_text(applicant_row.get("organization"))
        school = _to_text(applicant_row.get("school"))

        if organization and organization not in org_ancestors_cache:
            org_ancestors_cache[organization] = get_organization_ancestors_including_self(organization) or []
            all_ancestor_orgs.update(org_ancestors_cache[organization])

        if school and school not in school_ancestors_cache:
            school_ancestors_cache[school] = get_school_ancestors_including_self(school) or []
            all_school_ancestors.update(school_ancestors_cache[school])

    policy_rows: list[dict] = []
    if all_ancestor_orgs:
        org_values = sorted(all_ancestor_orgs)
        org_placeholders = ", ".join(["%s"] * len(org_values))

        school_scope_sql = ""
        school_params: tuple[str, ...] = ()
        if all_school_ancestors:
            school_values = sorted(all_school_ancestors)
            school_placeholders = ", ".join(["%s"] * len(school_values))
            school_scope_sql = f" OR ip.school IN ({school_placeholders})"
            school_params = tuple(school_values)

        mode_select_sql = (
            "ip.admissions_acknowledgement_mode AS admissions_acknowledgement_mode,"
            if institutional_policy_db_has_column("admissions_acknowledgement_mode")
            else "'Child Acknowledgement' AS admissions_acknowledgement_mode,"
        )
        policy_rows = frappe.db.sql(
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
            (*org_values, *school_params, "Applicant"),
            as_dict=True,
        )

    policy_rows_by_applicant: dict[str, list[dict]] = {}
    all_policy_versions: set[str] = set()

    for applicant_row in applicant_rows:
        applicant_name = _to_text(applicant_row.get("name"))
        organization = _to_text(applicant_row.get("organization"))
        school = _to_text(applicant_row.get("school"))

        if not applicant_name:
            continue

        if not organization:
            out[applicant_name] = {
                "ok": False,
                "missing": [],
                "required": [],
                "missing_rows": [],
            }
            policy_rows_by_applicant[applicant_name] = []
            continue

        ancestor_orgs = org_ancestors_cache.get(organization) or []
        school_ancestors = school_ancestors_cache.get(school) or []

        if not ancestor_orgs:
            out[applicant_name] = {
                "ok": True,
                "missing": [],
                "required": [],
                "missing_rows": [],
            }
            policy_rows_by_applicant[applicant_name] = []
            continue

        candidate_rows = [
            row_policy
            for row_policy in policy_rows
            if _to_text(row_policy.get("policy_organization")) in ancestor_orgs
            and (
                not _to_text(row_policy.get("policy_school"))
                or _to_text(row_policy.get("policy_school")) in school_ancestors
            )
        ]

        nearest_rows = select_nearest_policy_rows_by_key(
            rows=candidate_rows,
            context_organization=organization,
            context_school=school,
            policy_key_field="policy_key",
            policy_organization_field="policy_organization",
            policy_school_field="policy_school",
        )

        policy_rows_by_applicant[applicant_name] = nearest_rows
        for row_policy in nearest_rows:
            policy_version = _to_text(row_policy.get("policy_version"))
            if policy_version:
                all_policy_versions.add(policy_version)

    applicant_acknowledgements_by_pair: dict[tuple[str, str], dict] = {}
    if all_policy_versions and applicant_names:
        acknowledgement_rows = frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": ["in", sorted(all_policy_versions)],
                "acknowledged_for": "Applicant",
                "context_doctype": "Student Applicant",
                "context_name": ["in", applicant_names],
            },
            fields=["context_name", "policy_version", "acknowledged_by", "acknowledged_at"],
            order_by="acknowledged_at desc",
            limit=10000,
        )

        for row_ack in acknowledgement_rows:
            applicant_name = _to_text(row_ack.get("context_name"))
            policy_version = _to_text(row_ack.get("policy_version"))
            if not applicant_name or not policy_version:
                continue
            key = (applicant_name, policy_version)
            if key in applicant_acknowledgements_by_pair:
                continue
            applicant_acknowledgements_by_pair[key] = row_ack

    applicant_names_by_guardian: dict[str, set[str]] = defaultdict(set)
    if applicant_names:
        guardian_rows = frappe.get_all(
            "Student Applicant Guardian",
            filters={
                "parent": ["in", applicant_names],
                "parenttype": "Student Applicant",
                "parentfield": "guardians",
                "can_consent": 1,
                "is_primary_guardian": 1,
            },
            fields=["parent", "guardian"],
            limit=10000,
        )
        for row_guardian in guardian_rows:
            applicant_name = _to_text(row_guardian.get("parent"))
            guardian_name = _to_text(row_guardian.get("guardian"))
            if not applicant_name or not guardian_name:
                continue
            applicant_names_by_guardian[guardian_name].add(applicant_name)

    guardian_acknowledgements_by_pair: dict[tuple[str, str], dict] = {}
    guardian_names = sorted(applicant_names_by_guardian)
    if all_policy_versions and guardian_names:
        guardian_acknowledgement_rows = frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": ["in", sorted(all_policy_versions)],
                "acknowledged_for": "Guardian",
                "context_doctype": "Guardian",
                "context_name": ["in", guardian_names],
            },
            fields=["context_name", "policy_version", "acknowledged_by", "acknowledged_at"],
            order_by="acknowledged_at desc",
            limit=10000,
        )
        for row_ack in guardian_acknowledgement_rows:
            guardian_name = _to_text(row_ack.get("context_name"))
            policy_version = _to_text(row_ack.get("policy_version"))
            if not guardian_name or not policy_version:
                continue
            for applicant_name in applicant_names_by_guardian.get(guardian_name, set()):
                key = (applicant_name, policy_version)
                if key in guardian_acknowledgements_by_pair:
                    continue
                guardian_acknowledgements_by_pair[key] = row_ack

    for applicant_name in applicant_names:
        if applicant_name in out:
            continue

        assigned_rows = policy_rows_by_applicant.get(applicant_name, [])
        if not assigned_rows:
            out[applicant_name] = {
                "ok": True,
                "missing": [],
                "required": [],
                "missing_rows": [],
            }
            continue

        required_labels: list[str] = []
        missing_labels: list[str] = []
        missing_rows: list[dict] = []

        for row_policy in assigned_rows:
            label = (
                _to_text(row_policy.get("policy_key"))
                or _to_text(row_policy.get("policy_title"))
                or _to_text(row_policy.get("policy_name"))
            )
            acknowledgement_mode = get_policy_admissions_acknowledgement_mode(policy_row=row_policy)
            is_required = acknowledgement_mode != ADMISSIONS_POLICY_MODE_OPTIONAL
            if is_required:
                required_labels.append(label)

            policy_version = _to_text(row_policy.get("policy_version"))
            if acknowledgement_mode == ADMISSIONS_POLICY_MODE_FAMILY:
                ack = guardian_acknowledgements_by_pair.get((applicant_name, policy_version))
            else:
                ack = applicant_acknowledgements_by_pair.get((applicant_name, policy_version))
            if ack or not is_required:
                continue

            missing_labels.append(label)
            missing_rows.append(
                {
                    "label": label,
                    "policy_name": _to_text(row_policy.get("policy_name")) or None,
                    "policy_version": policy_version or None,
                    "admissions_acknowledgement_mode": acknowledgement_mode,
                }
            )

        out[applicant_name] = {
            "ok": not missing_labels,
            "missing": missing_labels,
            "required": required_labels,
            "missing_rows": missing_rows,
        }

    return out


def _build_health_requirement_by_school(applicant_rows: list[dict]) -> dict[str, bool]:
    school_names = sorted({_to_text(row.get("school")) for row in applicant_rows if _to_text(row.get("school"))})
    if not school_names:
        return {}

    rows = frappe.get_all(
        "School",
        filters={"name": ["in", school_names]},
        fields=["name", "require_health_profile_for_approval"],
        limit=len(school_names),
    )

    out: dict[str, bool] = {}
    for row in rows:
        school_name = _to_text(row.get("name"))
        if not school_name:
            continue
        required_value = row.get("require_health_profile_for_approval")
        out[school_name] = True if required_value is None else bool(cint(required_value))
    return out


def _build_issues(
    *,
    policies: dict,
    documents: dict,
    health: dict,
    profile: dict,
    recommendations: dict,
    health_required_for_approval: bool,
) -> list[str]:
    issues: list[str] = []

    if not policies.get("ok"):
        schema_error = _to_text(policies.get("schema_error"))
        if schema_error:
            issues.append(schema_error)
        else:
            missing = policies.get("missing") or []
            if missing:
                issues.append(
                    _("Missing policy acknowledgements: {policies}.").format(
                        policies=", ".join(str(item) for item in missing)
                    )
                )
            else:
                issues.append(_("Missing required policy acknowledgements."))

    if health_required_for_approval and not health.get("ok"):
        status = _to_text(health.get("status")) or "missing"
        if status == "needs_follow_up":
            issues.append(_("Health review requires follow-up."))
        else:
            issues.append(_("Health profile is missing or not cleared."))

    if not documents.get("ok"):
        missing = documents.get("missing") or []
        unapproved = documents.get("unapproved") or []
        if missing:
            issues.append(
                _("Missing required documents: {documents}.").format(documents=", ".join(str(item) for item in missing))
            )
        if unapproved:
            issues.append(
                _("Required documents not approved: {documents}.").format(
                    documents=", ".join(str(item) for item in unapproved)
                )
            )

    if not profile.get("ok"):
        missing = profile.get("missing") or []
        if missing:
            issues.append(
                _("Missing profile information: {fields}.").format(fields=", ".join(str(item) for item in missing))
            )
        else:
            issues.append(_("Missing required profile information."))

    if not recommendations.get("ok"):
        missing = recommendations.get("missing") or []
        required_total = cint(recommendations.get("required_total") or 0)
        received_total = cint(recommendations.get("received_total") or 0)
        if missing:
            issues.append(
                _("Missing required recommendations: {recommendations}.").format(
                    recommendations=", ".join(str(item) for item in missing)
                )
            )
        elif required_total > 0:
            issues.append(
                _("Required recommendations received: {received_total} of {required_total}.").format(
                    received_total=received_total,
                    required_total=required_total,
                )
            )

    return issues


def _build_readiness_batch(applicant_rows: list[dict]) -> dict[str, dict]:
    applicant_names = [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
    if not applicant_names:
        return {}

    policies_by_applicant = _build_policy_state(applicant_rows, applicant_names)
    documents_by_applicant = _build_documents_state(applicant_rows, applicant_names)
    health_by_applicant = _build_health_state(applicant_names)
    health_requirement_by_school = _build_health_requirement_by_school(applicant_rows)
    recommendations_by_applicant = get_recommendation_status_batch_for_applicants(
        applicant_rows=applicant_rows,
        include_confidential=True,
    )

    readiness_by_applicant: dict[str, dict] = {}

    for applicant_row in applicant_rows:
        applicant_name = _to_text(applicant_row.get("name"))
        if not applicant_name:
            continue

        policies = policies_by_applicant.get(applicant_name) or {
            "ok": False,
            "missing": [],
            "required": [],
            "missing_rows": [],
        }
        documents = documents_by_applicant.get(applicant_name) or {
            "ok": False,
            "missing": [],
            "unapproved": [],
            "required": [],
            "missing_rows": [],
            "unapproved_rows": [],
        }
        health = health_by_applicant.get(applicant_name) or {
            "ok": False,
            "required_for_approval": True,
            "status": "missing",
            "profile_name": None,
            "review_status": None,
            "reviewed_by": None,
            "reviewed_on": None,
            "declared_complete": False,
            "declared_by": None,
            "declared_on": None,
        }
        profile = _build_profile_state(applicant_row)
        recommendations = recommendations_by_applicant.get(applicant_name) or {
            "ok": True,
            "required_total": 0,
            "received_total": 0,
            "requested_total": 0,
            "missing": [],
            "rows": [],
            "state": "optional",
            "counts": {},
            "review_rows": [],
            "pending_review_count": 0,
            "first_pending_review": None,
            "latest_submitted_on": None,
        }
        school_name = _to_text(applicant_row.get("school"))
        health_required_for_approval = health_requirement_by_school.get(school_name, True)
        health = dict(health)
        health["required_for_approval"] = health_required_for_approval

        health_ok_for_approval = bool(health.get("ok")) if health_required_for_approval else True
        ready = bool(
            policies.get("ok")
            and documents.get("ok")
            and health_ok_for_approval
            and profile.get("ok")
            and recommendations.get("ok")
        )

        readiness_by_applicant[applicant_name] = {
            "policies": policies,
            "documents": documents,
            "health": health,
            "profile": profile,
            "recommendations": recommendations,
            "ready": ready,
            "issues": _build_issues(
                policies=policies,
                documents=documents,
                health=health,
                profile=profile,
                recommendations=recommendations,
                health_required_for_approval=health_required_for_approval,
            ),
        }

    return readiness_by_applicant
