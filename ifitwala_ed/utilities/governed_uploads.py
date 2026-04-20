# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/governed_uploads.py

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from typing import Tuple

import frappe
from frappe import _

from ifitwala_ed.integrations.drive.authority import get_drive_file_for_file
from ifitwala_ed.utilities.image_utils import (
    EMPLOYEE_VARIANT_PRIORITY,
    file_url_is_accessible,
    get_employee_image_variants_map,
    get_preferred_employee_image_url,
)
from ifitwala_ed.utilities.organization_media import (
    build_organization_media_slot,
)


def _get_uploaded_file() -> Tuple[str, bytes]:
    if not frappe.request:
        frappe.throw(_("No request context for upload."))

    uploaded = frappe.request.files.get("file")
    if not uploaded:
        frappe.throw(_("No file uploaded."))

    filename = uploaded.filename or uploaded.name
    content = b""
    if hasattr(uploaded, "stream"):
        try:
            if hasattr(uploaded.stream, "seek"):
                uploaded.stream.seek(0)
            content = uploaded.stream.read()
        except Exception:
            content = b""
    if not content and hasattr(uploaded, "read"):
        try:
            content = uploaded.read()
        except Exception:
            content = b""
    if not content:
        frappe.throw(_("Uploaded file is empty."))

    return filename, content


def _normalize_mime_type_hint(value: str | None) -> str | None:
    mime_type = str(value or "").strip().lower()
    if not mime_type:
        return None

    normalized = mime_type.split(";", 1)[0].strip()
    return normalized or None


def _resolve_upload_mime_type_hint(*, filename: str | None = None, explicit: str | None = None) -> str | None:
    request = getattr(frappe, "request", None)
    if request and getattr(request, "files", None):
        uploaded = request.files.get("file")
        if uploaded:
            uploaded_mime_type = _normalize_mime_type_hint(
                getattr(uploaded, "mimetype", None) or getattr(uploaded, "content_type", None)
            )
            if uploaded_mime_type and uploaded_mime_type != "multipart/form-data":
                return uploaded_mime_type

    explicit_mime_type = _normalize_mime_type_hint(explicit)
    if explicit_mime_type and explicit_mime_type != "multipart/form-data":
        return explicit_mime_type

    guessed_mime_type = mimetypes.guess_type(filename or "")[0]
    return _normalize_mime_type_hint(guessed_mime_type)


def _require_doc(doctype: str, name: str):
    if not name:
        frappe.throw(_("Missing document name."))
    doc = frappe.get_doc(doctype, name)
    doc.check_permission("write")
    return doc


def _require_clean_saved_doc(doc, *, action_label: str):
    if doc.is_new():
        frappe.throw(_("Please save the document before using {0}.").format(action_label))
    if doc.get("__unsaved"):
        frappe.throw(_("Please save the document before using {0}.").format(action_label))
    return doc


def _get_org_from_school(school: str) -> str:
    if not school:
        frappe.throw(_("School is required for this upload."))
    organization = frappe.db.get_value("School", school, "organization")
    if not organization:
        frappe.throw(_("Organization is required for file classification."))
    return organization


def _get_form_arg(key: str):
    value = frappe.form_dict.get(key)
    if value:
        return value

    args = frappe.form_dict.get("args")
    if not args:
        return None

    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            return None

    if isinstance(args, dict):
        return args.get(key)

    return None


def _response_payload(file_doc):
    return {
        "file": file_doc.name,
        "file_url": file_doc.file_url,
        "file_name": file_doc.file_name,
        "file_size": file_doc.file_size,
    }


def _append_attached_document_row(doc, *, fieldname: str, file_doc, title: str | None = None):
    doc.append(
        fieldname,
        {
            "section_break_sbex": title or file_doc.file_name,
            "file": file_doc.file_url,
            "file_name": file_doc.file_name,
            "file_size": file_doc.file_size,
            "public": 0,
        },
    )
    doc.save(ignore_permissions=True)


