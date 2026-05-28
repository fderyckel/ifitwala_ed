from __future__ import annotations

from frappe import _

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.api.timeline.utils import (
    _as_bool,
    _as_text,
    _desk_url,
    _item,
    _preview,
    _subtitle,
)


def _context_labels(context: dict, **extra) -> dict:
    labels = {
        "organization": context.get("organization"),
        "school": context.get("school"),
        "inquiry": (context.get("inquiry") or {}).get("name"),
        "student_applicant": (context.get("applicant") or {}).get("name"),
    }
    for key, value in extra.items():
        if clean(value):
            labels[key] = value
    return {key: value for key, value in labels.items() if clean(value)}


def _conversation_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        status = clean(row.get("status"))
        title = _("Admissions conversation opened")
        if status in {"Closed", "Archived"}:
            title = _("Admissions conversation {status}").format(status=status.lower())
        items.append(
            _item(
                kind="touchpoint",
                source_doctype="Admission Conversation",
                source_name=row["name"],
                occurred_at=row.get("creation"),
                title=title,
                summary=_preview(row.get("last_message_preview")),
                actor=clean(row.get("assigned_to")),
                context_labels=_context_labels(
                    context,
                    conversation=row.get("name"),
                    status=row.get("status"),
                ),
                open_url=_desk_url("Admission Conversation", row.get("name")),
                actions=[{"id": "open_conversation", "label": _("Open Conversation"), "enabled": True}],
            )
        )
    return items


def _inquiry_item(row: dict | None, context: dict) -> list[dict]:
    if not row:
        return []
    title = _("Inquiry captured")
    if clean(row.get("workflow_state")) == "Archived":
        title = _("Inquiry archived")
    summary = _subtitle(
        [clean(row.get("workflow_state")), clean(row.get("type_of_inquiry")), _preview(row.get("message"))]
    )
    return [
        _item(
            kind="intake",
            source_doctype="Inquiry",
            source_name=row["name"],
            occurred_at=row.get("submitted_at") or row.get("creation"),
            title=title,
            summary=summary,
            actor=clean(row.get("assigned_to")),
            context_labels=_context_labels(context),
            open_url=_desk_url("Inquiry", row.get("name")),
            actions=[{"id": "open_inquiry", "label": _("Open Inquiry"), "enabled": True}],
        )
    ]


def _applicant_item(row: dict | None, context: dict) -> list[dict]:
    if not row:
        return []
    status = clean(row.get("application_status"))
    return [
        _item(
            kind="applicant",
            source_doctype="Student Applicant",
            source_name=row["name"],
            occurred_at=row.get("submitted_at") or row.get("creation"),
            title=_("Applicant {status}").format(status=status.lower() if status else _("created")),
            summary=_subtitle([status, clean(row.get("program")), clean(row.get("academic_year"))]),
            context_labels=_context_labels(context),
            open_url=_desk_url("Student Applicant", row.get("name")),
            actions=[{"id": "open_applicant", "label": _("Open Applicant"), "enabled": True}],
        )
    ]


def _message_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        direction = clean(row.get("direction"))
        message_type = clean(row.get("message_type")) or _("message")
        title = _("Inbound message") if direction == "Inbound" else _("Outbound message")
        if direction == "System":
            title = _("System message")
        items.append(
            _item(
                kind="message",
                source_doctype="Admission Message",
                source_name=row["name"],
                occurred_at=row.get("message_at") or row.get("creation"),
                title=title,
                summary=_subtitle([message_type, _preview(row.get("body"))]),
                actor=direction,
                context_labels=_context_labels(
                    context,
                    conversation=row.get("conversation"),
                    inquiry=row.get("linked_inquiry"),
                    student_applicant=row.get("linked_student_applicant"),
                ),
                open_url=_desk_url("Admission Message", row.get("name")),
                actions=[{"id": "open_message", "label": _("Open Message"), "enabled": True}],
            )
        )
    return items


def _activity_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        activity_type = clean(row.get("activity_type")) or _("Touchpoint")
        items.append(
            _item(
                kind="touchpoint",
                source_doctype="Admission CRM Activity",
                source_name=row["name"],
                occurred_at=row.get("activity_at") or row.get("creation"),
                title=activity_type,
                summary=_subtitle(
                    [clean(row.get("activity_channel")), clean(row.get("outcome")), _preview(row.get("note"))]
                ),
                actor=clean(row.get("staff_user")),
                context_labels=_context_labels(
                    context,
                    conversation=row.get("conversation"),
                    inquiry=row.get("inquiry"),
                    student_applicant=row.get("student_applicant"),
                ),
                open_url=_desk_url("Admission CRM Activity", row.get("name")),
                actions=[{"id": "open_activity", "label": _("Open Activity"), "enabled": True}],
            )
        )
    return items


def _visit_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        items.append(
            _item(
                kind="visit",
                source_doctype="Admission Visit",
                source_name=row["name"],
                occurred_at=row.get("starts_on") or row.get("creation"),
                title=clean(row.get("visit_title")) or _("Admission visit"),
                summary=_subtitle(
                    [
                        clean(row.get("status")),
                        clean(row.get("visit_type")),
                        clean(row.get("visit_mode")),
                        clean(row.get("location")),
                    ]
                ),
                actor=clean(row.get("lead_user")),
                context_labels=_context_labels(
                    context,
                    conversation=row.get("conversation"),
                    inquiry=row.get("inquiry"),
                    student_applicant=row.get("student_applicant"),
                ),
                open_url=_desk_url("Admission Visit", row.get("name")),
                actions=[{"id": "open_visit", "label": _("Open Visit"), "enabled": True}],
            )
        )
    return items


