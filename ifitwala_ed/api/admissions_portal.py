# ifitwala_ed/api/admissions_portal.py

from __future__ import annotations

import base64
import io
import os

import frappe
from frappe import _
from frappe.utils import cint, now_datetime
from PIL import Image, UnidentifiedImageError

from ifitwala_ed.admission import admissions_portal as admission_api
from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    ensure_contact_for_email,
    ensure_inquiry_contact,
    get_applicant_scope_ancestors,
    get_contact_email_options,
    get_contact_primary_email,
    has_complete_applicant_document_type_classification,
    is_applicant_document_type_in_scope,
    normalize_email_value,
    sync_student_applicant_contact_binding,
    upsert_contact_email,
)
from ifitwala_ed.admission.applicant_review_workflow import materialize_health_review_assignments
from ifitwala_ed.governance.policy_scope_utils import (
    get_organization_ancestors_including_self,
    get_school_ancestors_including_self,
    select_nearest_policy_rows_by_key,
)
from ifitwala_ed.governance.policy_utils import ensure_policy_applies_to_column
from ifitwala_ed.utilities import file_dispatcher

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

APPLICANT_PROFILE_FIELDS = (
    "student_preferred_name",
    "student_date_of_birth",
    "student_gender",
    "student_mobile_number",
    "student_joining_date",
    "student_first_language",
    "student_second_language",
    "student_nationality",
    "student_second_nationality",
    "residency_status",
)

APPLICANT_PROFILE_REQUIRED_FIELD_LABELS = (
    ("student_date_of_birth", "Date of Birth"),
    ("student_gender", "Student Gender"),
    ("student_mobile_number", "Mobile Number"),
    ("student_first_language", "First Language"),
    ("student_nationality", "Nationality"),
    ("residency_status", "Residency Status"),
)

APPLICANT_PROFILE_GENDER_OPTIONS = ("Female", "Male", "Other")
APPLICANT_PROFILE_RESIDENCY_OPTIONS = ("Local Resident", "Expat Resident", "Boarder", "Other")


def _has_health_declaration_column() -> bool:
    try:
        return bool(frappe.db.has_column("Applicant Health Profile", "applicant_health_declared_complete"))
    except Exception:
        return False


def _default_health_payload() -> dict:
    payload = {field: "" for field in APPLICANT_HEALTH_FIELDS}
    payload["allergies"] = 0
    payload["vaccinations"] = []
    payload["applicant_health_declared_complete"] = 0
    payload["applicant_health_declared_by"] = ""
    payload["applicant_health_declared_on"] = ""
    payload["applicant_display_name"] = ""
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


def _as_bool(value) -> bool:
    return bool(_as_check(value))


def _normalize_signature_name(value: str | None) -> str:
    return " ".join((value or "").split()).casefold()


def _coerce_vaccination_date(value) -> str | None:
    text = _as_text(value).strip()
    return text or None


def _decode_base64_content(content_text: str | None) -> bytes:
    if not content_text:
        frappe.throw(_("Vaccination proof content is required."))
    try:
        return base64.b64decode(content_text)
    except Exception:
        frappe.throw(_("Vaccination proof content must be base64-encoded."))


def _decode_profile_image_content(content_text: str | None) -> bytes:
    if not content_text:
        frappe.throw(_("Profile image content is required."))
    try:
        content = base64.b64decode(content_text, validate=True)
    except Exception:
        frappe.throw(_("Profile image content must be base64-encoded."))
    if not content:
        frappe.throw(_("Profile image content is empty."))
    return content


def _validate_profile_image_content(content: bytes) -> None:
    try:
        with Image.open(io.BytesIO(content)) as img:
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError):
        frappe.throw(_("Uploaded profile image must be a valid image file."))