def _ensure_file_on_disk(file_doc):
    if not file_doc or not file_doc.file_url:
        frappe.throw(_("File URL missing after upload."))
    if file_doc.file_url.startswith("http"):
        return
    if not file_url_is_accessible(
        file_doc.file_url,
        file_name=getattr(file_doc, "name", None),
        is_private=getattr(file_doc, "is_private", 0),
    ):
        frappe.throw(_("File could not be finalized in managed storage. Please retry the upload."))


def _sync_linked_employee_user_image(employee_name: str, *, original_url: str | None = None) -> None:
    employee_name = (employee_name or "").strip()
    if not employee_name:
        return

    user_id = frappe.db.get_value("Employee", employee_name, "user_id")
    if not user_id:
        return

    avatar_url = get_preferred_employee_image_url(
        employee_name,
        original_url=original_url,
        slots=EMPLOYEE_VARIANT_PRIORITY,
    )
    if not avatar_url:
        return

    user_doc = frappe.get_doc("User", user_id)
    user_doc.flags.ignore_permissions = True
    if getattr(user_doc, "user_image", None) == avatar_url:
        return

    user_doc.user_image = avatar_url
    user_doc.save(ignore_permissions=True)


def _get_drive_media_callable(attribute: str):
    try:
        from ifitwala_drive.api import media as drive_media_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))
    create_session_callable = getattr(drive_media_api, attribute, None)
    if create_session_callable:
        return create_session_callable

    frappe.throw(
        _(
            "Ifitwala Drive is missing public media method '{0}'. Deploy the matching Drive API before using governed media uploads."
        ).format(attribute)
    )


def _drive_upload_and_finalize(*, create_session_callable, payload: dict, content: bytes):
    try:
        from ifitwala_drive.api import uploads as drive_uploads_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))

    if "idempotency_key" not in payload:
        payload = {
            **payload,
            "idempotency_key": _build_drive_idempotency_key(payload=payload, content=content),
        }

    session_response = create_session_callable(**payload)
    upload_session_id = session_response.get("upload_session_id")
    if not upload_session_id:
        frappe.throw(_("Drive did not return an upload_session_id."))

    ingest_upload_session_content = getattr(drive_uploads_api, "ingest_upload_session_content", None)
    if not callable(ingest_upload_session_content):
        frappe.throw(
            _(
                "Ifitwala Drive is missing ingest_upload_session_content. Deploy or restart the Drive app so the updated upload API is available."
            )
        )
    ingest_upload_session_content(upload_session_id=upload_session_id, content=content)

    finalize_response = drive_uploads_api.finalize_upload_session(
        upload_session_id=upload_session_id,
        received_size_bytes=len(content),
    )
    file_name = finalize_response.get("file_id")
    if not file_name:
        frappe.throw(_("Drive finalize did not return a file_id."))

    return session_response, finalize_response, frappe.get_doc("File", file_name)


def _build_drive_idempotency_key(*, payload: dict, content: bytes) -> str:
    content_hash = hashlib.sha256(content or b"").hexdigest()
    workflow_id = str(payload.get("workflow_id") or "").strip()
    workflow_payload = payload.get("workflow_payload")
    if isinstance(workflow_payload, str):
        try:
            workflow_payload = json.loads(workflow_payload)
        except Exception:
            workflow_payload = {"raw": workflow_payload}
    if not isinstance(workflow_payload, dict):
        workflow_payload = {}
    seed_parts = [
        workflow_id,
        json.dumps(workflow_payload, sort_keys=True, separators=(",", ":")),
        str(payload.get("task_submission") or "").strip(),
        str(payload.get("task") or "").strip(),
        str(payload.get("material") or "").strip(),
        str(payload.get("student_applicant") or "").strip(),
        str(payload.get("applicant_health_profile") or "").strip(),
        str(payload.get("employee") or "").strip(),
        str(payload.get("student") or "").strip(),
        str(payload.get("student_patient") or "").strip(),
        str(payload.get("organization") or "").strip(),
        str(payload.get("school") or "").strip(),
        str(payload.get("row_name") or "").strip(),
        str(payload.get("guardian_row_name") or "").strip(),
        str(payload.get("document_type") or "").strip(),
        str(payload.get("item_key") or "").strip(),
        str(payload.get("source_applicant_document_item") or "").strip(),
        str(payload.get("filename_original") or "").strip(),
        content_hash,
    ]
    seed = "|".join(seed_parts)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _derive_generic_media_key(*, filename: str, media_key: str | None = None) -> str:
    explicit = frappe.scrub((media_key or "").strip())
    if explicit:
        return explicit

    base_name = os.path.splitext(filename or "media")[0]
    slug_base = frappe.scrub(base_name) or "media"
    return f"{slug_base}_{frappe.generate_hash(length=6)}"


