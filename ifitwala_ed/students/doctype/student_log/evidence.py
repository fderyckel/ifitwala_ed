from __future__ import annotations

import importlib
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from ifitwala_ed.api.attachment_previews import (
    build_attachment_preview_item,
    extract_file_extension,
    preview_status_allows_preview,
)

STUDENT_LOG_EVIDENCE_BINDING_ROLE = "student_log_evidence"
STUDENT_LOG_EVIDENCE_DATA_CLASS = "safeguarding"
STUDENT_LOG_EVIDENCE_PURPOSE = "safeguarding_evidence"
STUDENT_LOG_EVIDENCE_RETENTION_POLICY = "fixed_7y"
STUDENT_LOG_EVIDENCE_SLOT_PREFIX = "student_log_evidence__"
STUDENT_LOG_EVIDENCE_CATEGORY = "Student Log Evidence"
STUDENT_LOG_EVIDENCE_TABLE_FIELD = "evidence_attachments"
STUDENT_LOG_EVIDENCE_CHILD_DOCTYPE = "Student Log Evidence Attachment"
STUDENT_LOG_DOCTYPE = "Student Log"

_UPLOAD_ADMIN_ROLES = {"Academic Admin", "System Manager", "Administrator"}


def _refresh_runtime_bindings():
    global frappe

    current_frappe = importlib.import_module("frappe")
    bound_is_stub = getattr(frappe, "__file__", None) is None
    current_is_real = getattr(current_frappe, "__file__", None) is not None

    if not bound_is_stub or not current_is_real or current_frappe is frappe:
        return frappe

    frappe = current_frappe
    return frappe


def _field_value(source: Any, fieldname: str):
    getter = getattr(source, "get", None)
    if callable(getter):
        return getter(fieldname)
    return getattr(source, fieldname, None)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_row_key(value: str | None) -> str:
    _refresh_runtime_bindings()

    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip()).strip("-_")
    if normalized:
        return normalized
    return frappe.generate_hash(length=10)


def parse_student_log_evidence_row_key(slot: str | None) -> str | None:
    resolved_slot = str(slot or "").strip()
    if not resolved_slot.startswith(STUDENT_LOG_EVIDENCE_SLOT_PREFIX):
        return None
    row_key = resolved_slot.split(STUDENT_LOG_EVIDENCE_SLOT_PREFIX, 1)[1].strip()
    return row_key or None


def _get_student_log_doc(name: str, *, permission_type: str | None = None):
    _refresh_runtime_bindings()

    resolved_name = str(name or "").strip()
    if not resolved_name:
        frappe.throw(_("Student Log is required."))
    if not frappe.db.exists(STUDENT_LOG_DOCTYPE, resolved_name):
        frappe.throw(
            _("Student Log does not exist: {student_log}").format(student_log=resolved_name), frappe.DoesNotExistError
        )

    doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, resolved_name)
    if permission_type:
        doc.check_permission(permission_type)
    return doc


def _find_evidence_row(doc, row_name: str):
    resolved_row_name = str(row_name or "").strip()
    if not resolved_row_name:
        frappe.throw(_("Evidence row name is required."), frappe.ValidationError)

    for row in doc.get(STUDENT_LOG_EVIDENCE_TABLE_FIELD) or []:
        if str(getattr(row, "name", "") or "").strip() != resolved_row_name:
            continue
        if cint(getattr(row, "is_removed", 0) or 0):
            break
        return row

    frappe.throw(
        _("Evidence attachment row was not found: {row_name}.").format(row_name=resolved_row_name),
        frappe.DoesNotExistError,
    )


def _has_open_follow_up_todo(log_name: str, user: str) -> bool:
    return bool(
        frappe.db.exists(
            "ToDo",
            {
                "reference_type": STUDENT_LOG_DOCTYPE,
                "reference_name": log_name,
                "allocated_to": user,
                "status": "Open",
            },
        )
    )


def _has_student_log_upload_access(doc, user: str) -> bool:
    roles = set(frappe.get_roles(user) or [])
    if roles & _UPLOAD_ADMIN_ROLES:
        return True
    if str(getattr(doc, "owner", "") or "").strip() == user:
        return True
    if str(getattr(doc, "follow_up_person", "") or "").strip() == user:
        return True
    if _has_open_follow_up_todo(doc.name, user):
        return True

    return bool(frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="write", doc=doc, user=user))