def _ensure_file_on_disk(file_doc) -> None:
    if not file_doc or not file_doc.file_url:
        frappe.throw(_("File URL missing after upload."))
    if file_doc.file_url.startswith("http"):
        return

    rel_path = file_doc.file_url.lstrip("/")
    if rel_path.startswith("private/") or rel_path.startswith("public/"):
        abs_path = frappe.utils.get_site_path(rel_path)
    else:
        base = "private" if file_doc.is_private else "public"
        abs_path = frappe.utils.get_site_path(base, rel_path)

    if not os.path.exists(abs_path):
        frappe.throw(_("File could not be finalized on disk. Please retry the upload."))


def _build_applicant_display_name(row: dict) -> str:
    parts = [
        _as_text(row.get("first_name")).strip(),
        _as_text(row.get("middle_name")).strip(),
        _as_text(row.get("last_name")).strip(),
    ]
    name = " ".join(part for part in parts if part).strip()
    return name or _as_text(row.get("name")).strip()


def _portal_health_state(student_applicant: str) -> dict:
    health_name = frappe.db.get_value(
        "Applicant Health Profile",
        {"student_applicant": student_applicant},
        "name",
    )
    if not health_name:
        return {"ok": False, "status": "missing"}

    if _has_health_declaration_column():
        declared = frappe.db.get_value(
            "Applicant Health Profile",
            health_name,
            "applicant_health_declared_complete",
        )
        if cint(declared):
            return {"ok": True, "status": "complete"}
        return {"ok": False, "status": "in_progress"}

    # Backward-compatible fallback for pre-migration sites.
    legacy_review_status = frappe.db.get_value(
        "Applicant Health Profile",
        health_name,
        "review_status",
    )
    if legacy_review_status == "Cleared":
        return {"ok": True, "status": "complete"}
    return {"ok": False, "status": "in_progress"}


def _vaccination_slot(row: dict, index: int) -> str:
    vaccine = _as_text(row.get("vaccine_name")).strip()
    date_value = _as_text(row.get("date")).strip()
    base = "_".join(part for part in [vaccine, date_value] if part) or f"row_{index + 1}"
    return f"health_vaccination_proof_{frappe.scrub(base)[:80]}"


def _upload_vaccination_proof(
    *,
    applicant_row: dict,
    health_doc,
    vaccination_row: dict,
    index: int,
) -> str:
    health_doc_name = _as_text(getattr(health_doc, "name", "")).strip()
    if not health_doc_name and hasattr(health_doc, "save"):
        health_doc.save(ignore_permissions=True)
        health_doc_name = _as_text(getattr(health_doc, "name", "")).strip()
    if not health_doc_name:
        frappe.log_error(
            message=frappe.as_json(
                {
                    "error": "health_profile_name_missing_for_vaccination_upload",
                    "health_doc_type": str(type(health_doc)),
                    "health_doc_name": getattr(health_doc, "name", None),
                    "applicant_row_name": applicant_row.get("name"),
                    "vaccination_index": index,
                }
            ),
            title="Applicant Health Upload Failed",
        )
        frappe.throw(_("Unable to attach vaccination proof because the health profile was not persisted."))

    content = _decode_base64_content(_as_text(vaccination_row.get("vaccination_proof_content")))
    file_name = (
        _as_text(vaccination_row.get("vaccination_proof_file_name")).strip() or f"vaccination_proof_{index + 1}.png"
    )
    slot = _vaccination_slot(vaccination_row, index)

    file_doc = file_dispatcher.create_and_classify_file(
        file_kwargs={
            "attached_to_doctype": "Applicant Health Profile",
            "attached_to_name": health_doc_name,
            "attached_to_field": "vaccinations",
            "file_name": file_name,
            "content": content,
            "is_private": 1,
        },
        classification={
            "primary_subject_type": "Student Applicant",
            "primary_subject_id": applicant_row.get("name"),
            "data_class": "safeguarding",
            "purpose": "medical_record",
            "retention_policy": "until_school_exit_plus_6m",
            "slot": slot,
            "organization": applicant_row.get("organization"),
            "school": applicant_row.get("school"),
            "upload_source": "SPA",
        },
        context_override={
            "root_folder": "Home/Admissions",
            "subfolder": f"Applicant/{applicant_row.get('name')}/Health",
            "file_category": "Admissions Health",
            "logical_key": slot,
        },
    )
    return _as_text(file_doc.file_url)


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
                "date": _coerce_vaccination_date(row.get("date")),
                "vaccination_proof": _as_text(row.get("vaccination_proof")),
                "additional_notes": _as_text(row.get("additional_notes")),
                "vaccination_proof_content": _as_text(row.get("vaccination_proof_content")),
                "vaccination_proof_file_name": _as_text(row.get("vaccination_proof_file_name")),
                "clear_vaccination_proof": _as_bool(row.get("clear_vaccination_proof")),
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
    if _has_health_declaration_column():
        payload["applicant_health_declared_complete"] = _as_check(doc.get("applicant_health_declared_complete"))
        payload["applicant_health_declared_by"] = _as_text(doc.get("applicant_health_declared_by"))
        payload["applicant_health_declared_on"] = _as_text(doc.get("applicant_health_declared_on"))
    else:
        payload["applicant_health_declared_complete"] = 1 if _as_text(doc.get("review_status")) == "Cleared" else 0
        payload["applicant_health_declared_by"] = ""
        payload["applicant_health_declared_on"] = ""
    return payload