@frappe.whitelist()
def upload_employee_image(employee: str | None = None, **_kwargs):
    employee = employee or _get_form_arg("employee") or frappe.form_dict.get("docname")
    doc = _require_doc("Employee", employee)
    if not doc.organization:
        frappe.throw(_("Organization is required for file classification."))

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=_get_drive_media_callable("upload_employee_image"),
        payload={
            "employee": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value("Employee", doc.name, "employee_image", file_doc.file_url, update_modified=False)
    _sync_linked_employee_user_image(doc.name, original_url=file_doc.file_url)
    return _response_payload(file_doc)


@frappe.whitelist()
def upload_student_image(student: str | None = None, **_kwargs):
    student = student or _get_form_arg("student") or frappe.form_dict.get("docname")
    doc = _require_doc("Student", student)
    if not doc.anchor_school:
        frappe.throw(_("Anchor School is required before uploading a student image."))

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=_get_drive_media_callable("upload_student_image"),
        payload={
            "student": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value("Student", doc.name, "student_image", file_doc.file_url, update_modified=False)
    doc.student_image = file_doc.file_url
    doc.sync_student_contact_image()
    return _response_payload(file_doc)


@frappe.whitelist()
def upload_guardian_image(guardian: str | None = None, **_kwargs):
    guardian = guardian or _get_form_arg("guardian") or frappe.form_dict.get("docname")
    doc = _require_doc("Guardian", guardian)

    filename, content = _get_uploaded_file()
    organization = doc.resolve_profile_image_organization()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=_get_drive_media_callable("upload_guardian_image"),
        payload={
            "guardian": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value(
        "Guardian",
        doc.name,
        {
            "guardian_image": file_doc.file_url,
            "organization": organization,
        },
        update_modified=False,
    )
    return _response_payload(file_doc)


@frappe.whitelist()
def upload_applicant_image(student_applicant: str | None = None, **_kwargs):
    student_applicant = student_applicant or _get_form_arg("student_applicant") or frappe.form_dict.get("docname")
    doc = _require_doc("Student Applicant", student_applicant)
    if not doc.organization or not doc.school:
        frappe.throw(_("Organization and School are required for file classification."))

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    try:
        from ifitwala_drive.api import admissions as drive_admissions_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))
    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_admissions_api.upload_applicant_profile_image,
        payload={
            "student_applicant": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value("Student Applicant", doc.name, "applicant_image", file_doc.file_url, update_modified=False)
    return _response_payload(file_doc)


@frappe.whitelist()
def upload_task_submission_attachment(task_submission: str | None = None, **_kwargs):
    task_submission = task_submission or _get_form_arg("task_submission") or frappe.form_dict.get("docname")
    doc = _require_doc("Task Submission", task_submission)
    if not doc.school or not doc.student:
        frappe.throw(_("Student and School are required for file classification."))

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    try:
        from ifitwala_drive.api import submissions as drive_submissions_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))

    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_submissions_api.upload_task_submission_artifact,
        payload={
            "task_submission": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    _append_attached_document_row(doc, fieldname="attachments", file_doc=file_doc)

    return _response_payload(file_doc)


@frappe.whitelist()
def upload_task_resource(task: str | None = None, row_name: str | None = None, **_kwargs):
    task = task or _get_form_arg("task") or frappe.form_dict.get("docname")
    row_name = row_name or _get_form_arg("row_name")
    doc = _require_clean_saved_doc(_require_doc("Task", task), action_label=_("Upload Task Resource"))

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    try:
        from ifitwala_drive.api import resources as drive_resources_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))

    session_response, finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_resources_api.upload_task_resource,
        payload={
            "task": doc.name,
            "row_name": row_name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    payload = _response_payload(file_doc)
    payload["row_name"] = finalize_response.get("row_name") or session_response.get("row_name")
    return payload


@frappe.whitelist()
def upload_supporting_material_file(material: str | None = None, **_kwargs):
    material = material or _get_form_arg("material") or frappe.form_dict.get("docname")
    doc = _require_clean_saved_doc(
        _require_doc("Supporting Material", material),
        action_label=_("Upload Supporting Material"),
    )

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    try:
        from ifitwala_drive.api import materials as drive_materials_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))

    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_materials_api.upload_supporting_material,
        payload={
            "material": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "SPA",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)
    return _response_payload(file_doc)