def assert_student_log_attachment_upload_access(
    student_log: str,
    *,
    permission_type: str = "write",
):
    _refresh_runtime_bindings()

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be signed in to attach Student Log evidence."), frappe.PermissionError)

    doc = _get_student_log_doc(student_log)
    if cint(getattr(doc, "docstatus", 0) or 0) == 2:
        frappe.throw(_("Cancelled Student Logs cannot accept evidence attachments."), frappe.ValidationError)
    if str(getattr(doc, "follow_up_status", "") or "").strip().lower() == "completed":
        frappe.throw(_("Completed Student Logs cannot accept new evidence attachments."), frappe.ValidationError)
    if not _has_student_log_upload_access(doc, user):
        frappe.throw(_("You do not have permission to attach evidence to this Student Log."), frappe.PermissionError)
    if permission_type and permission_type != "read":
        return doc
    return doc


def _current_student_for_user(user: str) -> str | None:
    resolved_user = str(user or "").strip()
    if not resolved_user or resolved_user == "Guest":
        return None
    user_email = frappe.db.get_value("User", resolved_user, "email") or resolved_user
    return _clean_text(frappe.db.get_value("Student", {"student_email": user_email}, "name"))


def _guardian_students_for_user(user: str) -> set[str]:
    try:
        from ifitwala_ed.api.guardian_home import _resolve_guardian_scope

        _guardian_name, children = _resolve_guardian_scope(user)
    except frappe.PermissionError:
        return set()

    return {child.get("student") for child in children or [] if child.get("student")}


def _user_can_read_evidence_row(doc, row, user: str) -> bool:
    if frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=doc, user=user):
        return True

    current_student = _current_student_for_user(user)
    if (
        current_student
        and current_student == getattr(doc, "student", None)
        and cint(getattr(doc, "visible_to_student", 0) or 0)
        and cint(_field_value(row, "visible_to_student") or 0)
    ):
        return True

    if (
        getattr(doc, "student", None) in _guardian_students_for_user(user)
        and cint(getattr(doc, "visible_to_guardians", 0) or 0)
        and cint(_field_value(row, "visible_to_guardians") or 0)
    ):
        return True

    return False


def assert_student_log_attachment_read_access(student_log: str, row_name: str) -> dict[str, Any]:
    _refresh_runtime_bindings()

    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("You must be signed in to view this evidence attachment."), frappe.PermissionError)

    doc = _get_student_log_doc(student_log)
    target_row = _find_evidence_row(doc, row_name)
    if not _user_can_read_evidence_row(doc, target_row, user):
        frappe.throw(_("You do not have permission to access this evidence attachment."), frappe.PermissionError)

    if _clean_text(_field_value(target_row, "external_url")):
        return {
            "student_log": doc.name,
            "row_name": str(row_name or "").strip(),
            "row": target_row,
            "log": doc,
        }

    if not _clean_text(_field_value(target_row, "file")):
        frappe.throw(_("Evidence attachment file is missing."), frappe.DoesNotExistError)

    drive_file_id, file_id = resolve_student_log_evidence_drive_file(doc.name, row_name)
    return {
        "student_log": doc.name,
        "row_name": str(row_name or "").strip(),
        "drive_file_id": drive_file_id,
        "file_id": file_id,
        "row": target_row,
        "log": doc,
    }


