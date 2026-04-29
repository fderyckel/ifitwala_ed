from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.students.doctype.student_log.evidence import (
    STUDENT_LOG_EVIDENCE_BINDING_ROLE,
    STUDENT_LOG_EVIDENCE_SLOT_PREFIX,
    STUDENT_LOG_EVIDENCE_TABLE_FIELD,
    assert_student_log_attachment_upload_access,
    get_visible_student_log_evidence_attachments,
    serialize_student_log_evidence_row,
)
from ifitwala_ed.utilities.governed_uploads import (
    _drive_upload_and_finalize,
    _get_uploaded_file,
    _resolve_upload_mime_type_hint,
    _workflow_result_payload,
)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _truthy(value: Any) -> int:
    return 1 if cint(value or 0) else 0


def _load_drive_callable(attribute: str):
    try:
        from ifitwala_drive.api import student_logs as drive_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for Student Log evidence attachments: {error}").format(error=exc))

    callable_obj = getattr(drive_api, attribute, None)
    if callable(callable_obj):
        return callable_obj

    frappe.throw(
        _(
            "Ifitwala Drive is missing public Student Log method '{method}'. Deploy the matching Drive API before using governed Student Log evidence."
        ).format(method=attribute)
    )


def _get_evidence_row(doc, row_name: str):
    resolved_row_name = str(row_name or "").strip()
    if not resolved_row_name:
        frappe.throw(_("Evidence row name is required."))

    for row in doc.get(STUDENT_LOG_EVIDENCE_TABLE_FIELD) or []:
        if str(getattr(row, "name", "") or "").strip() == resolved_row_name:
            return row

    frappe.throw(
        _("Evidence row was not found: {row_name}").format(row_name=resolved_row_name),
        frappe.DoesNotExistError,
    )


def _set_row_metadata(
    doc,
    row,
    *,
    title: str | None = None,
    description: str | None = None,
    visible_to_student: Any = None,
    visible_to_guardians: Any = None,
) -> bool:
    changed = False
    resolved_title = _clean_text(title)
    resolved_description = _clean_text(description)
    if resolved_title and getattr(row, "title", None) != resolved_title:
        row.title = resolved_title
        changed = True
    if resolved_description is not None and getattr(row, "description", None) != resolved_description:
        row.description = resolved_description
        changed = True
    if visible_to_student is not None:
        value = _truthy(visible_to_student)
        if cint(getattr(row, "visible_to_student", 0) or 0) != value:
            row.visible_to_student = value
            changed = True
    if visible_to_guardians is not None:
        value = _truthy(visible_to_guardians)
        if cint(getattr(row, "visible_to_guardians", 0) or 0) != value:
            row.visible_to_guardians = value
            changed = True
    if changed:
        doc.save(ignore_permissions=True)
    return changed


