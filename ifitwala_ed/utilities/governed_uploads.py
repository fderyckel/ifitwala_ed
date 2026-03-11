# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/governed_uploads.py

from __future__ import annotations

import json
import os
from typing import Tuple

import frappe
from frappe import _

from ifitwala_ed.utilities import file_dispatcher
from ifitwala_ed.utilities.organization_media import (
    build_organization_logo_slot,
    build_organization_media_classification,
    build_organization_media_context,
    build_organization_media_slot,
    build_school_gallery_slot,
    build_school_logo_slot,
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


def _ensure_file_on_disk(file_doc):
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


def _file_url_exists_on_disk(file_url: str | None, is_private: int | None = 0) -> bool:
    if not file_url:
        return False

    if file_url.startswith("http"):
        return True

    rel_path = file_url.lstrip("/")
    if rel_path.startswith("private/") or rel_path.startswith("public/"):
        abs_path = frappe.utils.get_site_path(rel_path)
    else:
        base = "private" if is_private else "public"
        abs_path = frappe.utils.get_site_path(base, rel_path)

    return os.path.exists(abs_path)


def _upload_organization_media_file(
    *,
    organization: str,
    slot: str,
    school: str | None = None,
    filename: str,
    content: bytes,
    upload_source: str = "Desk",
):
    return file_dispatcher.create_and_classify_file(
        file_kwargs={
            "attached_to_doctype": "Organization",
            "attached_to_name": organization,
            "file_name": filename,
            "content": content,
            "is_private": 0,
        },
        classification=build_organization_media_classification(
            organization=organization,
            school=school,
            slot=slot,
            upload_source=upload_source,
        ),
        context_override=build_organization_media_context(
            organization=organization,
            school=school,
            slot=slot,
        ),
    )


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

    file_doc = file_dispatcher.create_and_classify_file(
        file_kwargs={
            "attached_to_doctype": "Employee",
            "attached_to_name": doc.name,
            "attached_to_field": "employee_image",
            "file_name": filename,
            "content": content,
            "is_private": 0,
        },
        classification={
            "primary_subject_type": "Employee",
            "primary_subject_id": doc.name,
            "data_class": "identity_image",
            "purpose": "employee_profile_display",
            "retention_policy": "employment_duration_plus_grace",
            "slot": "profile_image",
            "organization": doc.organization,
            "school": doc.school,
            "upload_source": "Desk",
        },
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value("Employee", doc.name, "employee_image", file_doc.file_url, update_modified=False)
    return _response_payload(file_doc)


@frappe.whitelist()
def upload_student_image(student: str | None = None, **_kwargs):
    student = student or _get_form_arg("student") or frappe.form_dict.get("docname")
    doc = _require_doc("Student", student)
    if not doc.anchor_school:
        frappe.throw(_("Anchor School is required before uploading a student image."))

    organization = _get_org_from_school(doc.anchor_school)
    filename, content = _get_uploaded_file()

    file_doc = file_dispatcher.create_and_classify_file(
        file_kwargs={
            "attached_to_doctype": "Student",
            "attached_to_name": doc.name,
            "attached_to_field": "student_image",
            "file_name": filename,
            "content": content,
            "is_private": 0,
        },
        classification={
            "primary_subject_type": "Student",
            "primary_subject_id": doc.name,
            "data_class": "identity_image",
            "purpose": "student_profile_display",
            "retention_policy": "until_school_exit_plus_6m",
            "slot": "profile_image",
            "organization": organization,
            "school": doc.anchor_school,
            "upload_source": "Desk",
        },
    )
    _ensure_file_on_disk(file_doc)

    frappe.db.set_value("Student", doc.name, "student_image", file_doc.file_url, update_modified=False)
    doc.student_image = file_doc.file_url
    doc.sync_student_contact_image()
    return _response_payload(file_doc)


@frappe.whitelist()
def upload_applicant_image(student_applicant: str | None = None, **_kwargs):
    student_applicant = student_applicant or _get_form_arg("student_applicant") or frappe.form_dict.get("docname")
    doc = _require_doc("Student Applicant", student_applicant)
    if not doc.organization or not doc.school:
        frappe.throw(_("Organization and School are required for file classification."))

    filename, content = _get_uploaded_file()

    file_doc = file_dispatcher.create_and_classify_file(
        file_kwargs={
            "attached_to_doctype": "Student Applicant",
            "attached_to_name": doc.name,
            "attached_to_field": "applicant_image",
            "file_name": filename,
            "content": content,
            "is_private": 1,
        },
        classification={
            "primary_subject_type": "Student Applicant",
            "primary_subject_id": doc.name,
            "data_class": "identity_image",
            "purpose": "applicant_profile_display",
            "retention_policy": "until_school_exit_plus_6m",
            "slot": "profile_image",
            "organization": doc.organization,
            "school": doc.school,
            "upload_source": "Desk",
        },
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

    organization = _get_org_from_school(doc.school)
    filename, content = _get_uploaded_file()

    file_doc = file_dispatcher.create_and_classify_file(
        file_kwargs={
            "attached_to_doctype": "Task Submission",
            "attached_to_name": doc.name,
            "file_name": filename,
            "content": content,
            "is_private": 1,
        },
        classification={
            "primary_subject_type": "Student",
            "primary_subject_id": doc.student,
            "data_class": "academic",
            "purpose": "assessment_submission",
            "retention_policy": "until_program_end_plus_1y",
            "slot": "submission",
            "organization": organization,
            "school": doc.school,
            "upload_source": "Desk",
        },
    )
    _ensure_file_on_disk(file_doc)

    doc.append(
        "attachments",
        {
            "section_break_sbex": file_doc.file_name,
            "file": file_doc.file_url,
            "file_name": file_doc.file_name,
            "file_size": file_doc.file_size,
            "public": 0,
        },
    )
    doc.save(ignore_permissions=True)

    return _response_payload(file_doc)


@frappe.whitelist()
def upload_school_logo(school: str | None = None, **_kwargs):
    school = school or _get_form_arg("school") or frappe.form_dict.get("docname")
    doc = _require_clean_saved_doc(_require_doc("School", school), action_label=_("Upload School Logo"))
    if not doc.organization:
        frappe.throw(_("Organization is required before uploading a school logo."))

    filename, content = _get_uploaded_file()
    slot = build_school_logo_slot(school=doc.name)
    file_doc = _upload_organization_media_file(
        organization=doc.organization,
        school=doc.name,
        slot=slot,
        filename=filename,
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

    target_row = None
    if row_name:
        for row in doc.gallery_image or []:
            if row.name == row_name:
                target_row = row
                break
        if not target_row:
            frappe.throw(_("Gallery row '{0}' was not found on School '{1}'.").format(row_name, doc.name))
    else:
        target_row = doc.append("gallery_image", {})
        if not target_row.name:
            target_row.name = frappe.generate_hash(length=10)
        if caption:
            target_row.caption = caption

    slot = build_school_gallery_slot(row_name=target_row.name)
    file_doc = _upload_organization_media_file(
        organization=doc.organization,
        school=doc.name,
        slot=slot,
        filename=filename,
        content=content,
    )
    _ensure_file_on_disk(file_doc)

    target_row.governed_file = file_doc.name
    target_row.school_image = file_doc.file_url
    if caption:
        target_row.caption = caption
    doc.save(ignore_permissions=True)

    payload = _response_payload(file_doc)
    payload["school"] = doc.name
    payload["row_name"] = target_row.name
    payload["caption"] = target_row.caption
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
    file_doc = _upload_organization_media_file(
        organization=organization,
        school=school,
        slot=slot,
        filename=filename,
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
    slot = build_organization_logo_slot(organization=doc.name)
    file_doc = _upload_organization_media_file(
        organization=doc.name,
        school=None,
        slot=slot,
        filename=filename,
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

    classification = frappe.db.get_value("File Classification", {"file": file_name}, "name")
    return {
        "has_file": 1,
        "file": file_name,
        "classification": classification,
        "governed": 1 if classification else 0,
    }


@frappe.whitelist()
def get_employee_image_variants(employee: str):
    if not employee:
        frappe.throw(_("employee is required."))

    doc = frappe.get_doc("Employee", employee)
    doc.check_permission("read")

    slots = [
        "profile_image_thumb",
        "profile_image_card",
        "profile_image_medium",
        "profile_image",
    ]

    rows = frappe.get_all(
        "File Classification",
        filters={
            "primary_subject_type": "Employee",
            "primary_subject_id": doc.name,
            "slot": ("in", slots),
            "is_current_version": 1,
        },
        fields=["slot", "file"],
    )
    if not rows:
        return {}

    file_names = [row["file"] for row in rows if row.get("file")]
    if not file_names:
        return {}

    files = frappe.get_all(
        "File",
        filters={"name": ("in", file_names)},
        fields=["name", "file_url", "is_private"],
    )
    file_map = {row["name"]: row for row in files}

    variants = {}
    for row in rows:
        slot = row.get("slot")
        file_name = row.get("file")
        if not (slot and file_name):
            continue

        file_row = file_map.get(file_name)
        if not file_row:
            continue

        file_url = (file_row.get("file_url") or "").strip()
        if not file_url:
            continue

        if not _file_url_exists_on_disk(file_url, file_row.get("is_private")):
            continue

        variants[slot] = file_url

    return variants