def _default_profile_payload() -> dict:
    return {fieldname: "" for fieldname in APPLICANT_PROFILE_FIELDS}


def _application_context_payload(row) -> dict:
    return {
        "organization": _as_text(row.get("organization")),
        "school": _as_text(row.get("school")),
        "academic_year": _as_text(row.get("academic_year")),
        "term": _as_text(row.get("term")),
        "program": _as_text(row.get("program")),
        "program_offering": _as_text(row.get("program_offering")),
    }


def _serialize_applicant_profile(row) -> dict:
    payload = _default_profile_payload()
    for fieldname in APPLICANT_PROFILE_FIELDS:
        payload[fieldname] = _as_text(row.get(fieldname)).strip()
    return payload


def _profile_completeness(profile_payload: dict) -> dict:
    required = [label for _, label in APPLICANT_PROFILE_REQUIRED_FIELD_LABELS]
    missing: list[str] = []
    for fieldname, label in APPLICANT_PROFILE_REQUIRED_FIELD_LABELS:
        value = _as_text(profile_payload.get(fieldname)).strip()
        if not value:
            missing.append(label)
    return {"ok": not missing, "missing": missing, "required": required}


def _build_profile_payload(applicant) -> dict:
    profile = _serialize_applicant_profile(applicant)
    completeness = _profile_completeness(profile)
    return {
        "profile": profile,
        "completeness": completeness,
        "application_context": _application_context_payload(applicant),
        "options": _profile_reference_options(),
        "applicant_image": _as_text(applicant.get("applicant_image")).strip(),
    }


