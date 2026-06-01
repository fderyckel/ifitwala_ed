# ifitwala_ed/admission/api/recommendation_intake/status.py

from __future__ import annotations

import frappe
from frappe.utils import cint, now_datetime

from ifitwala_ed.admission.admission_utils import get_applicant_scope_ancestors
from ifitwala_ed.admission.api.recommendation_intake.access import _feature_ready, _table_exists
from ifitwala_ed.admission.api.recommendation_intake.constants import (
    RECOMMENDATION_REQUEST_DOCTYPE,
    RECOMMENDATION_SUBMISSION_DOCTYPE,
    RECOMMENDATION_TEMPLATE_DOCTYPE,
    REQUEST_STATUS_ALL,
)
from ifitwala_ed.admission.api.recommendation_intake.document_integration import (
    _load_drive_version_mime_map,
    _serialize_recommendation_attachment,
)
from ifitwala_ed.admission.api.recommendation_intake.dto import _sort_datetime_value, _text
from ifitwala_ed.admission.api.recommendation_intake.templates import _template_in_scope
from ifitwala_ed.api.file_access import get_drive_file_thumbnail_ready_map
from ifitwala_ed.integrations.drive.authority import get_current_drive_files_for_attachments


def _summary_from_rows(rows: list[dict], *, required_total: int, received_total: int) -> dict:
    counts = {status: 0 for status in sorted(REQUEST_STATUS_ALL)}
    for row in rows:
        status = (row.get("request_status") or "").strip()
        if status in counts:
            counts[status] += 1
    state = "optional"
    if required_total > 0:
        if received_total >= required_total:
            state = "complete"
        elif received_total > 0:
            state = "in_progress"
        else:
            state = "pending"
    return {
        "counts": counts,
        "required_total": required_total,
        "received_total": received_total,
        "state": state,
    }


def _default_recommendation_status_payload(*, include_confidential: bool = False) -> dict:
    payload = {
        "ok": True,
        "required_total": 0,
        "received_total": 0,
        "requested_total": 0,
        "missing": [],
        "rows": [],
        "state": "optional",
        "counts": {status: 0 for status in sorted(REQUEST_STATUS_ALL)},
    }
    if include_confidential:
        payload.update(
            {
                "review_rows": [],
                "pending_review_count": 0,
                "first_pending_review": None,
                "latest_submitted_on": None,
            }
        )
    return payload


def _refresh_expired_requests(*, student_applicant: str | None = None) -> None:
    if not _table_exists(RECOMMENDATION_REQUEST_DOCTYPE):
        return
    now_value = now_datetime()
    filters_sql = ""
    params = {"now": now_value}
    if student_applicant:
        filters_sql = " AND student_applicant = %(student_applicant)s"
        params["student_applicant"] = student_applicant

    frappe.db.sql(
        f"""
        UPDATE `tab{RECOMMENDATION_REQUEST_DOCTYPE}`
           SET request_status = 'Expired'
         WHERE request_status IN ('Sent', 'Opened')
           AND expires_on < %(now)s
           {filters_sql}
        """,
        params,
    )


