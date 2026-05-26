# ifitwala_ed/admission/api/portal/health.py

from __future__ import annotations

import base64

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission import admissions_portal as admission_api
from ifitwala_ed.admission.api.common.request_payload import _as_bool, _as_check
from ifitwala_ed.admission.api.portal.access import _as_text, _ensure_applicant_match, _require_admissions_applicant
from ifitwala_ed.admission.api.portal.profile import _assert_record_modified_matches
from ifitwala_ed.admission.api.portal.session import _build_applicant_display_name
from ifitwala_ed.admission.applicant_review_workflow import materialize_health_review_assignments

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
    payload["applicant_health_declared_complete"] = 0
    payload["applicant_health_declared_by"] = ""
    payload["applicant_health_declared_on"] = ""
    payload["applicant_display_name"] = ""
    return payload


def _has_health_declaration_column() -> bool:
    try:
        return bool(frappe.db.has_column("Applicant Health Profile", "applicant_health_declared_complete"))
    except Exception:
        return False


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


def get_applicant_health_impl(student_applicant: str | None = None):
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


def update_applicant_health_impl(
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