@frappe.whitelist()
def upload_school_logo(school: str | None = None, **_kwargs):
    school = school or _get_form_arg("school") or frappe.form_dict.get("docname")
    doc = _require_clean_saved_doc(_require_doc("School", school), action_label=_("Upload School Logo"))
    if not doc.organization:
        frappe.throw(_("Organization is required before uploading a school logo."))

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=_get_drive_media_callable("upload_school_logo"),
        payload={
            "school": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value(
        "School",
        doc.name,
        {
            "school_logo": file_doc.file_url,
            "school_logo_file": file_doc.name,
        },
        update_modified=False,
    )
    payload = _response_payload(file_doc)
    payload["school"] = doc.name
    return payload


@frappe.whitelist()
def upload_school_gallery_image(school: str | None = None, row_name: str | None = None, **_kwargs):
    school = school or _get_form_arg("school") or frappe.form_dict.get("docname")
    row_name = row_name or _get_form_arg("row_name")
    caption = (_get_form_arg("caption") or "").strip()
    doc = _require_clean_saved_doc(_require_doc("School", school), action_label=_("Upload Gallery Image"))
    if not doc.organization:
        frappe.throw(_("Organization is required before uploading a gallery image."))

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    try:
        from ifitwala_drive.api import media as drive_media_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))

    session_response, finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_media_api.upload_school_gallery_image,
        payload={
            "school": doc.name,
            "row_name": row_name,
            "caption": caption,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    payload = _response_payload(file_doc)
    payload["school"] = doc.name
    payload["row_name"] = finalize_response.get("row_name") or session_response.get("row_name")
    payload["caption"] = session_response.get("caption") or caption or None
    return payload


@frappe.whitelist()
def upload_organization_media_asset(
    organization: str | None = None,
    school: str | None = None,
    scope: str | None = None,
    media_key: str | None = None,
    **_kwargs,
):
    organization = organization or _get_form_arg("organization")
    school = school or _get_form_arg("school")
    scope = (scope or _get_form_arg("scope") or "organization").strip().lower()

    if school and not organization:
        school_doc = _require_clean_saved_doc(
            _require_doc("School", school), action_label=_("Upload Organization Media")
        )
        organization = school_doc.organization
    elif organization:
        organization_doc = _require_clean_saved_doc(
            _require_doc("Organization", organization),
            action_label=_("Upload Organization Media"),
        )
        organization = organization_doc.name

    if not organization:
        frappe.throw(_("Organization is required before uploading organization media."))

    if scope not in {"organization", "school"}:
        frappe.throw(_("Scope must be 'organization' or 'school'."))
    if scope == "school" and not school:
        frappe.throw(_("School is required for school-scoped organization media."))
    if scope == "organization":
        school = None

    filename, content = _get_uploaded_file()
    slot = build_organization_media_slot(
        media_key=_derive_generic_media_key(filename=filename, media_key=media_key),
    )
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    try:
        from ifitwala_drive.api import media as drive_media_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed upload execution: {0}").format(exc))
    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=drive_media_api.upload_organization_media_asset,
        payload={
            "organization": organization,
            "school": school,
            "scope": scope,
            "media_key": media_key,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    payload = _response_payload(file_doc)
    payload["organization"] = organization
    payload["school"] = school
    payload["scope"] = "school" if school else "organization"
    payload["slot"] = slot
    return payload


@frappe.whitelist()
def upload_organization_logo(organization: str | None = None, **_kwargs):
    organization = organization or _get_form_arg("organization") or frappe.form_dict.get("docname")
    doc = _require_clean_saved_doc(
        _require_doc("Organization", organization),
        action_label=_("Upload Organization Logo"),
    )

    filename, content = _get_uploaded_file()
    mime_type_hint = _resolve_upload_mime_type_hint(filename=filename)
    _session_response, _finalize_response, file_doc = _drive_upload_and_finalize(
        create_session_callable=_get_drive_media_callable("upload_organization_logo"),
        payload={
            "organization": doc.name,
            "filename_original": filename,
            "mime_type_hint": mime_type_hint,
            "expected_size_bytes": len(content),
            "upload_source": "Desk",
        },
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value(
        "Organization",
        doc.name,
        {
            "organization_logo": file_doc.file_url,
            "organization_logo_file": file_doc.name,
        },
        update_modified=False,
    )
    payload = _response_payload(file_doc)
    payload["organization"] = doc.name
    return payload


@frappe.whitelist()
def get_governed_status(doctype: str, name: str, fieldname: str | None = None):
    if not doctype or not name:
        frappe.throw(_("doctype and name are required."))

    doc = frappe.get_doc(doctype, name)
    doc.check_permission("read")

    filters = {
        "attached_to_doctype": doctype,
        "attached_to_name": name,
    }
    if fieldname:
        filters["attached_to_field"] = fieldname

    file_name = frappe.db.get_value("File", filters, "name")
    if not file_name:
        return {"has_file": 0, "governed": 0}

    drive_file = get_drive_file_for_file(file_name, fields=["name"], statuses=None)
    return {
        "has_file": 1,
        "file": file_name,
        "drive_file_id": (drive_file or {}).get("name"),
        "governed": 1 if drive_file else 0,
    }


@frappe.whitelist()
def get_employee_image_variants(employee: str):
    if not employee:
        frappe.throw(_("employee is required."))

    doc = frappe.get_doc("Employee", employee)
    doc.check_permission("read")

    variants = get_employee_image_variants_map([doc.name]).get(doc.name, {})
    if doc.employee_image and "profile_image" not in variants:
        variants["profile_image"] = doc.employee_image
    return variants


@frappe.whitelist()
def get_employee_image_display_map(employees):
    payload = employees
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = [payload]

    if not isinstance(payload, list):
        frappe.throw(_("employees must be a list of Employee names."))

    employee_names = []
    for employee_name in payload:
        clean_name = (str(employee_name or "")).strip()
        if not clean_name:
            continue
        employee_doc = frappe.get_doc("Employee", clean_name)
        employee_doc.check_permission("read")
        employee_names.append(clean_name)

    if not employee_names:
        return {}

    rows = frappe.get_all(
        "Employee",
        filters={"name": ("in", employee_names)},
        fields=["name", "employee_image"],
    )
    image_rows = {row["name"]: row.get("employee_image") for row in rows}

    return {
        employee_name: get_preferred_employee_image_url(
            employee_name,
            original_url=image_rows.get(employee_name),
            slots=EMPLOYEE_VARIANT_PRIORITY,
        )
        or ""
        for employee_name in employee_names
    }
