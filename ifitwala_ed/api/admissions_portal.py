# ifitwala_ed/api/admissions_portal.py

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.admission import admissions_portal as admission_api
from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    ensure_contact_for_email,
    ensure_inquiry_contact,
    get_contact_email_options,
    get_contact_primary_email,
    normalize_email_value,
    upsert_contact_email,
)
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
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
    "Withdrawn": "Withdrawn",
    "Promoted": "Completed",
}

PORTAL_EDITABLE_STATUSES = {"Invited", "In Progress", "Missing Info"}

READ_ONLY_REASON_MAP = {
    "Draft": _("Application not yet open."),
    "Submitted": _("Application submitted."),
    "Under Review": _("Application under review."),
    "Approved": _("Application accepted."),
    "Rejected": _("Application rejected."),
    "Withdrawn": _("Application withdrawn."),
    "Promoted": _("Application completed."),
}

APPLICANT_HEALTH_FIELDS = (
    "blood_group",
    "allergies",
    "food_allergies",
    "insect_bites",
    "medication_allergies",
    "asthma",
    "bladder__bowel_problems",
    "diabetes",
    "headache_migraine",
    "high_blood_pressure",
    "seizures",
    "bone_joints_scoliosis",
    "blood_disorder_info",
    "fainting_spells",
    "hearing_problems",
    "recurrent_ear_infections",
    "speech_problem",
    "birth_defect",
    "dental_problems",
    "g6pd",
    "heart_problems",
    "recurrent_nose_bleeding",
    "vision_problem",
    "diet_requirements",
    "medical_surgeries__hospitalizations",
    "other_medical_information",
)

APPLICANT_HEALTH_VACCINATION_FIELDS = (
    "vaccine_name",
    "date",
    "vaccination_proof",
    "additional_notes",
)


def _default_health_payload() -> dict:
    payload = {field: "" for field in APPLICANT_HEALTH_FIELDS}
    payload["allergies"] = 0
    payload["vaccinations"] = []
    return payload


def _as_text(value) -> str:
    if value is None:
        return ""
    return str(value)


def _as_check(value) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    normalized = str(value or "").strip().lower()
    return 1 if normalized in {"1", "true", "yes", "on"} else 0


def _normalize_vaccinations(vaccinations) -> list[dict]:
    if vaccinations is None:
        return []
    if isinstance(vaccinations, str):
        vaccinations = frappe.parse_json(vaccinations)
    if not isinstance(vaccinations, list):
        frappe.throw(_("Vaccinations payload must be a list."))

    normalized: list[dict] = []
    for row in vaccinations:
        if not isinstance(row, dict):
            frappe.throw(_("Each vaccination entry must be an object."))
        normalized.append(
            {
                "vaccine_name": _as_text(row.get("vaccine_name")),
                "date": row.get("date"),
                "vaccination_proof": _as_text(row.get("vaccination_proof")),
                "additional_notes": _as_text(row.get("additional_notes")),
            }
        )
    return normalized


def _serialize_health_doc(doc) -> dict:
    payload = _default_health_payload()
    for fieldname in APPLICANT_HEALTH_FIELDS:
        if fieldname == "allergies":
            payload[fieldname] = _as_check(doc.get(fieldname))
        else:
            payload[fieldname] = _as_text(doc.get(fieldname))

    payload["vaccinations"] = [
        {fieldname: _as_text(row.get(fieldname)) for fieldname in APPLICANT_HEALTH_VACCINATION_FIELDS}
        for row in (doc.get("vaccinations") or [])
    ]
    return payload


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
    return True, READ_ONLY_REASON_MAP.get(application_status) or _("Application is read-only.")


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

    health_name = frappe.db.get_value(
        "Applicant Health Profile",
        {"student_applicant": row.get("name")},
        "name",
    )
    if not health_name:
        return _default_health_payload()

    doc = frappe.get_doc("Applicant Health Profile", health_name)
    return _serialize_health_doc(doc)


