# ifitwala_ed/api/admission_cockpit.py

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    get_applicant_scope_ancestors,
    is_applicant_document_type_in_scope,
)
from ifitwala_ed.admission.doctype.student_applicant.student_applicant import STUDENT_PROFILE_REQUIRED_FIELD_LABELS
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_applies_to_column
from ifitwala_ed.utilities.school_tree import get_descendant_schools

ALLOWED_COCKPIT_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager", "Administrator"}
TERMINAL_STATUSES = {"Rejected", "Withdrawn", "Promoted"}
COCKPIT_CACHE_TTL_SECONDS = 120

KANBAN_COLUMNS = [
    ("draft", "Draft"),
    ("in_progress", "In Progress"),
    ("submitted", "Submitted"),
    ("under_review", "Under Review"),
    ("awaiting_decision", "Awaiting Decision"),
    ("accepted_pending_promotion", "Accepted (Pending Promotion)"),
]

BLOCKER_LABELS = {
    "missing_policies": "Missing Policies",
    "missing_documents": "Missing Documents",
    "documents_unapproved": "Documents Pending Review",
    "health_not_cleared": "Health Not Cleared",
    "profile_incomplete": "Profile Incomplete",
    "no_reviewer_assigned": "No Reviewer Assigned",
}


def _ensure_cockpit_access(user: str | None = None) -> str:
    user = user or frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access Admissions Cockpit."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & ALLOWED_COCKPIT_ROLES:
        return user

    frappe.throw(_("You do not have permission to access Admissions Cockpit."), frappe.PermissionError)
    return user


def _to_text(value) -> str:
    return str(value or "").strip()


def _to_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _as_str_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [_to_text(value)] if _to_text(value) else []
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            text = _to_text(item)
            if text:
                out.append(text)
        return out
    return []


