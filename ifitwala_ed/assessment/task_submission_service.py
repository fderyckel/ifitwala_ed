# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/assessment/task_submission_service.py

from types import SimpleNamespace

import frappe
from frappe import _
from frappe.utils import now_datetime

from ifitwala_ed.assessment.task_contribution_service import mark_contributions_stale

_PENDING_SUBMISSION_FILES_FLAG = "allow_pending_submission_files"


def get_next_submission_version(outcome_id):
    if not outcome_id:
        frappe.throw(_("Task Outcome is required for submissions."))

    rows = frappe.db.get_all(
        "Task Submission",
        filters={"task_outcome": outcome_id},
        fields=[{"MAX": "version", "as": "max_version"}],
    )
    max_version = rows[0].get("max_version") if rows else None
    try:
        max_version = int(max_version or 0)
    except Exception:
        max_version = 0
    return max_version + 1


def create_student_submission(payload, user=None, uploaded_files=None, expected_student=None):
    data = _normalize_payload(payload)
    outcome_id = _get_payload_value(data, "task_outcome", "outcome")
    if not outcome_id:
        frappe.throw(_("Task Outcome is required."))

    outcome_row = frappe.db.get_value(
        "Task Outcome",
        outcome_id,
        [
            "student",
            "student_group",
            "course",
            "academic_year",
            "school",
            "task_delivery",
            "task",
        ],
        as_dict=True,
    )
    if expected_student:
        actual_student = (outcome_row or {}).get("student")
        if not actual_student or str(actual_student).strip() != str(expected_student).strip():
            frappe.throw(_("You do not have access to this submission."), frappe.PermissionError)
    if not outcome_row:
        frappe.throw(_("Task Outcome not found."))
    _assert_submission_allowed(outcome_row)

    text_content = (data.get("text_content") or "").strip()
    link_url = (data.get("link_url") or "").strip()
    attachments = data.get("attachments") or []
    if attachments:
        frappe.throw(_("Attachments must be uploaded as raw files via dispatcher."))

    uploaded_files = uploaded_files or []
    has_uploads = bool(uploaded_files)

    if not text_content and not link_url and not has_uploads:
        frappe.throw(_("Student evidence is required."))

    next_version = get_next_submission_version(outcome_id)

    doc = frappe.new_doc("Task Submission")
    doc.task_outcome = outcome_id
    doc.version = next_version
    doc.submitted_by = user or frappe.session.user
    doc.submitted_on = now_datetime()
    doc.submission_origin = "Student Upload"
    doc.is_stub = 0
    doc.text_content = text_content or None
    doc.link_url = link_url or None
    if data.get("evidence_note"):
        doc.evidence_note = data.get("evidence_note")

    stamp_submission_context(doc, outcome_row)
    if has_uploads:
        _set_doc_flag(doc, _PENDING_SUBMISSION_FILES_FLAG, True)
    doc.insert(ignore_permissions=True)
    if has_uploads:
        _set_doc_flag(doc, _PENDING_SUBMISSION_FILES_FLAG, True)
        try:
            _attach_submission_files(doc, outcome_row, uploaded_files, data.get("upload_source"))
            doc.save(ignore_permissions=True)
        finally:
            _set_doc_flag(doc, _PENDING_SUBMISSION_FILES_FLAG, False)

    submission_status = "Submitted" if next_version == 1 else "Resubmitted"
    frappe.db.set_value(
        "Task Outcome",
        outcome_id,
        {
            "has_submission": 1,
            "has_new_submission": 1,
            "submission_status": submission_status,
        },
        update_modified=True,
    )

    mark_contributions_stale(outcome_id, latest_submission_id=doc.name)

    return {
        "submission_id": doc.name,
        "version": next_version,
        "outcome_flags": {
            "has_submission": True,
            "has_new_submission": True,
            "submission_status": submission_status,
        },
    }


def _attach_submission_files(submission_doc, outcome_row, uploaded_files, upload_source=None):
    from ifitwala_drive.api.submissions import upload_task_submission_artifact

    from ifitwala_ed.integrations.drive.content_uploads import upload_content_via_drive

    student = outcome_row.get("student")

    if not student:
        frappe.throw(_("Student is required for governed submission uploads."))

    source = upload_source or "API"
    for upload in uploaded_files:
        file_name = upload.get("file_name") or upload.get("filename")
        content = upload.get("content")
        if not file_name or not content:
            frappe.throw(_("Uploaded files must include file_name and content."))

        _session_response, _finalize_response, file_doc = upload_content_via_drive(
            create_session_callable=upload_task_submission_artifact,
            session_payload={
                "task_submission": submission_doc.name,
                "student": student,
                "upload_source": source,
            },
            file_name=file_name,
            content=content,
        )
        resolved_file_name = _clean_text(getattr(file_doc, "file_name", None)) or file_name

        submission_doc.append(
            "attachments",
            {
                "section_break_sbex": resolved_file_name,
                "file": file_doc.file_url,
                "file_name": resolved_file_name,
                "file_size": file_doc.file_size,
                "public": 0,
            },
        )