def build_student_log_evidence_upload_contract(
    doc,
    *,
    row_name: str | None = None,
) -> dict[str, Any]:
    if getattr(doc, "is_new", lambda: False)():
        frappe.throw(_("Save the Student Log before attaching governed evidence."))

    student = _clean_text(getattr(doc, "student", None))
    school = _clean_text(getattr(doc, "school", None))
    if not student:
        frappe.throw(_("Student Log evidence requires a student."))
    if not school:
        frappe.throw(_("Student Log evidence requires a school."))

    organization = _clean_text(frappe.db.get_value("School", school, "organization"))
    if not organization:
        frappe.throw(_("Student Log evidence requires an organization."))

    row_key = _normalize_row_key(row_name)
    return {
        "owner_doctype": STUDENT_LOG_DOCTYPE,
        "owner_name": doc.name,
        "attached_doctype": STUDENT_LOG_DOCTYPE,
        "attached_name": doc.name,
        "organization": organization,
        "school": school,
        "primary_subject_type": "Student",
        "primary_subject_id": student,
        "data_class": STUDENT_LOG_EVIDENCE_DATA_CLASS,
        "purpose": STUDENT_LOG_EVIDENCE_PURPOSE,
        "retention_policy": STUDENT_LOG_EVIDENCE_RETENTION_POLICY,
        "slot": f"{STUDENT_LOG_EVIDENCE_SLOT_PREFIX}{row_key}",
        "row_name": row_key,
    }


def validate_student_log_evidence_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != STUDENT_LOG_DOCTYPE:
        return None

    row_key = parse_student_log_evidence_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        frappe.throw(_("Student Log upload sessions require a student-log-evidence slot."))

    doc = assert_student_log_attachment_upload_access(upload_session_doc.owner_name, permission_type="write")
    authoritative = build_student_log_evidence_upload_contract(doc, row_name=row_key)
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
        if getattr(upload_session_doc, session_field, None) != authoritative[authoritative_field]:
            frappe.throw(
                _(
                    "Upload session no longer matches the authoritative Student Log evidence context for field '{fieldname}'."
                ).format(fieldname=session_field)
            )

    return authoritative


def get_student_log_evidence_context_override(owner_name: str | None, slot: str | None) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists(STUDENT_LOG_DOCTYPE, owner_name):
        return None

    doc = _get_student_log_doc(owner_name)
    authoritative = build_student_log_evidence_upload_contract(
        doc,
        row_name=parse_student_log_evidence_row_key(slot) or None,
    )
    return {
        "root_folder": "Home/Students",
        "subfolder": f"{authoritative['primary_subject_id']}/Student Logs/{doc.name}/Evidence",
        "file_category": STUDENT_LOG_EVIDENCE_CATEGORY,
        "logical_key": str(slot or "").strip() or f"student_log_evidence_{doc.name}",
    }


def run_student_log_evidence_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    if getattr(upload_session_doc, "owner_doctype", None) != STUDENT_LOG_DOCTYPE:
        return {}

    row_key = parse_student_log_evidence_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        return {}

    doc = frappe.get_doc(STUDENT_LOG_DOCTYPE, upload_session_doc.owner_name)
    target_row = None
    for row in doc.get(STUDENT_LOG_EVIDENCE_TABLE_FIELD) or []:
        if str(getattr(row, "name", "") or "").strip() == row_key:
            target_row = row
            break

    if not target_row:
        target_row = doc.append(STUDENT_LOG_EVIDENCE_TABLE_FIELD, {})
        target_row.name = row_key

    file_url = getattr(created_file, "file_url", None) or frappe.db.get_value("File", created_file.name, "file_url")
    file_name = getattr(created_file, "file_name", None) or frappe.db.get_value("File", created_file.name, "file_name")
    file_size = getattr(created_file, "file_size", None) or frappe.db.get_value("File", created_file.name, "file_size")

    if not getattr(target_row, "title", None):
        target_row.title = file_name or _("Evidence attachment")
    target_row.file = file_url
    target_row.file_name = file_name
    target_row.file_size = file_size
    target_row.external_url = None
    target_row.uploaded_by = getattr(upload_session_doc, "owner", None) or frappe.session.user
    target_row.uploaded_on = now_datetime()
    target_row.is_removed = 0
    doc.save(ignore_permissions=True)

    return {
        "row_name": row_key,
        "file_url": file_url,
    }


def _attachment_slot(row_name: str) -> str:
    return f"{STUDENT_LOG_EVIDENCE_SLOT_PREFIX}{str(row_name or '').strip()}"


