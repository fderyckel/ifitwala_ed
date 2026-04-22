from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_PROFILE_IMAGE_SLOT = "profile_image"


def _require_doc(doctype: str, name: str, *, permission_type: str | None = "write"):
    if not name or not frappe.db.exists(doctype, name):
        frappe.throw(_("{doctype} does not exist: {name}").format(doctype=doctype, name=name))

    doc = frappe.get_doc(doctype, name)
    if permission_type:
        doc.check_permission(permission_type)
    return doc


def _get_org_from_school(school: str) -> str:
    organization = frappe.db.get_value("School", school, "organization")
    if not organization:
        frappe.throw(_("Organization is required for file classification."))
    return organization


def build_employee_image_contract(employee_doc) -> dict[str, Any]:
    if not getattr(employee_doc, "organization", None):
        frappe.throw(_("Organization is required for file classification."))

    return {
        "owner_doctype": "Employee",
        "owner_name": employee_doc.name,
        "attached_doctype": "Employee",
        "attached_name": employee_doc.name,
        "organization": employee_doc.organization,
        "school": getattr(employee_doc, "school", None),
        "primary_subject_type": "Employee",
        "primary_subject_id": employee_doc.name,
        "data_class": "identity_image",
        "purpose": "employee_profile_display",
        "retention_policy": "employment_duration_plus_grace",
        "slot": _PROFILE_IMAGE_SLOT,
    }


def assert_employee_image_read_access(employee: str, *, file_name: str) -> dict[str, Any]:
    from ifitwala_ed.api.file_access import (
        _require_authenticated_user,
        _resolve_employee_profile_image_access,
    )

    resolved_employee = str(employee or "").strip()
    resolved_file_name = str(file_name or "").strip()
    if not resolved_employee:
        frappe.throw(_("Employee is required."), frappe.ValidationError)
    if not resolved_file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    user = _require_authenticated_user()
    context = _resolve_employee_profile_image_access(
        user=user,
        file_name=resolved_file_name,
        context_doctype="Employee",
        context_name=resolved_employee,
        strict=True,
    )
    return {
        "employee": context["file_employee"],
        "file_id": str((context.get("file_row") or {}).get("name") or resolved_file_name).strip(),
        "drive_file_id": context["drive_file_id"],
    }


def assert_student_image_read_access(student: str, *, file_name: str) -> dict[str, Any]:
    from ifitwala_ed.api.file_access import (
        _require_authenticated_user,
        _resolve_student_profile_image_access,
    )

    resolved_student = str(student or "").strip()
    resolved_file_name = str(file_name or "").strip()
    if not resolved_student:
        frappe.throw(_("Student is required."), frappe.ValidationError)
    if not resolved_file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    user = _require_authenticated_user()
    context = _resolve_student_profile_image_access(
        user=user,
        file_name=resolved_file_name,
        context_doctype="Student",
        context_name=resolved_student,
        strict=True,
    )
    return {
        "student": context["file_student"],
        "school": context.get("school"),
        "file_id": str((context.get("file_row") or {}).get("name") or resolved_file_name).strip(),
        "drive_file_id": context["drive_file_id"],
    }


def build_student_image_contract(student_doc) -> dict[str, Any]:
    school = getattr(student_doc, "anchor_school", None)
    if not school:
        frappe.throw(_("Anchor School is required before uploading a student image."))

    return {
        "owner_doctype": "Student",
        "owner_name": student_doc.name,
        "attached_doctype": "Student",
        "attached_name": student_doc.name,
        "organization": _get_org_from_school(school),
        "school": school,
        "primary_subject_type": "Student",
        "primary_subject_id": student_doc.name,
        "data_class": "identity_image",
        "purpose": "student_profile_display",
        "retention_policy": "until_school_exit_plus_6m",
        "slot": _PROFILE_IMAGE_SLOT,
    }


def build_guardian_image_contract(guardian_doc) -> dict[str, Any]:
    if hasattr(guardian_doc, "resolve_profile_image_organization"):
        organization = guardian_doc.resolve_profile_image_organization()
    else:
        organization = getattr(guardian_doc, "organization", None)
    if not organization:
        frappe.throw(_("Guardian organization is required before uploading a guardian image."))

    return {
        "owner_doctype": "Guardian",
        "owner_name": guardian_doc.name,
        "attached_doctype": "Guardian",
        "attached_name": guardian_doc.name,
        "organization": organization,
        "school": None,
        "primary_subject_type": "Guardian",
        "primary_subject_id": guardian_doc.name,
        "data_class": "identity_image",
        "purpose": "guardian_profile_display",
        "retention_policy": "until_school_exit_plus_6m",
        "slot": _PROFILE_IMAGE_SLOT,
    }


