from __future__ import annotations

import json
import re
from typing import Any

import frappe
from frappe import _

from ifitwala_ed.utilities.governed_file_contract import LEARNING_RESOURCE_PURPOSE

_TASK_RESOURCE_DATA_CLASS = "academic"
_TASK_RESOURCE_PURPOSE = LEARNING_RESOURCE_PURPOSE
_TASK_RESOURCE_RETENTION_POLICY = "until_program_end_plus_1y"
_TASK_RESOURCE_SLOT_PREFIX = "supporting_material__"
_TASK_SUBMISSION_DATA_CLASS = "assessment"
_TASK_SUBMISSION_PURPOSE = "assessment_submission"
_TASK_SUBMISSION_RETENTION_POLICY = "until_school_exit_plus_6m"
_TASK_SUBMISSION_SLOT = "submission"
_TASK_FEEDBACK_DATA_CLASS = "assessment"
_TASK_FEEDBACK_PURPOSE = "assessment_feedback"
_TASK_FEEDBACK_RETENTION_POLICY = "until_school_exit_plus_6m"
_TASK_FEEDBACK_EXPORT_SLOT_PREFIX = "feedback_export__released__"


def _get_doc(doctype: str, name: str, *, permission_type: str | None = None):
    if not frappe.db.exists(doctype, name):
        frappe.throw(_("{doctype} does not exist: {name}").format(doctype=doctype, name=name))

    doc = frappe.get_doc(doctype, name)
    if permission_type:
        doc.check_permission(permission_type)
    return doc


def _get_task_submission_doc(task_submission: str, *, permission_type: str | None = None):
    return _get_doc("Task Submission", task_submission, permission_type=permission_type)


def _get_task_doc(task: str, *, permission_type: str | None = None):
    return _get_doc("Task", task, permission_type=permission_type)


def _get_organization_from_school(school: str | None) -> str:
    if not school:
        frappe.throw(_("Task Submission is missing school."))

    organization = frappe.db.get_value("School", school, "organization")
    if not organization:
        frappe.throw(_("Task Submission school is missing organization."))

    return organization


def _normalize_row_key(value: str | None) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "-", str(value or "").strip()).strip("-_")
    if normalized:
        return normalized
    return frappe.generate_hash(length=10)


def _parse_task_resource_row_key(slot: str | None) -> str | None:
    resolved_slot = str(slot or "").strip()
    if not resolved_slot.startswith(_TASK_RESOURCE_SLOT_PREFIX):
        return None
    row_key = resolved_slot.split(_TASK_RESOURCE_SLOT_PREFIX, 1)[1].strip()
    return row_key or None


def _get_task_course(task_doc) -> str:
    course = (getattr(task_doc, "default_course", None) or getattr(task_doc, "course", None) or "").strip()
    if not course:
        frappe.throw(_("Task is missing its authoritative course context."))
    return course


def _get_course_school_context(course: str) -> tuple[str, str]:
    school = frappe.db.get_value("Course", course, "school")
    if not school:
        frappe.throw(_("Task course is missing its school context."))
    return school, _get_organization_from_school(school)


def _assert_task_resource_row_exists(task_doc, row_key: str) -> None:
    if not row_key:
        frappe.throw(_("Task resource row key is required."))
    for row in task_doc.get("attachments") or []:
        if str(getattr(row, "name", "") or "").strip() == row_key:
            return
    frappe.throw(_("Task attachment row was not found: {row_key}.").format(row_key=row_key))


def build_task_resource_upload_contract(
    task_doc,
    *,
    row_name: str | None = None,
    allow_missing_row: bool = False,
) -> dict[str, Any]:
    course = _get_task_course(task_doc)
    school, organization = _get_course_school_context(course)
    row_key = _normalize_row_key(row_name)
    if row_name and not allow_missing_row:
        _assert_task_resource_row_exists(task_doc, row_key)

    return {
        "owner_doctype": "Task",
        "owner_name": task_doc.name,
        "attached_doctype": "Task",
        "attached_name": task_doc.name,
        "organization": organization,
        "school": school,
        "primary_subject_type": "Organization",
        "primary_subject_id": organization,
        "data_class": _TASK_RESOURCE_DATA_CLASS,
        "purpose": _TASK_RESOURCE_PURPOSE,
        "retention_policy": _TASK_RESOURCE_RETENTION_POLICY,
        "slot": f"{_TASK_RESOURCE_SLOT_PREFIX}{row_key}",
        "row_name": row_key,
        "course": course,
    }


def build_task_submission_upload_contract(task_submission_doc) -> dict[str, Any]:
    student = getattr(task_submission_doc, "student", None)
    school = getattr(task_submission_doc, "school", None)
    if not student:
        frappe.throw(_("Task Submission is missing student."))
    if not school:
        frappe.throw(_("Task Submission is missing school."))

    return {
        "owner_doctype": "Task Submission",
        "owner_name": task_submission_doc.name,
        "attached_doctype": "Task Submission",
        "attached_name": task_submission_doc.name,
        "organization": _get_organization_from_school(school),
        "school": school,
        "primary_subject_type": "Student",
        "primary_subject_id": student,
        "data_class": _TASK_SUBMISSION_DATA_CLASS,
        "purpose": _TASK_SUBMISSION_PURPOSE,
        "retention_policy": _TASK_SUBMISSION_RETENTION_POLICY,
        "slot": _TASK_SUBMISSION_SLOT,
    }