def _applicant_case_item(applicant_row: dict | None, case_summary: dict, context: dict) -> list[dict]:
    if not applicant_row or not clean(case_summary.get("thread_name")):
        return []
    return [
        _item(
            kind="message",
            source_doctype="Org Communication",
            source_name=case_summary["thread_name"],
            occurred_at=case_summary.get("last_message_at") or applicant_row.get("modified"),
            title=_("Applicant case message"),
            summary=_preview(case_summary.get("last_message_preview")),
            actor=clean(case_summary.get("last_message_from")),
            context_labels=_context_labels(context, student_applicant=applicant_row.get("name")),
            open_url=_desk_url("Student Applicant", applicant_row.get("name")),
            actions=[{"id": "message_family", "label": _("Message Family"), "enabled": True}],
        )
    ]


def _plan_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        status = clean(row.get("status"))
        offer_at = (
            row.get("offer_accepted_on") or row.get("offer_sent_on") or row.get("modified") or row.get("creation")
        )
        items.append(
            _item(
                kind="offer",
                source_doctype="Applicant Enrollment Plan",
                source_name=row["name"],
                occurred_at=offer_at,
                title=_("Offer plan {status}").format(status=status.lower() if status else _("updated")),
                summary=_subtitle([status, clean(row.get("program_offering")), clean(row.get("academic_year"))]),
                actor=clean(row.get("hydrated_by")),
                context_labels=_context_labels(context, student_applicant=row.get("student_applicant")),
                open_url=_desk_url("Applicant Enrollment Plan", row.get("name")),
                actions=[{"id": "manage_offer", "label": _("Manage Offer"), "enabled": True}],
            )
        )
        if _as_bool(row.get("deposit_required")) or clean(row.get("deposit_invoice")):
            deposit_summary = (
                _("Deposit invoice linked") if clean(row.get("deposit_invoice")) else _("Deposit required")
            )
            items.append(
                _item(
                    kind="deposit",
                    source_doctype="Applicant Enrollment Plan",
                    source_name=row["name"],
                    occurred_at=row.get("deposit_due_date") or row.get("modified") or row.get("creation"),
                    title=_("Admissions deposit"),
                    summary=_subtitle([deposit_summary, _as_text(row.get("deposit_due_date"))]),
                    context_labels=_context_labels(context, student_applicant=row.get("student_applicant")),
                    open_url=_desk_url("Applicant Enrollment Plan", row.get("name")),
                    actions=[{"id": "check_deposit", "label": _("Check Deposit"), "enabled": True}],
                )
            )
    return items


def _request_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        items.append(
            _item(
                kind="enrollment",
                source_doctype="Program Enrollment Request",
                source_name=row["name"],
                occurred_at=row.get("modified") or row.get("creation"),
                title=_("Enrollment request {status}").format(status=clean(row.get("status")).lower()),
                summary=_subtitle(
                    [clean(row.get("request_kind")), clean(row.get("program")), clean(row.get("academic_year"))]
                ),
                context_labels=_context_labels(
                    context,
                    student_applicant=row.get("source_student_applicant"),
                ),
                open_url=_desk_url("Program Enrollment Request", row.get("name")),
                actions=[{"id": "open_enrollment_request", "label": _("Open Request"), "enabled": True}],
            )
        )
    return items


def _program_enrollment_items(rows: list[dict], context: dict) -> list[dict]:
    items: list[dict] = []
    for row in rows:
        archived = _as_bool(row.get("archived"))
        items.append(
            _item(
                kind="enrollment",
                source_doctype="Program Enrollment",
                source_name=row["name"],
                occurred_at=row.get("enrollment_date") or row.get("creation"),
                title=_("Program enrollment archived") if archived else _("Program enrollment active"),
                summary=_subtitle(
                    [clean(row.get("program")), clean(row.get("academic_year")), clean(row.get("enrollment_source"))]
                ),
                context_labels=_context_labels(context),
                open_url=_desk_url("Program Enrollment", row.get("name")),
                actions=[{"id": "open_enrollment", "label": _("Open Enrollment"), "enabled": True}],
            )
        )
    return items


def _promotion_item(applicant_row: dict | None, context: dict) -> list[dict]:
    if not applicant_row or not clean(applicant_row.get("student")):
        return []
    return [
        _item(
            kind="enrollment",
            source_doctype="Student Applicant",
            source_name=applicant_row["name"],
            occurred_at=applicant_row.get("decision_at")
            or applicant_row.get("modified")
            or applicant_row.get("creation"),
            title=_("Applicant promoted to student"),
            summary=clean(applicant_row.get("student")),
            context_labels=_context_labels(context, student_applicant=applicant_row.get("name")),
            open_url=_desk_url("Student Applicant", applicant_row.get("name")),
            actions=[{"id": "open_student", "label": _("Open Student"), "enabled": True}],
        )
    ]