def assert_guardian_image_read_access(guardian: str, *, file_name: str) -> dict[str, Any]:
    from ifitwala_ed.api.file_access import (
        _require_authenticated_user,
        _resolve_guardian_profile_image_access,
    )

    resolved_guardian = str(guardian or "").strip()
    resolved_file_name = str(file_name or "").strip()
    if not resolved_guardian:
        frappe.throw(_("Guardian is required."), frappe.ValidationError)
    if not resolved_file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    user = _require_authenticated_user()
    context = _resolve_guardian_profile_image_access(
        user=user,
        file_name=resolved_file_name,
        context_doctype="Guardian",
        context_name=resolved_guardian,
        strict=True,
    )
    return {
        "guardian": context["file_guardian"],
        "file_id": str((context.get("file_row") or {}).get("name") or resolved_file_name).strip(),
        "drive_file_id": context["drive_file_id"],
    }


def assert_public_website_media_read_access(*, file_name: str) -> dict[str, Any]:
    from ifitwala_ed.api.file_access import (
        _assert_public_website_media_visible,
        _resolve_public_website_media_row,
    )

    resolved_file_name = str(file_name or "").strip()
    if not resolved_file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_public_website_media_row(resolved_file_name)
    _assert_public_website_media_visible(file_row)

    drive_file_id = str((file_row or {}).get("drive_file_id") or "").strip()
    if not drive_file_id:
        frappe.throw(_("Governed public website media file was not found."))

    return {
        "file_id": str((file_row.get("name") or resolved_file_name) or "").strip(),
        "drive_file_id": drive_file_id,
        "organization": str((file_row.get("organization") or "")).strip(),
        "school": str((file_row.get("school") or "")).strip() or None,
    }


def assert_public_employee_image_read_access(employee: str, *, file_name: str) -> dict[str, Any]:
    from ifitwala_ed.api.file_access import _resolve_public_employee_image_row

    resolved_employee = str(employee or "").strip()
    resolved_file_name = str(file_name or "").strip()
    if not resolved_employee:
        frappe.throw(_("Employee is required."), frappe.ValidationError)
    if not resolved_file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_public_employee_image_row(
        employee=resolved_employee,
        file_name=resolved_file_name,
    )
    drive_file_id = str((file_row or {}).get("drive_file_id") or "").strip()
    if not drive_file_id:
        frappe.throw(_("Governed public employee photo file was not found."))

    return {
        "employee": resolved_employee,
        "file_id": str((file_row.get("name") or resolved_file_name) or "").strip(),
        "drive_file_id": drive_file_id,
        "organization": str((file_row.get("organization") or "")).strip() or None,
        "school": str((file_row.get("school") or "")).strip() or None,
    }


def build_organization_media_contract(
    *,
    organization: str,
    slot: str,
    school: str | None = None,
    upload_source: str,
) -> dict[str, Any]:
    from ifitwala_ed.utilities.organization_media import build_organization_media_classification

    classification = build_organization_media_classification(
        organization=organization,
        school=school,
        slot=slot,
        upload_source=upload_source,
    )

    return {
        "owner_doctype": "Organization",
        "owner_name": organization,
        "attached_doctype": "Organization",
        "attached_name": organization,
        "organization": organization,
        "school": school,
        "primary_subject_type": classification["primary_subject_type"],
        "primary_subject_id": classification["primary_subject_id"],
        "data_class": classification["data_class"],
        "purpose": classification["purpose"],
        "retention_policy": classification["retention_policy"],
        "slot": classification["slot"],
    }


def get_attached_field_override(upload_session_doc) -> str | None:
    if upload_session_doc.owner_doctype == "Employee" and upload_session_doc.intended_slot == _PROFILE_IMAGE_SLOT:
        return "employee_image"
    if upload_session_doc.owner_doctype == "Guardian" and upload_session_doc.intended_slot == _PROFILE_IMAGE_SLOT:
        return "guardian_image"
    if upload_session_doc.owner_doctype == "Student" and upload_session_doc.intended_slot == _PROFILE_IMAGE_SLOT:
        return "student_image"
    return None