def resolve_student_log_evidence_drive_file(student_log: str, row_name: str) -> tuple[str, str | None]:
    row_slot = _attachment_slot(row_name)
    drive_file = frappe.db.get_value(
        "Drive Binding",
        {
            "binding_doctype": STUDENT_LOG_DOCTYPE,
            "binding_name": student_log,
            "binding_role": STUDENT_LOG_EVIDENCE_BINDING_ROLE,
            "slot": row_slot,
            "status": "active",
        },
        ["drive_file", "file"],
        as_dict=True,
    )
    if drive_file and drive_file.get("drive_file"):
        return drive_file.get("drive_file"), (drive_file.get("file") or "").strip() or None

    drive_file = frappe.db.get_value(
        "Drive File",
        {
            "owner_doctype": STUDENT_LOG_DOCTYPE,
            "owner_name": student_log,
            "slot": row_slot,
            "status": "active",
        },
        ["name", "file"],
        as_dict=True,
    )
    if drive_file and drive_file.get("name"):
        return drive_file.get("name"), (drive_file.get("file") or "").strip() or None

    frappe.throw(_("Governed evidence file was not found."), frappe.DoesNotExistError)


def _get_evidence_preview_meta(student_log: str, row_name: str) -> dict[str, Any]:
    try:
        drive_file_id, file_id = resolve_student_log_evidence_drive_file(student_log, row_name)
    except frappe.DoesNotExistError:
        return {"preview_status": None, "inline_preview_ready": False}

    drive_file = (
        frappe.db.get_value(
            "Drive File",
            drive_file_id,
            ["preview_status", "current_version"],
            as_dict=True,
        )
        or {}
    )
    preview_status = _clean_text(drive_file.get("preview_status"))
    return {
        "drive_file_id": drive_file_id,
        "file_id": file_id,
        "preview_status": preview_status,
        "inline_preview_ready": preview_status == "ready",
    }


def serialize_student_log_evidence_row(student_log: str, row) -> dict[str, Any]:
    row_name = str(_field_value(row, "name") or "").strip()
    file_url = str(_field_value(row, "file") or "").strip()
    external_url = str(_field_value(row, "external_url") or "").strip()
    title = _clean_text(_field_value(row, "title"))
    description = _clean_text(_field_value(row, "description"))
    file_name = _clean_text(_field_value(row, "file_name"))
    file_size = _field_value(row, "file_size")

    if not title:
        title = file_name or external_url or row_name or _("Evidence attachment")

    if file_url and not file_name:
        file_name = frappe.db.get_value(
            "File",
            {
                "attached_to_doctype": STUDENT_LOG_DOCTYPE,
                "attached_to_name": student_log,
                "file_url": file_url,
            },
            "file_name",
        )

    if file_url:
        from ifitwala_ed.api import file_access as file_access_api

        preview_meta = _get_evidence_preview_meta(student_log, row_name)
        preview_status = preview_meta.get("preview_status")
        open_url = file_access_api.build_student_log_evidence_attachment_open_url(
            student_log=student_log,
            row_name=row_name,
        )
        preview_url = file_access_api.build_student_log_evidence_attachment_preview_url(
            student_log=student_log,
            row_name=row_name,
        )
        if not preview_status_allows_preview(preview_status):
            preview_url = None
        thumbnail_url = (
            file_access_api.build_student_log_evidence_attachment_thumbnail_url(
                student_log=student_log,
                row_name=row_name,
            )
            if preview_meta.get("inline_preview_ready")
            else None
        )
        attachment_preview = build_attachment_preview_item(
            item_id=row_name,
            owner_doctype=STUDENT_LOG_DOCTYPE,
            owner_name=student_log,
            display_name=title,
            description=description,
            extension=extract_file_extension(file_name=file_name, file_url=file_url),
            size_bytes=file_size,
            preview_status=preview_status,
            thumbnail_url=thumbnail_url,
            preview_url=preview_url,
            open_url=open_url,
            download_url=open_url,
            source_label=_("Evidence"),
        )
        return {
            "row_name": row_name,
            "kind": "file",
            "title": title,
            "description": description,
            "file_name": file_name or title,
            "file_size": file_size,
            "visible_to_student": bool(cint(_field_value(row, "visible_to_student") or 0)),
            "visible_to_guardians": bool(cint(_field_value(row, "visible_to_guardians") or 0)),
            "preview_status": preview_status,
            "thumbnail_url": thumbnail_url,
            "preview_url": preview_url,
            "open_url": open_url,
            "attachment_preview": attachment_preview,
        }

    attachment_preview = build_attachment_preview_item(
        item_id=row_name,
        owner_doctype=STUDENT_LOG_DOCTYPE,
        owner_name=student_log,
        link_url=external_url,
        display_name=title,
        description=description,
        open_url=external_url,
        source_label=_("Evidence"),
    )
    return {
        "row_name": row_name,
        "kind": "link",
        "title": title,
        "description": description,
        "external_url": external_url or None,
        "visible_to_student": bool(cint(_field_value(row, "visible_to_student") or 0)),
        "visible_to_guardians": bool(cint(_field_value(row, "visible_to_guardians") or 0)),
        "open_url": external_url or None,
        "attachment_preview": attachment_preview,
    }


