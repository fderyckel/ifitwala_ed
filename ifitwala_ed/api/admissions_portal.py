# ifitwala_ed/api/admissions_portal.py

from __future__ import annotations

import base64
import io
import os
import warnings
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from frappe.utils import cint, now_datetime, validate_email_address, validate_phone_number
from PIL import Image, ImageOps, UnidentifiedImageError

from ifitwala_ed.admission import admissions_portal as admission_api
from ifitwala_ed.admission.access import (
    ADMISSIONS_ACCESS_MODE_FAMILY,
    ADMISSIONS_FAMILY_ROLE,
    ADMISSIONS_PORTAL_ROLES,
    get_admissions_access_mode,
    get_admissions_portal_applicant_names_for_user,
    get_guardian_names_for_user,
    is_family_workspace_enabled,
)
from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE as ADMISSIONS_ROLE,
)
from ifitwala_ed.admission.admission_utils import (
    ensure_admissions_permission,
    ensure_contact_dynamic_link,
    ensure_contact_for_email,
    ensure_inquiry_contact,
    get_applicant_scope_ancestors,
    get_contact_primary_email,
    has_complete_applicant_document_type_classification,
    is_applicant_document_type_in_scope,
    normalize_email_value,
    sync_student_applicant_contact_binding,
    upsert_contact_email,
)
from ifitwala_ed.admission.applicant_review_workflow import materialize_health_review_assignments
from ifitwala_ed.admission.doctype.applicant_enrollment_plan.applicant_enrollment_plan import (
    get_applicant_enrollment_choice_state,
    get_latest_applicant_enrollment_plan,
)
from ifitwala_ed.api.attachment_previews import build_attachment_preview_item, extract_file_extension
from ifitwala_ed.api.file_access import (
    get_drive_file_thumbnail_ready_map,
    resolve_admissions_file_open_url,
    resolve_admissions_file_preview_url,
    resolve_admissions_file_thumbnail_url,
)
from ifitwala_ed.api.recommendation_intake import (
    get_recommendation_status_for_applicant,
    get_recommendation_template_rows_for_applicant,
)
from ifitwala_ed.governance.doctype.policy_acknowledgement.policy_acknowledgement import (
    get_policy_version_acknowledgement_clauses_map,
    populate_policy_acknowledgement_evidence,
)
from ifitwala_ed.governance.policy_utils import (
    ADMISSIONS_POLICY_MODE_FAMILY,
    get_applicant_policy_status,
)
from ifitwala_ed.integrations.drive.authority import (
    get_current_drive_file_for_slot,
    get_current_drive_files_for_attachments,
    get_drive_file_for_file,
)
from ifitwala_ed.utilities.html_sanitizer import sanitize_html

INVALID_SESSION_USERS = {"guest", "none", "null", "undefined"}

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

PROFILE_IMAGE_ALLOWED_EXTENSIONS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
}
PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL = "JPG, JPEG, PNG"
PROFILE_IMAGE_MAX_BYTES = 10 * 1024 * 1024
PROFILE_IMAGE_MAX_PIXELS = 25_000_000

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
APPLICANT_GUARDIAN_RELATIONSHIP_OPTIONS = (
    "Mother",
    "Father",
    "Stepmother",
    "Stepfather",
    "Grandmother",
    "Grandfather",
    "Aunt",
    "Uncle",
    "Sister",
    "Brother",
    "Other",
)
APPLICANT_GUARDIAN_GENDER_OPTIONS = ("Female", "Male", "Other", "Prefer Not To Say")
APPLICANT_GUARDIAN_EMPLOYMENT_SECTOR_OPTIONS = (
    "Corporate – Finance / Banking",
    "Corporate – Tech / IT",
    "Corporate – Manufacturing",
    "Corporate – Retail / FMCG",
    "Corporate – Hospitality / Tourism",
    "Corporate – Logistics / Transport",
    "Corporate – Construction / Engineering",
    "Corporate – Real Estate / Property",
    "Healthcare / Medical",
    "Education",
    "Government",
    "Embassy / Diplomatic Corps",
    "NGO / Non-Profit",
    "Armed Forces",
    "Creative Industries (Media / Design / Arts)",
    "Self-Employed",
    "Freelance / Consultant",
    "Homemaker",
    "Retired",
    "Other",
)
APPLICANT_GUARDIAN_CHECK_FIELDS = (
    "use_applicant_contact",
    "is_primary",
    "can_consent",
    "is_primary_guardian",
    "is_financial_guardian",
)
APPLICANT_GUARDIAN_TEXT_FIELDS = (
    "guardian",
    "contact",
    "relationship",
    "salutation",
    "guardian_full_name",
    "guardian_first_name",
    "guardian_last_name",
    "guardian_gender",
    "guardian_mobile_phone",
    "guardian_email",
    "guardian_work_email",
    "guardian_work_phone",
    "guardian_image",
    "user",
    "employment_sector",
    "work_place",
    "guardian_designation",
)
APPLICANT_GUARDIAN_FIELDS = ("name",) + APPLICANT_GUARDIAN_TEXT_FIELDS + APPLICANT_GUARDIAN_CHECK_FIELDS
APPLICANT_GUARDIAN_REQUIRED_FIELD_LABELS = (
    ("guardian_first_name", "Guardian First Name"),
    ("guardian_last_name", "Guardian Last Name"),
    ("guardian_email", "Guardian Personal Email"),
    ("guardian_mobile_phone", "Guardian Mobile Phone"),
    ("guardian_image", "Guardian Photo"),
)


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