def validate_media_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    owner_doctype = getattr(upload_session_doc, "owner_doctype", None)
    if owner_doctype == "Employee":
        doc = _require_doc("Employee", upload_session_doc.owner_name)
        authoritative = build_employee_image_contract(doc)
    elif owner_doctype == "Guardian":
        doc = _require_doc("Guardian", upload_session_doc.owner_name)
        authoritative = build_guardian_image_contract(doc)
    elif owner_doctype == "Student":
        doc = _require_doc("Student", upload_session_doc.owner_name)
        authoritative = build_student_image_contract(doc)
    elif owner_doctype == "Organization":
        school = getattr(upload_session_doc, "school", None)
        slot = getattr(upload_session_doc, "intended_slot", None)
        if school:
            _require_doc("School", school)
        else:
            _require_doc("Organization", upload_session_doc.owner_name)
        authoritative = build_organization_media_contract(
            organization=upload_session_doc.owner_name,
            slot=slot,
            school=school,
            upload_source=upload_session_doc.upload_source,
        )
    else:
        return None

    field_map = {
        "owner_doctype": "owner_doctype",
        "owner_name": "owner_name",
        "attached_doctype": "attached_doctype",
        "attached_name": "attached_name",
        "organization": "organization",
        "school": "school",
        "intended_primary_subject_type": "primary_subject_type",
        "intended_primary_subject_id": "primary_subject_id",
        "intended_data_class": "data_class",
        "intended_purpose": "purpose",
        "intended_retention_policy": "retention_policy",
        "intended_slot": "slot",
    }
    for session_field, authoritative_field in field_map.items():
        if getattr(upload_session_doc, session_field, None) != authoritative.get(authoritative_field):
            frappe.throw(
                _("Upload session no longer matches the authoritative media context for field '{field_name}'.").format(
                    field_name=session_field
                )
            )

    return authoritative


def run_media_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    file_url = getattr(created_file, "file_url", None) or frappe.db.get_value("File", created_file.name, "file_url")
    slot = upload_session_doc.intended_slot or ""

    if upload_session_doc.owner_doctype == "Employee":
        frappe.db.set_value(
            "Employee",
            upload_session_doc.owner_name,
            "employee_image",
            file_url,
            update_modified=False,
        )
        return {"file_url": file_url}

    if upload_session_doc.owner_doctype == "Student":
        student_doc = frappe.get_doc("Student", upload_session_doc.owner_name)
        frappe.db.set_value(
            "Student",
            student_doc.name,
            "student_image",
            file_url,
            update_modified=False,
        )
        student_doc.student_image = file_url
        if hasattr(student_doc, "sync_student_contact_image"):
            student_doc.sync_student_contact_image()
        return {"file_url": file_url}

    if upload_session_doc.owner_doctype == "Guardian":
        frappe.db.set_value(
            "Guardian",
            upload_session_doc.owner_name,
            {
                "guardian_image": file_url,
                "organization": upload_session_doc.organization,
            },
            update_modified=False,
        )
        return {"file_url": file_url}

    if upload_session_doc.owner_doctype != "Organization":
        return {}

    if slot.startswith("organization_logo__"):
        frappe.db.set_value(
            "Organization",
            upload_session_doc.owner_name,
            {
                "organization_logo": file_url,
                "organization_logo_file": created_file.name,
            },
            update_modified=False,
        )
        return {"file_url": file_url}

    if getattr(upload_session_doc, "school", None) and slot.startswith("school_logo__"):
        frappe.db.set_value(
            "School",
            upload_session_doc.school,
            {
                "school_logo": file_url,
                "school_logo_file": created_file.name,
            },
            update_modified=False,
        )
        return {"file_url": file_url}

    if getattr(upload_session_doc, "school", None) and slot.startswith("school_gallery_image__"):
        row_name = slot.split("school_gallery_image__", 1)[1]
        school_doc = frappe.get_doc("School", upload_session_doc.school)
        target_row = None
        for row in school_doc.gallery_image or []:
            if row.name == row_name:
                target_row = row
                break
        if not target_row:
            frappe.throw(
                _("Gallery row '{row_name}' was not found on School '{school_name}'.").format(
                    row_name=row_name,
                    school_name=school_doc.name,
                )
            )
        target_row.governed_file = created_file.name
        target_row.school_image = file_url
        school_doc.save(ignore_permissions=True)
        return {"file_url": file_url, "row_name": row_name}

    return {"file_url": file_url}