@frappe.whitelist()
def update_applicant_health(
    *,
    student_applicant: str | None = None,
    blood_group: str | None = None,
    allergies=None,
    food_allergies: str | None = None,
    insect_bites: str | None = None,
    medication_allergies: str | None = None,
    asthma: str | None = None,
    bladder__bowel_problems: str | None = None,
    diabetes: str | None = None,
    headache_migraine: str | None = None,
    high_blood_pressure: str | None = None,
    seizures: str | None = None,
    bone_joints_scoliosis: str | None = None,
    blood_disorder_info: str | None = None,
    fainting_spells: str | None = None,
    hearing_problems: str | None = None,
    recurrent_ear_infections: str | None = None,
    speech_problem: str | None = None,
    birth_defect: str | None = None,
    dental_problems: str | None = None,
    g6pd: str | None = None,
    heart_problems: str | None = None,
    recurrent_nose_bleeding: str | None = None,
    vision_problem: str | None = None,
    diet_requirements: str | None = None,
    medical_surgeries__hospitalizations: str | None = None,
    other_medical_information: str | None = None,
    vaccinations=None,
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
        "blood_group": _as_text(blood_group),
        "allergies": _as_check(allergies),
        "food_allergies": _as_text(food_allergies),
        "insect_bites": _as_text(insect_bites),
        "medication_allergies": _as_text(medication_allergies),
        "asthma": _as_text(asthma),
        "bladder__bowel_problems": _as_text(bladder__bowel_problems),
        "diabetes": _as_text(diabetes),
        "headache_migraine": _as_text(headache_migraine),
        "high_blood_pressure": _as_text(high_blood_pressure),
        "seizures": _as_text(seizures),
        "bone_joints_scoliosis": _as_text(bone_joints_scoliosis),
        "blood_disorder_info": _as_text(blood_disorder_info),
        "fainting_spells": _as_text(fainting_spells),
        "hearing_problems": _as_text(hearing_problems),
        "recurrent_ear_infections": _as_text(recurrent_ear_infections),
        "speech_problem": _as_text(speech_problem),
        "birth_defect": _as_text(birth_defect),
        "dental_problems": _as_text(dental_problems),
        "g6pd": _as_text(g6pd),
        "heart_problems": _as_text(heart_problems),
        "recurrent_nose_bleeding": _as_text(recurrent_nose_bleeding),
        "vision_problem": _as_text(vision_problem),
        "diet_requirements": _as_text(diet_requirements),
        "medical_surgeries__hospitalizations": _as_text(medical_surgeries__hospitalizations),
        "other_medical_information": _as_text(other_medical_information),
    }
    normalized_vaccinations = _normalize_vaccinations(vaccinations)

    doc.update(updates)
    doc.set("vaccinations", [])
    for row in normalized_vaccinations:
        doc.append("vaccinations", row)
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
    school_ancestors = get_school_ancestors_including_self(school)

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
        school_scope_sql = ""
        school_params: tuple[str, ...] = ()
        if school_ancestors:
            school_placeholders = ", ".join(["%s"] * len(school_ancestors))
            school_scope_sql = f" OR ip.school IN ({school_placeholders})"
            school_params = tuple(school_ancestors)
        policies_source = frappe.db.sql(
            f"""
            SELECT ip.name AS policy_name,
                   ip.policy_key AS policy_key,
                   ip.policy_title AS policy_title,
                   ip.organization AS policy_organization,
                   ip.school AS policy_school,
                   pv.name AS policy_version,
                   pv.policy_text AS policy_text
              FROM `tabInstitutional Policy` ip
              JOIN `tabPolicy Version` pv
                ON pv.institutional_policy = ip.name
             WHERE ip.is_active = 1
               AND pv.is_active = 1
               AND ip.organization IN ({org_placeholders})
               AND (ip.school IS NULL OR ip.school = ''{school_scope_sql})
               AND ip.applies_to LIKE %s
            """,
            (*ancestor_orgs, *school_params, "%Applicant%"),
            as_dict=True,
        )
        policies_source = select_nearest_policy_rows_by_key(
            rows=policies_source,
            context_organization=organization,
            context_school=school,
            policy_key_field="policy_key",
            policy_organization_field="policy_organization",
            policy_school_field="policy_school",
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
def withdraw_application(
    *,
    student_applicant: str | None = None,
    reason: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    result = applicant.withdraw_application(reason=reason)
    return {"ok": True, "changed": result.get("changed")}


def _ensure_admissions_applicant_role(user_doc) -> None:
    changed = False
    if ADMISSIONS_ROLE not in {r.role for r in user_doc.roles}:
        user_doc.append("roles", {"role": ADMISSIONS_ROLE})
        changed = True
    if not int(user_doc.enabled or 0):
        user_doc.enabled = 1
        changed = True
    if changed:
        user_doc.save(ignore_permissions=True)


def _call_user_method_if_available(user_doc, method_name: str) -> bool:
    target = getattr(user_doc, method_name, None)
    if not callable(target):
        return False
    try:
        target()
        return True
    except TypeError:
        return False


def _send_applicant_invite_email(user_doc, recipient: str) -> bool:
    try:
        if _call_user_method_if_available(user_doc, "send_welcome_email"):
            return True
        if _call_user_method_if_available(user_doc, "send_password_notification"):
            return True
        frappe.sendmail(
            recipients=[recipient],
            subject=_("Admissions Portal Access"),
            message=_("Your admissions portal access is ready. Use Forgot Password if needed."),
        )
        return True
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Admissions applicant invite email failed")
        return False


def _get_inquiry_contact_for_applicant(applicant_doc) -> str | None:
    inquiry_name = (applicant_doc.get("inquiry") or "").strip()
    if not inquiry_name:
        return None
    inquiry = frappe.get_doc("Inquiry", inquiry_name)
    return ensure_inquiry_contact(inquiry)


def _resolve_applicant_contact(
    applicant_doc, invite_email: str | None = None, *, allow_create: bool = False
) -> str | None:
    contact_name = (applicant_doc.get("applicant_contact") or "").strip()
    if not contact_name:
        contact_name = _get_inquiry_contact_for_applicant(applicant_doc) or ""

    invite_email = normalize_email_value(invite_email)
    if invite_email:
        existing_parent = frappe.db.get_value("Contact Email", {"email_id": invite_email}, "parent")
        if existing_parent and contact_name and existing_parent != contact_name:
            frappe.throw(_("Invite email is linked to a different Contact."))

        if not contact_name and allow_create:
            contact_name = ensure_contact_for_email(
                first_name=applicant_doc.get("first_name"),
                last_name=applicant_doc.get("last_name"),
                email=invite_email,
            )

        if contact_name:
            upsert_contact_email(contact_name, invite_email, set_primary_if_missing=True)

    return contact_name or None


@frappe.whitelist()
def get_invite_email_options(*, student_applicant: str | None = None) -> dict:
    ensure_admissions_permission()

    if not student_applicant:
        frappe.throw(_("student_applicant is required."))

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    contact_name = _resolve_applicant_contact(applicant, allow_create=False)

    emails: list[str] = []
    seen: set[str] = set()
    for value in (
        normalize_email_value(applicant.get("portal_account_email")),
        normalize_email_value(applicant.get("applicant_email")),
        normalize_email_value(applicant.get("applicant_user")),
    ):
        if value and value not in seen:
            seen.add(value)
            emails.append(value)

    for value in get_contact_email_options(contact_name):
        if value and value not in seen:
            seen.add(value)
            emails.append(value)

    selected = (
        normalize_email_value(applicant.get("portal_account_email"))
        or normalize_email_value(applicant.get("applicant_user"))
        or normalize_email_value(applicant.get("applicant_email"))
        or (emails[0] if emails else None)
    )

    return {
        "contact": contact_name,
        "emails": emails,
        "selected_email": selected,
    }


@frappe.whitelist()
def invite_applicant(*, student_applicant: str | None = None, email: str | None = None) -> dict:
    ensure_admissions_permission()

    if not student_applicant:
        frappe.throw(_("student_applicant is required."))
    if not email:
        frappe.throw(_("email is required."))

    email = normalize_email_value(email)
    if not email:
        frappe.throw(_("email is required."))

    applicant = frappe.get_doc("Student Applicant", student_applicant)

    if applicant.applicant_user:
        linked_user = normalize_email_value(applicant.applicant_user)
        if linked_user != email:
            frappe.throw(_("Applicant already linked to a different user."))

    contact_name = _resolve_applicant_contact(applicant, invite_email=email, allow_create=True)
    if not contact_name:
        frappe.throw(_("Unable to resolve Applicant Contact for this invite."))
    primary_contact_email = get_contact_primary_email(contact_name) or email

    if applicant.applicant_user:
        user_doc = frappe.get_doc("User", linked_user)
        _ensure_admissions_applicant_role(user_doc)

        applicant.flags.from_applicant_invite = True
        applicant.flags.from_contact_sync = True
        applicant.applicant_contact = contact_name
        applicant.applicant_email = primary_contact_email
        applicant.portal_account_email = email

        if applicant.application_status == "Draft":
            applicant._set_status("Invited", "Applicant invited", permission_checker=None)
        else:
            applicant.save(ignore_permissions=True)

        email_sent = _send_applicant_invite_email(user_doc, email)
        applicant.add_comment(
            "Comment",
            text=_("Applicant portal invite email re-sent for {0} by {1}.").format(
                frappe.bold(applicant.name), frappe.bold(frappe.session.user)
            ),
        )
        return {"ok": True, "user": user_doc.name, "resent": True, "email_sent": email_sent}

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

    _ensure_admissions_applicant_role(user_doc)

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
    applicant.flags.from_contact_sync = True
    applicant.applicant_user = user_doc.name
    applicant.applicant_contact = contact_name
    applicant.applicant_email = primary_contact_email
    applicant.portal_account_email = email

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

    email_sent = _send_applicant_invite_email(user_doc, email)

    return {"ok": True, "user": user_doc.name, "resent": False, "email_sent": email_sent}