def _visible_row_for_audience(doc, row, audience: str) -> bool:
    if cint(_field_value(row, "is_removed") or 0):
        return False
    if not (_clean_text(_field_value(row, "file")) or _clean_text(_field_value(row, "external_url"))):
        return False
    if audience == "student":
        return bool(
            cint(getattr(doc, "visible_to_student", 0) or 0) and cint(_field_value(row, "visible_to_student") or 0)
        )
    if audience == "guardian":
        return bool(
            cint(getattr(doc, "visible_to_guardians", 0) or 0) and cint(_field_value(row, "visible_to_guardians") or 0)
        )
    return True


def get_visible_student_log_evidence_attachments(student_log: str, *, audience: str = "staff") -> list[dict[str, Any]]:
    doc = _get_student_log_doc(student_log)
    resolved_audience = str(audience or "staff").strip().lower()

    user = frappe.session.user
    if resolved_audience == "student":
        current_student = _current_student_for_user(user)
        if current_student != getattr(doc, "student", None) or not cint(getattr(doc, "visible_to_student", 0) or 0):
            frappe.throw(_("You do not have permission to view this Student Log."), frappe.PermissionError)
    elif resolved_audience == "guardian":
        if getattr(doc, "student", None) not in _guardian_students_for_user(user) or not cint(
            getattr(doc, "visible_to_guardians", 0) or 0
        ):
            frappe.throw(_("You do not have permission to view this Student Log."), frappe.PermissionError)
    elif not frappe.has_permission(STUDENT_LOG_DOCTYPE, ptype="read", doc=doc, user=user):
        frappe.throw(_("You do not have permission to view this Student Log."), frappe.PermissionError)

    return [
        serialize_student_log_evidence_row(doc.name, row)
        for row in doc.get(STUDENT_LOG_EVIDENCE_TABLE_FIELD) or []
        if _visible_row_for_audience(doc, row, resolved_audience)
    ]


def get_student_log_evidence_count_map(log_names: list[str], *, audience: str) -> dict[str, int]:
    names = [str(name or "").strip() for name in log_names or [] if str(name or "").strip()]
    if not names:
        return {}

    resolved_audience = str(audience or "staff").strip().lower()
    visibility_sql = ""
    if resolved_audience == "student":
        visibility_sql = "AND IFNULL(visible_to_student, 0) = 1"
    elif resolved_audience == "guardian":
        visibility_sql = "AND IFNULL(visible_to_guardians, 0) = 1"

    rows = frappe.db.sql(
        f"""
        SELECT parent, COUNT(*) AS attachment_count
        FROM `tabStudent Log Evidence Attachment`
        WHERE parenttype = 'Student Log'
          AND parentfield = 'evidence_attachments'
          AND parent IN %(parents)s
          AND IFNULL(is_removed, 0) = 0
          AND (IFNULL(file, '') != '' OR IFNULL(external_url, '') != '')
          {visibility_sql}
        GROUP BY parent
        """,
        {"parents": tuple(names)},
        as_dict=True,
    )
    return {row.get("parent"): cint(row.get("attachment_count") or 0) for row in rows if row.get("parent")}


def get_student_log_evidence_map(log_names: list[str], *, audience: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for log_name in [str(name or "").strip() for name in log_names or [] if str(name or "").strip()]:
        result[log_name] = get_visible_student_log_evidence_attachments(log_name, audience=audience)
    return result