def get_recommendation_status_batch_for_applicants(
    *,
    applicant_rows: list[dict],
    include_confidential: bool = False,
) -> dict[str, dict]:
    normalized_applicants: list[dict] = []
    applicant_names: list[str] = []
    seen_names: set[str] = set()
    for row in applicant_rows or []:
        applicant_name = (row.get("name") or "").strip()
        if not applicant_name or applicant_name in seen_names:
            continue
        seen_names.add(applicant_name)
        normalized_row = {
            "name": applicant_name,
            "organization": (row.get("organization") or "").strip(),
            "school": (row.get("school") or "").strip(),
        }
        normalized_applicants.append(normalized_row)
        applicant_names.append(applicant_name)

    if not applicant_names:
        return {}

    if not _feature_ready():
        return {
            applicant_name: _default_recommendation_status_payload(include_confidential=include_confidential)
            for applicant_name in applicant_names
        }

    template_query_fields = ["name", "template_name", "minimum_required", "organization", "school"]
    if not include_confidential:
        template_query_fields.append("applicant_can_view_status")

    active_template_rows = frappe.get_all(
        RECOMMENDATION_TEMPLATE_DOCTYPE,
        filters={"is_active": 1},
        fields=template_query_fields,
        limit=10000,
    )

    scope_cache: dict[tuple[str, str], tuple[set[str], set[str]]] = {}
    templates_by_applicant: dict[str, list[dict]] = {}
    active_template_names: set[str] = set()

    for applicant_row in normalized_applicants:
        organization = applicant_row.get("organization")
        school = applicant_row.get("school")
        applicant_name = applicant_row.get("name")

        scope_key = (organization or "", school or "")
        if scope_key not in scope_cache:
            org_scope, school_scope = get_applicant_scope_ancestors(
                organization=organization,
                school=school,
            )
            scope_cache[scope_key] = (set(org_scope), set(school_scope))

        org_scope, school_scope = scope_cache[scope_key]
        in_scope_templates: list[dict] = []
        for template_row in active_template_rows:
            if not _template_in_scope(template_row=template_row, org_scope=org_scope, school_scope=school_scope):
                continue
            if not include_confidential and not cint(template_row.get("applicant_can_view_status")):
                continue
            in_scope_templates.append(template_row)
            template_name = (template_row.get("name") or "").strip()
            if template_name:
                active_template_names.add(template_name)

        templates_by_applicant[applicant_name] = in_scope_templates

    summary_request_rows = []
    if active_template_names:
        summary_request_rows = frappe.get_all(
            RECOMMENDATION_REQUEST_DOCTYPE,
            filters={
                "student_applicant": ["in", applicant_names],
                "recommendation_template": ["in", sorted(active_template_names)],
            },
            fields=["student_applicant", "recommendation_template", "request_status"],
            limit=10000,
        )

    grouped_statuses_by_applicant: dict[str, dict[str, list[str]]] = {
        applicant_name: {} for applicant_name in applicant_names
    }
    status_counts_by_applicant: dict[str, dict[str, int]] = {
        applicant_name: {status: 0 for status in sorted(REQUEST_STATUS_ALL)} for applicant_name in applicant_names
    }

    for request_row in summary_request_rows:
        applicant_name = (request_row.get("student_applicant") or "").strip()
        template_name = (request_row.get("recommendation_template") or "").strip()
        if not applicant_name or not template_name:
            continue
        status = (request_row.get("request_status") or "").strip()
        grouped_statuses_by_applicant.setdefault(applicant_name, {}).setdefault(template_name, []).append(status)
        if status in status_counts_by_applicant.get(applicant_name, {}):
            status_counts_by_applicant[applicant_name][status] += 1

    review_rows_by_applicant: dict[str, list[dict]] = {applicant_name: [] for applicant_name in applicant_names}
    pending_review_count_by_applicant: dict[str, int] = {applicant_name: 0 for applicant_name in applicant_names}
    first_pending_review_by_applicant: dict[str, dict | None] = {
        applicant_name: None for applicant_name in applicant_names
    }
    latest_submitted_on_by_applicant: dict[str, object | None] = {
        applicant_name: None for applicant_name in applicant_names
    }

    if include_confidential and frappe.db.table_exists(RECOMMENDATION_REQUEST_DOCTYPE):
        review_request_rows = frappe.get_all(
            RECOMMENDATION_REQUEST_DOCTYPE,
            filters={"student_applicant": ["in", applicant_names]},
            fields=[
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
                "resend_count",
                "submission",
            ],
            order_by="consumed_on desc, modified desc",
            limit=10000,
        )

        review_template_names = sorted(
            {
                (row.get("recommendation_template") or "").strip()
                for row in review_request_rows
                if (row.get("recommendation_template") or "").strip()
            }
        )
        review_template_map = {}
        if review_template_names:
            review_template_map = {
                (row.get("name") or "").strip(): row
                for row in frappe.get_all(
                    RECOMMENDATION_TEMPLATE_DOCTYPE,
                    filters={"name": ["in", review_template_names]},
                    fields=["name", "template_name"],
                    limit=len(review_template_names),
                )
                if (row.get("name") or "").strip()
            }

        submission_by_request: dict[str, dict] = {}
        submission_names = [
            (row.get("submission") or "").strip()
            for row in review_request_rows
            if (row.get("submission") or "").strip()
        ]
        if submission_names and frappe.db.table_exists(RECOMMENDATION_SUBMISSION_DOCTYPE):
            submission_rows = frappe.get_all(
                RECOMMENDATION_SUBMISSION_DOCTYPE,
                filters={"name": ["in", sorted(set(submission_names))]},
                fields=[
                    "name",
                    "recommendation_request",
                    "applicant_document",
                    "applicant_document_item",
                    "submitted_on",
                    "has_file",
                    "attestation_confirmed",
                ],
                limit=len(set(submission_names)),
            )
            submission_by_request = {
                (row.get("recommendation_request") or "").strip(): row
                for row in submission_rows
                if (row.get("recommendation_request") or "").strip()
            }

        applicant_document_item_names = sorted(
            {
                (submission_by_request.get((row.get("name") or "").strip()) or {}).get("applicant_document_item")
                or row.get("applicant_document_item")
                for row in review_request_rows
                if (
                    (submission_by_request.get((row.get("name") or "").strip()) or {}).get("applicant_document_item")
                    or row.get("applicant_document_item")
                )
            }
        )
        item_map = {}
        if applicant_document_item_names:
            item_rows = frappe.get_all(
                "Applicant Document Item",
                filters={"name": ["in", applicant_document_item_names]},
                fields=["name", "review_status", "reviewed_by", "reviewed_on"],
                limit=len(applicant_document_item_names),
            )
            item_map = {(row.get("name") or "").strip(): row for row in item_rows if (row.get("name") or "").strip()}

        latest_drive_file_by_item = {}
        if applicant_document_item_names:
            drive_rows = get_current_drive_files_for_attachments(
                attached_doctype="Applicant Document Item",
                attached_names=applicant_document_item_names,
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
            for drive_row in drive_rows:
                attached_to_name = _text(drive_row.get("attached_name"))
                if not attached_to_name or attached_to_name in latest_drive_file_by_item:
                    continue
                latest_drive_file_by_item[attached_to_name] = drive_row

        drive_thumbnail_ready_map = get_drive_file_thumbnail_ready_map(
            [
                _text(row_drive.get("name"))
                for row_drive in latest_drive_file_by_item.values()
                if _text(row_drive.get("name"))
            ]
        )
        drive_version_mime_map = _load_drive_version_mime_map(
            [
                _text(row_drive.get("current_version"))
                for row_drive in latest_drive_file_by_item.values()
                if _text(row_drive.get("current_version"))
            ]
        )

        for request_row in review_request_rows:
            applicant_name = (request_row.get("student_applicant") or "").strip()
            request_name = (request_row.get("name") or "").strip()
            if not applicant_name or not request_name:
                continue

            submission_row = submission_by_request.get(request_name) or {}
            applicant_document_item = (submission_row.get("applicant_document_item") or "").strip() or (
                request_row.get("applicant_document_item") or ""
            ).strip()
            item_row = item_map.get(applicant_document_item) or {}
            review_status = (item_row.get("review_status") or "").strip() or "Pending"
            latest_attachment = _serialize_recommendation_attachment(
                student_applicant=applicant_name,
                latest_drive_file=latest_drive_file_by_item.get(applicant_document_item),
                thumbnail_ready_map=drive_thumbnail_ready_map,
                version_mime_map=drive_version_mime_map,
            )
            submitted_on = submission_row.get("submitted_on") or request_row.get("consumed_on")
            template_name = (request_row.get("recommendation_template") or "").strip()
            template_meta = review_template_map.get(template_name) or {}
            needs_review = (
                request_row.get("request_status") or ""
            ).strip() == "Submitted" and review_status == "Pending"

            review_row = {
                "recommendation_request": request_name,
                "recommendation_submission": (submission_row.get("name") or "").strip() or None,
                "student_applicant": applicant_name,
                "recommendation_template": template_name or None,
                "template_name": (template_meta.get("template_name") or template_name or "").strip() or None,
                "target_document_type": (request_row.get("target_document_type") or "").strip() or None,
                "applicant_document": (
                    (submission_row.get("applicant_document") or "").strip()
                    or (request_row.get("applicant_document") or "").strip()
                    or None
                ),
                "applicant_document_item": applicant_document_item or None,
                "item_key": (request_row.get("item_key") or "").strip() or None,
                "item_label": (request_row.get("item_label") or "").strip() or None,
                "request_status": (request_row.get("request_status") or "").strip() or None,
                "review_status": review_status,
                "reviewed_by": (item_row.get("reviewed_by") or "").strip() or None,
                "reviewed_on": item_row.get("reviewed_on"),
                "recommender_name": (request_row.get("recommender_name") or "").strip() or None,
                "recommender_email": (request_row.get("recommender_email") or "").strip() or None,
                "recommender_relationship": (request_row.get("recommender_relationship") or "").strip() or None,
                "sent_on": request_row.get("sent_on"),
                "opened_on": request_row.get("opened_on"),
                "submitted_on": submitted_on,
                "expires_on": request_row.get("expires_on"),
                "resend_count": cint(request_row.get("resend_count") or 0),
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
                "needs_review": bool(needs_review),
                "can_review": bool(
                    (request_row.get("request_status") or "").strip() == "Submitted" and applicant_document_item
                ),
            }
            review_rows_by_applicant.setdefault(applicant_name, []).append(review_row)

            if submitted_on and not latest_submitted_on_by_applicant.get(applicant_name):
                latest_submitted_on_by_applicant[applicant_name] = submitted_on

            if needs_review:
                pending_review_count_by_applicant[applicant_name] = (
                    pending_review_count_by_applicant.get(applicant_name, 0) + 1
                )
                if not first_pending_review_by_applicant.get(applicant_name):
                    first_pending_review_by_applicant[applicant_name] = {
                        "recommendation_request": review_row.get("recommendation_request"),
                        "recommendation_submission": review_row.get("recommendation_submission"),
                        "applicant_document_item": review_row.get("applicant_document_item"),
                        "recommender_name": review_row.get("recommender_name"),
                        "template_name": review_row.get("template_name"),
                        "submitted_on": review_row.get("submitted_on"),
                    }

        for applicant_name, rows in review_rows_by_applicant.items():
            rows.sort(
                key=lambda row: (
                    _sort_datetime_value(row.get("submitted_on")),
                    _sort_datetime_value(row.get("sent_on")),
                    row.get("recommendation_request") or "",
                ),
                reverse=True,
            )
            latest_submitted = next((row.get("submitted_on") for row in rows if row.get("submitted_on")), None)
            latest_submitted_on_by_applicant[applicant_name] = latest_submitted

    status_by_applicant: dict[str, dict] = {}
    for applicant_name in applicant_names:
        template_rows = templates_by_applicant.get(applicant_name) or []
        required_total = 0
        received_total = 0
        requested_total = 0
        missing: list[str] = []
        aggregate_rows: list[dict] = []

        for template_row in template_rows:
            template_name = (template_row.get("name") or "").strip()
            template_label = (template_row.get("template_name") or template_name or "").strip()
            minimum_required = max(0, cint(template_row.get("minimum_required") or 0))
            template_statuses = grouped_statuses_by_applicant.get(applicant_name, {}).get(template_name, [])
            submitted_count = len([status for status in template_statuses if status == "Submitted"])
            requested_count = len([status for status in template_statuses if status in {"Sent", "Opened", "Submitted"}])

            required_total += minimum_required
            received_total += submitted_count
            requested_total += requested_count
            if minimum_required > submitted_count:
                missing.append(template_label or template_name)

            aggregate_rows.append(
                {
                    "recommendation_template": template_name or None,
                    "template_name": template_label or None,
                    "minimum_required": minimum_required,
                    "submitted_count": submitted_count,
                    "requested_count": requested_count,
                }
            )

        summary = _summary_from_rows(
            [
                {"request_status": status}
                for template_statuses in grouped_statuses_by_applicant.get(applicant_name, {}).values()
                for status in template_statuses
            ],
            required_total=required_total,
            received_total=received_total,
        )
        payload = {
            "ok": not missing,
            "required_total": required_total,
            "received_total": received_total,
            "requested_total": requested_total,
            "missing": missing,
            "rows": aggregate_rows,
            "state": summary.get("state"),
            "counts": status_counts_by_applicant.get(applicant_name)
            or {status: 0 for status in sorted(REQUEST_STATUS_ALL)},
        }
        if include_confidential:
            payload.update(
                {
                    "review_rows": review_rows_by_applicant.get(applicant_name) or [],
                    "pending_review_count": pending_review_count_by_applicant.get(applicant_name, 0),
                    "first_pending_review": first_pending_review_by_applicant.get(applicant_name),
                    "latest_submitted_on": latest_submitted_on_by_applicant.get(applicant_name),
                }
            )
        status_by_applicant[applicant_name] = payload

    return status_by_applicant


def get_recommendation_status_for_applicant(
    *,
    student_applicant: str,
    include_confidential: bool = False,
) -> dict:
    student_applicant = (student_applicant or "").strip()
    if not student_applicant:
        return _default_recommendation_status_payload(include_confidential=include_confidential)

    applicant_row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        ["name", "organization", "school"],
        as_dict=True,
    )
    if not applicant_row:
        return _default_recommendation_status_payload(include_confidential=include_confidential)

    _refresh_expired_requests(student_applicant=student_applicant)
    batch_payload = get_recommendation_status_batch_for_applicants(
        applicant_rows=[applicant_row],
        include_confidential=include_confidential,
    )
    return batch_payload.get(student_applicant) or _default_recommendation_status_payload(
        include_confidential=include_confidential
    )
