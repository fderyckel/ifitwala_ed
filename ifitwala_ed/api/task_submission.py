# Copyright (c) 2026
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.assessment import task_submission_service


@frappe.whitelist()
def create_or_resubmit(payload=None, **kwargs):
    _require_authenticated()
    data = _normalize_payload(payload, kwargs)
    uploaded_files = _extract_uploaded_files()
    result = task_submission_service.create_student_submission(
        data,
        user=frappe.session.user,
        uploaded_files=uploaded_files,
    )
    return result


@frappe.whitelist()
def get_latest_submission(outcome_id=None):
    _require_authenticated()
    _require(outcome_id, "Task Outcome")

    rows = frappe.get_all(
        "Task Submission",
        filters={"task_outcome": outcome_id},
        fields=["name", "version", "submitted_on", "text_content", "link_url"],
        order_by="version desc",
        limit_page_length=1,
    )
    if not rows:
        return None

    latest = rows[0]
    attachments = frappe.get_all(
        "Attached Document",
        filters={
            "parent": latest.get("name"),
            "parenttype": "Task Submission",
            "parentfield": "attachments",
        },
        fields=["file", "external_url", "description", "public", "file_name", "file_size"],
        order_by="idx asc",
        limit_page_length=0,
    )

    return {
        "submission_id": latest.get("name"),
        "version": latest.get("version"),
        "submitted_on": latest.get("submitted_on"),
        "text_content": latest.get("text_content"),
        "link_url": latest.get("link_url"),
        "attachments": attachments,
    }


def _require(value, label):
    if not value:
        frappe.throw(_("{0} is required.").format(label))


def _normalize_payload(payload, kwargs):
    data = payload if payload is not None else kwargs
    if isinstance(data, str):
        data = frappe.parse_json(data)
    if not isinstance(data, dict):
        frappe.throw(_("Payload must be a dict."))
    return data


def _require_authenticated():
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw(_("Not permitted."), frappe.PermissionError)


def _extract_uploaded_files():
    uploads = []
    if not frappe.request or not getattr(frappe.request, "files", None):
        return uploads

    files = []
    if hasattr(frappe.request.files, "getlist"):
        files = frappe.request.files.getlist("files") or []
    if not files:
        single = frappe.request.files.get("file")
        if single:
            files = [single]

    for upload in files:
        filename = getattr(upload, "filename", None)
        content = upload.read()
        if not filename or not content:
            frappe.throw(_("Uploaded files must include a filename and content."))
        uploads.append(
            {
                "file_name": filename,
                "content": content,
            }
        )

    return uploads