@frappe.whitelist()
def get_student_log_attachments(
    student_log: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    resolved_student_log = str(student_log or "").strip()
    if not resolved_student_log:
        frappe.throw(_("Student Log is required."))

    resolved_audience = str(audience or "staff").strip().lower()
    return {
        "student_log": resolved_student_log,
        "attachments": get_visible_student_log_evidence_attachments(
            resolved_student_log,
            audience=resolved_audience,
        ),
    }


@frappe.whitelist()
def upload_student_log_evidence_attachment(
    student_log: str | None = None,
    row_name: str | None = None,
    title: str | None = None,
    description: str | None = None,
    visible_to_student: Any = None,
    visible_to_guardians: Any = None,
    **_kwargs,
) -> dict[str, Any]:
    doc = assert_student_log_attachment_upload_access(str(student_log or "").strip(), permission_type="write")
    filename, content = _get_uploaded_file()
    create_session_callable = _load_drive_callable("upload_student_log_evidence_attachment")

    session_payload = {
        "student_log": doc.name,
        "row_name": _clean_text(row_name),
        "filename_original": filename,
        "mime_type_hint": _resolve_upload_mime_type_hint(filename=filename),
        "expected_size_bytes": len(content),
        "upload_source": "Desk",
    }
    session_response, finalize_response, _file_doc = _drive_upload_and_finalize(
        create_session_callable=create_session_callable,
        payload=session_payload,
        content=content,
    )

    doc.reload()
    session_workflow_result = _workflow_result_payload(session_response)
    finalize_workflow_result = _workflow_result_payload(finalize_response)
    resolved_row_name = (
        _clean_text(finalize_workflow_result.get("row_name"))
        or _clean_text(session_workflow_result.get("row_name"))
        or _clean_text(row_name)
    )
    target_row = _get_evidence_row(doc, resolved_row_name)
    _set_row_metadata(
        doc,
        target_row,
        title=title,
        description=description,
        visible_to_student=visible_to_student,
        visible_to_guardians=visible_to_guardians,
    )
    if title or description or visible_to_student is not None or visible_to_guardians is not None:
        doc.reload()
        target_row = _get_evidence_row(doc, resolved_row_name)

    return {
        "ok": True,
        "student_log": doc.name,
        "attachment": serialize_student_log_evidence_row(doc.name, target_row),
    }


@frappe.whitelist()
def add_student_log_evidence_link(
    student_log: str | None = None,
    external_url: str | None = None,
    title: str | None = None,
    description: str | None = None,
    visible_to_student: Any = 0,
    visible_to_guardians: Any = 0,
) -> dict[str, Any]:
    doc = assert_student_log_attachment_upload_access(str(student_log or "").strip(), permission_type="write")
    resolved_url = _clean_text(external_url)
    if not resolved_url:
        frappe.throw(_("External URL is required."))

    row = doc.append(
        STUDENT_LOG_EVIDENCE_TABLE_FIELD,
        {
            "title": _clean_text(title) or resolved_url,
            "external_url": resolved_url,
            "description": _clean_text(description),
            "visible_to_student": _truthy(visible_to_student),
            "visible_to_guardians": _truthy(visible_to_guardians),
        },
    )
    doc.save(ignore_permissions=True)
    return {
        "ok": True,
        "student_log": doc.name,
        "attachment": serialize_student_log_evidence_row(doc.name, row),
    }


def _mark_binding_inactive(student_log: str, row_name: str) -> None:
    binding_names = frappe.get_all(
        "Drive Binding",
        filters={
            "binding_doctype": "Student Log",
            "binding_name": student_log,
            "binding_role": STUDENT_LOG_EVIDENCE_BINDING_ROLE,
            "slot": f"{STUDENT_LOG_EVIDENCE_SLOT_PREFIX}{row_name}",
            "status": "active",
        },
        pluck="name",
    )
    for binding_name in binding_names or []:
        binding_doc = frappe.get_doc("Drive Binding", binding_name)
        binding_doc.status = "inactive"
        binding_doc.save(ignore_permissions=True)


@frappe.whitelist()
def remove_student_log_evidence_attachment(
    student_log: str | None = None,
    row_name: str | None = None,
) -> dict[str, Any]:
    doc = assert_student_log_attachment_upload_access(str(student_log or "").strip(), permission_type="write")
    resolved_row_name = str(row_name or "").strip()
    target_row = _get_evidence_row(doc, resolved_row_name)
    if str(getattr(target_row, "file", "") or "").strip():
        _mark_binding_inactive(doc.name, resolved_row_name)

    remaining_rows = [
        row.as_dict() if hasattr(row, "as_dict") else row
        for row in (doc.get(STUDENT_LOG_EVIDENCE_TABLE_FIELD) or [])
        if str(getattr(row, "name", "") or "").strip() != resolved_row_name
    ]
    doc.set(STUDENT_LOG_EVIDENCE_TABLE_FIELD, remaining_rows)
    doc.save(ignore_permissions=True)
    return {
        "ok": True,
        "student_log": doc.name,
        "row_name": resolved_row_name,
    }