def _value_present(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(str(value).strip())


def _display_name(row: dict) -> str:
    parts = [
        _to_text(row.get("first_name")),
        _to_text(row.get("middle_name")),
        _to_text(row.get("last_name")),
    ]
    full_name = " ".join(part for part in parts if part).strip()
    return full_name or _to_text(row.get("name"))


def _get_descendant_organizations(root_org: str) -> list[str]:
    root_org = _to_text(root_org)
    if not root_org:
        return []

    bounds = frappe.db.get_value("Organization", root_org, ["lft", "rgt"], as_dict=True)
    if not bounds:
        return []

    rows = frappe.db.sql(
        """
        SELECT name
        FROM `tabOrganization`
        WHERE lft >= %(lft)s AND rgt <= %(rgt)s
        ORDER BY lft ASC, name ASC
        """,
        {"lft": bounds.lft, "rgt": bounds.rgt},
        as_list=True,
    )
    return [row[0] for row in rows]


def _resolve_stage(application_status: str, ready: bool) -> str:
    status = _to_text(application_status)
    if status == "Draft":
        return "draft"
    if status in {"Invited", "In Progress", "Missing Info"}:
        return "in_progress"
    if status == "Submitted":
        return "submitted"
    if status == "Under Review":
        return "awaiting_decision" if ready else "under_review"
    if status == "Approved":
        return "accepted_pending_promotion"
    return "in_progress"


def _desk_route_slug(doctype: str) -> str:
    return frappe.scrub(doctype).replace("_", "-")


def _doc_url(doctype: str, name: str) -> str:
    return f"/desk/{_desk_route_slug(doctype)}/{quote(_to_text(name), safe='')}"


def _new_doc_url(doctype: str, params: dict[str, str] | None = None) -> str:
    slug = _desk_route_slug(doctype)
    base = f"/desk/{slug}/new-{slug}-1"
    if not params:
        return base

    query = "&".join(
        f"{quote(_to_text(key), safe='')}={quote(_to_text(value), safe='')}"
        for key, value in params.items()
        if _to_text(key) and _to_text(value)
    )
    if not query:
        return base
    return f"{base}?{query}"


def _target(
    *,
    doctype: str,
    name: str | None = None,
    target_label: str,
    params: dict[str, str] | None = None,
    is_new: bool = False,
) -> dict:
    if is_new:
        url = _new_doc_url(doctype, params=params)
    elif name:
        url = _doc_url(doctype, name)
    else:
        url = f"/desk/{_desk_route_slug(doctype)}"

    return {
        "target_doctype": doctype,
        "target_name": _to_text(name),
        "target_url": url,
        "target_label": target_label,
    }


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
        limit_page_length=10000,
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
    out: dict[str, dict] = {}

    type_rows = frappe.get_all(
        "Applicant Document Type",
        filters={"is_active": 1},
        fields=[
            "name",
            "code",
            "document_type_name",
            "is_required",
            "organization",
            "school",
        ],
        limit_page_length=10000,
    )

    scope_cache: dict[tuple[str, str], tuple[set[str], set[str]]] = {}
    required_by_applicant: dict[str, list[dict]] = {}

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
                "unapproved": [],
                "required": [],
                "missing_rows": [],
                "unapproved_rows": [],
            }
            required_by_applicant[applicant_name] = []
            continue

        scope_key = (organization, school)
        if scope_key not in scope_cache:
            org_ancestors, school_ancestors = get_applicant_scope_ancestors(
                organization=organization,
                school=school,
            )
            scope_cache[scope_key] = (set(org_ancestors), set(school_ancestors))

        applicant_org_ancestors, applicant_school_ancestors = scope_cache[scope_key]

        required_rows: list[dict] = []
        for row_type in type_rows:
            if not is_applicant_document_type_in_scope(
                document_type_organization=row_type.get("organization"),
                document_type_school=row_type.get("school"),
                applicant_org_ancestors=applicant_org_ancestors,
                applicant_school_ancestors=applicant_school_ancestors,
            ):
                continue
            if not cint(row_type.get("is_required")):
                continue

            doc_type = _to_text(row_type.get("name"))
            if not doc_type:
                continue

            label = _to_text(row_type.get("code")) or _to_text(row_type.get("document_type_name")) or doc_type
            required_rows.append(
                {
                    "document_type": doc_type,
                    "label": label,
                }
            )

        required_by_applicant[applicant_name] = required_rows

    if not applicant_names:
        return out

    document_rows = frappe.get_all(
        "Applicant Document",
        filters={"student_applicant": ["in", applicant_names]},
        fields=[
            "name",
            "student_applicant",
            "document_type",
            "document_label",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=10000,
    )

    latest_by_applicant_type: dict[str, dict[str, dict]] = defaultdict(dict)
    for row_doc in document_rows:
        applicant_name = _to_text(row_doc.get("student_applicant"))
        document_type = _to_text(row_doc.get("document_type"))
        if not applicant_name or not document_type:
            continue
        if document_type in latest_by_applicant_type[applicant_name]:
            continue
        latest_by_applicant_type[applicant_name][document_type] = row_doc

    for applicant_name in applicant_names:
        if applicant_name in out:
            continue

        required_rows = required_by_applicant.get(applicant_name, [])
        latest_docs = latest_by_applicant_type.get(applicant_name, {})

        missing_labels: list[str] = []
        unapproved_labels: list[str] = []
        missing_rows: list[dict] = []
        unapproved_rows: list[dict] = []

        for required_row in required_rows:
            doc_type = _to_text(required_row.get("document_type"))
            label = _to_text(required_row.get("label")) or doc_type
            document_row = latest_docs.get(doc_type)

            if not document_row:
                missing_labels.append(label)
                missing_rows.append(
                    {
                        "document_type": doc_type,
                        "label": label,
                        "applicant_document": None,
                    }
                )
                continue

            review_status = _to_text(document_row.get("review_status")) or "Pending"
            if review_status != "Approved":
                unapproved_labels.append(label)
                unapproved_rows.append(
                    {
                        "document_type": doc_type,
                        "label": label,
                        "applicant_document": _to_text(document_row.get("name")) or None,
                        "review_status": review_status,
                    }
                )

        out[applicant_name] = {
            "ok": not missing_labels and not unapproved_labels,
            "missing": missing_labels,
            "unapproved": unapproved_labels,
            "required": [
                _to_text(required_row.get("label")) or _to_text(required_row.get("document_type"))
                for required_row in required_rows
            ],
            "missing_rows": missing_rows,
            "unapproved_rows": unapproved_rows,
        }

    return out


def _build_policy_state(applicant_rows: list[dict], applicant_names: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}

    schema_check = ensure_policy_applies_to_column(caller="admission_cockpit.get_admissions_cockpit_data")
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

        policy_rows = frappe.db.sql(
            f"""
            SELECT ip.name AS policy_name,
                   ip.policy_key AS policy_key,
                   ip.policy_title AS policy_title,
                   ip.organization AS policy_organization,
                   ip.school AS policy_school,
                   pv.name AS policy_version
              FROM `tabInstitutional Policy` ip
              JOIN `tabPolicy Version` pv
                ON pv.institutional_policy = ip.name
             WHERE ip.is_active = 1
               AND pv.is_active = 1
               AND ip.organization IN ({org_placeholders})
               AND (ip.school IS NULL OR ip.school = ''{school_scope_sql})
               AND ip.applies_to LIKE %s
            """,
            (*org_values, *school_params, "%Applicant%"),
            as_dict=True,
        )

    required_policy_rows_by_applicant: dict[str, list[dict]] = {}
    all_required_versions: set[str] = set()

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
            required_policy_rows_by_applicant[applicant_name] = []
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
            required_policy_rows_by_applicant[applicant_name] = []
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

        required_policy_rows_by_applicant[applicant_name] = nearest_rows
        for row_policy in nearest_rows:
            policy_version = _to_text(row_policy.get("policy_version"))
            if policy_version:
                all_required_versions.add(policy_version)

    acknowledgements_by_pair: dict[tuple[str, str], dict] = {}
    if all_required_versions and applicant_names:
        acknowledgement_rows = frappe.get_all(
            "Policy Acknowledgement",
            filters={
                "policy_version": ["in", sorted(all_required_versions)],
                "acknowledged_for": "Applicant",
                "context_doctype": "Student Applicant",
                "context_name": ["in", applicant_names],
            },
            fields=["context_name", "policy_version", "acknowledged_by", "acknowledged_at"],
            order_by="acknowledged_at desc",
            limit_page_length=10000,
        )

        for row_ack in acknowledgement_rows:
            applicant_name = _to_text(row_ack.get("context_name"))
            policy_version = _to_text(row_ack.get("policy_version"))
            if not applicant_name or not policy_version:
                continue
            key = (applicant_name, policy_version)
            if key in acknowledgements_by_pair:
                continue
            acknowledgements_by_pair[key] = row_ack

    for applicant_name in applicant_names:
        if applicant_name in out:
            continue

        required_rows = required_policy_rows_by_applicant.get(applicant_name, [])
        if not required_rows:
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

        for row_policy in required_rows:
            label = (
                _to_text(row_policy.get("policy_key"))
                or _to_text(row_policy.get("policy_title"))
                or _to_text(row_policy.get("policy_name"))
            )
            required_labels.append(label)

            policy_version = _to_text(row_policy.get("policy_version"))
            ack = acknowledgements_by_pair.get((applicant_name, policy_version))
            if ack:
                continue

            missing_labels.append(label)
            missing_rows.append(
                {
                    "label": label,
                    "policy_name": _to_text(row_policy.get("policy_name")) or None,
                    "policy_version": policy_version or None,
                }
            )

        out[applicant_name] = {
            "ok": not missing_labels,
            "missing": missing_labels,
            "required": required_labels,
            "missing_rows": missing_rows,
        }

    return out


def _build_issues(*, policies: dict, documents: dict, health: dict, profile: dict) -> list[str]:
    issues: list[str] = []

    if not policies.get("ok"):
        schema_error = _to_text(policies.get("schema_error"))
        if schema_error:
            issues.append(schema_error)
        else:
            missing = policies.get("missing") or []
            if missing:
                issues.append(
                    _("Missing policy acknowledgements: {0}.").format(", ".join(str(item) for item in missing))
                )
            else:
                issues.append(_("Missing required policy acknowledgements."))

    if not health.get("ok"):
        status = _to_text(health.get("status")) or "missing"
        if status == "needs_follow_up":
            issues.append(_("Health review requires follow-up."))
        else:
            issues.append(_("Health profile is missing or not cleared."))

    if not documents.get("ok"):
        missing = documents.get("missing") or []
        unapproved = documents.get("unapproved") or []
        if missing:
            issues.append(_("Missing required documents: {0}.").format(", ".join(str(item) for item in missing)))
        if unapproved:
            issues.append(
                _("Required documents not approved: {0}.").format(", ".join(str(item) for item in unapproved))
            )

    if not profile.get("ok"):
        missing = profile.get("missing") or []
        if missing:
            issues.append(_("Missing profile information: {0}.").format(", ".join(str(item) for item in missing)))
        else:
            issues.append(_("Missing required profile information."))

    return issues


def _build_readiness_batch(applicant_rows: list[dict]) -> dict[str, dict]:
    applicant_names = [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
    if not applicant_names:
        return {}

    policies_by_applicant = _build_policy_state(applicant_rows, applicant_names)
    documents_by_applicant = _build_documents_state(applicant_rows, applicant_names)
    health_by_applicant = _build_health_state(applicant_names)

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

        ready = bool(policies.get("ok") and documents.get("ok") and health.get("ok") and profile.get("ok"))

        readiness_by_applicant[applicant_name] = {
            "policies": policies,
            "documents": documents,
            "health": health,
            "profile": profile,
            "ready": ready,
            "issues": _build_issues(
                policies=policies,
                documents=documents,
                health=health,
                profile=profile,
            ),
        }

    return readiness_by_applicant


def _build_blockers(
    *,
    snapshot: dict,
    application_status: str,
    open_assignments: int,
    applicant_name: str,
    first_open_assignment: dict | None,
) -> list[dict]:
    blockers: list[dict] = []

    policies = snapshot.get("policies") or {}
    documents = snapshot.get("documents") or {}
    health = snapshot.get("health") or {}
    profile = snapshot.get("profile") or {}

    applicant_target = _target(
        doctype="Student Applicant",
        name=applicant_name,
        target_label=_("Open applicant"),
    )

    if not policies.get("ok"):
        missing = policies.get("missing") or []
        missing_rows = policies.get("missing_rows") or []
        first_missing = missing_rows[0] if missing_rows else {}
        policy_version = _to_text(first_missing.get("policy_version"))

        target = (
            _target(
                doctype="Policy Version",
                name=policy_version,
                target_label=_("Open policy version"),
            )
            if policy_version
            else applicant_target
        )

        label = _("Missing policies") if not missing else _("Missing policies: {0}").format(len(missing))
        blockers.append(
            {
                "kind": "missing_policies",
                "label": label,
                "items": [str(item) for item in missing],
                **target,
            }
        )

    if not documents.get("ok"):
        missing = documents.get("missing") or []
        unapproved = documents.get("unapproved") or []
        missing_rows = documents.get("missing_rows") or []
        unapproved_rows = documents.get("unapproved_rows") or []

        if missing:
            first_missing = missing_rows[0] if missing_rows else {}
            missing_type = _to_text(first_missing.get("document_type"))

            target = (
                _target(
                    doctype="Applicant Document",
                    is_new=True,
                    params={
                        "student_applicant": applicant_name,
                        "document_type": missing_type,
                    },
                    target_label=_("Create missing document record"),
                )
                if missing_type
                else applicant_target
            )

            blockers.append(
                {
                    "kind": "missing_documents",
                    "label": _("Missing required documents: {0}").format(len(missing)),
                    "items": [str(item) for item in missing],
                    **target,
                }
            )

        if unapproved:
            first_unapproved = unapproved_rows[0] if unapproved_rows else {}
            applicant_document = _to_text(first_unapproved.get("applicant_document"))

            target = (
                _target(
                    doctype="Applicant Document",
                    name=applicant_document,
                    target_label=_("Open document review"),
                )
                if applicant_document
                else applicant_target
            )

            blockers.append(
                {
                    "kind": "documents_unapproved",
                    "label": _("Required documents pending review: {0}").format(len(unapproved)),
                    "items": [str(item) for item in unapproved],
                    **target,
                }
            )

    if not health.get("ok"):
        health_profile = _to_text(health.get("profile_name"))
        target = (
            _target(
                doctype="Applicant Health Profile",
                name=health_profile,
                target_label=_("Open health profile"),
            )
            if health_profile
            else _target(
                doctype="Applicant Health Profile",
                is_new=True,
                params={"student_applicant": applicant_name},
                target_label=_("Create health profile"),
            )
        )

        blockers.append(
            {
                "kind": "health_not_cleared",
                "label": _("Health profile is missing or not cleared"),
                "items": [],
                **target,
            }
        )

    if not profile.get("ok"):
        missing = profile.get("missing") or []
        blockers.append(
            {
                "kind": "profile_incomplete",
                "label": _("Profile information incomplete"),
                "items": [str(item) for item in missing],
                **applicant_target,
            }
        )

    status = _to_text(application_status)
    if status in {"Submitted", "Under Review"} and open_assignments == 0:
        if first_open_assignment and _to_text(first_open_assignment.get("name")):
            target = _target(
                doctype="Applicant Review Assignment",
                name=_to_text(first_open_assignment.get("name")),
                target_label=_("Open review assignment"),
            )
        else:
            target = _target(
                doctype="Applicant Review Assignment",
                is_new=True,
                params={
                    "target_type": "Student Applicant",
                    "target_name": applicant_name,
                    "student_applicant": applicant_name,
                },
                target_label=_("Create review assignment"),
            )

        blockers.append(
            {
                "kind": "no_reviewer_assigned",
                "label": _("No reviewer assignment is open"),
                "items": [],
                **target,
            }
        )

    return blockers


def _empty_payload(organizations: list[str], schools: list[str]) -> dict:
    return {
        "config": {
            "organizations": organizations,
            "schools": schools,
            "columns": [{"id": col_id, "title": title} for col_id, title in KANBAN_COLUMNS],
        },
        "counts": {
            "active_applications": 0,
            "blocked_applications": 0,
            "ready_for_decision": 0,
            "accepted_pending_promotion": 0,
            "my_open_assignments": 0,
        },
        "blockers": [],
        "columns": [{"id": col_id, "title": title, "items": []} for col_id, title in KANBAN_COLUMNS],
        "generated_at": frappe.utils.now_datetime(),
    }


def _cache_key_for_payload(payload: dict) -> str:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"admissions:cockpit:v2:{digest}"


@frappe.whitelist()
def get_admissions_cockpit_data(filters=None):
    user = _ensure_cockpit_access()
    user_roles = set(frappe.get_roles(user))

    filters = frappe.parse_json(filters) or {}
    organization_filter = _to_text(filters.get("organization"))
    school_filter = _to_text(filters.get("school"))
    include_terminal = bool(cint(filters.get("include_terminal")))
    assigned_to_me_only = bool(cint(filters.get("assigned_to_me")))
    status_filters = sorted(_as_str_list(filters.get("application_statuses")))

    limit = _to_int(filters.get("limit"), 120)
    if limit < 1:
        limit = 1
    if limit > 250:
        limit = 250

    cache_payload = {
        "user": user,
        "organization": organization_filter,
        "school": school_filter,
        "include_terminal": int(include_terminal),
        "assigned_to_me": int(assigned_to_me_only),
        "application_statuses": status_filters,
        "limit": limit,
    }
    cache = frappe.cache()
    cache_key = _cache_key_for_payload(cache_payload)
    cached_payload = cache.get_value(cache_key)
    if cached_payload:
        try:
            parsed = frappe.parse_json(cached_payload)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

    organization_scope = _get_descendant_organizations(organization_filter) if organization_filter else []
    if organization_filter and not organization_scope:
        response = _empty_payload([], [])
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    school_scope = get_descendant_schools(school_filter) if school_filter else []
    if school_filter and not school_scope:
        organizations = [
            row[0]
            for row in frappe.db.sql("SELECT name FROM `tabOrganization` ORDER BY lft ASC, name ASC", as_list=True)
        ]
        response = _empty_payload(organizations, [])
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    all_organizations = [
        row[0] for row in frappe.db.sql("SELECT name FROM `tabOrganization` ORDER BY lft ASC, name ASC", as_list=True)
    ]

    if organization_scope:
        schools = frappe.get_all(
            "School",
            filters={"organization": ["in", organization_scope]},
            fields=["name"],
            order_by="lft asc, name asc",
        )
    else:
        schools = frappe.get_all("School", fields=["name"], order_by="lft asc, name asc")
    all_schools = [row.get("name") for row in schools if row.get("name")]

    applicant_filters: dict = {}
    if organization_scope:
        applicant_filters["organization"] = ["in", organization_scope]
    if school_scope:
        applicant_filters["school"] = ["in", school_scope]
    if status_filters:
        applicant_filters["application_status"] = ["in", status_filters]
    elif not include_terminal:
        applicant_filters["application_status"] = ["not in", sorted(TERMINAL_STATUSES)]

    fetch_limit = limit * 4 if assigned_to_me_only else limit
    if fetch_limit > 600:
        fetch_limit = 600

    applicant_rows = frappe.get_all(
        "Student Applicant",
        filters=applicant_filters,
        fields=[
            "name",
            "first_name",
            "middle_name",
            "last_name",
            "application_status",
            "organization",
            "school",
            "program_offering",
            "student",
            "modified",
            "student_date_of_birth",
            "student_gender",
            "student_mobile_number",
            "student_joining_date",
            "student_first_language",
            "student_nationality",
            "residency_status",
        ],
        order_by="modified desc",
        limit_page_length=fetch_limit,
    )

    if not applicant_rows:
        response = _empty_payload(all_organizations, all_schools)
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    applicant_names = [_to_text(row.get("name")) for row in applicant_rows if _to_text(row.get("name"))]
    assignment_rows = frappe.get_all(
        "Applicant Review Assignment",
        filters={
            "status": "Open",
            "student_applicant": ["in", applicant_names],
        },
        fields=[
            "name",
            "student_applicant",
            "target_type",
            "target_name",
            "assigned_to_user",
            "assigned_to_role",
            "modified",
        ],
        order_by="modified desc",
        limit_page_length=10000,
    )

    assignment_summary = {name: {"open_total": 0, "open_for_me": 0} for name in applicant_names}
    first_open_assignment_by_applicant: dict[str, dict] = {}
    for row_assignment in assignment_rows:
        applicant_name = _to_text(row_assignment.get("student_applicant"))
        if not applicant_name or applicant_name not in assignment_summary:
            continue

        assignment_summary[applicant_name]["open_total"] += 1
        if applicant_name not in first_open_assignment_by_applicant:
            first_open_assignment_by_applicant[applicant_name] = row_assignment

        assigned_user = _to_text(row_assignment.get("assigned_to_user"))
        assigned_role = _to_text(row_assignment.get("assigned_to_role"))
        if assigned_user and assigned_user == user:
            assignment_summary[applicant_name]["open_for_me"] += 1
            continue
        if assigned_role and assigned_role in user_roles:
            assignment_summary[applicant_name]["open_for_me"] += 1

    if assigned_to_me_only:
        applicant_rows = [
            row
            for row in applicant_rows
            if assignment_summary.get(_to_text(row.get("name")), {}).get("open_for_me", 0) > 0
        ]

    applicant_rows = applicant_rows[:limit]
    if not applicant_rows:
        response = _empty_payload(all_organizations, all_schools)
        cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
        return response

    readiness_by_applicant: dict[str, dict]
    try:
        readiness_by_applicant = _build_readiness_batch(applicant_rows)
    except Exception:
        frappe.logger("admissions_cockpit", allow_site=True).exception("Admissions cockpit readiness batch failed.")
        readiness_by_applicant = {}

    columns = {col_id: {"id": col_id, "title": title, "items": []} for col_id, title in KANBAN_COLUMNS}
    blocker_counts = {key: 0 for key in BLOCKER_LABELS}
    counts = {
        "active_applications": 0,
        "blocked_applications": 0,
        "ready_for_decision": 0,
        "accepted_pending_promotion": 0,
        "my_open_assignments": 0,
    }

    for row in applicant_rows:
        applicant_name = _to_text(row.get("name"))
        if not applicant_name:
            continue

        assignee_stats = assignment_summary.get(applicant_name, {"open_total": 0, "open_for_me": 0})
        snapshot = readiness_by_applicant.get(applicant_name) or _empty_readiness_snapshot()

        ready = bool(snapshot.get("ready"))
        stage = _resolve_stage(_to_text(row.get("application_status")), ready)

        blockers = _build_blockers(
            snapshot=snapshot,
            application_status=_to_text(row.get("application_status")),
            open_assignments=assignee_stats.get("open_total", 0),
            applicant_name=applicant_name,
            first_open_assignment=first_open_assignment_by_applicant.get(applicant_name),
        )

        for blocker in blockers:
            kind = blocker.get("kind")
            if kind in blocker_counts:
                blocker_counts[kind] += 1

        if blockers:
            counts["blocked_applications"] += 1

        if stage == "awaiting_decision":
            counts["ready_for_decision"] += 1
        if stage == "accepted_pending_promotion":
            counts["accepted_pending_promotion"] += 1

        counts["active_applications"] += 1
        counts["my_open_assignments"] += assignee_stats.get("open_for_me", 0)

        card = {
            "name": applicant_name,
            "display_name": _display_name(row),
            "application_status": _to_text(row.get("application_status")),
            "organization": _to_text(row.get("organization")),
            "school": _to_text(row.get("school")),
            "program_offering": _to_text(row.get("program_offering")),
            "open_assignments": assignee_stats.get("open_total", 0),
            "open_assignments_for_me": assignee_stats.get("open_for_me", 0),
            "ready": ready,
            "readiness": {
                "profile_ok": bool((snapshot.get("profile") or {}).get("ok")),
                "policies_ok": bool((snapshot.get("policies") or {}).get("ok")),
                "documents_ok": bool((snapshot.get("documents") or {}).get("ok")),
                "health_ok": bool((snapshot.get("health") or {}).get("ok")),
            },
            "top_blockers": [
                {
                    "kind": row_blocker.get("kind"),
                    "label": row_blocker.get("label"),
                    "target_url": row_blocker.get("target_url"),
                    "target_label": row_blocker.get("target_label"),
                }
                for row_blocker in blockers[:2]
                if row_blocker.get("label")
            ],
            "blockers": blockers,
            "issues": [str(item) for item in (snapshot.get("issues") or [])],
            "open_url": _doc_url("Student Applicant", applicant_name),
        }

        if stage in columns:
            columns[stage]["items"].append(card)

    blocker_tiles = []
    for kind, label in BLOCKER_LABELS.items():
        count = blocker_counts.get(kind, 0)
        if count <= 0:
            continue
        blocker_tiles.append({"kind": kind, "label": label, "count": count})

    blocker_tiles.sort(key=lambda row_blocker: row_blocker.get("count", 0), reverse=True)

    response = {
        "config": {
            "organizations": all_organizations,
            "schools": all_schools,
            "columns": [{"id": col_id, "title": title} for col_id, title in KANBAN_COLUMNS],
        },
        "counts": counts,
        "blockers": blocker_tiles,
        "columns": [columns[col_id] for col_id, _ in KANBAN_COLUMNS],
        "generated_at": frappe.utils.now_datetime(),
    }

    cache.set_value(cache_key, frappe.as_json(response), expires_in_sec=COCKPIT_CACHE_TTL_SECONDS)
    return response