def _build_task_feedback_export_slot(*, audience: str | None = None) -> str:
    resolved_audience = str(audience or "student").strip().lower() or "student"
    if resolved_audience not in {"student"}:
        frappe.throw(_("Unsupported feedback export audience: {0}").format(resolved_audience))
    return f"{_TASK_FEEDBACK_EXPORT_SLOT_PREFIX}{resolved_audience}"


def build_task_feedback_export_upload_contract(task_submission_doc, *, audience: str | None = None) -> dict[str, Any]:
    student = getattr(task_submission_doc, "student", None)
    school = getattr(task_submission_doc, "school", None)
    if not student:
        frappe.throw(_("Task Submission is missing student."))
    if not school:
        frappe.throw(_("Task Submission is missing school."))

    return {
        "owner_doctype": "Task Submission",
        "owner_name": task_submission_doc.name,
        "attached_doctype": "Task Submission",
        "attached_name": task_submission_doc.name,
        "organization": _get_organization_from_school(school),
        "school": school,
        "primary_subject_type": "Student",
        "primary_subject_id": student,
        "data_class": _TASK_FEEDBACK_DATA_CLASS,
        "purpose": _TASK_FEEDBACK_PURPOSE,
        "retention_policy": _TASK_FEEDBACK_RETENTION_POLICY,
        "slot": _build_task_feedback_export_slot(audience=audience),
    }


def assert_task_submission_upload_access(task_submission: str, *, permission_type: str = "write"):
    doc = _get_task_submission_doc(task_submission)
    if not permission_type:
        return doc

    try:
        doc.check_permission(permission_type)
    except Exception as exc:
        permission_error = getattr(frappe, "PermissionError", None)
        if (
            permission_type == "write"
            and isinstance(permission_error, type)
            and isinstance(exc, permission_error)
            and _task_submission_owned_by_session_student(doc)
        ):
            return doc
        raise
    return doc


def assert_task_resource_upload_access(task: str, *, permission_type: str = "write"):
    return _get_task_doc(task, permission_type=permission_type)


def _task_submission_owned_by_session_student(task_submission_doc) -> bool:
    student = str(getattr(task_submission_doc, "student", None) or "").strip()
    if not student:
        return False

    session_student = _get_session_student_name()
    if not session_student:
        return False

    return student == session_student


def _load_workflow_payload(upload_session_doc) -> dict[str, Any]:
    raw = str(getattr(upload_session_doc, "upload_contract_json", None) or "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}
    workflow = parsed.get("workflow")
    if not isinstance(workflow, dict):
        return {}
    workflow_payload = workflow.get("workflow_payload")
    return workflow_payload if isinstance(workflow_payload, dict) else {}


def _get_session_student_name() -> str | None:
    try:
        from ifitwala_ed.api import courses as courses_api

        return str(courses_api._require_student_name_for_session_user() or "").strip() or None
    except Exception as exc:
        handled_exceptions = tuple(
            error_type
            for error_type in (
                getattr(frappe, "PermissionError", None),
                getattr(frappe, "AuthenticationError", None),
            )
            if isinstance(error_type, type) and issubclass(error_type, Exception)
        )
        if handled_exceptions and isinstance(exc, handled_exceptions):
            return None
        raise


def validate_task_resource_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Task":
        return None

    row_key = _parse_task_resource_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        frappe.throw(_("Task resource upload sessions require a task-resource slot."))

    task_doc = assert_task_resource_upload_access(upload_session_doc.owner_name, permission_type="write")
    authoritative = build_task_resource_upload_contract(task_doc, row_name=row_key, allow_missing_row=True)

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
                    "Upload session no longer matches the authoritative Task resource context for field '{field_name}'."
                ).format(field_name=session_field)
            )

    return authoritative


def get_task_resource_context_override(owner_name: str | None, slot: str | None) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists("Task", owner_name):
        return None

    task_doc = _get_task_doc(owner_name)
    course = _get_task_course(task_doc)
    return {
        "root_folder": "Home/Courses",
        "subfolder": f"{course}/Tasks/{task_doc.name}/Resources",
        "file_category": "Task Resource",
        "logical_key": str(slot or "").strip() or f"task_resource_{task_doc.name}",
    }