def _profile_reference_options() -> dict:
    language_rows = frappe.get_all(
        "Language Xtra",
        filters={"enabled": 1},
        fields=["name", "language_name"],
        order_by="language_name asc",
    )
    country_rows = frappe.get_all(
        "Country",
        fields=["name"],
        order_by="name asc",
    )
    return {
        "genders": list(APPLICANT_PROFILE_GENDER_OPTIONS),
        "residency_statuses": list(APPLICANT_PROFILE_RESIDENCY_OPTIONS),
        "languages": [
            {
                "value": _as_text(row.get("name")).strip(),
                "label": _as_text(row.get("language_name")).strip() or _as_text(row.get("name")).strip(),
            }
            for row in language_rows
            if _as_text(row.get("name")).strip()
        ],
        "countries": [
            {
                "value": _as_text(row.get("name")).strip(),
                "label": _as_text(row.get("name")).strip(),
            }
            for row in country_rows
            if _as_text(row.get("name")).strip()
        ],
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
    fields = fields or [
        "name",
        "application_status",
        "organization",
        "school",
        "academic_year",
        "term",
        "program",
        "program_offering",
        "first_name",
        "middle_name",
        "last_name",
        *APPLICANT_PROFILE_FIELDS,
    ]
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
    profile = readiness.get("profile") or {}

    if not profile.get("ok"):
        actions.append(
            {
                "label": _("Complete profile information"),
                "route_name": "admissions-profile",
                "intent": "primary",
                "is_blocking": True,
            }
        )

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
        missing_docs = documents.get("missing") or []
        unapproved_docs = documents.get("unapproved") or []
        if missing_docs:
            actions.append(
                {
                    "label": _("Upload required documents"),
                    "route_name": "admissions-documents",
                    "intent": "primary",
                    "is_blocking": True,
                }
            )
        elif unapproved_docs:
            actions.append(
                {
                    "label": _("Documents under review"),
                    "route_name": "admissions-documents",
                    "intent": "default",
                    "is_blocking": False,
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
            "academic_year": row.get("academic_year"),
            "term": row.get("term"),
            "program": row.get("program"),
            "program_offering": row.get("program_offering"),
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
    portal_health = _portal_health_state(applicant.name)
    readiness_for_portal = dict(readiness)
    readiness_for_portal["health"] = portal_health

    completeness = {
        "profile": _completion_state_for_requirement(
            (readiness.get("profile") or {}).get("required") or [],
            (readiness.get("profile") or {}).get("missing") or [],
        ),
        "health": _completion_state_for_health(portal_health),
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
    next_actions = _derive_next_actions(applicant.application_status, readiness_for_portal)

    return {
        "applicant": {
            "name": applicant.name,
            "portal_status": portal_status,
            "submitted_at": applicant.get("submitted_at"),
            "decision_at": applicant.get("decision_at"),
        },
        "application_context": _application_context_payload(applicant),
        "profile": _serialize_applicant_profile(applicant),
        "completeness": completeness,
        "next_actions": next_actions,
    }


@frappe.whitelist()
def get_applicant_profile(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    return _build_profile_payload(applicant)


@frappe.whitelist()
def update_applicant_profile(
    *,
    student_applicant: str | None = None,
    student_preferred_name: str | None = None,
    student_date_of_birth: str | None = None,
    student_gender: str | None = None,
    student_mobile_number: str | None = None,
    student_joining_date: str | None = None,
    student_first_language: str | None = None,
    student_second_language: str | None = None,
    student_nationality: str | None = None,
    student_second_nationality: str | None = None,
    residency_status: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    incoming_joining_date = _as_text(student_joining_date).strip() if student_joining_date is not None else None
    existing_joining_date = _as_text(applicant.get("student_joining_date")).strip()
    if incoming_joining_date is not None and incoming_joining_date != existing_joining_date:
        frappe.throw(_("Admission Date can only be set by the admissions office."), frappe.PermissionError)

    updates = {
        "student_preferred_name": _as_text(
            applicant.get("student_preferred_name") if student_preferred_name is None else student_preferred_name
        ).strip(),
        "student_date_of_birth": _as_text(
            applicant.get("student_date_of_birth") if student_date_of_birth is None else student_date_of_birth
        ).strip(),
        "student_gender": _as_text(
            applicant.get("student_gender") if student_gender is None else student_gender
        ).strip(),
        "student_mobile_number": _as_text(
            applicant.get("student_mobile_number") if student_mobile_number is None else student_mobile_number
        ).strip(),
        "student_joining_date": existing_joining_date,
        "student_first_language": _as_text(
            applicant.get("student_first_language") if student_first_language is None else student_first_language
        ).strip(),
        "student_second_language": _as_text(
            applicant.get("student_second_language") if student_second_language is None else student_second_language
        ).strip(),
        "student_nationality": _as_text(
            applicant.get("student_nationality") if student_nationality is None else student_nationality
        ).strip(),
        "student_second_nationality": _as_text(
            applicant.get("student_second_nationality")
            if student_second_nationality is None
            else student_second_nationality
        ).strip(),
        "residency_status": _as_text(
            applicant.get("residency_status") if residency_status is None else residency_status
        ).strip(),
    }

    applicant.update(updates)
    applicant.save(ignore_permissions=True)
    payload = _build_profile_payload(applicant)
    payload["ok"] = True
    return payload


@frappe.whitelist()
def upload_applicant_profile_image(
    *,
    student_applicant: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    is_read_only, reason = _read_only_for(_as_text(row.get("application_status")).strip())
    if is_read_only:
        frappe.throw(reason or _("This application is read-only."), frappe.PermissionError)

    applicant_name = _as_text(row.get("name")).strip()
    if not applicant_name:
        frappe.throw(_("Applicant context is missing."))

    upload_name = _as_text(file_name).strip()
    if not upload_name:
        frappe.throw(_("file_name is required."))

    upload_content = _decode_profile_image_content(_as_text(content))
    _validate_profile_image_content(upload_content)

    applicant = frappe.get_doc("Student Applicant", applicant_name)
    if not applicant.get("organization") or not applicant.get("school"):
        frappe.throw(_("Organization and School are required for file classification."))

    file_doc = file_dispatcher.create_and_classify_file(
        file_kwargs={
            "attached_to_doctype": "Student Applicant",
            "attached_to_name": applicant.name,
            "attached_to_field": "applicant_image",
            "file_name": upload_name,
            "content": upload_content,
            "is_private": 1,
        },
        classification={
            "primary_subject_type": "Student Applicant",
            "primary_subject_id": applicant.name,
            "data_class": "identity_image",
            "purpose": "applicant_profile_display",
            "retention_policy": "until_school_exit_plus_6m",
            "slot": "profile_image",
            "organization": applicant.organization,
            "school": applicant.school,
            "upload_source": "SPA",
        },
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value(
        "Student Applicant",
        applicant.name,
        "applicant_image",
        file_doc.file_url,
        update_modified=False,
    )
    classification_name = frappe.db.get_value("File Classification", {"file": file_doc.name}, "name")

    return {
        "ok": True,
        "file": file_doc.name,
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
        "file_size": file_doc.file_size,
        "classification": classification_name,
    }


@frappe.whitelist()
def get_applicant_health(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    applicant_display_name = _build_applicant_display_name(row)

    health_name = frappe.db.get_value(
        "Applicant Health Profile",
        {"student_applicant": row.get("name")},
        "name",
    )
    if not health_name:
        payload = _default_health_payload()
        payload["applicant_display_name"] = applicant_display_name
        return payload

    doc = frappe.get_doc("Applicant Health Profile", health_name)
    payload = _serialize_health_doc(doc)
    payload["applicant_display_name"] = applicant_display_name
    return payload


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
    applicant_health_declared_complete=None,
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
    has_declaration_column = _has_health_declaration_column()
    if has_declaration_column:
        previous_declared_complete = bool(cint(doc.get("applicant_health_declared_complete")))
    else:
        previous_declared_complete = bool(_portal_health_state(row.get("name")).get("ok"))

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
    if vaccinations is None:
        normalized_vaccinations = [
            {
                "vaccine_name": _as_text(row_existing.get("vaccine_name")),
                "date": _coerce_vaccination_date(row_existing.get("date")),
                "vaccination_proof": _as_text(row_existing.get("vaccination_proof")),
                "additional_notes": _as_text(row_existing.get("additional_notes")),
                "vaccination_proof_content": "",
                "vaccination_proof_file_name": "",
                "clear_vaccination_proof": False,
            }
            for row_existing in (doc.get("vaccinations") or [])
        ]
    else:
        normalized_vaccinations = _normalize_vaccinations(vaccinations)
    declaration_provided = applicant_health_declared_complete is not None
    declaration_confirmed = _as_bool(applicant_health_declared_complete)

    doc.update(updates)
    if doc.is_new() or not _as_text(doc.name).strip():
        # Vaccination proof uploads attach to this profile and require a persisted name.
        doc.save(ignore_permissions=True)
    if not _as_text(doc.name).strip():
        frappe.log_error(
            message=frappe.as_json(
                {
                    "error": "health_profile_name_missing_after_save",
                    "doc_type": str(type(doc)),
                    "doc_name": getattr(doc, "name", None),
                    "student_applicant": row.get("name"),
                }
            ),
            title="Applicant Health Save Failed",
        )
        frappe.throw(_("Unable to save health information because the profile identifier is missing."))

    doc.set("vaccinations", [])
    for index, vaccination_row in enumerate(normalized_vaccinations):
        proof_url = _as_text(vaccination_row.get("vaccination_proof"))
        if vaccination_row.get("clear_vaccination_proof"):
            proof_url = ""
        if _as_text(vaccination_row.get("vaccination_proof_content")):
            proof_url = _upload_vaccination_proof(
                applicant_row=row,
                health_doc=doc,
                vaccination_row=vaccination_row,
                index=index,
            )

        doc.append(
            "vaccinations",
            {
                "vaccine_name": _as_text(vaccination_row.get("vaccine_name")),
                "date": _coerce_vaccination_date(vaccination_row.get("date")),
                "vaccination_proof": proof_url,
                "additional_notes": _as_text(vaccination_row.get("additional_notes")),
            },
        )

    if declaration_provided and has_declaration_column:
        if declaration_confirmed:
            doc.applicant_health_declared_complete = 1
            doc.applicant_health_declared_by = user
            doc.applicant_health_declared_on = now_datetime()
        else:
            doc.applicant_health_declared_complete = 0
            doc.applicant_health_declared_by = None
            doc.applicant_health_declared_on = None

    doc.save(ignore_permissions=True)

    if has_declaration_column:
        declared_complete = bool(cint(doc.get("applicant_health_declared_complete")))
    else:
        declared_complete = bool(_portal_health_state(row.get("name")).get("ok"))

    if has_declaration_column and declared_complete and not previous_declared_complete:
        materialize_health_review_assignments(
            applicant_health_profile=doc.name,
            source_event="health_submitted",
        )

    return {
        "ok": True,
        "applicant_health_declared_complete": declared_complete,
    }


@frappe.whitelist()
def list_applicant_documents(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    documents = frappe.get_all(
        "Applicant Document",
        filters={"student_applicant": row.get("name")},
        fields=["name", "document_type", "review_status", "reviewed_by", "reviewed_on", "modified"],
        order_by="modified desc",
    )

    if not documents:
        return {"documents": []}

    name_list = [d["name"] for d in documents]
    item_rows = frappe.get_all(
        "Applicant Document Item",
        filters={"applicant_document": ["in", name_list]},
        fields=[
            "name",
            "applicant_document",
            "item_key",
            "item_label",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "modified",
        ],
        order_by="modified desc",
    )
    item_names = [row_item.get("name") for row_item in item_rows if row_item.get("name")]

    latest_file_by_item: dict[str, dict] = {}
    if item_names:
        item_file_rows = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": ["in", item_names],
            },
            fields=["attached_to_name", "file_url", "file_name", "creation"],
            order_by="creation desc",
        )
        for row_file in item_file_rows:
            parent = row_file.get("attached_to_name")
            if not parent or parent in latest_file_by_item:
                continue
            latest_file_by_item[parent] = row_file

    legacy_latest_file_by_document: dict[str, dict] = {}
    legacy_file_rows = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Applicant Document",
            "attached_to_name": ["in", name_list],
        },
        fields=["attached_to_name", "file_url", "file_name", "creation"],
        order_by="creation desc",
    )
    for row_file in legacy_file_rows:
        parent = row_file.get("attached_to_name")
        if not parent or parent in legacy_latest_file_by_document:
            continue
        legacy_latest_file_by_document[parent] = row_file

    items_by_document: dict[str, list[dict]] = {}
    for row_item in item_rows:
        parent = row_item.get("applicant_document")
        if not parent:
            continue
        latest_file = latest_file_by_item.get(row_item.get("name"), {})
        items_by_document.setdefault(parent, []).append(
            {
                "name": row_item.get("name"),
                "item_key": row_item.get("item_key"),
                "item_label": row_item.get("item_label"),
                "review_status": row_item.get("review_status") or "Pending",
                "reviewed_by": row_item.get("reviewed_by"),
                "reviewed_on": row_item.get("reviewed_on"),
                "uploaded_at": latest_file.get("creation"),
                "file_url": latest_file.get("file_url"),
                "file_name": latest_file.get("file_name"),
            }
        )

    payload = []
    for doc in documents:
        doc_name = doc.get("name")
        items = items_by_document.get(doc_name, [])

        if not items:
            legacy_file = legacy_latest_file_by_document.get(doc_name, {})
            if legacy_file:
                items = [
                    {
                        "name": "",
                        "item_key": "legacy",
                        "item_label": _("Existing upload"),
                        "review_status": doc.get("review_status") or "Pending",
                        "reviewed_by": doc.get("reviewed_by"),
                        "reviewed_on": doc.get("reviewed_on"),
                        "uploaded_at": legacy_file.get("creation"),
                        "file_url": legacy_file.get("file_url"),
                        "file_name": legacy_file.get("file_name"),
                    }
                ]

        latest_uploaded_at = None
        latest_file_url = None
        if items:
            sorted_items = sorted(
                items,
                key=lambda row_item: row_item.get("uploaded_at") or "",
                reverse=True,
            )
            latest_uploaded_at = sorted_items[0].get("uploaded_at")
            latest_file_url = sorted_items[0].get("file_url")

        payload.append(
            {
                "name": doc_name,
                "document_type": doc.get("document_type"),
                "review_status": doc.get("review_status") or "Pending",
                "uploaded_at": latest_uploaded_at,
                "file_url": latest_file_url,
                "items": items,
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

    applicant_org_ancestors, applicant_school_ancestors = get_applicant_scope_ancestors(
        organization=organization,
        school=school,
    )
    applicant_org_ancestors = set(applicant_org_ancestors)
    applicant_school_ancestors = set(applicant_school_ancestors)

    rows = frappe.get_all(
        "Applicant Document Type",
        filters={"is_active": 1},
        fields=[
            "name",
            "code",
            "document_type_name",
            "belongs_to",
            "is_required",
            "is_repeatable",
            "min_items_required",
            "description",
            "school",
            "organization",
        ],
        order_by="is_required desc, document_type_name asc",
    )

    payload = []
    for row_type in rows:
        if not is_applicant_document_type_in_scope(
            document_type_organization=row_type.get("organization"),
            document_type_school=row_type.get("school"),
            applicant_org_ancestors=applicant_org_ancestors,
            applicant_school_ancestors=applicant_school_ancestors,
        ):
            continue
        payload.append(
            {
                "name": row_type.get("name"),
                "code": row_type.get("code"),
                "document_type_name": row_type.get("document_type_name"),
                "belongs_to": row_type.get("belongs_to") or "",
                "is_required": bool(row_type.get("is_required")),
                "is_repeatable": bool(row_type.get("is_repeatable")),
                "min_items_required": cint(row_type.get("min_items_required") or 1),
                "description": row_type.get("description") or "",
            }
        )

    return {"document_types": payload}


@frappe.whitelist()
def upload_applicant_document(
    *,
    student_applicant: str | None = None,
    document_type: str | None = None,
    applicant_document_item: str | None = None,
    item_key: str | None = None,
    item_label: str | None = None,
    client_request_id: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    if not document_type:
        frappe.throw(_("document_type is required."))
    if not applicant_document_item and not _as_text(item_key).strip() and not _as_text(item_label).strip():
        frappe.throw(_("Provide a short description for this file."))

    if not content and not (getattr(frappe.request, "files", None) and frappe.request.files.get("file")):
        frappe.throw(_("File content is required."))

    doc_type_row = frappe.db.get_value(
        "Applicant Document Type",
        document_type,
        [
            "organization",
            "school",
            "is_active",
            "code",
            "classification_slot",
            "classification_data_class",
            "classification_purpose",
            "classification_retention_policy",
        ],
        as_dict=True,
    )
    if not doc_type_row or not doc_type_row.get("is_active"):
        frappe.throw(_("Invalid or inactive document type."))

    applicant_org_ancestors, applicant_school_ancestors = get_applicant_scope_ancestors(
        organization=row.get("organization"),
        school=row.get("school"),
    )
    applicant_org_ancestors = set(applicant_org_ancestors)
    applicant_school_ancestors = set(applicant_school_ancestors)
    if not is_applicant_document_type_in_scope(
        document_type_organization=doc_type_row.get("organization"),
        document_type_school=doc_type_row.get("school"),
        applicant_org_ancestors=applicant_org_ancestors,
        applicant_school_ancestors=applicant_school_ancestors,
    ):
        frappe.throw(_("Document type is outside the Applicant scope."))

    if not has_complete_applicant_document_type_classification(doc_type_row):
        missing_labels = []
        for fieldname, label in (
            ("classification_slot", "slot"),
            ("classification_data_class", "data class"),
            ("classification_purpose", "purpose"),
            ("classification_retention_policy", "retention policy"),
        ):
            if not _as_text(doc_type_row.get(fieldname)).strip():
                missing_labels.append(label)
        doc_type_label = _as_text(doc_type_row.get("code") or document_type).strip() or _("Unknown")
        if missing_labels:
            frappe.throw(
                _("This document type is not configured for uploads ({0}). Missing: {1}.").format(
                    doc_type_label,
                    ", ".join(missing_labels),
                )
            )
        frappe.throw(_("This document type is not configured for uploads ({0}).").format(doc_type_label))

    payload = {
        "student_applicant": row.get("name"),
        "document_type": document_type,
        "applicant_document_item": applicant_document_item,
        "item_key": _as_text(item_key).strip() or None,
        "item_label": _as_text(item_label).strip() or None,
        "client_request_id": _as_text(client_request_id).strip() or None,
        "upload_source": "SPA",
        "is_private": 1,
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
    expected_signature_name = _build_applicant_display_name(row)

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
                "expected_signature_name": expected_signature_name,
            }
        )

    return {"policies": payload}


@frappe.whitelist()
def acknowledge_policy(
    *,
    policy_version: str | None = None,
    student_applicant: str | None = None,
    typed_signature_name: str | None = None,
    attestation_confirmed: int | str | bool | None = None,
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

    expected_signature_name = _build_applicant_display_name(row)
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
            _("Typed signature must match exactly: {0}").format(expected_signature_name),
            frappe.ValidationError,
        )

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
    result = applicant._submit_application(permission_checker=None)
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
    role_names = []
    seen = set()
    had_desk_user = False

    for row in user_doc.roles or []:
        role = (row.role or "").strip()
        if not role:
            continue
        if role == "Desk User":
            had_desk_user = True
            continue
        if role in seen:
            continue
        seen.add(role)
        role_names.append(role)

    if ADMISSIONS_ROLE not in seen:
        role_names.append(ADMISSIONS_ROLE)
        changed = True

    if had_desk_user:
        changed = True

    if changed:
        user_doc.set("roles", [{"role": role} for role in role_names])

    if (user_doc.user_type or "").strip() != "Website User":
        user_doc.user_type = "Website User"
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
        sync_student_applicant_contact_binding(
            student_applicant=applicant.name,
            contact_name=contact_name,
        )

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
    sync_student_applicant_contact_binding(
        student_applicant=applicant.name,
        contact_name=contact_name,
    )

    applicant.add_comment(
        "Comment",
        text=_("Applicant portal user invited for {0} by {1}.").format(
            frappe.bold(applicant.name), frappe.bold(frappe.session.user)
        ),
    )

    email_sent = _send_applicant_invite_email(user_doc, email)

    return {"ok": True, "user": user_doc.name, "resent": False, "email_sent": email_sent}