def _has_bound_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _parse_request_payload(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode()
        except Exception:
            return None
    if isinstance(value, str):
        try:
            value = frappe.parse_json(value)
        except Exception:
            return None
        if isinstance(value, dict):
            return value
    return None


def _request_json_payload() -> dict:
    request = getattr(frappe, "request", None)
    if not request:
        return {}

    get_json = getattr(request, "get_json", None)
    if callable(get_json):
        try:
            payload = get_json(silent=True)
        except TypeError:
            try:
                payload = get_json()
            except Exception:
                payload = None
        except Exception:
            payload = None
        parsed_payload = _parse_request_payload(payload)
        if isinstance(parsed_payload, dict):
            return parsed_payload

    parsed_payload = _parse_request_payload(getattr(request, "data", None))
    if isinstance(parsed_payload, dict):
        return parsed_payload
    return {}


def _request_form_value(key: str, current_value=None):
    if _has_bound_value(current_value):
        return current_value

    form_dict = getattr(frappe, "form_dict", None)
    if form_dict and hasattr(form_dict, "get"):
        value = form_dict.get(key)
        if _has_bound_value(value):
            return value

        args = _parse_request_payload(form_dict.get("args"))
        if isinstance(args, dict):
            value = args.get(key)
            if _has_bound_value(value):
                return value

    request_payload = _request_json_payload()
    value = request_payload.get(key)
    if _has_bound_value(value):
        return value

    args = _parse_request_payload(request_payload.get("args"))
    if isinstance(args, dict):
        value = args.get(key)
        if _has_bound_value(value):
            return value

    return current_value


def _session_user() -> str:
    user = _as_text(getattr(frappe.session, "user", None)).strip()
    if not user:
        return ""
    if user.lower() in INVALID_SESSION_USERS:
        return ""
    return user


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


def _profile_image_allowed_formats_message() -> str:
    return _(
        "Only {accepted_formats} image files are accepted. Convert HEIC or HEIF photos to JPG before uploading."
    ).format(accepted_formats=PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL)


def _profile_image_invalid_content_message() -> str:
    return _("Uploaded profile image must be a valid {accepted_format} image.").format(
        accepted_format=PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL
    )


def _profile_image_extension_mismatch_message() -> str:
    return _("The selected file extension does not match the uploaded image content. Please upload a JPG or PNG image.")


def _profile_image_size_limit_message() -> str:
    return _("Image is too large. Max file size is {max_size_mb} MB.").format(
        max_size_mb=PROFILE_IMAGE_MAX_BYTES // (1024 * 1024)
    )


def _profile_image_pixel_limit_message() -> str:
    return _("Image is too large. Max image size is {max_megapixels} megapixels.").format(
        max_megapixels=PROFILE_IMAGE_MAX_PIXELS // 1_000_000
    )


def _profile_image_output_filename(prefix: str) -> str:
    return f"{prefix}_{frappe.generate_hash(length=12)}.jpg"


def _profile_image_extension(upload_name: str | None) -> str:
    return os.path.splitext(_as_text(upload_name).strip().lower())[1]


def _sniff_profile_image_format(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    return None


def _profile_image_to_rgb(image_obj):
    if image_obj.mode in {"RGBA", "LA"} or (image_obj.mode == "P" and "transparency" in getattr(image_obj, "info", {})):
        rgba_image = image_obj.convert("RGBA")
        background = Image.new("RGB", rgba_image.size, (255, 255, 255))
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background
    return image_obj.convert("RGB")


def _normalize_profile_image_bytes(content: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source_image:
                image_format = (_as_text(getattr(source_image, "format", None)).strip() or "").upper()
                if image_format not in {"JPEG", "PNG"}:
                    frappe.throw(_profile_image_invalid_content_message())

                width, height = source_image.size or (0, 0)
                if width <= 0 or height <= 0:
                    frappe.throw(_profile_image_invalid_content_message())
                if width * height > PROFILE_IMAGE_MAX_PIXELS:
                    frappe.throw(_profile_image_pixel_limit_message())

                source_image.load()
                normalized_image = ImageOps.exif_transpose(source_image)
                normalized_rgb = _profile_image_to_rgb(normalized_image)
                output_buffer = io.BytesIO()
                normalized_rgb.save(output_buffer, format="JPEG", optimize=True, quality=85)
                normalized_bytes = output_buffer.getvalue()
                if not normalized_bytes:
                    frappe.throw(_profile_image_invalid_content_message())
                return normalized_bytes
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        frappe.throw(_profile_image_pixel_limit_message())
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        frappe.throw(_profile_image_invalid_content_message())


def _prepare_profile_image_upload(
    *, upload_name: str | None, content: bytes, filename_prefix: str
) -> tuple[str, bytes]:
    extension = _profile_image_extension(upload_name)
    if extension not in PROFILE_IMAGE_ALLOWED_EXTENSIONS:
        frappe.throw(_profile_image_allowed_formats_message())

    if len(content) > PROFILE_IMAGE_MAX_BYTES:
        frappe.throw(_profile_image_size_limit_message())

    sniffed_format = _sniff_profile_image_format(content)
    if not sniffed_format:
        frappe.throw(_profile_image_invalid_content_message())

    expected_format = PROFILE_IMAGE_ALLOWED_EXTENSIONS.get(extension)
    if sniffed_format != expected_format:
        frappe.throw(_profile_image_extension_mismatch_message())

    normalized_bytes = _normalize_profile_image_bytes(content)
    return _profile_image_output_filename(filename_prefix), normalized_bytes


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

    upload_result = admission_api.upload_applicant_health_vaccination_proof(
        student_applicant=applicant_row.get("name"),
        applicant_health_profile=health_doc_name,
        vaccine_name=_as_text(vaccination_row.get("vaccine_name")).strip(),
        date=_as_text(vaccination_row.get("date")).strip(),
        row_index=index,
        file_name=file_name,
        content=content,
        upload_source="SPA",
    )
    return _as_text(upload_result.get("file_url"))


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
    payload["record_modified"] = _as_text(doc.get("modified")).strip()
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
    guardians_enabled = _guardians_feature_enabled()
    applicant_name = _as_text(applicant.get("name")).strip()
    return {
        "profile": profile,
        "completeness": completeness,
        "application_context": _application_context_payload(applicant),
        "options": _profile_reference_options(),
        "applicant_image": _applicant_image_open_url(
            applicant_name=applicant_name,
            applicant_image=applicant.get("applicant_image"),
        ),
        "record_modified": _as_text(applicant.get("modified")).strip(),
        "guardian_section_enabled": guardians_enabled,
        "guardians": _serialize_applicant_guardians(applicant) if guardians_enabled else [],
    }


def _normalize_record_modified(value) -> str:
    return _as_text(value).strip()


def _assert_record_modified_matches(*, expected_modified, current_modified, section_label: str) -> None:
    if expected_modified is None:
        return
    expected = _normalize_record_modified(expected_modified)
    current = _normalize_record_modified(current_modified)
    if expected == current:
        return
    frappe.throw(
        _("{0} was updated by another user. Reload this page before saving again.").format(section_label),
        frappe.ValidationError,
    )


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
        "guardian_relationships": list(APPLICANT_GUARDIAN_RELATIONSHIP_OPTIONS),
        "guardian_genders": list(APPLICANT_GUARDIAN_GENDER_OPTIONS),
        "guardian_employment_sectors": list(APPLICANT_GUARDIAN_EMPLOYMENT_SECTOR_OPTIONS),
        "salutations": _guardian_salutation_options(),
    }


def _guardian_salutation_options() -> list[dict]:
    try:
        rows = frappe.get_all(
            "Salutation",
            fields=["name", "salutation"],
            order_by="name asc",
        )
    except Exception:
        return []
    output = []
    for row in rows:
        value = _as_text(row.get("name")).strip()
        if not value:
            continue
        label = _as_text(row.get("salutation")).strip() or value
        output.append({"value": value, "label": label})
    return output


def _guardians_feature_enabled() -> bool:
    try:
        setting = frappe.db.get_single_value("Admission Settings", "show_guardians_in_admissions_profile")
    except Exception:
        return False
    return bool(cint(setting or 0))


def _serialize_applicant_guardians(applicant) -> list[dict]:
    rows: list[dict] = []
    for row in applicant.get("guardians") or []:
        payload: dict = {}
        for fieldname in APPLICANT_GUARDIAN_FIELDS:
            if fieldname in APPLICANT_GUARDIAN_CHECK_FIELDS:
                payload[fieldname] = _as_check(row.get(fieldname))
            elif fieldname == "guardian_image":
                payload[fieldname] = _guardian_image_open_url(
                    applicant_name=applicant.name,
                    guardian_row_name=_as_text(row.get("name")).strip(),
                    guardian_image=_as_text(row.get(fieldname)).strip(),
                )
            else:
                payload[fieldname] = _as_text(row.get(fieldname)).strip()
        rows.append(payload)
    return rows


def _guardian_profile_image_slot(guardian_row_name: str) -> str:
    return f"guardian_profile_image__{frappe.scrub((guardian_row_name or '').strip())[:80]}"


def _resolve_applicant_profile_image_drive_file(*, applicant_name: str) -> dict | None:
    return get_current_drive_file_for_slot(
        primary_subject_type="Student Applicant",
        primary_subject_id=applicant_name,
        slot="profile_image",
        attached_doctype="Student Applicant",
        attached_name=applicant_name,
        fields=["name", "file", "canonical_ref"],
        statuses=("active", "processing", "blocked"),
    )


def _resolve_guardian_image_drive_file(*, applicant_name: str, guardian_row_name: str | None) -> dict | None:
    resolved_guardian_row_name = _as_text(guardian_row_name).strip()
    if not resolved_guardian_row_name:
        return None
    return get_current_drive_file_for_slot(
        primary_subject_type="Student Applicant",
        primary_subject_id=applicant_name,
        slot=_guardian_profile_image_slot(resolved_guardian_row_name),
        attached_doctype="Student Applicant Guardian",
        attached_name=resolved_guardian_row_name,
        fields=["name", "file", "canonical_ref"],
        statuses=("active", "processing", "blocked"),
    )


def _resolve_guardian_image_file(
    *,
    applicant_name: str,
    guardian_row_name: str | None = None,
    guardian_image: str | None,
) -> dict | None:
    image_value = _as_text(guardian_image).strip()
    if not image_value:
        return None

    drive_file = _resolve_guardian_image_drive_file(
        applicant_name=applicant_name,
        guardian_row_name=guardian_row_name,
    )
    file_name = _as_text((drive_file or {}).get("file")).strip()
    if file_name:
        row = frappe.db.get_value(
            "File",
            file_name,
            ["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        if row and _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    file_name = ""
    if "download_admissions_file" in image_value:
        parsed = urlparse(image_value)
        file_name = _as_text((parse_qs(parsed.query).get("file") or [""])[0]).strip()
    if file_name:
        row = frappe.db.get_value(
            "File",
            file_name,
            ["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        if row and _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    file_rows = frappe.get_all(
        "File",
        filters={"file_url": image_value},
        fields=["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
        order_by="creation desc",
        limit=5,
    )
    for row in file_rows:
        if _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    return None


def _file_is_scoped_to_applicant(*, file_row: dict, applicant_name: str) -> bool:
    file_name = _as_text(file_row.get("name")).strip()
    if file_name:
        drive_file = get_drive_file_for_file(
            file_name,
            fields=["primary_subject_type", "primary_subject_id"],
            statuses=("active", "processing", "blocked"),
        )
        if drive_file and (
            _as_text(drive_file.get("primary_subject_type")).strip() == "Student Applicant"
            and _as_text(drive_file.get("primary_subject_id")).strip() == applicant_name
        ):
            return True

    return (
        _as_text(file_row.get("attached_to_doctype")).strip() == "Student Applicant"
        and _as_text(file_row.get("attached_to_name")).strip() == applicant_name
    )


def _applicant_image_open_url(*, applicant_name: str, applicant_image: str | None) -> str:
    image_value = _as_text(applicant_image).strip()
    if not image_value:
        return ""

    drive_file = _resolve_applicant_profile_image_drive_file(applicant_name=applicant_name) or {}
    return (
        resolve_admissions_file_open_url(
            file_name=drive_file.get("file"),
            file_url=image_value,
            drive_file_id=drive_file.get("name"),
            canonical_ref=drive_file.get("canonical_ref"),
            context_doctype="Student Applicant",
            context_name=applicant_name,
        )
        or ""
    )


def _guardian_image_open_url(
    *,
    applicant_name: str,
    guardian_row_name: str | None = None,
    guardian_image: str | None,
) -> str:
    image_value = _as_text(guardian_image).strip()
    if not image_value:
        return ""

    drive_file = (
        _resolve_guardian_image_drive_file(
            applicant_name=applicant_name,
            guardian_row_name=guardian_row_name,
        )
        or {}
    )
    file_row = _resolve_guardian_image_file(
        applicant_name=applicant_name,
        guardian_row_name=guardian_row_name,
        guardian_image=image_value,
    )
    if not file_row:
        return (
            resolve_admissions_file_open_url(
                file_name=drive_file.get("file"),
                file_url=image_value,
                drive_file_id=drive_file.get("name"),
                canonical_ref=drive_file.get("canonical_ref"),
                context_doctype="Student Applicant",
                context_name=applicant_name,
            )
            or ""
        )

    return (
        resolve_admissions_file_open_url(
            file_name=file_row.get("name"),
            file_url=file_row.get("file_url"),
            drive_file_id=drive_file.get("name"),
            canonical_ref=drive_file.get("canonical_ref"),
            context_doctype="Student Applicant",
            context_name=applicant_name,
        )
        or ""
    )


def _rehome_guardian_image_to_contact(
    *,
    applicant_name: str,
    guardian_image: str | None,
    contact_name: str | None,
) -> str:
    resolved_contact = _as_text(contact_name).strip()
    if not resolved_contact:
        return _as_text(guardian_image).strip()

    file_row = _resolve_guardian_image_file(applicant_name=applicant_name, guardian_image=guardian_image)
    if not file_row:
        return _as_text(guardian_image).strip()

    attached_doctype = _as_text(file_row.get("attached_to_doctype")).strip()
    attached_name = _as_text(file_row.get("attached_to_name")).strip()
    attached_field = _as_text(file_row.get("attached_to_field")).strip()
    if attached_doctype == "Contact" and attached_name == resolved_contact:
        return _as_text(file_row.get("file_url")).strip()

    row_parent = ""
    if attached_doctype == "Student Applicant Guardian" and attached_name:
        row_parent = _as_text(frappe.db.get_value("Student Applicant Guardian", attached_name, "parent")).strip()

    can_rehome_from_applicant = attached_doctype == "Student Applicant" and attached_name == applicant_name
    can_rehome_from_guardian_row = attached_doctype == "Student Applicant Guardian" and row_parent == applicant_name

    if not can_rehome_from_applicant and not can_rehome_from_guardian_row:
        return _as_text(file_row.get("file_url")).strip() or _as_text(guardian_image).strip()

    if attached_field == "applicant_image":
        return _as_text(file_row.get("file_url")).strip() or _as_text(guardian_image).strip()

    frappe.db.set_value(
        "File",
        file_row.get("name"),
        {
            "attached_to_doctype": "Contact",
            "attached_to_name": resolved_contact,
            "attached_to_field": None,
        },
        update_modified=False,
    )

    drive_file = get_drive_file_for_file(
        file_row.get("name"),
        fields=["name"],
        statuses=("active", "processing", "blocked"),
    )
    if drive_file and drive_file.get("name"):
        frappe.db.set_value(
            "Drive File",
            drive_file.get("name"),
            {
                "attached_doctype": "Contact",
                "attached_name": resolved_contact,
            },
            update_modified=False,
        )

    return _as_text(file_row.get("file_url")).strip() or _as_text(guardian_image).strip()


def _parse_guardians_payload(guardians) -> list[dict] | None:
    if guardians is None:
        return None

    payload = guardians
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, list):
        frappe.throw(_("Guardians payload must be a list."))

    normalized: list[dict] = []
    for row in payload:
        if not isinstance(row, dict):
            frappe.throw(_("Each guardian entry must be an object."))
        normalized.append(row)
    return normalized


def _guardian_row_is_empty(row: dict) -> bool:
    identity_fields = (
        "guardian",
        "guardian_first_name",
        "guardian_last_name",
        "guardian_email",
        "guardian_mobile_phone",
        "salutation",
        "guardian_work_email",
        "guardian_work_phone",
        "employment_sector",
        "work_place",
        "guardian_designation",
        "guardian_image",
    )
    return not any(_as_text(row.get(fieldname)).strip() for fieldname in identity_fields)


def _guardian_signer_flag_from_primary_guardian(row: dict) -> int:
    return 1 if _as_check(row.get("is_primary_guardian")) else 0


def _validate_guardian_profile_row(row: dict) -> dict:
    missing_labels = [
        _(label)
        for fieldname, label in APPLICANT_GUARDIAN_REQUIRED_FIELD_LABELS
        if not _as_text(row.get(fieldname)).strip()
    ]
    if missing_labels:
        frappe.throw(
            _("Each guardian must include: {missing_fields}.").format(missing_fields=", ".join(missing_labels))
        )

    guardian_email = normalize_email_value(row.get("guardian_email"))
    try:
        validate_email_address(guardian_email, True)
    except Exception:
        frappe.throw(_("Guardian personal email must be a valid email address."))
    row["guardian_email"] = guardian_email

    guardian_work_email = normalize_email_value(row.get("guardian_work_email"))
    if guardian_work_email:
        try:
            validate_email_address(guardian_work_email, True)
        except Exception:
            frappe.throw(_("Guardian work email must be a valid email address."))
    row["guardian_work_email"] = guardian_work_email

    guardian_mobile_phone = _as_text(row.get("guardian_mobile_phone")).strip()
    try:
        validate_phone_number(guardian_mobile_phone, throw=True)
    except Exception:
        frappe.throw(_("Guardian mobile phone must be a valid phone number."))
    row["guardian_mobile_phone"] = guardian_mobile_phone

    guardian_work_phone = _as_text(row.get("guardian_work_phone")).strip()
    if guardian_work_phone:
        try:
            validate_phone_number(guardian_work_phone, throw=True)
        except Exception:
            frappe.throw(_("Guardian work phone must be a valid phone number."))
    row["guardian_work_phone"] = guardian_work_phone
    row["can_consent"] = _guardian_signer_flag_from_primary_guardian(row)

    return row


def _contact_is_linked_to_applicant(*, contact_name: str, applicant_name: str) -> bool:
    if not contact_name or not applicant_name:
        return False
    return bool(
        frappe.db.exists(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "parent": contact_name,
                "link_doctype": "Student Applicant",
                "link_name": applicant_name,
            },
        )
    )


def _set_contact_primary_mobile(contact_doc, mobile: str) -> bool:
    mobile = _as_text(mobile).strip()
    if not mobile:
        return False

    changed = False
    phone_rows = list(contact_doc.get("phone_nos") or [])
    has_phone = any(_as_text(row.get("phone")).strip() == mobile for row in phone_rows)
    if not has_phone:
        contact_doc.append("phone_nos", {"phone": mobile, "is_primary_mobile_no": 1})
        changed = True
        phone_rows = list(contact_doc.get("phone_nos") or [])

    primary_set = False
    for row in phone_rows:
        row_phone = _as_text(row.get("phone")).strip()
        should_be_primary = row_phone == mobile and not primary_set
        if should_be_primary:
            primary_set = True
        desired = 1 if should_be_primary else 0
        if cint(row.get("is_primary_mobile_no") or 0) != desired:
            row.is_primary_mobile_no = desired
            changed = True

    if _as_text(contact_doc.get("mobile_no")).strip() != mobile:
        contact_doc.mobile_no = mobile
        changed = True

    return changed


def _guardian_contact_name_from_guardian_email(email: str) -> str:
    normalized = normalize_email_value(email)
    if not normalized:
        return ""
    return _as_text(
        frappe.db.get_value(
            "Contact Email",
            {"email_id": normalized},
            "parent",
        )
    ).strip()


def _hydrate_guardian_row_from_guardian_doc(*, row_payload: dict, guardian_doc) -> dict:
    row = dict(row_payload)
    row["guardian"] = guardian_doc.name
    row["salutation"] = row.get("salutation") or _as_text(guardian_doc.get("salutation")).strip()
    row["guardian_first_name"] = (
        row.get("guardian_first_name") or _as_text(guardian_doc.get("guardian_first_name")).strip()
    )
    row["guardian_last_name"] = (
        row.get("guardian_last_name") or _as_text(guardian_doc.get("guardian_last_name")).strip()
    )
    row["guardian_gender"] = row.get("guardian_gender") or _as_text(guardian_doc.get("guardian_gender")).strip()
    row["guardian_mobile_phone"] = (
        row.get("guardian_mobile_phone") or _as_text(guardian_doc.get("guardian_mobile_phone")).strip()
    )
    row["guardian_email"] = row.get("guardian_email") or _as_text(guardian_doc.get("guardian_email")).strip()
    row["guardian_work_email"] = (
        row.get("guardian_work_email") or _as_text(guardian_doc.get("guardian_work_email")).strip()
    )
    row["guardian_work_phone"] = (
        row.get("guardian_work_phone") or _as_text(guardian_doc.get("guardian_work_phone")).strip()
    )
    row["employment_sector"] = row.get("employment_sector") or _as_text(guardian_doc.get("employment_sector")).strip()
    row["work_place"] = row.get("work_place") or _as_text(guardian_doc.get("work_place")).strip()
    row["guardian_designation"] = (
        row.get("guardian_designation") or _as_text(guardian_doc.get("guardian_designation")).strip()
    )
    row["guardian_image"] = row.get("guardian_image") or _as_text(guardian_doc.get("guardian_image")).strip()
    row["user"] = row.get("user") or _as_text(guardian_doc.get("user")).strip()

    if row.get("is_primary_guardian") in (None, ""):
        row["is_primary_guardian"] = _as_check(guardian_doc.get("is_primary_guardian"))
    if row.get("is_financial_guardian") in (None, ""):
        row["is_financial_guardian"] = _as_check(guardian_doc.get("is_financial_guardian"))

    row["guardian_full_name"] = _as_text(guardian_doc.get("guardian_full_name")).strip() or " ".join(
        part for part in [row.get("guardian_first_name"), row.get("guardian_last_name")] if _as_text(part).strip()
    )

    contact_name = _as_text(row.get("contact")).strip()
    if not contact_name:
        contact_name = _guardian_contact_name_from_guardian_email(_as_text(row.get("guardian_email")).strip())
    if contact_name:
        row["contact"] = contact_name

    return row


def _create_or_update_guardian_contact(
    *,
    applicant,
    row_payload: dict,
    existing_contact_name: str | None = None,
) -> str:
    use_applicant_contact = _as_bool(row_payload.get("use_applicant_contact"))
    applicant_contact = _as_text(applicant.get("applicant_contact")).strip()
    if use_applicant_contact:
        if not applicant_contact:
            frappe.throw(_("Applicant Contact is required before using it for guardian contact tracking."))
        ensure_contact_dynamic_link(
            contact_name=applicant_contact,
            link_doctype="Student Applicant",
            link_name=applicant.name,
        )
        return applicant_contact

    first_name = _as_text(row_payload.get("guardian_first_name")).strip()
    last_name = _as_text(row_payload.get("guardian_last_name")).strip()
    email = normalize_email_value(row_payload.get("guardian_email"))
    mobile = _as_text(row_payload.get("guardian_mobile_phone")).strip()

    if not first_name:
        frappe.throw(_("Guardian first name is required."))
    if not last_name:
        frappe.throw(_("Guardian last name is required."))
    if not email:
        frappe.throw(_("Guardian personal email is required."))
    if not mobile:
        frappe.throw(_("Guardian mobile phone is required."))

    contact_name = _as_text(existing_contact_name).strip()
    if contact_name:
        if not frappe.db.exists("Contact", contact_name):
            contact_name = ""
        elif not _contact_is_linked_to_applicant(contact_name=contact_name, applicant_name=applicant.name):
            frappe.throw(_("Guardian Contact must already be linked to this applicant."))

    contact_from_email = _guardian_contact_name_from_guardian_email(email)
    if contact_from_email and contact_from_email != contact_name:
        if not _contact_is_linked_to_applicant(contact_name=contact_from_email, applicant_name=applicant.name):
            frappe.throw(
                _("Guardian email is linked to another contact. Ask admissions staff to link that contact first.")
            )
        contact_name = contact_from_email

    if contact_name:
        contact_doc = frappe.get_doc("Contact", contact_name)
    else:
        contact_doc = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": first_name,
                "last_name": last_name,
                "email_ids": [{"email_id": email, "is_primary": 1}],
                "phone_nos": [{"phone": mobile, "is_primary_mobile_no": 1}],
                "mobile_no": mobile,
            }
        )
        contact_doc.insert(ignore_permissions=True)
        contact_name = contact_doc.name

    changed = False
    if _as_text(contact_doc.get("first_name")).strip() != first_name:
        contact_doc.first_name = first_name
        changed = True
    if _as_text(contact_doc.get("last_name")).strip() != last_name:
        contact_doc.last_name = last_name
        changed = True

    upsert_contact_email(contact_name, email, set_primary_if_missing=True)
    if _set_contact_primary_mobile(contact_doc, mobile):
        changed = True

    if changed:
        contact_doc.save(ignore_permissions=True)

    ensure_contact_dynamic_link(
        contact_name=contact_name,
        link_doctype="Student Applicant",
        link_name=applicant.name,
    )
    return contact_name


def _normalize_guardian_row(row_payload: dict) -> dict:
    normalized: dict = {}
    for fieldname in APPLICANT_GUARDIAN_TEXT_FIELDS:
        normalized[fieldname] = _as_text(row_payload.get(fieldname)).strip()
    for fieldname in APPLICANT_GUARDIAN_CHECK_FIELDS:
        normalized[fieldname] = _as_check(row_payload.get(fieldname))

    normalized["name"] = _as_text(row_payload.get("name")).strip()
    normalized["relationship"] = normalized.get("relationship") or "Other"
    normalized["can_consent"] = _guardian_signer_flag_from_primary_guardian(normalized)
    return normalized


def _apply_guardians_to_applicant(*, applicant, guardians_payload: list[dict]):
    existing_by_name = {row.name: row for row in (applicant.get("guardians") or []) if row.name}
    normalized_rows: list[dict] = []

    for row_payload in guardians_payload:
        row = _normalize_guardian_row(row_payload)
        existing_row = existing_by_name.get(_as_text(row.get("name")).strip())

        if _guardian_row_is_empty(row):
            continue

        guardian_name = _as_text(row.get("guardian")).strip()
        if guardian_name:
            if not frappe.db.exists("Guardian", guardian_name):
                frappe.throw(_("Invalid Guardian: {guardian}.").format(guardian=guardian_name))
            guardian_doc = frappe.get_doc("Guardian", guardian_name)
            row = _hydrate_guardian_row_from_guardian_doc(row_payload=row, guardian_doc=guardian_doc)
        row = _validate_guardian_profile_row(row)

        existing_contact_name = _as_text(row.get("contact")).strip()
        if not existing_contact_name and existing_row:
            existing_contact_name = _as_text(existing_row.get("contact")).strip()
        row["contact"] = _create_or_update_guardian_contact(
            applicant=applicant,
            row_payload=row,
            existing_contact_name=existing_contact_name,
        )
        row["guardian_image"] = _rehome_guardian_image_to_contact(
            applicant_name=applicant.name,
            guardian_image=row.get("guardian_image"),
            contact_name=row.get("contact"),
        )

        if not _as_text(row.get("guardian_full_name")).strip():
            row["guardian_full_name"] = " ".join(
                part
                for part in [
                    _as_text(row.get("guardian_first_name")).strip(),
                    _as_text(row.get("guardian_last_name")).strip(),
                ]
                if part
            )

        normalized_rows.append(row)

    applicant.set("guardians", [])
    for row in normalized_rows:
        applicant.append(
            "guardians",
            {
                "guardian": row.get("guardian") or None,
                "contact": row.get("contact") or None,
                "use_applicant_contact": _as_check(row.get("use_applicant_contact")),
                "relationship": row.get("relationship") or "Other",
                "is_primary": _as_check(row.get("is_primary")),
                "can_consent": _as_check(row.get("can_consent")),
                "salutation": row.get("salutation") or None,
                "guardian_full_name": row.get("guardian_full_name") or None,
                "guardian_first_name": row.get("guardian_first_name") or None,
                "guardian_last_name": row.get("guardian_last_name") or None,
                "guardian_gender": row.get("guardian_gender") or None,
                "guardian_mobile_phone": row.get("guardian_mobile_phone") or None,
                "guardian_email": normalize_email_value(row.get("guardian_email")) or None,
                "guardian_work_email": normalize_email_value(row.get("guardian_work_email")) or None,
                "guardian_work_phone": row.get("guardian_work_phone") or None,
                "guardian_image": row.get("guardian_image") or None,
                "user": row.get("user") or None,
                "is_primary_guardian": _as_check(row.get("is_primary_guardian")),
                "is_financial_guardian": _as_check(row.get("is_financial_guardian")),
                "employment_sector": row.get("employment_sector") or None,
                "work_place": row.get("work_place") or None,
                "guardian_designation": row.get("guardian_designation") or None,
            },
        )


def _require_admissions_portal_user() -> str:
    user = _session_user()
    if not user:
        frappe.throw(_("You must be logged in."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if not roles & ADMISSIONS_PORTAL_ROLES:
        frappe.throw(_("You do not have permission to access the admissions portal."), frappe.PermissionError)

    return user


def _require_admissions_applicant() -> str:
    return _require_admissions_portal_user()


def _get_applicant_rows_for_user(
    *,
    user: str,
    fields: list[str],
    limit: int = 25,
    include_promoted: bool = False,
) -> list[dict]:
    selected_fields = [field for field in fields if field]
    if "name" not in selected_fields:
        selected_fields = ["name", *selected_fields]

    applicant_names = get_admissions_portal_applicant_names_for_user(user=user, include_promoted=include_promoted)
    if not applicant_names:
        return []

    return frappe.get_all(
        "Student Applicant",
        filters={"name": ["in", applicant_names]},
        fields=selected_fields,
        limit=limit,
        order_by="creation asc",
    )


def _family_workspace_available_for_user(user: str) -> bool:
    roles = set(frappe.get_roles(user))
    return ADMISSIONS_FAMILY_ROLE in roles and is_family_workspace_enabled()


def _get_applicant_for_user(
    user: str,
    fields: list[str] | None = None,
    *,
    student_applicant: str | None = None,
) -> dict:
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
    rows = _get_applicant_rows_for_user(user=user, fields=fields, limit=50, include_promoted=False)
    if not rows:
        frappe.throw(
            _(
                "Admissions access is not linked to any active Applicant. Contact the admissions office to relink your account."
            ),
            frappe.PermissionError,
        )

    if student_applicant:
        for row in rows:
            if (row.get("name") or "").strip() == (student_applicant or "").strip():
                return row
        frappe.throw(_("You do not have permission to access this Applicant."), frappe.PermissionError)

    if len(rows) > 1 and not _family_workspace_available_for_user(user):
        frappe.log_error(
            title="Admissions Portal applicant identity conflict",
            message=frappe.as_json(
                {
                    "user": user,
                    "matched_applicants": sorted(
                        [_as_text(row.get("name")).strip() for row in rows if _as_text(row.get("name")).strip()]
                    ),
                }
            ),
        )
        frappe.throw(
            _(
                "Admissions access is linked to multiple Applicants. Contact the admissions office to relink your account."
            ),
            frappe.PermissionError,
        )
    return rows[0]


def _ensure_applicant_match(student_applicant: str | None, user: str) -> dict:
    return _get_applicant_for_user(user, student_applicant=student_applicant)


def _applicant_summary_payload(row: dict) -> dict:
    portal_status = _portal_status_for(_as_text(row.get("application_status")).strip())
    is_read_only, reason = _read_only_for(_as_text(row.get("application_status")).strip())
    return {
        "name": row.get("name"),
        "display_name": _build_applicant_display_name(row),
        "portal_status": portal_status,
        "application_status": row.get("application_status"),
        "school": row.get("school"),
        "organization": row.get("organization"),
        "academic_year": row.get("academic_year"),
        "term": row.get("term"),
        "program": row.get("program"),
        "program_offering": row.get("program_offering"),
        "is_read_only": bool(is_read_only),
        "read_only_reason": reason,
    }


def _resolve_family_guardian_context(*, student_applicant: str, user: str) -> str:
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

    frappe.throw(
        _("Your account is not linked to a consenting family collaborator record for this Applicant."),
        frappe.PermissionError,
    )


def _empty_applicant_enrollment_choice_state(message: str | None = None) -> dict:
    return {
        "plan": None,
        "summary": {
            "has_plan": False,
            "has_courses": False,
            "has_selectable_courses": False,
            "can_edit_choices": False,
            "ready_for_offer_response": True,
            "required_course_count": 0,
            "optional_course_count": 0,
            "selected_optional_count": 0,
            "message": message or "",
        },
        "validation": {
            "status": None,
            "ready_for_offer_response": True,
            "reasons": [],
            "violations": [],
            "missing_required_courses": [],
            "ambiguous_courses": [],
            "group_summary": {},
        },
        "required_basket_groups": [],
        "courses": [],
    }


def _serialize_enrollment_offer(plan) -> dict | None:
    if not plan:
        return None
    status = _as_text(plan.get("status")).strip()
    choice_state = get_applicant_enrollment_choice_state(plan)
    choice_summary = choice_state.get("summary") or {}
    choice_validation = choice_state.get("validation") or {}
    return {
        "name": _as_text(plan.get("name")).strip(),
        "status": status,
        "academic_year": _as_text(plan.get("academic_year")).strip(),
        "term": _as_text(plan.get("term")).strip(),
        "program": _as_text(plan.get("program")).strip(),
        "program_offering": _as_text(plan.get("program_offering")).strip(),
        "offer_expires_on": _as_text(plan.get("offer_expires_on")).strip(),
        "offer_sent_on": _as_text(plan.get("offer_sent_on")).strip(),
        "offer_accepted_on": _as_text(plan.get("offer_accepted_on")).strip(),
        "offer_declined_on": _as_text(plan.get("offer_declined_on")).strip(),
        "offer_message": _as_text(plan.get("offer_message")).strip(),
        "can_accept": status == "Offer Sent",
        "can_decline": status == "Offer Sent",
        "course_choices_available": bool(choice_summary.get("has_courses")),
        "course_choices_can_edit": bool(choice_summary.get("can_edit_choices")),
        "course_choices_ready": bool(choice_validation.get("ready_for_offer_response")),
        "course_choice_blocking_reasons": list(choice_validation.get("reasons") or []),
        "course_choice_optional_count": cint(choice_summary.get("optional_course_count") or 0),
        "course_choice_selected_optional_count": cint(choice_summary.get("selected_optional_count") or 0),
    }


def _portal_status_for(application_status: str, enrollment_offer: dict | None = None) -> str:
    offer_status = _as_text((enrollment_offer or {}).get("status")).strip()
    if application_status == "Approved":
        if offer_status == "Offer Sent":
            return "Offer Sent"
        if offer_status == "Offer Accepted":
            return "Accepted"
        if offer_status == "Offer Declined":
            return "Declined"
        if offer_status == "Offer Expired":
            return "Offer Expired"
        return "In Review"
    if application_status not in PORTAL_STATUS_MAP:
        frappe.throw(
            _("Invalid Application Status: {application_status}.").format(application_status=application_status)
        )
    return PORTAL_STATUS_MAP[application_status]


def _read_only_for(application_status: str, enrollment_offer: dict | None = None) -> tuple[bool, str | None]:
    if application_status in PORTAL_EDITABLE_STATUSES:
        return False, None
    offer_status = _as_text((enrollment_offer or {}).get("status")).strip()
    if application_status == "Approved":
        if offer_status == "Offer Sent":
            return True, _("Review your enrollment offer below.")
        if offer_status == "Offer Accepted":
            return True, _("Offer accepted.")
        if offer_status == "Offer Declined":
            return True, _("Offer declined.")
        if offer_status == "Offer Expired":
            return True, _("Offer expired.")
        return True, _("Admissions decision is being finalized.")
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
    if not bool(health.get("required_for_approval", True)):
        return "optional"
    status = (health.get("status") or "missing").strip()
    if status == "missing":
        return "pending"
    return "in_progress"


def _completion_state_for_interviews(interviews: dict) -> str:
    if interviews.get("ok"):
        return "complete"
    return "optional"


def _completion_state_for_recommendations(summary: dict) -> str:
    state = (summary or {}).get("state")
    if state in {"pending", "in_progress", "complete", "optional"}:
        return state

    required_total = max(0, cint((summary or {}).get("required_total") or 0))
    received_total = max(0, cint((summary or {}).get("received_total") or 0))
    if required_total <= 0:
        return "optional"
    if received_total >= required_total:
        return "complete"
    if received_total > 0:
        return "in_progress"
    return "pending"


def _derive_next_actions(application_status: str, readiness: dict, enrollment_offer: dict | None = None) -> list[dict]:
    actions: list[dict] = []
    offer_status = _as_text((enrollment_offer or {}).get("status")).strip()

    if offer_status == "Offer Sent":
        if not bool((enrollment_offer or {}).get("course_choices_ready", True)):
            actions.append(
                {
                    "label": _("Choose your courses"),
                    "route_name": "admissions-course-choices",
                    "intent": "primary",
                    "is_blocking": True,
                }
            )
        actions.append(
            {
                "label": _("Review and respond to your offer"),
                "route_name": "admissions-status",
                "intent": "secondary" if actions else "primary",
                "is_blocking": True,
            }
        )
        return actions

    if application_status not in PORTAL_EDITABLE_STATUSES:
        return actions

    policies = readiness.get("policies") or {}
    documents = readiness.get("documents") or {}
    health = readiness.get("health") or {}
    profile = readiness.get("profile") or {}
    recommendations = readiness.get("recommendations") or {}

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

    if bool(health.get("required_for_approval", True)) and not health.get("ok"):
        actions.append(
            {
                "label": _("Complete health information"),
                "route_name": "admissions-health",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    required_recommendations = max(0, cint(recommendations.get("required_total") or 0))
    if required_recommendations > 0 and not recommendations.get("ok"):
        actions.append(
            {
                "label": _("Check recommendation status"),
                "route_name": "admissions-status",
                "intent": "primary",
                "is_blocking": True,
            }
        )

    return actions


@frappe.whitelist()
def get_admissions_session(student_applicant: str | None = None):
    user = _require_admissions_portal_user()
    list_fields = [
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
    ]
    available_rows = _get_applicant_rows_for_user(user=user, fields=list_fields, limit=50, include_promoted=False)
    row = _get_applicant_for_user(user, fields=list_fields, student_applicant=student_applicant)
    latest_plan = get_latest_applicant_enrollment_plan(row.get("name"))
    enrollment_offer = _serialize_enrollment_offer(latest_plan)

    portal_status = _portal_status_for(row.get("application_status"), enrollment_offer)
    is_read_only, reason = _read_only_for(row.get("application_status"), enrollment_offer)

    user_row = frappe.db.get_value("User", user, ["name", "full_name"], as_dict=True) or {}
    roles = sorted(set(frappe.get_roles(user)) & ADMISSIONS_PORTAL_ROLES)

    return {
        "user": {
            "name": user_row.get("name") or user,
            "full_name": user_row.get("full_name") or user,
            "roles": roles,
        },
        "access_mode": get_admissions_access_mode(),
        "family_workspace_enabled": bool(get_admissions_access_mode() == ADMISSIONS_ACCESS_MODE_FAMILY),
        "selected_applicant": row.get("name"),
        "available_applicants": [_applicant_summary_payload(candidate) for candidate in available_rows],
        "applicant": {
            "name": row.get("name"),
            "display_name": _build_applicant_display_name(row),
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
        "enrollment_offer": enrollment_offer,
    }


@frappe.whitelist()
def get_applicant_snapshot(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    latest_plan = get_latest_applicant_enrollment_plan(applicant.name)
    enrollment_offer = _serialize_enrollment_offer(latest_plan)
    readiness = applicant.get_readiness_snapshot()
    portal_health = _portal_health_state(applicant.name)
    health_required_for_approval = bool((readiness.get("health") or {}).get("required_for_approval", True))
    portal_health["required_for_approval"] = health_required_for_approval
    recommendation_status = get_recommendation_status_for_applicant(
        student_applicant=applicant.name,
        include_confidential=False,
    )
    readiness_for_portal = dict(readiness)
    readiness_for_portal["health"] = portal_health
    readiness_for_portal["recommendations"] = recommendation_status

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
        "recommendations": _completion_state_for_recommendations(recommendation_status),
    }

    portal_status = _portal_status_for(applicant.application_status, enrollment_offer)
    next_actions = _derive_next_actions(applicant.application_status, readiness_for_portal, enrollment_offer)

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
        "enrollment_offer": enrollment_offer,
        "recommendations_summary": recommendation_status,
    }


@frappe.whitelist()
def get_applicant_enrollment_choices(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(row.get("name"))
    if not plan:
        return _empty_applicant_enrollment_choice_state(
            _("Course choices will appear once admissions sends your enrollment offer.")
        )

    payload = get_applicant_enrollment_choice_state(plan)
    summary = payload.get("summary") or {}
    summary["message"] = (
        _("No program-offering courses are configured for this offer.") if not summary.get("has_courses") else ""
    )
    payload["summary"] = summary
    return payload


@frappe.whitelist()
def update_applicant_enrollment_choices(*, student_applicant: str | None = None, courses=None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(row.get("name"))
    if not plan:
        frappe.throw(_("No enrollment plan is available."))

    parsed_courses = frappe.parse_json(courses) if courses is not None else []
    if parsed_courses is None:
        parsed_courses = []
    if not isinstance(parsed_courses, list):
        frappe.throw(_("Courses payload must be a list."))

    payload = plan.update_portal_choices(user=user, courses=parsed_courses)
    return {"ok": True, **payload}


@frappe.whitelist()
def accept_enrollment_offer(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(
        row.get("name"),
        statuses={"Offer Sent", "Offer Accepted"},
    )
    if not plan:
        frappe.throw(_("No active enrollment offer is available."))

    result = plan.accept_offer(user=user)
    plan.reload()
    return {"ok": True, "result": result, "enrollment_offer": _serialize_enrollment_offer(plan)}


@frappe.whitelist()
def decline_enrollment_offer(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    plan = get_latest_applicant_enrollment_plan(
        row.get("name"),
        statuses={"Offer Sent", "Offer Declined"},
    )
    if not plan:
        frappe.throw(_("No active enrollment offer is available."))

    result = plan.decline_offer(user=user)
    plan.reload()
    return {"ok": True, "result": result, "enrollment_offer": _serialize_enrollment_offer(plan)}


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
    expected_modified: str | None = None,
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
    guardians=None,
):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    applicant = frappe.get_doc("Student Applicant", row.get("name"))
    _assert_record_modified_matches(
        expected_modified=expected_modified,
        current_modified=applicant.get("modified"),
        section_label=_("Profile information"),
    )
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
    guardians_payload = _parse_guardians_payload(guardians)
    if guardians_payload is not None and _guardians_feature_enabled():
        _apply_guardians_to_applicant(applicant=applicant, guardians_payload=guardians_payload)
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
    student_applicant = _request_form_value("student_applicant", student_applicant)
    file_name = _request_form_value("file_name", file_name)
    content = _request_form_value("content", content)
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
    normalized_file_name, normalized_content = _prepare_profile_image_upload(
        upload_name=upload_name,
        content=upload_content,
        filename_prefix="applicant_profile_image",
    )

    applicant = frappe.get_doc("Student Applicant", applicant_name)
    if not applicant.get("organization") or not applicant.get("school"):
        frappe.throw(_("Organization and School are required for governed admissions uploads."))

    upload_result = admission_api.upload_applicant_profile_image(
        student_applicant=applicant.name,
        file_name=normalized_file_name,
        content=normalized_content,
        upload_source="SPA",
    )

    return {
        "ok": True,
        "file": upload_result.get("file"),
        "image_url": resolve_admissions_file_open_url(
            file_name=upload_result.get("file"),
            file_url=upload_result.get("file_url"),
            drive_file_id=upload_result.get("drive_file_id"),
            canonical_ref=upload_result.get("canonical_ref"),
            context_doctype="Student Applicant",
            context_name=applicant.name,
        ),
        "file_name": normalized_file_name,
        "file_size": len(normalized_content),
        "drive_file_id": upload_result.get("drive_file_id"),
        "canonical_ref": upload_result.get("canonical_ref"),
    }


@frappe.whitelist()
def upload_applicant_guardian_image(
    *,
    student_applicant: str | None = None,
    guardian_row_name: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    student_applicant = _request_form_value("student_applicant", student_applicant)
    file_name = _request_form_value("file_name", file_name)
    content = _request_form_value("content", content)
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    is_read_only, reason = _read_only_for(_as_text(row.get("application_status")).strip())
    if is_read_only:
        frappe.throw(reason or _("This application is read-only."), frappe.PermissionError)

    applicant_name = _as_text(row.get("name")).strip()
    if not applicant_name:
        frappe.throw(_("Applicant context is missing."))
    guardian_row_name = _as_text(_request_form_value("guardian_row_name", guardian_row_name)).strip()
    if not guardian_row_name:
        frappe.throw(_("guardian_row_name is required."))

    upload_name = _as_text(file_name).strip()
    if not upload_name:
        frappe.throw(_("file_name is required."))

    upload_content = _decode_profile_image_content(_as_text(content))
    normalized_file_name, normalized_content = _prepare_profile_image_upload(
        upload_name=upload_name,
        content=upload_content,
        filename_prefix="guardian_profile_image",
    )

    applicant = frappe.get_doc("Student Applicant", applicant_name)
    if not applicant.get("organization") or not applicant.get("school"):
        frappe.throw(_("Organization and School are required for governed admissions uploads."))

    upload_result = admission_api.upload_applicant_guardian_image(
        student_applicant=applicant.name,
        guardian_row_name=guardian_row_name,
        file_name=normalized_file_name,
        content=normalized_content,
        upload_source="SPA",
    )

    return {
        "ok": True,
        "file": upload_result.get("file"),
        "image_url": resolve_admissions_file_open_url(
            file_name=upload_result.get("file"),
            file_url=upload_result.get("file_url"),
            drive_file_id=upload_result.get("drive_file_id"),
            canonical_ref=upload_result.get("canonical_ref"),
            context_doctype="Student Applicant",
            context_name=applicant.name,
        ),
        "file_name": normalized_file_name,
        "file_size": len(normalized_content),
        "drive_file_id": upload_result.get("drive_file_id"),
        "canonical_ref": upload_result.get("canonical_ref"),
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
        payload["record_modified"] = ""
        return payload

    doc = frappe.get_doc("Applicant Health Profile", health_name)
    payload = _serialize_health_doc(doc)
    payload["applicant_display_name"] = applicant_display_name
    return payload


@frappe.whitelist()
def update_applicant_health(
    *,
    student_applicant: str | None = None,
    expected_modified: str | None = None,
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
    _assert_record_modified_matches(
        expected_modified=expected_modified,
        current_modified=doc.get("modified"),
        section_label=_("Health information"),
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
        "record_modified": _as_text(doc.get("modified")).strip(),
    }


def _load_drive_version_mime_map(version_ids: list[str]) -> dict[str, str]:
    resolved_version_ids = [version_id for version_id in dict.fromkeys(version_ids) if _as_text(version_id).strip()]
    if not resolved_version_ids:
        return {}

    rows = frappe.get_all(
        "Drive File Version",
        filters={"name": ["in", resolved_version_ids]},
        fields=["name", "mime_type"],
        limit=0,
    )
    return {
        _as_text(row.get("name")).strip(): _as_text(row.get("mime_type")).strip()
        for row in rows
        if _as_text(row.get("name")).strip()
    }


def _serialize_applicant_document_attachment(
    *,
    latest_drive_file: dict,
    student_applicant_name: str,
    thumbnail_ready_map: dict[str, bool],
    version_mime_map: dict[str, str],
) -> dict:
    drive_file_id = _as_text(latest_drive_file.get("name")).strip()
    compatibility_file_id = _as_text(latest_drive_file.get("file")).strip()
    canonical_ref = _as_text(latest_drive_file.get("canonical_ref")).strip() or None
    file_name = (
        _as_text(latest_drive_file.get("display_name")).strip()
        or _as_text(latest_drive_file.get("file_name")).strip()
        or compatibility_file_id
    )
    preview_status = _as_text(latest_drive_file.get("preview_status")).strip() or None
    open_url = resolve_admissions_file_open_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant_name,
    )
    preview_url = resolve_admissions_file_preview_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant_name,
        preview_ready=preview_status == "ready",
    )
    thumbnail_url = resolve_admissions_file_thumbnail_url(
        file_name=compatibility_file_id or None,
        file_url=None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype="Student Applicant",
        context_name=student_applicant_name,
        thumbnail_ready=thumbnail_ready_map.get(drive_file_id, False),
    )
    mime_type = version_mime_map.get(_as_text(latest_drive_file.get("current_version")).strip())
    attachment_preview = build_attachment_preview_item(
        item_id=drive_file_id or compatibility_file_id or file_name,
        owner_doctype="Student Applicant",
        owner_name=student_applicant_name,
        file_id=drive_file_id or compatibility_file_id,
        display_name=file_name,
        mime_type=mime_type,
        extension=extract_file_extension(file_name=file_name, file_url=None),
        preview_status=preview_status,
        thumbnail_url=thumbnail_url,
        preview_url=preview_url,
        open_url=open_url,
        download_url=open_url,
    )
    return {
        "drive_file_id": drive_file_id or None,
        "canonical_ref": canonical_ref,
        "file_name": file_name or None,
        "uploaded_at": latest_drive_file.get("creation"),
        "open_url": open_url,
        "preview_url": preview_url,
        "thumbnail_url": thumbnail_url,
        "preview_status": preview_status,
        "attachment_preview": attachment_preview,
    }


@frappe.whitelist()
def list_applicant_documents(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    student_applicant_name = (row.get("name") or "").strip()
    hidden_document_types = _recommendation_target_document_types_for_applicant(student_applicant_name)

    documents = frappe.get_all(
        "Applicant Document",
        filters={"student_applicant": row.get("name")},
        fields=[
            "name",
            "document_type",
            "document_label",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "requirement_override",
            "override_reason",
            "override_by",
            "override_on",
            "modified",
        ],
        order_by="modified desc",
    )
    if hidden_document_types:
        documents = [doc for doc in documents if (doc.get("document_type") or "").strip() not in hidden_document_types]

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

    latest_drive_file_by_item: dict[str, dict] = {}
    if item_names:
        drive_rows = get_current_drive_files_for_attachments(
            attached_doctype="Applicant Document Item",
            attached_names=item_names,
            fields=[
                "name",
                "attached_name",
                "file",
                "canonical_ref",
                "display_name",
                "preview_status",
                "current_version",
                "creation",
            ],
            statuses=("active", "processing", "blocked"),
        )
        for drive_row in drive_rows:
            parent = drive_row.get("attached_name")
            if not parent or parent in latest_drive_file_by_item:
                continue
            latest_drive_file_by_item[parent] = drive_row

    drive_thumbnail_ready_map = get_drive_file_thumbnail_ready_map(
        [
            _as_text(row_drive.get("name")).strip()
            for row_drive in latest_drive_file_by_item.values()
            if _as_text(row_drive.get("name")).strip()
        ]
    )
    drive_version_mime_map = _load_drive_version_mime_map(
        [
            _as_text(row_drive.get("current_version")).strip()
            for row_drive in latest_drive_file_by_item.values()
            if _as_text(row_drive.get("current_version")).strip()
        ]
    )

    doc_type_names = sorted({doc.get("document_type") for doc in documents if doc.get("document_type")})
    doc_type_meta: dict[str, dict] = {}
    if doc_type_names:
        for row_type in frappe.get_all(
            "Applicant Document Type",
            filters={"name": ["in", doc_type_names]},
            fields=[
                "name",
                "code",
                "document_type_name",
                "description",
                "is_required",
                "is_repeatable",
                "min_items_required",
            ],
        ):
            doc_type_meta[row_type.get("name")] = row_type

    items_by_document: dict[str, list[dict]] = {}
    for row_item in item_rows:
        parent = row_item.get("applicant_document")
        if not parent:
            continue
        latest_drive_file = latest_drive_file_by_item.get(row_item.get("name"), {})
        attachment = (
            _serialize_applicant_document_attachment(
                latest_drive_file=latest_drive_file,
                student_applicant_name=student_applicant_name,
                thumbnail_ready_map=drive_thumbnail_ready_map,
                version_mime_map=drive_version_mime_map,
            )
            if latest_drive_file
            else {
                "drive_file_id": None,
                "canonical_ref": None,
                "file_name": None,
                "uploaded_at": None,
                "open_url": None,
                "preview_url": None,
                "thumbnail_url": None,
                "preview_status": None,
                "attachment_preview": None,
            }
        )
        items_by_document.setdefault(parent, []).append(
            {
                "name": row_item.get("name"),
                "item_key": row_item.get("item_key"),
                "item_label": row_item.get("item_label"),
                "review_status": row_item.get("review_status") or "Pending",
                "reviewed_by": row_item.get("reviewed_by"),
                "reviewed_on": row_item.get("reviewed_on"),
                "uploaded_at": attachment.get("uploaded_at"),
                "open_url": attachment.get("open_url"),
                "preview_url": attachment.get("preview_url"),
                "thumbnail_url": attachment.get("thumbnail_url"),
                "preview_status": attachment.get("preview_status"),
                "file_name": attachment.get("file_name"),
                "drive_file_id": attachment.get("drive_file_id"),
                "canonical_ref": attachment.get("canonical_ref"),
                "attachment_preview": attachment.get("attachment_preview"),
            }
        )

    payload = []
    for doc in documents:
        doc_name = doc.get("name")
        type_meta = doc_type_meta.get(doc.get("document_type")) or {}
        items = items_by_document.get(doc_name, [])

        latest_uploaded_at = None
        latest_open_url = None
        if items:
            sorted_items = sorted(
                items,
                key=lambda row_item: row_item.get("uploaded_at") or "",
                reverse=True,
            )
            latest_uploaded_at = sorted_items[0].get("uploaded_at")
            latest_open_url = sorted_items[0].get("open_url")

        is_required = bool(type_meta.get("is_required"))
        is_repeatable = bool(type_meta.get("is_repeatable"))
        required_count = _portal_required_document_count(type_meta)
        uploaded_count = len([item for item in items if item.get("open_url")])
        approved_count = len(
            [item for item in items if item.get("open_url") and item.get("review_status") == "Approved"]
        )
        rejected_count = len(
            [item for item in items if item.get("open_url") and item.get("review_status") == "Rejected"]
        )
        pending_count = len(
            [
                item
                for item in items
                if item.get("open_url")
                and (item.get("review_status") or "Pending").strip() not in {"Approved", "Rejected"}
            ]
        )
        override_status = (doc.get("requirement_override") or "").strip() or None
        state_key, state_label = _portal_document_requirement_state(
            is_required=is_required,
            required_count=required_count,
            uploaded_count=uploaded_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            pending_count=pending_count,
            override_status=override_status,
        )

        payload.append(
            {
                "name": doc_name,
                "document_type": doc.get("document_type"),
                "label": (
                    (doc.get("document_label") or "").strip()
                    or (type_meta.get("document_type_name") or "").strip()
                    or (type_meta.get("code") or "").strip()
                    or (doc.get("document_type") or "").strip()
                    or doc_name
                ),
                "description": type_meta.get("description") or "",
                "is_required": is_required,
                "is_repeatable": is_repeatable,
                "required_count": required_count,
                "uploaded_count": uploaded_count,
                "approved_count": approved_count,
                "rejected_count": rejected_count,
                "pending_count": pending_count,
                "requirement_state": state_key,
                "requirement_state_label": state_label,
                "requirement_override": override_status,
                "override_reason": doc.get("override_reason"),
                "override_by": doc.get("override_by"),
                "override_on": doc.get("override_on"),
                "review_status": doc.get("review_status") or "Pending",
                "reviewed_by": doc.get("reviewed_by"),
                "reviewed_on": doc.get("reviewed_on"),
                "uploaded_at": latest_uploaded_at,
                "open_url": latest_open_url,
                "items": items,
            }
        )

    return {"documents": payload}


def _recommendation_target_document_types_for_applicant(student_applicant: str) -> set[str]:
    template_rows = get_recommendation_template_rows_for_applicant(
        student_applicant=student_applicant,
        include_confidential=True,
        fields=["target_document_type"],
    )
    return {
        (row.get("target_document_type") or "").strip()
        for row in template_rows
        if (row.get("target_document_type") or "").strip()
    }


def _portal_required_document_count(row_type: dict | None) -> int:
    if not row_type or not row_type.get("is_required"):
        return 0
    if not cint(row_type.get("is_repeatable")):
        return 1
    return max(1, cint(row_type.get("min_items_required") or 1))


def _portal_document_requirement_state(
    *,
    is_required: bool,
    required_count: int,
    uploaded_count: int,
    approved_count: int,
    rejected_count: int,
    pending_count: int,
    override_status: str | None,
) -> tuple[str, str]:
    if override_status == "Waived":
        return "waived", _("Waived by admissions")
    if override_status == "Exception Approved":
        return "exception_approved", _("Exception approved by admissions")

    needed_count = required_count if is_required else max(1, uploaded_count)
    if uploaded_count <= 0:
        return "not_started", _("Not started")
    if approved_count >= needed_count and needed_count > 0:
        return "complete", _("Complete")
    if rejected_count > 0:
        return "changes_requested", _("Changes requested")
    if pending_count > 0 or uploaded_count > 0:
        return "waiting_review", _("Uploaded - waiting for review")
    return "not_started", _("Not started")


@frappe.whitelist()
def list_applicant_document_types(student_applicant: str | None = None):
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    hidden_document_types = _recommendation_target_document_types_for_applicant((row.get("name") or "").strip())

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
        if (row_type.get("name") or "").strip() in hidden_document_types:
            continue
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
    student_applicant = _request_form_value("student_applicant", student_applicant)
    document_type = _request_form_value("document_type", document_type)
    applicant_document_item = _request_form_value("applicant_document_item", applicant_document_item)
    item_key = _request_form_value("item_key", item_key)
    item_label = _request_form_value("item_label", item_label)
    client_request_id = _request_form_value("client_request_id", client_request_id)
    file_name = _request_form_value("file_name", file_name)
    content = _request_form_value("content", content)

    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)
    hidden_document_types = _recommendation_target_document_types_for_applicant((row.get("name") or "").strip())

    if not document_type:
        frappe.throw(_("document_type is required."))
    if (document_type or "").strip() in hidden_document_types:
        frappe.throw(_("Recommendation submissions are managed through referee links and cannot be uploaded here."))

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
                _(
                    "This document type is not configured for uploads ({document_type}). Missing: {missing_fields}."
                ).format(
                    document_type=doc_type_label,
                    missing_fields=", ".join(missing_labels),
                )
            )
        frappe.throw(
            _("This document type is not configured for uploads ({document_type}).").format(
                document_type=doc_type_label
            )
        )

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

    upload_result = admission_api.upload_applicant_document(**payload)
    resolved_drive_file_id = _as_text(upload_result.get("drive_file_id")).strip() or None
    resolved_canonical_ref = _as_text(upload_result.get("canonical_ref")).strip() or None
    preview_status = (
        _as_text(frappe.db.get_value("Drive File", resolved_drive_file_id, "preview_status")).strip()
        if resolved_drive_file_id
        else ""
    )
    thumbnail_ready = (
        get_drive_file_thumbnail_ready_map([resolved_drive_file_id]).get(resolved_drive_file_id, False)
        if resolved_drive_file_id
        else False
    )
    open_url = resolve_admissions_file_open_url(
        file_name=upload_result.get("file"),
        file_url=upload_result.get("file_url"),
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype="Student Applicant",
        context_name=row.get("name"),
    )
    preview_url = resolve_admissions_file_preview_url(
        file_name=upload_result.get("file"),
        file_url=upload_result.get("file_url"),
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype="Student Applicant",
        context_name=row.get("name"),
        preview_ready=preview_status == "ready",
    )
    thumbnail_url = resolve_admissions_file_thumbnail_url(
        file_name=upload_result.get("file"),
        file_url=upload_result.get("file_url"),
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype="Student Applicant",
        context_name=row.get("name"),
        thumbnail_ready=thumbnail_ready,
    )
    return {
        "file": upload_result.get("file"),
        "open_url": open_url,
        "preview_url": preview_url,
        "thumbnail_url": thumbnail_url,
        "preview_status": preview_status or None,
        "drive_file_id": resolved_drive_file_id,
        "canonical_ref": resolved_canonical_ref,
        "applicant_document": upload_result.get("applicant_document"),
        "applicant_document_item": upload_result.get("applicant_document_item"),
        "item_key": upload_result.get("item_key"),
        "item_label": upload_result.get("item_label"),
    }


@frappe.whitelist()
def get_applicant_policies(student_applicant: str | None = None):
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

    payload = []
    for row_policy in policy_rows:
        policy_version = row_policy.get("policy_version")
        payload.append(
            {
                "name": row_policy.get("label"),
                "policy_version": policy_version,
                "content_html": sanitize_html(policy_text_by_version.get(policy_version, ""), allow_headings_from="h2"),
                "is_required": bool(row_policy.get("is_required")),
                "acknowledgement_mode": row_policy.get("admissions_acknowledgement_mode"),
                "is_acknowledged": bool(row_policy.get("is_acknowledged")),
                "acknowledged_at": row_policy.get("acknowledged_at"),
                "acknowledged_by": row_policy.get("acknowledged_by"),
                "expected_signature_name": row_policy.get("expected_signature_name") or "",
                "acknowledgement_clauses": clauses_by_version.get((policy_version or "").strip(), []),
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


def _ensure_admissions_family_role(user_doc) -> None:
    changed = False
    role_names = []
    seen = set()

    for row in user_doc.roles or []:
        role = (row.role or "").strip()
        if not role or role in seen:
            continue
        seen.add(role)
        role_names.append(role)

    if ADMISSIONS_FAMILY_ROLE not in seen:
        role_names.append(ADMISSIONS_FAMILY_ROLE)
        changed = True

    if changed:
        user_doc.set("roles", [{"role": role} for role in role_names])

    if not (user_doc.user_type or "").strip():
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


def _contact_linked_to_user(user_name: str | None) -> str | None:
    user_name = (user_name or "").strip()
    if not user_name:
        return None

    contact_name = (frappe.db.get_value("Contact", {"user": user_name}, "name") or "").strip()
    if contact_name:
        return contact_name

    contact_name = (
        frappe.db.get_value(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "link_doctype": "User",
                "link_name": user_name,
            },
            "parent",
        )
        or ""
    ).strip()
    return contact_name or None


def _contact_linked_to_applicant(contact_name: str | None) -> str | None:
    contact_name = (contact_name or "").strip()
    if not contact_name:
        return None

    applicant_name = (
        frappe.db.get_value(
            "Dynamic Link",
            {
                "parenttype": "Contact",
                "parentfield": "links",
                "parent": contact_name,
                "link_doctype": "Student Applicant",
            },
            "link_name",
        )
        or ""
    ).strip()
    return applicant_name or None


def _canonical_applicant_contact_for_invite(
    applicant_doc,
    *,
    user_doc=None,
    contact_name: str | None = None,
    invite_email: str | None = None,
    allow_create: bool = False,
) -> str | None:
    current_contact = (applicant_doc.get("applicant_contact") or "").strip()
    if current_contact:
        return current_contact

    invite_email = normalize_email_value(invite_email)
    candidate_names: list[str] = []
    for candidate in (
        _contact_linked_to_user(getattr(user_doc, "name", None) if user_doc else None),
        (frappe.db.get_value("Contact Email", {"email_id": invite_email}, "parent") or "").strip()
        if invite_email
        else "",
        (contact_name or "").strip(),
    ):
        candidate = (candidate or "").strip()
        if not candidate or candidate in candidate_names:
            continue
        linked_applicant = _contact_linked_to_applicant(candidate)
        if linked_applicant and linked_applicant != applicant_doc.name:
            frappe.throw(_("Invite email is linked to a different Contact."))
        candidate_names.append(candidate)

    if candidate_names:
        return candidate_names[0]

    if allow_create and invite_email:
        return ensure_contact_for_email(
            first_name=applicant_doc.get("first_name"),
            last_name=applicant_doc.get("last_name"),
            email=invite_email,
        )

    return None


def _invite_contact_email_options(contact_name: str | None) -> list[str]:
    contact_name = (contact_name or "").strip()
    if not contact_name:
        return []

    rows = frappe.get_all(
        "Contact Email",
        filters={"parent": contact_name},
        fields=["email_id", "is_primary", "idx"],
        order_by="is_primary desc, idx asc, creation asc",
        ignore_permissions=True,
    )
    emails: list[str] = []
    seen: set[str] = set()
    for row in rows:
        normalized = normalize_email_value(row.get("email_id"))
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        emails.append(normalized)
    return emails


def _invite_contact_primary_email(contact_name: str | None) -> str | None:
    options = _invite_contact_email_options(contact_name)
    if options:
        return options[0]
    return get_contact_primary_email(contact_name)


def _require_family_workspace_mode() -> None:
    if not is_family_workspace_enabled():
        frappe.throw(
            _("Family Workspace mode is not enabled in Admission Settings."),
            frappe.ValidationError,
        )


def _guardian_row_display_name(row) -> str:
    full_name = _as_text(row.get("guardian_full_name")).strip()
    if full_name:
        return full_name
    parts = [
        _as_text(row.get("guardian_first_name")).strip(),
        _as_text(row.get("guardian_last_name")).strip(),
    ]
    name = " ".join(part for part in parts if part).strip()
    return name or _as_text(row.get("relationship")).strip() or _as_text(row.get("name")).strip()


def _get_applicant_guardian_row(applicant, guardian_row_name: str):
    target_name = (guardian_row_name or "").strip()
    if not target_name:
        frappe.throw(_("guardian_row is required."))
    for row in applicant.get("guardians") or []:
        if (row.name or "").strip() == target_name:
            return row
    frappe.throw(
        _("Guardian row {guardian_row} was not found on this Applicant.").format(guardian_row=target_name),
        frappe.DoesNotExistError,
    )


def _ensure_family_guardian_user(*, guardian, email: str, applicant_name: str, row_payload: dict):
    resolved_email = normalize_email_value(email)
    if not resolved_email:
        frappe.throw(_("Guardian email is required."))

    existing_user_guardian = frappe.db.get_value("Guardian", {"user": resolved_email}, "name")
    if existing_user_guardian and existing_user_guardian != guardian.name:
        frappe.throw(_("This email is already linked to a different Guardian account."))

    existing_applicant = frappe.db.get_value("Student Applicant", {"applicant_user": resolved_email}, "name")
    if existing_applicant:
        frappe.throw(
            _(
                "This email is already reserved as an Applicant login ({applicant}). Use a different family collaborator email."
            ).format(applicant=existing_applicant)
        )

    resent = False
    if guardian.user:
        linked_user = normalize_email_value(guardian.user)
        if linked_user != resolved_email:
            frappe.throw(_("Guardian is already linked to a different user account."))
        user_doc = frappe.get_doc("User", linked_user)
        resent = True
    elif frappe.db.exists("User", resolved_email):
        user_doc = frappe.get_doc("User", resolved_email)
    else:
        user_doc = frappe.get_doc(
            {
                "doctype": "User",
                "enabled": 1,
                "first_name": row_payload.get("guardian_first_name") or resolved_email,
                "last_name": row_payload.get("guardian_last_name") or "",
                "email": resolved_email,
                "username": resolved_email,
                "mobile_no": row_payload.get("guardian_mobile_phone") or "",
                "user_type": "Website User",
            }
        )
        user_doc.append("roles", {"role": ADMISSIONS_FAMILY_ROLE})
        user_doc.insert(ignore_permissions=True)

    _ensure_admissions_family_role(user_doc)

    if not (guardian.user or "").strip():
        guardian.db_set("user", user_doc.name, update_modified=False)
    if (guardian.user or "").strip() != user_doc.name:
        frappe.throw(_("Guardian is already linked to a different user account."))

    return user_doc, resent


@frappe.whitelist()
def get_family_invite_options(*, student_applicant: str | None = None) -> dict:
    ensure_admissions_permission()
    _require_family_workspace_mode()

    if not student_applicant:
        frappe.throw(_("student_applicant is required."))

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    guardian_payload = []
    for row in applicant.get("guardians") or []:
        email = normalize_email_value(row.get("guardian_email"))
        is_primary_guardian = bool(cint(row.get("is_primary_guardian") or 0))
        eligible = bool(email and cint(row.get("can_consent")) and is_primary_guardian)
        reason = ""
        if not is_primary_guardian:
            reason = _("Mark this guardian as the primary guardian before inviting portal access.")
        elif not cint(row.get("can_consent")):
            reason = _("Only the primary guardian may be invited as the authorized signer.")
        elif not email:
            reason = _("Add a guardian personal email before inviting portal access.")
        guardian_payload.append(
            {
                "name": row.name,
                "label": _guardian_row_display_name(row),
                "relationship": _as_text(row.get("relationship")).strip(),
                "email": email,
                "user": _as_text(row.get("user")).strip() or None,
                "guardian": _as_text(row.get("guardian")).strip() or None,
                "can_consent": bool(cint(row.get("can_consent"))),
                "eligible": eligible,
                "reason": reason or None,
            }
        )

    return {"guardians": guardian_payload}


@frappe.whitelist()
def invite_family_collaborator(
    *,
    student_applicant: str | None = None,
    guardian_row: str | None = None,
    email: str | None = None,
) -> dict:
    ensure_admissions_permission()
    _require_family_workspace_mode()

    if not student_applicant:
        frappe.throw(_("student_applicant is required."))

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    target_row = _get_applicant_guardian_row(applicant, guardian_row or "")
    if not cint(target_row.get("is_primary_guardian") or 0):
        frappe.throw(_("Only primary guardian rows may be invited to the family workspace as signers."))
    if not cint(target_row.get("can_consent")):
        frappe.throw(_("Only guardian rows marked as authorized signers may be invited to the family workspace."))

    invite_email = normalize_email_value(email or target_row.get("guardian_email"))
    if not invite_email:
        frappe.throw(_("email is required."))

    row_payload = dict(target_row.as_dict())
    row_payload["guardian_email"] = invite_email
    row_payload = _validate_guardian_profile_row(_normalize_guardian_row(row_payload))
    contact_name = _create_or_update_guardian_contact(
        applicant=applicant,
        row_payload=row_payload,
        existing_contact_name=_as_text(target_row.get("contact")).strip() or None,
    )
    row_payload["contact"] = contact_name

    if (target_row.get("guardian") or "").strip():
        guardian_doc = frappe.get_doc("Guardian", target_row.get("guardian"))
    else:
        guardian_spec = applicant._create_or_reuse_guardian_from_profile_row(row_payload)
        guardian_doc = guardian_spec["guardian"]

    user_doc, resent = _ensure_family_guardian_user(
        guardian=guardian_doc,
        email=invite_email,
        applicant_name=applicant.name,
        row_payload=row_payload,
    )

    if contact_name:
        ensure_contact_dynamic_link(contact_name=contact_name, link_doctype="Guardian", link_name=guardian_doc.name)
        contact_user = _as_text(frappe.db.get_value("Contact", contact_name, "user")).strip()
        if not contact_user:
            frappe.db.set_value("Contact", contact_name, "user", user_doc.name, update_modified=False)

    target_row.guardian = guardian_doc.name
    target_row.contact = contact_name
    target_row.user = user_doc.name
    target_row.guardian_email = invite_email
    target_row.guardian_full_name = _guardian_row_display_name(row_payload)
    applicant.save(ignore_permissions=True)

    email_sent = _send_applicant_invite_email(user_doc, invite_email)
    applicant.add_comment(
        "Comment",
        text=_("Family admissions portal access invited for {guardian_label} ({invite_email}) by {actor}.").format(
            guardian_label=frappe.bold(_guardian_row_display_name(target_row)),
            invite_email=frappe.bold(invite_email),
            actor=frappe.bold(frappe.session.user),
        ),
    )

    return {"ok": True, "user": user_doc.name, "resent": resent, "email_sent": email_sent}


@frappe.whitelist()
def get_invite_email_options(*, student_applicant: str | None = None) -> dict:
    ensure_admissions_permission()
    if is_family_workspace_enabled():
        frappe.throw(
            _("Single applicant invites are disabled while Family Workspace mode is enabled."),
            frappe.ValidationError,
        )

    if not student_applicant:
        frappe.throw(_("student_applicant is required."))

    applicant = frappe.get_doc("Student Applicant", student_applicant)
    contact_name = _canonical_applicant_contact_for_invite(
        applicant,
        user_doc=frappe.get_doc("User", applicant.applicant_user)
        if applicant.applicant_user and frappe.db.exists("User", applicant.applicant_user)
        else None,
        contact_name=_resolve_applicant_contact(applicant, allow_create=False),
        invite_email=normalize_email_value(applicant.get("portal_account_email"))
        or normalize_email_value(applicant.get("applicant_email"))
        or normalize_email_value(applicant.get("applicant_user")),
        allow_create=False,
    )

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

    for value in _invite_contact_email_options(contact_name):
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
    if is_family_workspace_enabled():
        frappe.throw(
            _("Use Invite Family Collaborator while Family Workspace mode is enabled."),
            frappe.ValidationError,
        )

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

    contact_name = _resolve_applicant_contact(applicant, invite_email=email, allow_create=False)

    if applicant.applicant_user:
        user_doc = frappe.get_doc("User", linked_user)
        _ensure_admissions_applicant_role(user_doc)
        contact_name = _canonical_applicant_contact_for_invite(
            applicant,
            user_doc=user_doc,
            contact_name=contact_name,
            invite_email=email,
            allow_create=True,
        )
        if not contact_name:
            frappe.throw(_("Unable to resolve Applicant Contact for this invite."))
        upsert_contact_email(contact_name, email, set_primary_if_missing=True)
        primary_contact_email = _invite_contact_primary_email(contact_name) or email

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
            text=_("Applicant portal invite email re-sent for {applicant} by {actor}.").format(
                applicant=frappe.bold(applicant.name),
                actor=frappe.bold(frappe.session.user),
            ),
        )
        return {"ok": True, "user": user_doc.name, "resent": True, "email_sent": email_sent}

    user_doc = None
    if frappe.db.exists("User", email):
        user_doc = frappe.get_doc("User", email)
        existing_roles = {row.role for row in (user_doc.roles or [])}
        non_portal_roles = existing_roles - {ADMISSIONS_ROLE, "All", "Guest", "Desk User"}
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
                "username": email,
                "user_type": "Website User",
            }
        )
        user_doc.append("roles", {"role": ADMISSIONS_ROLE})
        user_doc.insert(ignore_permissions=True)

    _ensure_admissions_applicant_role(user_doc)
    contact_name = _canonical_applicant_contact_for_invite(
        applicant,
        user_doc=user_doc,
        contact_name=contact_name,
        invite_email=email,
        allow_create=True,
    )
    if not contact_name:
        frappe.throw(_("Unable to resolve Applicant Contact for this invite."))
    upsert_contact_email(contact_name, email, set_primary_if_missing=True)
    primary_contact_email = _invite_contact_primary_email(contact_name) or email

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
        text=_("Applicant portal user invited for {applicant} by {actor}.").format(
            applicant=frappe.bold(applicant.name),
            actor=frappe.bold(frappe.session.user),
        ),
    )

    email_sent = _send_applicant_invite_email(user_doc, email)

    return {"ok": True, "user": user_doc.name, "resent": False, "email_sent": email_sent}
