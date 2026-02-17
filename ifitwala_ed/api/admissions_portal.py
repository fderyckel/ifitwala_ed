# ifitwala_ed/api/admissions_portal.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission import admissions_portal as admission_api
from ifitwala_ed.admission.admission_utils import ensure_admissions_permission
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_applies_to_column

ADMISSIONS_ROLE = "Admissions Applicant"

PORTAL_STATUS_MAP = {
    "Draft": "Draft",
    "Invited": "Draft",
    "In Progress": "In Progress",
    "Missing Info": "Action Required",
    "Submitted": "In Review",
    "Under Review": "In Review",
    "Approved": "Accepted",
    "Rejected": "Rejected",
    "Promoted": "Completed",
}

PORTAL_EDITABLE_STATUSES = {"Invited", "In Progress", "Missing Info"}

READ_ONLY_REASON_MAP = {
    "Draft": _("Application not yet open."),
    "Submitted": _("Application submitted."),
    "Under Review": _("Application under review."),
    "Approved": _("Application accepted."),
    "Rejected": _("Application rejected."),
    "Promoted": _("Application completed."),
}


def _require_admissions_applicant() -> str:
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if ADMISSIONS_ROLE not in roles:
        frappe.throw(_("You do not have permission to access the admissions portal."), frappe.PermissionError)

    return user


def _get_applicant_for_user(user: str, fields: list[str] | None = None) -> dict:
    fields = fields or ["name", "application_status", "organization", "school", "first_name", "last_name"]
    rows = frappe.get_all(
        "Student Applicant",
        filters={"applicant_user": user},
        fields=fields,
        limit=2,
    )
    if not rows:
        frappe.throw(_("Admissions access is not linked to any Applicant."), frappe.PermissionError)
    if len(rows) > 1:
        frappe.throw(_("Admissions access is linked to multiple Applicants."), frappe.PermissionError)
    return rows[0]


def _ensure_applicant_match(student_applicant: str | None, user: str) -> dict:
    row = _get_applicant_for_user(user)
    if student_applicant and row.get("name") != student_applicant:
        frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)
    return row


def _portal_status_for(application_status: str) -> str:
    if application_status not in PORTAL_STATUS_MAP:
        frappe.throw(_("Invalid Application Status: {0}.").format(application_status))
    return PORTAL_STATUS_MAP[application_status]


def _read_only_for(application_status: str) -> tuple[bool, str | None]:
    if application_status in PORTAL_EDITABLE_STATUSES:
        return False, None
    return True, READ_ONLY_REASON_MAP.get(application_status)


def _completion_state_for_requirement(required: list, missing: list, unapproved: list | None = None) -> str:
    if not required:
        return "optional"
    missing = missing or []
    unapproved = unapproved or []
    if not missing and not unapproved:
        return "complete"
    if len(missing) < len(required) or unapproved:
        return "in_progress"
    return "pending"


def _completion_state_for_health(health: dict) -> str:
    if health.get("ok"):
        return "complete"
    status = (health.get("status") or "missing").strip()
    if status == "missing":
        return "pending"
    return "in_progress"


def _completion_state_for_interviews(interviews: dict) -> str:
    if interviews.get("ok"):
        return "complete"
    return "optional"


