# Copyright (c) 2026, Francois de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import csv
import io
from collections import Counter

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime
from frappe.utils.file_manager import save_file

from ifitwala_ed.schedule.enrollment_request_utils import (
    materialize_program_enrollment_request,
    validate_program_enrollment_request,
)
from ifitwala_ed.schedule.report.program_enrollment_request_overview.program_enrollment_request_overview import (
    VIEW_MODE_SUMMARY,
    get_filtered_requests,
)

FAST_TRACK_QUEUE_THRESHOLD = 100
FAST_TRACK_PROGRESS_EVENT = "program_enrollment_request_fast_track"
FAST_TRACK_DONE_EVENT = "program_enrollment_request_fast_track_done"
ACADEMIC_REQUEST_KIND = "Academic"
ACTION_APPROVE_ONLY = "approve_only"
ACTION_MATERIALIZE_ONLY = "materialize_only"
ACTION_APPROVE_AND_MATERIALIZE = "approve_and_materialize"
PERMISSION_ERROR_REQUEST = _("You need write access to Program Enrollment Request to approve requests in bulk.")
PERMISSION_ERROR_ENROLLMENT = _(
    "You need create and write access to Program Enrollment to materialize requests in bulk."
)
FAST_TRACK_ACTION_META = {
    ACTION_APPROVE_ONLY: {
        "title": _("Batch Approval Finished"),
        "progress_label": _("Approving requests"),
        "queue_message": _("{0} requests were queued for batch approval. You will be notified when the job completes."),
        "preview_note": _(
            "Draft, submitted, and under-review requests will be revalidated. Valid academic requests will be approved. Nothing will materialize."
        ),
        "requires_enrollment_date": False,
    },
    ACTION_MATERIALIZE_ONLY: {
        "title": _("Batch Materialization Finished"),
        "progress_label": _("Materializing enrollments"),
        "queue_message": _(
            "{0} requests were queued for batch materialization. You will be notified when the job completes."
        ),
        "preview_note": _(
            "Only Approved and Valid academic requests will materialize. Requests that are not ready or already materialized will be skipped."
        ),
        "requires_enrollment_date": True,
    },
    ACTION_APPROVE_AND_MATERIALIZE: {
        "title": _("Fast-Track Enrollment Finished"),
        "progress_label": _("Approving and creating enrollments"),
        "queue_message": _(
            "{0} requests were queued for fast-track approval and materialization. You will be notified when the job completes."
        ),
        "preview_note": _(
            "Draft, submitted, and under-review requests will be revalidated during execution. Invalid, override-required, and already-materialized requests will be skipped."
        ),
        "requires_enrollment_date": True,
    },
}


def _run_fast_track_job(request_names: list[str], enrollment_date: str, target_user: str, action: str):
    previous_user = frappe.session.user
    frappe.set_user(target_user)
    try:
        _assert_fast_track_permissions(action=action, user=target_user)
        _execute_fast_track(
            request_names=request_names,
            enrollment_date=enrollment_date,
            target_user=target_user,
            batch_mode=True,
            action=action,
        )
    finally:
        frappe.set_user(previous_user)


@frappe.whitelist()
def get_fast_track_access():
    access = _get_batch_action_access(user=frappe.session.user)
    can_run, reason = _get_fast_track_access(user=frappe.session.user)
    access["can_run"] = 1 if can_run else 0
    access["reason"] = reason
    return access


@frappe.whitelist()
def preview_fast_track_requests(filters=None, action=None):
    action = _normalize_fast_track_action(action)
    _assert_fast_track_permissions(action=action, user=frappe.session.user)
    filters = _normalize_fast_track_filters(filters)
    _normalized, requests = get_filtered_requests(filters, require_matrix_offering=False)
    request_names = [request.get("name") for request in requests if request.get("name")]
    if not request_names:
        frappe.throw(_("No Program Enrollment Requests match the current filters."))

    materialized_request_names = _get_materialized_request_names(request_names)
    counts = _build_preview_counts(
        requests=requests, materialized_request_names=materialized_request_names, action=action
    )

    return {
        "counts": dict(counts),
        "default_enrollment_date": (
            str(_resolve_default_enrollment_date(filters.get("academic_year")))
            if FAST_TRACK_ACTION_META[action]["requires_enrollment_date"]
            else ""
        ),
        "request_count": len(requests),
        "note": FAST_TRACK_ACTION_META[action]["preview_note"],
        "action": action,
    }