def run_task_post_finalize(upload_session_doc, created_file) -> dict[str, Any]:
    if getattr(upload_session_doc, "owner_doctype", None) != "Task":
        return {}

    row_key = _parse_task_resource_row_key(getattr(upload_session_doc, "intended_slot", None))
    if not row_key:
        return {}

    task_doc = frappe.get_doc("Task", upload_session_doc.owner_name)
    target_row = None
    for row in task_doc.get("attachments") or []:
        if str(getattr(row, "name", "") or "").strip() == row_key:
            target_row = row
            break

    if not target_row:
        target_row = task_doc.append("attachments", {})
        target_row.name = row_key

    file_url = getattr(created_file, "file_url", None) or frappe.db.get_value("File", created_file.name, "file_url")
    file_name = getattr(created_file, "file_name", None) or frappe.db.get_value("File", created_file.name, "file_name")
    file_size = getattr(created_file, "file_size", None) or frappe.db.get_value("File", created_file.name, "file_size")

    if not getattr(target_row, "section_break_sbex", None):
        target_row.section_break_sbex = file_name
    target_row.file = file_url
    target_row.file_name = file_name
    target_row.file_size = file_size
    target_row.public = 0
    task_doc.save(ignore_permissions=True)

    return {
        "row_name": row_key,
        "file_url": file_url,
    }


def reconcile_task_submission_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("owner_doctype") != "Task Submission":
        return payload

    task_submission_name = payload.get("owner_name")
    if not task_submission_name:
        frappe.throw(_("Missing required field: owner_name"))

    task_submission_doc = assert_task_submission_upload_access(task_submission_name, permission_type="write")
    authoritative = build_task_submission_upload_contract(task_submission_doc)

    for fieldname, authoritative_value in authoritative.items():
        provided = payload.get(fieldname)
        if provided not in (None, "", authoritative_value):
            frappe.throw(
                _("Task Submission upload field '{field_name}' does not match the authoritative owner context.").format(
                    field_name=fieldname
                )
            )

    return {
        **payload,
        **authoritative,
    }


def reconcile_task_feedback_export_session_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("owner_doctype") != "Task Submission":
        return payload

    task_submission_name = payload.get("owner_name")
    if not task_submission_name:
        frappe.throw(_("Missing required field: owner_name"))

    task_submission_doc = assert_task_submission_upload_access(task_submission_name, permission_type="write")
    authoritative = build_task_feedback_export_upload_contract(
        task_submission_doc,
        audience=payload.get("audience"),
    )

    for fieldname, authoritative_value in authoritative.items():
        provided = payload.get(fieldname)
        if provided not in (None, "", authoritative_value):
            frappe.throw(
                _("Task Feedback export field '{field_name}' does not match the authoritative owner context.").format(
                    field_name=fieldname
                )
            )

    return {
        **payload,
        **authoritative,
    }


def validate_task_submission_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Task Submission":
        return None

    task_submission_doc = assert_task_submission_upload_access(
        upload_session_doc.owner_name,
        permission_type="write",
    )
    authoritative = build_task_submission_upload_contract(task_submission_doc)

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
                    "Upload session no longer matches the authoritative Task Submission context for field '{field_name}'."
                ).format(field_name=session_field)
            )

    return authoritative


def validate_task_feedback_export_finalize_context(upload_session_doc) -> dict[str, Any] | None:
    if getattr(upload_session_doc, "owner_doctype", None) != "Task Submission":
        return None

    workflow_payload = _load_workflow_payload(upload_session_doc)
    task_submission_doc = assert_task_submission_upload_access(
        upload_session_doc.owner_name,
        permission_type="write",
    )
    authoritative = build_task_feedback_export_upload_contract(
        task_submission_doc,
        audience=workflow_payload.get("audience"),
    )

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
                    "Upload session no longer matches the authoritative Task Feedback export context for field '{field_name}'."
                ).format(field_name=session_field)
            )

    return authoritative


def get_task_submission_context_override(owner_name: str | None) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists("Task Submission", owner_name):
        return None

    task_submission = _get_task_submission_doc(owner_name)
    student = getattr(task_submission, "student", None)
    task_name = getattr(task_submission, "task", None) or task_submission.name

    if not student:
        return None

    try:
        from ifitwala_ed.utilities import file_management
    except ImportError:
        return None

    return file_management.build_task_submission_context(
        student=student,
        task_name=task_name,
        settings=file_management.get_settings(),
    )


def get_task_feedback_export_context_override(owner_name: str | None, slot: str | None) -> dict[str, Any] | None:
    if not owner_name or not frappe.db.exists("Task Submission", owner_name):
        return None

    task_submission = _get_task_submission_doc(owner_name)
    student = getattr(task_submission, "student", None)
    task_name = getattr(task_submission, "task", None) or task_submission.name
    if not student:
        return None

    try:
        from ifitwala_ed.utilities import file_management
    except ImportError:
        return None

    base = file_management.build_task_submission_context(
        student=student,
        task_name=task_name,
        settings=file_management.get_settings(),
    )
    resolved_slot = str(slot or "").strip() or _build_task_feedback_export_slot(audience="student")
    return {
        "root_folder": base.get("root_folder"),
        "subfolder": f"{base.get('subfolder')}/Feedback",
        "file_category": "Assessment Feedback",
        "logical_key": f"feedback_{task_name}_{resolved_slot}",
    }