def _clean_text(value):
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _set_doc_flag(doc, flagname, value):
    flags = getattr(doc, "flags", None)
    if flags is None:
        flags = SimpleNamespace()
        doc.flags = flags
    if isinstance(flags, dict):
        flags[flagname] = value
        return
    setattr(flags, flagname, value)


def _assert_submission_allowed(outcome_row):
    task_delivery = (outcome_row or {}).get("task_delivery")
    if not task_delivery:
        frappe.throw(_("This task does not accept submissions."))

    delivery_row = frappe.db.get_value(
        "Task Delivery",
        task_delivery,
        ["requires_submission"],
        as_dict=True,
    )
    if not delivery_row:
        frappe.throw(_("This task does not accept submissions."))
    if int(delivery_row.get("requires_submission") or 0) != 1:
        frappe.throw(_("This task does not accept submissions."))


def stamp_submission_context(submission_doc, outcome_row):
    if not outcome_row:
        return

    fieldnames = [
        "student",
        "student_group",
        "course",
        "academic_year",
        "school",
        "task_delivery",
        "task",
    ]
    for field in fieldnames:
        if outcome_row.get(field):
            if not getattr(submission_doc, field, None):
                setattr(submission_doc, field, outcome_row.get(field))


def apply_outcome_submission_effects(outcome_id, submission_id, source="student"):
    if not outcome_id or not submission_id:
        return

    outcome = (
        frappe.db.get_value(
            "Task Outcome",
            outcome_id,
            [
                "grading_status",
                "official_score",
                "official_grade",
                "official_feedback",
                "has_new_submission",
                "has_submission",
                "is_stale",
            ],
            as_dict=True,
        )
        or {}
    )

    if source == "teacher_stub":
        updates = {
            "submission_status": "Submitted",
            "has_submission": 1,
            "has_new_submission": 0,
            "is_stale": 0,
        }
        frappe.db.set_value("Task Outcome", outcome_id, updates, update_modified=True)
        return

    submission = (
        frappe.db.get_value(
            "Task Submission",
            submission_id,
            ["is_late"],
            as_dict=True,
        )
        or {}
    )

    grading_started = _grading_started(outcome)
    updates = {"submission_status": "Late" if submission.get("is_late") else "Submitted"}

    updates["has_submission"] = 1
    updates["has_new_submission"] = 1
    updates["is_stale"] = 1 if grading_started else 0

    frappe.db.set_value("Task Outcome", outcome_id, updates, update_modified=True)

    mark_contributions_stale(outcome_id, latest_submission_id=submission_id)


def ensure_evidence_stub_submission(outcome_id, origin="Teacher Observation", note=None, created_by=None):
    if not outcome_id:
        frappe.throw(_("Task Outcome is required."))

    outcome_row = frappe.db.get_value(
        "Task Outcome",
        outcome_id,
        [
            "student",
            "student_group",
            "course",
            "academic_year",
            "school",
            "task_delivery",
            "task",
        ],
        as_dict=True,
    )
    if not outcome_row:
        frappe.throw(_("Task Outcome not found."))

    latest_real = frappe.get_all(
        "Task Submission",
        filters={"task_outcome": outcome_id, "is_stub": ["!=", 1]},
        fields=["name", "version", "is_stub", "submission_origin"],
        order_by="version desc",
        limit=1,
    )
    if latest_real:
        return latest_real[0]["name"]

    latest_stub = frappe.get_all(
        "Task Submission",
        filters={"task_outcome": outcome_id, "is_stub": 1},
        fields=["name", "version", "is_stub", "submission_origin"],
        order_by="version desc",
        limit=1,
    )
    if latest_stub:
        return latest_stub[0]["name"]

    doc = frappe.new_doc("Task Submission")
    doc.task_outcome = outcome_id
    doc.version = get_next_submission_version(outcome_id)
    doc.submitted_by = created_by or frappe.session.user
    doc.submitted_on = now_datetime()
    doc.submission_origin = origin
    doc.is_stub = 1
    doc.evidence_note = note or "Evidence stub (no student submission)"

    stamp_submission_context(doc, outcome_row)
    doc.insert(ignore_permissions=True)
    apply_outcome_submission_effects(outcome_id, doc.name, source="teacher_stub")
    return doc.name


def create_evidence_stub(outcome_id, created_by=None, note=None):
    return ensure_evidence_stub_submission(
        outcome_id,
        origin="Teacher Observation",
        note=note,
        created_by=created_by,
    )


def _normalize_payload(payload):
    if payload is None:
        return {}
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if not isinstance(payload, dict):
        frappe.throw(_("Payload must be a dict."))
    return payload


def _get_payload_value(data, *keys):
    for key in keys:
        if key in data and data.get(key) not in (None, ""):
            return data.get(key)
    return None


def _grading_started(outcome):
    status = (outcome.get("grading_status") or "").strip()
    if status and status not in ("Not Applicable", "Not Started"):
        return True
    if outcome.get("official_score") not in (None, ""):
        return True
    if (outcome.get("official_grade") or "").strip():
        return True
    if (outcome.get("official_feedback") or "").strip():
        return True
    return False