@frappe.whitelist()
def run_fast_track_requests(filters=None, enrollment_date=None, action=None):
    action = _normalize_fast_track_action(action)
    _assert_fast_track_permissions(action=action, user=frappe.session.user)
    filters = _normalize_fast_track_filters(filters)
    _normalized, requests = get_filtered_requests(filters, require_matrix_offering=False)
    request_names = [request.get("name") for request in requests if request.get("name")]
    if not request_names:
        frappe.throw(_("No Program Enrollment Requests match the current filters."))

    resolved_enrollment_date = ""
    if FAST_TRACK_ACTION_META[action]["requires_enrollment_date"]:
        resolved_enrollment_date = str(
            _resolve_requested_enrollment_date(
                academic_year=filters.get("academic_year"),
                enrollment_date=enrollment_date,
            )
        )
    target_user = frappe.session.user

    if len(request_names) > FAST_TRACK_QUEUE_THRESHOLD:
        frappe.enqueue(
            _run_fast_track_job,
            queue="long",
            job_name=f"{action} {len(request_names)} Program Enrollment Requests",
            request_names=request_names,
            enrollment_date=resolved_enrollment_date,
            target_user=target_user,
            action=action,
        )
        return {
            "queued": 1,
            "request_count": len(request_names),
            "message": FAST_TRACK_ACTION_META[action]["queue_message"].format(len(request_names)),
            "action": action,
        }

    return _execute_fast_track(
        request_names=request_names,
        enrollment_date=resolved_enrollment_date,
        target_user=target_user,
        batch_mode=False,
        action=action,
    )


def _normalize_fast_track_filters(filters):
    if isinstance(filters, str):
        filters = frappe.parse_json(filters)

    filters = frappe._dict(filters or {})
    filters["view_mode"] = VIEW_MODE_SUMMARY
    filters["request_kind"] = (filters.get("request_kind") or ACADEMIC_REQUEST_KIND).strip() or ACADEMIC_REQUEST_KIND
    filters["latest_request_only"] = 1 if int(filters.get("latest_request_only") or 0) == 1 else 0

    if filters["request_kind"] != ACADEMIC_REQUEST_KIND:
        frappe.throw(_("Fast-track enrollment only supports Academic requests."))
    if filters["latest_request_only"] != 1:
        frappe.throw(
            _(
                "Fast-track enrollment requires Latest Request Only = 1 so older requests cannot materialize over newer intent."
            )
        )
    return filters


def _normalize_fast_track_action(action) -> str:
    normalized = (action or ACTION_APPROVE_AND_MATERIALIZE).strip() or ACTION_APPROVE_AND_MATERIALIZE
    if normalized not in FAST_TRACK_ACTION_META:
        frappe.throw(_("Unsupported batch request action: {0}.").format(normalized))
    return normalized


def _get_batch_action_access(*, user: str | None):
    actor = (user or frappe.session.user or "").strip()
    can_approve = frappe.has_permission("Program Enrollment Request", ptype="write", user=actor)
    can_create_enrollment = frappe.has_permission("Program Enrollment", ptype="create", user=actor)
    can_write_enrollment = frappe.has_permission("Program Enrollment", ptype="write", user=actor)
    can_materialize = can_create_enrollment and can_write_enrollment
    return {
        "can_approve": 1 if can_approve else 0,
        "approve_reason": "" if can_approve else PERMISSION_ERROR_REQUEST,
        "can_materialize": 1 if can_materialize else 0,
        "materialize_reason": "" if can_materialize else PERMISSION_ERROR_ENROLLMENT,
    }


def _get_fast_track_access(*, user: str | None):
    access = _get_batch_action_access(user=user)
    if not access["can_approve"]:
        return False, access["approve_reason"]
    if not access["can_materialize"]:
        return False, access["materialize_reason"]
    return True, ""


def _assert_fast_track_permissions(*, action: str, user: str | None):
    access = _get_batch_action_access(user=user)
    if action == ACTION_APPROVE_ONLY and not access["can_approve"]:
        frappe.throw(access["approve_reason"])
    if action == ACTION_MATERIALIZE_ONLY and not access["can_materialize"]:
        frappe.throw(access["materialize_reason"])
    if action == ACTION_APPROVE_AND_MATERIALIZE:
        can_run, reason = _get_fast_track_access(user=user)
        if not can_run:
            frappe.throw(reason)