def _derive_next_actions(application_status: str, readiness: dict) -> list[dict]:
    if application_status not in PORTAL_EDITABLE_STATUSES:
        return []

    actions: list[dict] = []

    policies = readiness.get("policies") or {}
    documents = readiness.get("documents") or {}
    health = readiness.get("health") or {}

    if not policies.get("ok"):
        actions.append(
            {
                "label": _("Review required policies"),
                "route_name": "admissions-policies",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    if not documents.get("ok"):
        actions.append(
            {
                "label": _("Upload required documents"),
                "route_name": "admissions-documents",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    if not health.get("ok"):
        actions.append(
            {
                "label": _("Complete health information"),
                "route_name": "admissions-health",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    return actions


@frappe.whitelist()
def get_admissions_session():
    user = _require_admissions_applicant()
    row = _get_applicant_for_user(user)

    portal_status = _portal_status_for(row.get("application_status"))
    is_read_only, reason = _read_only_for(row.get("application_status"))

    user_row = frappe.db.get_value("User", user, ["name", "full_name"], as_dict=True) or {}

    return {
        "user": {
            "name": user_row.get("name") or user,
            "full_name": user_row.get("full_name") or user,
            "roles": [ADMISSIONS_ROLE],
        },
        "applicant": {
            "name": row.get("name"),
            "portal_status": portal_status,
            "school": row.get("school"),
            "organization": row.get("organization"),
            "is_read_only": bool(is_read_only),
            "read_only_reason": reason,
        },
    }


@frappe.whitelist()
def get_applicant_snapshot(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    readiness = applicant.get_readiness_snapshot()

    completeness = {
        "health": _completion_state_for_health(readiness.get("health") or {}),
        "documents": _completion_state_for_requirement(
            (readiness.get("documents") or {}).get("required") or [],
            (readiness.get("documents") or {}).get("missing") or [],
            (readiness.get("documents") or {}).get("unapproved") or [],
        ),
        "policies": _completion_state_for_requirement(
            (readiness.get("policies") or {}).get("required") or [],
            (readiness.get("policies") or {}).get("missing") or [],
        ),
        "interviews": _completion_state_for_interviews(readiness.get("interviews") or {}),
    }

    portal_status = _portal_status_for(applicant.application_status)
    next_actions = _derive_next_actions(applicant.application_status, readiness)

    return {
        "applicant": {
            "name": applicant.name,
            "portal_status": portal_status,
            "submitted_at": applicant.get("submitted_at"),
            "decision_at": applicant.get("decision_at"),
        },
        "completeness": completeness,
        "next_actions": next_actions,
    }


@frappe.whitelist()
def get_applicant_health(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    health = frappe.db.get_value(
        "Applicant Health Profile",
        {"student_applicant": row.get("name")},
        ["health_summary", "medical_conditions", "allergies", "medications"],
        as_dict=True,
    )
    if not health:
        health = {
            "health_summary": "",
            "medical_conditions": "",
            "allergies": "",
            "medications": "",
        }

    return health


@frappe.whitelist()
def update_applicant_health(
    *,
    student_applicant: str | None = None,
    health_summary: str | None = None,
    medical_conditions: str | None = None,
    allergies: str | None = None,
    medications: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    existing = frappe.db.get_value(
        "Applicant Health Profile",
        {"student_applicant": row.get("name")},
        "name",
    )
    if existing:
        doc = frappe.get_doc("Applicant Health Profile", existing)
    else:
        doc = frappe.get_doc(
            {
                "doctype": "Applicant Health Profile",
                "student_applicant": row.get("name"),
            }
        )

    updates = {
        "health_summary": health_summary or "",
        "medical_conditions": medical_conditions or "",
        "allergies": allergies or "",
        "medications": medications or "",
    }

    doc.update(updates)
    doc.save(ignore_permissions=True)

    return {"ok": True}


@frappe.whitelist()
def list_applicant_documents(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    documents = frappe.get_all(
        "Applicant Document",
        filters={"student_applicant": row.get("name")},
        fields=["name", "document_type", "review_status", "modified"],
        order_by="modified desc",
    )

    if not documents:
        return {"documents": []}

    name_list = [d["name"] for d in documents]
    file_rows = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Applicant Document",
            "attached_to_name": ["in", name_list],
        },
        fields=["attached_to_name", "file_url", "file_name", "creation"],
        order_by="creation desc",
    )

    latest_file: dict[str, dict] = {}
    for row_file in file_rows:
        parent = row_file.get("attached_to_name")
        if not parent or parent in latest_file:
            continue
        latest_file[parent] = row_file

    payload = []
    for doc in documents:
        file_row = latest_file.get(doc["name"], {})
        payload.append(
            {
                "name": doc["name"],
                "document_type": doc.get("document_type"),
                "review_status": doc.get("review_status") or "Pending",
                "uploaded_at": file_row.get("creation"),
                "file_url": file_row.get("file_url"),
            }
        )

    return {"documents": payload}


@frappe.whitelist()
def list_applicant_document_types(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    organization = row.get("organization")
    school = row.get("school")

    if not organization:
        return {"document_types": []}

    rows = frappe.get_all(
        "Applicant Document Type",
        filters={"is_active": 1},
        fields=[
            "name",
            "code",
            "document_type_name",
            "belongs_to",
            "is_required",
            "description",
            "school",
            "organization",
        ],
        order_by="is_required desc, document_type_name asc",
    )

    payload = []
    for row_type in rows:
        if row_type.get("organization") and row_type.get("organization") != organization:
            continue
        if row_type.get("school") and school and row_type.get("school") != school:
            continue
        payload.append(
            {
                "name": row_type.get("name"),
                "code": row_type.get("code"),
                "document_type_name": row_type.get("document_type_name"),
                "belongs_to": row_type.get("belongs_to") or "",
                "is_required": bool(row_type.get("is_required")),
                "description": row_type.get("description") or "",
            }
        )

    return {"document_types": payload}


@frappe.whitelist()
def upload_applicant_document(
    *,
    student_applicant: str | None = None,
    document_type: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    if not document_type:
        frappe.throw(_("document_type is required."))

    if not content and not (getattr(frappe.request, "files", None) and frappe.request.files.get("file")):
        frappe.throw(_("File content is required."))

    doc_type_row = frappe.db.get_value(
        "Applicant Document Type",
        document_type,
        ["organization", "school", "is_active"],
        as_dict=True,
    )
    if not doc_type_row or not doc_type_row.get("is_active"):
        frappe.throw(_("Invalid or inactive document type."))
    if doc_type_row.get("organization") and doc_type_row.get("organization") != row.get("organization"):
        frappe.throw(_("Document type does not belong to the Applicant organization."))
    if doc_type_row.get("school") and doc_type_row.get("school") != row.get("school"):
        frappe.throw(_("Document type does not belong to the Applicant school."))

    payload = {
        "student_applicant": row.get("name"),
        "document_type": document_type,
        "upload_source": "SPA",
        "is_private": 1,
        "ignore_permissions": 1,
    }

    if content:
        payload["content"] = content
    if file_name:
        payload["file_name"] = file_name

    return admission_api.upload_applicant_document(**payload)


@frappe.whitelist()
def get_applicant_policies(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    organization = row.get("organization")
    school = row.get("school")

    if not organization:
        return {"policies": []}

    ancestor_orgs = get_organization_ancestors_including_self(organization)
    if not ancestor_orgs:
        return {"policies": []}

    ensure_policy_applies_to_column(
        caller="admissions_portal.get_applicant_policies",
        throw=True,
    )

    cache = frappe.cache()
    cache_key = f"admissions:policies:{organization}:{school or 'all'}"
    cached = cache.get_value(cache_key)
    policies_source = None
    if cached:
        try:
            policies_source = frappe.parse_json(cached)
        except Exception:
            policies_source = None

    if policies_source is None:
        org_placeholders = ", ".join(["%s"] * len(ancestor_orgs))
        policies_source = frappe.db.sql(
            f"""
			SELECT ip.name AS policy_name,
			       ip.policy_key AS policy_key,
			       ip.policy_title AS policy_title,
			       ip.organization AS policy_organization,
			       pv.name AS policy_version,
			       pv.policy_text AS policy_text
			  FROM `tabInstitutional Policy` ip
			  JOIN `tabPolicy Version` pv
			    ON pv.institutional_policy = ip.name
			 WHERE ip.is_active = 1
			   AND pv.is_active = 1
			   AND ip.organization IN ({org_placeholders})
			   AND (ip.school IS NULL OR ip.school = '' OR ip.school = %s)
			   AND ip.applies_to LIKE %s
			""",
            (*ancestor_orgs, school, "%Applicant%"),
            as_dict=True,
        )
        policies_source = select_nearest_policy_rows_by_key(
            rows=policies_source,
            context_organization=organization,
            policy_key_field="policy_key",
            policy_organization_field="policy_organization",
        )
        cache.set_value(cache_key, frappe.as_json(policies_source), expires_in_sec=600)

    if not policies_source:
        return {"policies": []}

    versions = [row_policy["policy_version"] for row_policy in policies_source]
    ack_rows = frappe.get_all(
        "Policy Acknowledgement",
        filters={
            "policy_version": ["in", versions],
            "acknowledged_for": "Applicant",
            "context_doctype": "Student Applicant",
            "context_name": row.get("name"),
        },
        fields=["policy_version", "acknowledged_at"],
    )
    ack_map = {row_ack["policy_version"]: row_ack.get("acknowledged_at") for row_ack in ack_rows}

    payload = []
    for row_policy in policies_source:
        policy_version = row_policy["policy_version"]
        acknowledged_at = ack_map.get(policy_version)
        label = row_policy.get("policy_key") or row_policy.get("policy_title") or row_policy.get("policy_name")
        payload.append(
            {
                "name": label,
                "policy_version": policy_version,
                "content_html": row_policy.get("policy_text") or "",
                "is_acknowledged": bool(acknowledged_at),
                "acknowledged_at": acknowledged_at,
            }
        )

    return {"policies": payload}


@frappe.whitelist()
def acknowledge_policy(
    *,
    policy_version: str | None = None,
    student_applicant: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    if not policy_version:
        frappe.throw(_("policy_version is required."))

    existing = frappe.db.get_value(
        "Policy Acknowledgement",
        {
            "policy_version": policy_version,
            "acknowledged_for": "Applicant",
            "context_doctype": "Student Applicant",
            "context_name": row.get("name"),
        },
        ["name", "acknowledged_at"],
        as_dict=True,
    )
    if existing:
        return {"ok": True, "acknowledged_at": existing.get("acknowledged_at")}

    doc = frappe.get_doc(
        {
            "doctype": "Policy Acknowledgement",
            "policy_version": policy_version,
            "acknowledged_by": user,
            "acknowledged_for": "Applicant",
            "context_doctype": "Student Applicant",
            "context_name": row.get("name"),
        }
    )
    doc.insert(ignore_permissions=True)

    return {"ok": True, "acknowledged_at": doc.acknowledged_at}


@frappe.whitelist()
def submit_application(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    result = applicant._set_status("Submitted", "Application submitted", permission_checker=None)
    return {"ok": True, "changed": result.get("changed")}


@frappe.whitelist()
def invite_applicant(*, student_applicant: str | None = None, email: str | None = None) -> dict:
    ensure_admissions_permission()

    if not student_applicant:
        frappe.throw(_("student_applicant is required."))
    if not email:
        frappe.throw(_("email is required."))

    email = email.strip().lower()
    if not email:
        frappe.throw(_("email is required."))

    applicant = frappe.get_doc("Student Applicant", student_applicant)

    if applicant.applicant_user:
        if applicant.applicant_user != email:
            frappe.throw(_("Applicant already linked to a different user."))
        # Idempotent: ensure role exists and return
        user_doc = frappe.get_doc("User", applicant.applicant_user)
        if ADMISSIONS_ROLE not in {r.role for r in user_doc.roles}:
            user_doc.append("roles", {"role": ADMISSIONS_ROLE})
            user_doc.save(ignore_permissions=True)
        return {"ok": True, "user": user_doc.name}

    user_doc = None
    if frappe.db.exists("User", email):
        user_doc = frappe.get_doc("User", email)
        existing_roles = {row.role for row in (user_doc.roles or [])}
        non_portal_roles = existing_roles - {ADMISSIONS_ROLE}
        if non_portal_roles:
            frappe.throw(_("User already has non-admissions roles and cannot be invited."))
    else:
        user_doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": applicant.first_name or email,
                "last_name": applicant.last_name or "",
                "enabled": 1,
            }
        )
        user_doc.append("roles", {"role": ADMISSIONS_ROLE})
        user_doc.insert(ignore_permissions=True)

    if ADMISSIONS_ROLE not in {r.role for r in user_doc.roles}:
        user_doc.append("roles", {"role": ADMISSIONS_ROLE})
        user_doc.save(ignore_permissions=True)

    existing_link = frappe.db.get_value(
        "Student Applicant",
        {"applicant_user": user_doc.name},
        "name",
    )
    if existing_link and existing_link != applicant.name:
        frappe.throw(_("User is already linked to another Applicant."))

    if frappe.db.exists("Student", {"student_user_id": user_doc.name}):
        frappe.throw(_("User is already linked to a Student."))
    if frappe.db.exists("Guardian", {"user": user_doc.name}):
        frappe.throw(_("User is already linked to a Guardian."))
    if frappe.db.exists("Employee", {"user_id": user_doc.name}):
        frappe.throw(_("User is already linked to an Employee."))

    applicant.flags.from_applicant_invite = True
    applicant.applicant_user = user_doc.name

    if applicant.application_status == "Draft":
        applicant._set_status("Invited", "Applicant invited", permission_checker=None)
    else:
        applicant.save(ignore_permissions=True)

    applicant.add_comment(
        "Comment",
        text=_("Applicant portal user invited for {0} by {1}.").format(
            frappe.bold(applicant.name), frappe.bold(frappe.session.user)
        ),
    )

    # Send welcome/invite email if supported
    try:
        if hasattr(user_doc, "send_welcome_email"):
            user_doc.send_welcome_email()
        elif hasattr(user_doc, "send_password_notification"):
            user_doc.send_password_notification()
        else:
            frappe.sendmail(
                recipients=[email],
                subject=_("Admissions Portal Access"),
                message=_("Your admissions portal access is ready."),
            )
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Admissions applicant invite email failed")
        frappe.throw(_("Unable to send invite email."))

    return {"ok": True, "user": user_doc.name}
