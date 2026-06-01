# ifitwala_ed/admission/api/recommendation_intake/review_payload.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from ifitwala_ed.admission.api.recommendation_intake.access import (
    _require_feature_ready,
    _require_staff_recommendation_access,
)
from ifitwala_ed.admission.api.recommendation_intake.constants import (
    RECOMMENDATION_REQUEST_DOCTYPE,
    RECOMMENDATION_SUBMISSION_DOCTYPE,
    RECOMMENDATION_TEMPLATE_DOCTYPE,
)
from ifitwala_ed.admission.api.recommendation_intake.document_integration import (
    _load_drive_version_mime_map,
    _serialize_recommendation_attachment,
)
from ifitwala_ed.admission.api.recommendation_intake.dto import _build_recommendation_answer_rows, _text
from ifitwala_ed.admission.api.recommendation_intake.templates import _parse_snapshot
from ifitwala_ed.api.file_access import get_drive_file_thumbnail_ready_map
from ifitwala_ed.integrations.drive.authority import get_current_drive_files_for_attachments


def get_recommendation_review_payload(
    *,
    student_applicant: str | None = None,
    recommendation_request: str | None = None,
    recommendation_submission: str | None = None,
    applicant_document_item: str | None = None,
):
    _require_feature_ready()

    applicant_name = (student_applicant or "").strip()
    request_name = (recommendation_request or "").strip()
    submission_name = (recommendation_submission or "").strip()
    item_name = (applicant_document_item or "").strip()

    anchors_used = sum(bool(value) for value in (request_name, submission_name, item_name))
    if anchors_used != 1:
        frappe.throw(_("Provide exactly one recommendation reference."), frappe.ValidationError)

    request_filters: dict[str, object]
    if request_name:
        request_filters = {"name": request_name}
    elif submission_name:
        request_filters = {"submission": submission_name}
    else:
        request_filters = {"applicant_document_item": item_name}

    request_row = frappe.db.get_value(
        RECOMMENDATION_REQUEST_DOCTYPE,
        request_filters,
        [
            "name",
            "student_applicant",
            "recommendation_template",
            "target_document_type",
            "applicant_document",
            "applicant_document_item",
            "item_key",
            "item_label",
            "request_status",
            "recommender_name",
            "recommender_email",
            "recommender_relationship",
            "expires_on",
            "sent_on",
            "opened_on",
            "consumed_on",
            "submission",
            "template_snapshot_json",
        ],
        as_dict=True,
    )
    if not request_row:
        frappe.throw(_("Recommendation review reference was not found."), frappe.DoesNotExistError)

    resolved_applicant = (request_row.get("student_applicant") or "").strip()
    if applicant_name and applicant_name != resolved_applicant:
        frappe.throw(_("Recommendation does not belong to this Applicant."), frappe.PermissionError)

    _require_staff_recommendation_access(student_applicant=resolved_applicant)

    request_status = (request_row.get("request_status") or "").strip()
    if request_status != "Submitted" or not (request_row.get("submission") or "").strip():
        frappe.throw(_("This recommendation has not been submitted yet."), frappe.ValidationError)

    submission_row = frappe.db.get_value(
        RECOMMENDATION_SUBMISSION_DOCTYPE,
        (request_row.get("submission") or "").strip(),
        [
            "name",
            "recommendation_request",
            "student_applicant",
            "recommendation_template",
            "applicant_document",
            "applicant_document_item",
            "recommender_name",
            "recommender_email",
            "answers_json",
            "attestation_confirmed",
            "has_file",
            "submitted_on",
        ],
        as_dict=True,
    )
    if not submission_row:
        frappe.throw(_("Recommendation submission payload was not found."), frappe.DoesNotExistError)

    applicant_document_item_name = (submission_row.get("applicant_document_item") or "").strip() or (
        request_row.get("applicant_document_item") or ""
    ).strip()
    item_row = {}
    if applicant_document_item_name:
        item_row = (
            frappe.db.get_value(
                "Applicant Document Item",
                applicant_document_item_name,
                ["name", "review_status", "reviewed_by", "reviewed_on"],
                as_dict=True,
            )
            or {}
        )

    latest_attachment = {}
    if applicant_document_item_name:
        latest_drive_file = get_current_drive_files_for_attachments(
            attached_doctype="Applicant Document Item",
            attached_names=[applicant_document_item_name],
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
        latest_drive_file = latest_drive_file[0] if latest_drive_file else None
        latest_attachment = _serialize_recommendation_attachment(
            student_applicant=resolved_applicant,
            latest_drive_file=latest_drive_file,
            thumbnail_ready_map=get_drive_file_thumbnail_ready_map(
                [_text(latest_drive_file.get("name"))] if latest_drive_file else []
            ),
            version_mime_map=_load_drive_version_mime_map(
                [_text(latest_drive_file.get("current_version"))] if latest_drive_file else []
            ),
        )

    template_name = (request_row.get("recommendation_template") or "").strip()
    template_meta = (
        frappe.db.get_value(
            RECOMMENDATION_TEMPLATE_DOCTYPE,
            template_name,
            ["name", "template_name"],
            as_dict=True,
        )
        or {}
    )
    snapshot = _parse_snapshot(request_row.get("template_snapshot_json"), template_name)

    return {
        "ok": True,
        "recommendation": {
            "student_applicant": resolved_applicant,
            "recommendation_request": (request_row.get("name") or "").strip(),
            "recommendation_submission": (submission_row.get("name") or "").strip(),
            "recommendation_template": template_name or None,
            "template_name": (template_meta.get("template_name") or template_name or "").strip() or None,
            "target_document_type": (request_row.get("target_document_type") or "").strip() or None,
            "applicant_document": (
                (submission_row.get("applicant_document") or "").strip()
                or (request_row.get("applicant_document") or "").strip()
                or None
            ),
            "applicant_document_item": applicant_document_item_name or None,
            "item_key": (request_row.get("item_key") or "").strip() or None,
            "item_label": (request_row.get("item_label") or "").strip() or None,
            "request_status": request_status,
            "review_status": (item_row.get("review_status") or "").strip() or "Pending",
            "reviewed_by": (item_row.get("reviewed_by") or "").strip() or None,
            "reviewed_on": item_row.get("reviewed_on"),
            "recommender_name": (request_row.get("recommender_name") or "").strip() or None,
            "recommender_email": (request_row.get("recommender_email") or "").strip() or None,
            "recommender_relationship": (request_row.get("recommender_relationship") or "").strip() or None,
            "sent_on": request_row.get("sent_on"),
            "opened_on": request_row.get("opened_on"),
            "submitted_on": submission_row.get("submitted_on") or request_row.get("consumed_on"),
            "expires_on": request_row.get("expires_on"),
            "has_file": bool(cint(submission_row.get("has_file"))),
            "attestation_confirmed": bool(cint(submission_row.get("attestation_confirmed"))),
            "file_name": latest_attachment.get("file_name"),
            "open_url": latest_attachment.get("open_url"),
            "preview_url": latest_attachment.get("preview_url"),
            "thumbnail_url": latest_attachment.get("thumbnail_url"),
            "preview_status": latest_attachment.get("preview_status"),
            "drive_file_id": latest_attachment.get("drive_file_id"),
            "canonical_ref": latest_attachment.get("canonical_ref"),
            "attachment_preview": latest_attachment.get("attachment_preview"),
            "answers": _build_recommendation_answer_rows(snapshot, submission_row.get("answers_json")),
            "can_review": bool(
                applicant_document_item_name
                and (item_row.get("review_status") or "").strip() in {"", "Pending", "Needs Follow-Up"}
            ),
            "needs_review": bool(
                applicant_document_item_name and (item_row.get("review_status") or "").strip() in {"", "Pending"}
            ),
        },
    }