def _resolve_default_enrollment_date(academic_year: str):
    row = frappe.db.get_value(
        "Academic Year",
        academic_year,
        ["year_start_date", "year_end_date"],
        as_dict=True,
    )
    if not row or not row.get("year_start_date") or not row.get("year_end_date"):
        frappe.throw(_("Selected Academic Year must have start and end dates."))
    return getdate(row.get("year_start_date"))


def _resolve_requested_enrollment_date(*, academic_year: str, enrollment_date=None):
    row = frappe.db.get_value(
        "Academic Year",
        academic_year,
        ["year_start_date", "year_end_date"],
        as_dict=True,
    )
    if not row or not row.get("year_start_date") or not row.get("year_end_date"):
        frappe.throw(_("Selected Academic Year must have start and end dates."))

    ay_start = getdate(row.get("year_start_date"))
    ay_end = getdate(row.get("year_end_date"))
    resolved = getdate(enrollment_date) if enrollment_date else ay_start
    if not (ay_start <= resolved <= ay_end):
        frappe.throw(_("Enrollment Date must fall inside Academic Year {0}.").format(academic_year))
    return resolved


def _get_materialized_request_names(request_names: list[str]) -> set[str]:
    names = [(name or "").strip() for name in (request_names or []) if (name or "").strip()]
    if not names:
        return set()
    return set(
        frappe.get_all(
            "Program Enrollment",
            filters={"program_enrollment_request": ["in", names]},
            pluck="program_enrollment_request",
        )
    )


def _build_preview_counts(*, requests: list[dict], materialized_request_names: set[str], action: str):
    counts = Counter(selected=len(requests or []))
    for request in requests or []:
        name = (request.get("name") or "").strip()
        status = (request.get("request_status") or "").strip()
        validation_status = (request.get("validation_status") or "").strip()
        requires_override = int(request.get("requires_override") or 0) == 1

        if action == ACTION_APPROVE_ONLY:
            if name in materialized_request_names:
                counts["already_materialized"] += 1
                continue
            if status in {"Rejected", "Cancelled"}:
                counts["terminal"] += 1
                continue
            if status == "Approved" and validation_status == "Valid":
                counts["already_approved"] += 1
                continue
            if requires_override:
                counts["needs_override"] += 1
                continue
            if validation_status == "Valid":
                counts["ready_to_approve"] += 1
            elif validation_status == "Invalid":
                counts["invalid"] += 1
            else:
                counts["needs_validation"] += 1
            continue

        if action == ACTION_MATERIALIZE_ONLY:
            if name in materialized_request_names:
                counts["already_materialized"] += 1
                continue
            if status in {"Rejected", "Cancelled"}:
                counts["terminal"] += 1
                continue
            if status == "Approved" and validation_status == "Valid":
                counts["ready_to_materialize"] += 1
            else:
                counts["not_ready"] += 1
            continue

        if name in materialized_request_names:
            counts["already_materialized"] += 1
            continue
        if status in {"Rejected", "Cancelled"}:
            counts["terminal"] += 1
            continue
        if requires_override:
            counts["needs_override"] += 1
            continue
        if validation_status == "Valid":
            counts["currently_valid"] += 1
            if status == "Approved":
                counts["ready_now"] += 1
        elif validation_status == "Invalid":
            counts["currently_invalid"] += 1
        else:
            counts["pending_validation"] += 1

    return counts


def _publish_progress(*, position: int, total: int, target_user: str, action: str):
    frappe.publish_realtime(
        FAST_TRACK_PROGRESS_EVENT,
        {
            "action_label": FAST_TRACK_ACTION_META[action]["progress_label"],
            "progress": [position, total],
        },
        user=target_user,
    )


def _finalize(*, counts: dict, issues: list[tuple[str, str, str]], target_user: str, batch_mode: bool, action: str):
    summary = {
        "title": FAST_TRACK_ACTION_META[action]["title"],
        "counts": counts,
        "action": action,
    }

    if issues:
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["request", "student", "detail"])
        for request_name, student, detail in issues:
            writer.writerow([request_name, student, detail])
        filedoc = save_file(
            f"program_enrollment_request_fast_track_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv",
            buf.getvalue(),
            "User",
            target_user,
            is_private=1,
        )
        summary["details_link"] = filedoc.file_url

    if batch_mode:
        frappe.publish_realtime(FAST_TRACK_DONE_EVENT, summary, user=target_user)
    return summary


def _execute_fast_track(
    *, request_names: list[str], enrollment_date: str, target_user: str, batch_mode: bool, action: str
):
    names = [(name or "").strip() for name in (request_names or []) if (name or "").strip()]
    if not names:
        frappe.throw(_("No Program Enrollment Requests were selected for fast-track processing."))

    materialized_request_names = _get_materialized_request_names(names)
    if action == ACTION_APPROVE_ONLY:
        counts = {
            "selected": len(names),
            "approved_now": 0,
            "already_approved": 0,
            "already_materialized": 0,
            "invalid": 0,
            "needs_override": 0,
            "blocked": 0,
            "failed": 0,
        }
    elif action == ACTION_MATERIALIZE_ONLY:
        counts = {
            "selected": len(names),
            "materialized": 0,
            "already_materialized": 0,
            "blocked": 0,
            "failed": 0,
        }
    else:
        counts = {
            "selected": len(names),
            "approved_now": 0,
            "already_approved": 0,
            "materialized": 0,
            "already_materialized": 0,
            "invalid": 0,
            "needs_override": 0,
            "blocked": 0,
            "failed": 0,
        }
    issues: list[tuple[str, str, str]] = []
    total = len(names)

    for position, request_name in enumerate(names, start=1):
        request_doc = None
        student = ""
        try:
            request_doc = frappe.get_doc("Program Enrollment Request", request_name)
            student = (request_doc.student or "").strip()
            status = (request_doc.status or "").strip()
            request_kind = (request_doc.request_kind or ACADEMIC_REQUEST_KIND).strip() or ACADEMIC_REQUEST_KIND

            if request_name in materialized_request_names:
                counts["already_materialized"] += 1
                issues.append((request_name, student, _("Enrollment already exists for this request.")))
                continue

            if request_kind != ACADEMIC_REQUEST_KIND:
                counts["blocked"] += 1
                issues.append((request_name, student, _("Activity requests are excluded from fast-track enrollment.")))
                continue

            if status in {"Rejected", "Cancelled"}:
                counts["blocked"] += 1
                issues.append((request_name, student, _("Request is in terminal status {0}.").format(status)))
                continue

            if action in {ACTION_APPROVE_ONLY, ACTION_APPROVE_AND_MATERIALIZE}:
                if status == "Approved" and (request_doc.validation_status or "").strip() == "Valid":
                    counts["already_approved"] += 1
                else:
                    if status == "Draft":
                        request_doc.status = "Submitted"
                        request_doc.save(ignore_permissions=True)
                        request_doc.reload()
                    else:
                        validate_program_enrollment_request(request_doc.name, force=1)
                        request_doc.reload()

                    if (request_doc.validation_status or "").strip() != "Valid":
                        counts["invalid"] += 1
                        issues.append((request_name, student, _("Request is invalid and needs review.")))
                        continue

                    if int(request_doc.requires_override or 0) == 1:
                        counts["needs_override"] += 1
                        issues.append((request_name, student, _("Request requires an override before approval.")))
                        continue

                    if (request_doc.status or "").strip() != "Approved":
                        request_doc.status = "Approved"
                        request_doc.save(ignore_permissions=True)
                        request_doc.reload()
                        counts["approved_now"] += 1
                    else:
                        counts["already_approved"] += 1

                if action == ACTION_APPROVE_ONLY:
                    continue

            if (request_doc.status or "").strip() != "Approved" or (
                request_doc.validation_status or ""
            ).strip() != "Valid":
                counts["blocked"] += 1
                issues.append((request_name, student, _("Request must be Approved and Valid before materializing.")))
                continue

            materialize_program_enrollment_request(request_doc.name, enrollment_date=enrollment_date)
            request_doc.add_comment(
                "Comment",
                _("{0} on {1}.").format(FAST_TRACK_ACTION_META[action]["title"], enrollment_date),
            )
            counts["materialized"] += 1
        except Exception as exc:
            counts["failed"] += 1
            issues.append((request_name, student, str(exc)))
        finally:
            _publish_progress(position=position, total=total, target_user=target_user, action=action)

    return _finalize(
        counts=counts,
        issues=issues,
        target_user=target_user,
        batch_mode=batch_mode,
        action=action,
    )
