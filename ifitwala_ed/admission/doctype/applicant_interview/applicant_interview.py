# ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py

from __future__ import annotations

import re
from datetime import datetime, time, timedelta
from html.parser import HTMLParser
from typing import Iterable, Sequence

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import format_datetime, get_datetime, get_link_to_form, getdate, now_datetime, nowdate

from ifitwala_ed.admission.admission_utils import (
    ADMISSIONS_ROLES,
    READ_LIKE_PERMISSION_TYPES,
    build_admissions_file_scope_exists_sql,
    build_open_applicant_review_access_exists_sql,
    has_open_applicant_review_access,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
)
from ifitwala_ed.api.file_access import resolve_admissions_file_open_url
from ifitwala_ed.api.recommendation_intake import get_recommendation_status_for_applicant
from ifitwala_ed.utilities.employee_booking import find_employee_conflicts
from ifitwala_ed.utilities.location_utils import (
    find_room_conflicts,
    get_visible_location_rows_for_school,
    is_schedulable_location,
)

TERMINAL_APPLICANT_STATES = {"Rejected", "Promoted"}
DEFAULT_INTERVIEW_DURATION_MINUTES = 30
DEFAULT_SUGGESTION_WINDOW_START = "07:00:00"
DEFAULT_SUGGESTION_WINDOW_END = "17:00:00"
DEFAULT_SUGGESTION_LIMIT = 8
DEFAULT_SUGGESTION_STEP_MINUTES = 15
INTERVIEW_EVENT_REFERENCE_TYPE = "Applicant Interview"
INTERVIEW_FEEDBACK_FIELDS = (
    "strengths",
    "concerns",
    "shared_values",
    "other_notes",
    "recommendation",
)
INTERVIEW_FEEDBACK_STATUS = {"Draft", "Submitted"}
INTERVIEW_TIMELINE_LIMIT = 8
INTERVIEW_WORKSPACE_DOC_LIMIT = 30
INTERVIEW_WORKSPACE_INTERVIEW_LIMIT = 20
INTERVIEW_FEEDBACK_DOCTYPE = "Applicant Interview Feedback"
_RICH_TEXT_BLOCK_TAGS = {
    "blockquote",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "ol",
    "p",
    "tr",
    "ul",
}


class _RichTextPlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "li":
            self._append_newline()
            self._parts.append("- ")
        elif tag.lower() in _RICH_TEXT_BLOCK_TAGS:
            self._append_newline()

    def handle_endtag(self, tag):
        if tag.lower() in _RICH_TEXT_BLOCK_TAGS:
            self._append_newline()

    def handle_data(self, data):
        if data:
            self._parts.append(data)

    def _append_newline(self):
        if self._parts and not self._parts[-1].endswith("\n"):
            self._parts.append("\n")

    def get_text(self):
        text = "".join(self._parts).replace("\xa0", " ")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line).strip()


class ApplicantInterview(Document):
    def validate(self):
        self._validate_permissions()
        self._validate_applicant_state()
        self._validate_time_window()
        self._sync_interview_date_from_start()

    def after_insert(self):
        self._add_audit_comment("Interview recorded")

    def on_update(self):
        # Frappe calls on_update during insert as well; avoid duplicate insert-time audit rows.
        if getattr(self.flags, "in_insert", False):
            return
        if not self.get_doc_before_save():
            return
        self._add_audit_comment("Interview updated")

    def _validate_permissions(self):
        _assert_manage_interview_permission(
            interview_name=self.name if not self.is_new() else None,
            student_applicant=self.student_applicant,
        )

    def _validate_applicant_state(self):
        if not self.student_applicant:
            return
        status = frappe.db.get_value("Student Applicant", self.student_applicant, "application_status")
        if status in TERMINAL_APPLICANT_STATES:
            frappe.throw(_("Applicant is read-only in terminal states."))

    def _validate_time_window(self):
        has_start = bool(self.get("interview_start"))
        has_end = bool(self.get("interview_end"))

        if has_start != has_end:
            frappe.throw(_("Interview Start and Interview End must both be set."), title=_("Incomplete Time Window"))

        if self._requires_schedule_interview_path():
            frappe.throw(
                _(
                    "New interviews must be scheduled from Schedule Interview so interviewer calendars and rooms are checked."
                ),
                title=_("Use Schedule Interview"),
            )

        if not has_start or not has_end:
            return

        start_dt = _to_datetime_or_throw(self.get("interview_start"), fieldname="interview_start")
        end_dt = _to_datetime_or_throw(self.get("interview_end"), fieldname="interview_end")

        if end_dt <= start_dt:
            frappe.throw(
                _("Interview End must be after Interview Start."),
                title=_("Invalid Time Window"),
            )

    def _sync_interview_date_from_start(self):
        if self.get("interview_start"):
            self.interview_date = getdate(self.interview_start)

    def _requires_schedule_interview_path(self):
        return (
            self.is_new()
            and not self.get("school_event")
            and not getattr(self.flags, "from_schedule_applicant_interview", False)
            and not getattr(self.flags, "ignore_permissions", False)
        )

    def _add_audit_comment(self, label):
        if not self.student_applicant:
            return
        applicant = frappe.get_doc("Student Applicant", self.student_applicant)
        interview_link = get_link_to_form("Applicant Interview", self.name)
        applicant.add_comment(
            "Comment",
            text=_("{label}: {interview} by {user} on {timestamp}.").format(
                label=label,
                interview=interview_link,
                user=frappe.bold(frappe.session.user),
                timestamp=now_datetime(),
            ),
        )


@frappe.whitelist()
def get_interview_schedule_options(*, student_applicant: str):
    """
    Return one bounded payload for Schedule Interview surfaces.

    Desk and the Admissions Cockpit use this to avoid assembling the same
    applicant, interviewer-default, and room context through separate calls.
    """

    _assert_manage_interview_permission(student_applicant=student_applicant)
    applicant_row = _get_applicant_context(student_applicant)

    room_rows = []
    if applicant_row.get("school"):
        room_rows = get_visible_location_rows_for_school(
            applicant_row.get("school"),
            include_groups=False,
            only_schedulable=True,
            fields=[
                "name",
                "location_name",
                "school",
                "parent_location",
                "location_type",
                "maximum_capacity",
            ],
            limit=200,
        )

    return {
        "ok": True,
        "applicant": {
            "name": applicant_row.get("name"),
            "display_name": _applicant_display_name(applicant_row),
            "school": applicant_row.get("school"),
        },
        "defaults": {
            "date": nowdate(),
            "start_time": "09:00:00",
            "duration_minutes": DEFAULT_INTERVIEW_DURATION_MINUTES,
            "window_start_time": DEFAULT_SUGGESTION_WINDOW_START,
            "window_end_time": DEFAULT_SUGGESTION_WINDOW_END,
            "current_user": frappe.session.user,
        },
        "rooms": [_serialize_room_option(row) for row in room_rows],
        "interview_types": ["Family", "Student", "Joint"],
        "modes": ["In Person", "Online", "Phone"],
        "confidentiality_levels": ["Admissions Team", "Leadership Only"],
    }


@frappe.whitelist()
def suggest_interview_slots(
    *,
    student_applicant: str | None = None,
    interview_date: str | None = None,
    primary_interviewer: str | None = None,
    interviewer_users: Sequence[str] | str | None = None,
    mode: str | None = None,
    location: str | None = None,
    duration_minutes: int | str | None = None,
    window_start_time=None,
    window_end_time=None,
    limit: int | str | None = None,
):
    """
    Return common free slot suggestions for selected interviewers on a given date.

    This endpoint is reusable by Desk dialogs and SPA overlays.
    """

    _assert_manage_interview_permission(student_applicant=student_applicant)
    applicant_row = _get_applicant_context(student_applicant) if student_applicant else None
    location_value = _resolve_schedule_location(
        location=location,
        mode=mode,
        applicant_row=applicant_row,
        require_for_in_person=False,
    )

    target_date = _to_date_or_throw(interview_date, fieldname="interview_date")
    selected_users = _normalize_interviewer_users(
        primary_interviewer=primary_interviewer,
        interviewer_users=interviewer_users,
    )
    if not selected_users:
        selected_users = [frappe.session.user]

    _assert_users_exist_and_enabled(selected_users)
    employee_rows = _resolve_employee_rows_for_users(selected_users)

    duration = _to_positive_int(
        value=duration_minutes,
        default=DEFAULT_INTERVIEW_DURATION_MINUTES,
        fieldname="duration_minutes",
    )

    start_time = _coerce_time(
        window_start_time or DEFAULT_SUGGESTION_WINDOW_START,
        fieldname="window_start_time",
    )
    end_time = _coerce_time(
        window_end_time or DEFAULT_SUGGESTION_WINDOW_END,
        fieldname="window_end_time",
    )

    window_start, window_end = _build_window_datetimes_for_date(
        target_date=target_date,
        start_time=start_time,
        end_time=end_time,
    )

    max_rows = _to_positive_int(value=limit, default=DEFAULT_SUGGESTION_LIMIT, fieldname="limit")
    slots = _suggest_common_free_slots(
        employees=[row["name"] for row in employee_rows],
        location=location_value,
        window_start=window_start,
        window_end=window_end,
        duration_minutes=duration,
        step_minutes=DEFAULT_SUGGESTION_STEP_MINUTES,
        limit=max_rows,
    )

    return {
        "ok": True,
        "interviewers": [
            {
                "user": row["user_id"],
                "employee": row["name"],
                "employee_name": row.get("employee_full_name") or row["name"],
            }
            for row in employee_rows
        ],
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "duration_minutes": duration,
            "step_minutes": DEFAULT_SUGGESTION_STEP_MINUTES,
            "location": location_value,
        },
        "slots": slots,
    }


def get_permission_query_conditions(user: str | None = None) -> str | None:
    user = (user or frappe.session.user or "").strip()
    if not user or user == "Guest":
        return "1=0"

    conditions: list[str] = []
    if _is_interview_privileged_user(user):
        staff_condition = build_admissions_file_scope_exists_sql(
            user=user,
            student_applicant_expr_sql="`tabApplicant Interview`.`student_applicant`",
        )
        if staff_condition is None:
            return None
        if staff_condition != "1=0":
            conditions.append(f"({staff_condition})")

    escaped_user = frappe.db.escape(user)
    interviewer_condition = (
        "exists ("
        "select 1 from `tabApplicant Interviewer` ai "
        "where ai.parent = `tabApplicant Interview`.`name` "
        "and ai.parenttype = 'Applicant Interview' "
        "and ai.parentfield = 'interviewers' "
        f"and ai.interviewer = {escaped_user}"
        ")"
    )
    conditions.append(f"({interviewer_condition})")
    reviewer_condition = build_open_applicant_review_access_exists_sql(
        user=user,
        student_applicant_expr_sql="`tabApplicant Interview`.`student_applicant`",
    )
    if reviewer_condition != "1=0":
        conditions.append(f"({reviewer_condition})")
    return " OR ".join(conditions) if conditions else "1=0"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()
    if not user or user == "Guest":
        return False

    if op == "create":
        return _is_interview_privileged_user(user)
    if op in {"delete", "submit"}:
        return False
    if op == "write" and not _is_interview_privileged_user(user):
        return False
    if op not in READ_LIKE_PERMISSION_TYPES and op != "write":
        return False

    if _is_interview_privileged_user(user):
        if not doc:
            return True
        student_applicant = _resolve_interview_student_applicant(doc)
        return has_scoped_staff_access_to_student_applicant(user=user, student_applicant=student_applicant)

    if op in READ_LIKE_PERMISSION_TYPES and doc:
        student_applicant = _resolve_interview_student_applicant(doc)
        if has_open_applicant_review_access(user=user, student_applicant=student_applicant):
            return True

    if not doc:
        if op not in READ_LIKE_PERMISSION_TYPES:
            return False
        return bool(
            frappe.db.exists(
                "Applicant Interviewer",
                {
                    "parenttype": "Applicant Interview",
                    "parentfield": "interviewers",
                    "interviewer": user,
                },
            )
        )

    if isinstance(doc, str):
        interview_name = (doc or "").strip()
    elif isinstance(doc, dict):
        interview_name = (doc.get("name") or "").strip()
    else:
        interview_name = (getattr(doc, "name", None) or "").strip()
    if not interview_name:
        return False

    return _is_interviewer_on_interview(user=user, interview_name=interview_name)


@frappe.whitelist()
def schedule_applicant_interview(
    *,
    student_applicant: str,
    interview_start: str,
    interview_end: str | None = None,
    duration_minutes: int | str | None = None,
    interview_type: str | None = None,
    mode: str | None = None,
    location: str | None = None,
    confidentiality_level: str | None = None,
    notes: str | None = None,
    primary_interviewer: str | None = None,
    interviewer_users: Sequence[str] | str | None = None,
    suggestion_window_start_time=None,
    suggestion_window_end_time=None,
    suggestion_limit: int | str | None = None,
):
    """
    Atomically create Applicant Interview + linked School Event.

    If the selected interviewers or room are busy, returns a structured
    conflict payload with suggested alternative times instead of throwing a hard
    validation error.
    """

    _assert_manage_interview_permission(student_applicant=student_applicant)

    applicant_row = _get_applicant_context(student_applicant)
    location_value = _resolve_schedule_location(
        location=location,
        mode=mode,
        applicant_row=applicant_row,
        require_for_in_person=True,
    )

    selected_users = _normalize_interviewer_users(
        primary_interviewer=primary_interviewer,
        interviewer_users=interviewer_users,
    )
    if not selected_users:
        selected_users = [frappe.session.user]

    _assert_users_exist_and_enabled(selected_users)
    employee_rows = _resolve_employee_rows_for_users(selected_users)

    start_dt = _to_datetime_or_throw(interview_start, fieldname="interview_start")
    if interview_end:
        end_dt = _to_datetime_or_throw(interview_end, fieldname="interview_end")
    else:
        minutes = _to_positive_int(
            value=duration_minutes,
            default=DEFAULT_INTERVIEW_DURATION_MINUTES,
            fieldname="duration_minutes",
        )
        end_dt = start_dt + timedelta(minutes=minutes)

    if end_dt <= start_dt:
        frappe.throw(_("Interview End must be after Interview Start."), title=_("Invalid Time Window"))

    employee_conflict_rows = _collect_employee_conflicts(
        employee_rows=employee_rows,
        start_dt=start_dt,
        end_dt=end_dt,
        exclude_source=None,
    )
    room_conflict_rows = _collect_room_conflicts(
        location=location_value,
        start_dt=start_dt,
        end_dt=end_dt,
        exclude_source=None,
    )
    conflict_rows = _combine_conflict_rows(
        employee_conflict_rows=employee_conflict_rows,
        room_conflict_rows=room_conflict_rows,
    )

    if conflict_rows:
        window_start_time = _coerce_time(
            suggestion_window_start_time or DEFAULT_SUGGESTION_WINDOW_START,
            fieldname="suggestion_window_start_time",
        )
        window_end_time = _coerce_time(
            suggestion_window_end_time or DEFAULT_SUGGESTION_WINDOW_END,
            fieldname="suggestion_window_end_time",
        )
        suggestion_window_start, suggestion_window_end = _build_window_datetimes_for_date(
            target_date=getdate(start_dt),
            start_time=window_start_time,
            end_time=window_end_time,
        )

        suggestion_rows = _suggest_common_free_slots(
            employees=[row["name"] for row in employee_rows],
            location=location_value,
            window_start=suggestion_window_start,
            window_end=suggestion_window_end,
            duration_minutes=int((end_dt - start_dt).total_seconds() // 60),
            step_minutes=DEFAULT_SUGGESTION_STEP_MINUTES,
            limit=_to_positive_int(
                value=suggestion_limit,
                default=DEFAULT_SUGGESTION_LIMIT,
                fieldname="suggestion_limit",
            ),
        )

        conflict_code = _schedule_conflict_code(
            employee_conflict_rows=employee_conflict_rows,
            room_conflict_rows=room_conflict_rows,
        )
        return {
            "ok": False,
            "code": conflict_code,
            "message": _schedule_conflict_message(conflict_code),
            "conflicts": conflict_rows,
            "employee_conflicts": employee_conflict_rows,
            "room_conflicts": room_conflict_rows,
            "suggestions": suggestion_rows,
            "window": {
                "start": suggestion_window_start.isoformat(),
                "end": suggestion_window_end.isoformat(),
                "location": location_value,
            },
        }

    savepoint = "schedule_applicant_interview"
    frappe.db.savepoint(savepoint)

    try:
        interview_doc = frappe.new_doc("Applicant Interview")
        interview_doc.student_applicant = applicant_row["name"]
        interview_doc.interview_type = interview_type
        interview_doc.interview_start = start_dt
        interview_doc.interview_end = end_dt
        interview_doc.interview_date = getdate(start_dt)
        interview_doc.mode = mode
        interview_doc.location = location_value
        interview_doc.confidentiality_level = confidentiality_level
        interview_doc.notes = notes

        for user in selected_users:
            interview_doc.append("interviewers", {"interviewer": user})

        interview_doc.flags.ignore_permissions = True
        interview_doc.flags.from_schedule_applicant_interview = True
        interview_doc.insert()

        school_event_doc = _create_school_event_for_interview(
            interview_doc=interview_doc,
            applicant_row=applicant_row,
            interviewer_users=selected_users,
            starts_on=start_dt,
            ends_on=end_dt,
            location=location_value,
        )

        interview_doc.db_set("school_event", school_event_doc.name, update_modified=False)

    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

    return {
        "ok": True,
        "interview": interview_doc.name,
        "school_event": school_event_doc.name,
        "window": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "location": location_value,
        },
    }


@frappe.whitelist()
def get_interview_workspace(*, interview: str):
    interview_name = (interview or "").strip()
    if not interview_name:
        frappe.throw(_("Interview is required."), title=_("Missing Interview"))

    _assert_interview_workspace_permission(interview_name=interview_name)

    interview_doc = frappe.get_doc("Applicant Interview", interview_name)
    applicant_row = _get_applicant_workspace_context(interview_doc.student_applicant)
    timeline_rows = _load_applicant_timeline(interview_doc.student_applicant)
    document_payload = _load_applicant_documents_for_workspace(
        interview_doc.student_applicant,
        context_doctype="Applicant Interview",
        context_name=interview_name,
    )
    recommendation_payload = _load_recommendations_for_workspace(interview_doc.student_applicant)
    feedback_payload = _load_feedback_panel_for_workspace(interview_name=interview_name)

    return {
        "ok": True,
        "interview": _serialize_interview_for_workspace(interview_doc),
        "applicant": applicant_row,
        "timeline": timeline_rows,
        "documents": document_payload,
        "recommendations": recommendation_payload,
        "feedback": feedback_payload,
    }


@frappe.whitelist()
def get_applicant_workspace(*, student_applicant: str):
    applicant_name = (student_applicant or "").strip()
    if not applicant_name:
        frappe.throw(_("Student Applicant is required."), title=_("Missing Applicant"))

    _assert_applicant_workspace_permission(student_applicant=applicant_name)

    applicant_row = _get_applicant_workspace_context(applicant_name)
    applicant_doc = frappe.get_doc("Student Applicant", applicant_name)
    timeline_rows = _load_applicant_timeline(applicant_name)
    recommendation_payload = _load_recommendations_for_workspace(applicant_name)
    interview_rows = _load_interviews_for_applicant_workspace(student_applicant=applicant_name)
    current_user = (frappe.session.user or "").strip()
    document_review_payload = applicant_doc.has_required_documents()
    document_review_payload["can_review_submissions"] = _can_review_document_submissions_in_workspace(current_user)
    document_review_payload["can_manage_overrides"] = _can_manage_document_overrides_in_workspace(current_user)

    return {
        "ok": True,
        "applicant": applicant_row,
        "timeline": timeline_rows,
        "document_review": document_review_payload,
        "recommendations": recommendation_payload,
        "interviews": interview_rows,
    }


@frappe.whitelist()
def save_my_interview_feedback(
    *,
    interview: str,
    strengths: str | None = None,
    concerns: str | None = None,
    shared_values: str | None = None,
    other_notes: str | None = None,
    recommendation: str | None = None,
    feedback_status: str | None = None,
):
    interview_name = (interview or "").strip()
    if not interview_name:
        frappe.throw(_("Interview is required."), title=_("Missing Interview"))

    current_user = (frappe.session.user or "").strip()
    if not current_user or current_user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.PermissionError)

    _assert_interview_workspace_permission(interview_name=interview_name, require_write=True)
    if not _is_interviewer_on_interview(user=current_user, interview_name=interview_name):
        frappe.throw(_("Only assigned interviewers can submit interview feedback."), frappe.PermissionError)

    resolved_status = _normalize_feedback_status(feedback_status)

    feedback_doc = _load_or_create_my_feedback_doc(interview_name=interview_name, user=current_user)
    feedback_input = {
        "strengths": strengths,
        "concerns": concerns,
        "shared_values": shared_values,
        "other_notes": other_notes,
        "recommendation": recommendation,
    }
    for fieldname in INTERVIEW_FEEDBACK_FIELDS:
        feedback_doc.set(fieldname, _clean_optional_text(feedback_input.get(fieldname)))

    if (
        feedback_doc.feedback_status == "Submitted"
        and resolved_status == "Draft"
        and not _is_interview_privileged_user(current_user)
    ):
        resolved_status = "Submitted"

    feedback_doc.feedback_status = resolved_status
    feedback_doc.flags.ignore_permissions = True
    if feedback_doc.is_new():
        feedback_doc.insert()
    else:
        feedback_doc.save()

    refreshed = _load_feedback_panel_for_workspace(interview_name=interview_name)
    return {
        "ok": True,
        "feedback_name": feedback_doc.name,
        "feedback_status": feedback_doc.feedback_status,
        "submitted_on": feedback_doc.submitted_on,
        "feedback": refreshed,
    }


def _assert_manage_interview_permission(
    *,
    interview_name: str | None = None,
    student_applicant: str | None = None,
    user: str | None = None,
) -> None:
    current_user = (user or frappe.session.user or "").strip()
    if not current_user or current_user == "Guest":
        frappe.throw(_("You do not have permission to manage Applicant Interviews."), frappe.PermissionError)

    if _is_interview_privileged_user(current_user):
        target_applicant = (student_applicant or "").strip()
        if not target_applicant and interview_name:
            target_applicant = (
                frappe.db.get_value("Applicant Interview", interview_name, "student_applicant") or ""
            ).strip()
        if target_applicant and not has_scoped_staff_access_to_student_applicant(
            user=current_user,
            student_applicant=target_applicant,
        ):
            frappe.throw(_("You do not have permission to manage Applicant Interviews."), frappe.PermissionError)
        return

    frappe.throw(_("You do not have permission to manage Applicant Interviews."), frappe.PermissionError)


def _is_interview_privileged_user(user: str) -> bool:
    return is_admissions_file_staff_user(user)


def _can_review_document_submissions_in_workspace(user: str | None) -> bool:
    roles = set(frappe.get_roles(user or frappe.session.user))
    return bool(roles & (ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}))


def _can_manage_document_overrides_in_workspace(user: str | None) -> bool:
    roles = set(frappe.get_roles(user or frappe.session.user))
    return bool(roles & {"Admission Manager", "Academic Admin", "System Manager"})


def _is_interviewer_on_interview(*, user: str, interview_name: str) -> bool:
    resolved_user = (user or "").strip()
    resolved_name = (interview_name or "").strip()
    if not resolved_user or not resolved_name:
        return False
    strict_match = frappe.db.exists(
        "Applicant Interviewer",
        {
            "parent": resolved_name,
            "parenttype": "Applicant Interview",
            "parentfield": "interviewers",
            "interviewer": resolved_user,
        },
    )
    if strict_match:
        return True

    # Backward-compatible fallback for rows with missing parent metadata.
    relaxed_match = frappe.db.exists(
        "Applicant Interviewer",
        {
            "parent": resolved_name,
            "interviewer": resolved_user,
        },
    )
    if relaxed_match:
        return True

    # Legacy fieldname fallback used on early interviewer schema drafts.
    if frappe.db.table_exists("Applicant Interviewer") and frappe.db.has_column(
        "Applicant Interviewer", "interviewer_user"
    ):
        return bool(
            frappe.db.exists(
                "Applicant Interviewer",
                {
                    "parent": resolved_name,
                    "interviewer_user": resolved_user,
                },
            )
        )

    return False


def _normalized_interviewer_rows(rows: Sequence[frappe._dict] | Sequence[dict] | Sequence[Document]) -> list[str]:
    users = []
    for row in rows or []:
        if isinstance(row, dict):
            user = (row.get("interviewer") or "").strip()
        else:
            user = (getattr(row, "interviewer", None) or "").strip()
        if user:
            users.append(user)
    return sorted(set(users))


def _assert_interview_workspace_permission(
    *,
    interview_name: str,
    require_write: bool = False,
    user: str | None = None,
) -> None:
    current_user = (user or frappe.session.user or "").strip()
    if not current_user or current_user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.PermissionError)

    if _is_interview_privileged_user(current_user):
        student_applicant = (
            frappe.db.get_value("Applicant Interview", interview_name, "student_applicant") or ""
        ).strip()
        if student_applicant and has_scoped_staff_access_to_student_applicant(
            user=current_user,
            student_applicant=student_applicant,
        ):
            return
    else:
        student_applicant = (
            frappe.db.get_value("Applicant Interview", interview_name, "student_applicant") or ""
        ).strip()

    if (
        student_applicant
        and not require_write
        and has_open_applicant_review_access(
            user=current_user,
            student_applicant=student_applicant,
        )
    ):
        return

    if _is_interviewer_on_interview(user=current_user, interview_name=interview_name):
        return

    action = _("edit") if require_write else _("view")
    frappe.throw(
        _("You do not have permission to {action} this interview workspace.").format(action=action),
        frappe.PermissionError,
    )


def _assert_applicant_workspace_permission(*, student_applicant: str, user: str | None = None) -> None:
    current_user = (user or frappe.session.user or "").strip()
    if not current_user or current_user == "Guest":
        frappe.throw(_("Please sign in to continue."), frappe.PermissionError)

    if _is_interview_privileged_user(current_user):
        if has_scoped_staff_access_to_student_applicant(user=current_user, student_applicant=student_applicant):
            return
        frappe.throw(_("You do not have permission to view this applicant workspace."), frappe.PermissionError)

    if has_open_applicant_review_access(user=current_user, student_applicant=student_applicant):
        return

    frappe.throw(_("You do not have permission to view this applicant workspace."), frappe.PermissionError)


def _normalize_feedback_status(value: str | None) -> str:
    status = (value or "Draft").strip() or "Draft"
    if status not in INTERVIEW_FEEDBACK_STATUS:
        frappe.throw(
            _("Feedback Status must be one of: {statuses}.").format(
                statuses=", ".join(sorted(INTERVIEW_FEEDBACK_STATUS))
            ),
            title=_("Invalid Feedback Status"),
        )
    return status


def _clean_optional_text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_interview_student_applicant(doc) -> str:
    if isinstance(doc, str):
        interview_name = (doc or "").strip()
        if not interview_name:
            return ""
        return (frappe.db.get_value("Applicant Interview", interview_name, "student_applicant") or "").strip()

    if isinstance(doc, dict):
        student_applicant = (doc.get("student_applicant") or "").strip()
        if student_applicant:
            return student_applicant
        interview_name = (doc.get("name") or "").strip()
    else:
        student_applicant = (getattr(doc, "student_applicant", None) or "").strip()
        if student_applicant:
            return student_applicant
        interview_name = (getattr(doc, "name", None) or "").strip()

    if not interview_name:
        return ""
    return (frappe.db.get_value("Applicant Interview", interview_name, "student_applicant") or "").strip()


def _load_or_create_my_feedback_doc(*, interview_name: str, user: str):
    existing_name = frappe.db.get_value(
        INTERVIEW_FEEDBACK_DOCTYPE,
        {
            "applicant_interview": interview_name,
            "interviewer_user": user,
        },
        "name",
    )
    if existing_name:
        return frappe.get_doc(INTERVIEW_FEEDBACK_DOCTYPE, existing_name)

    student_applicant = frappe.db.get_value("Applicant Interview", interview_name, "student_applicant")
    if not student_applicant:
        frappe.throw(
            _("Applicant Interview {interview} was not found.").format(interview=interview_name),
            frappe.DoesNotExistError,
        )

    return frappe.get_doc(
        {
            "doctype": INTERVIEW_FEEDBACK_DOCTYPE,
            "applicant_interview": interview_name,
            "student_applicant": student_applicant,
            "interviewer_user": user,
            "feedback_status": "Draft",
        }
    )


def _serialize_interview_for_workspace(interview_doc: ApplicantInterview) -> dict:
    interviewer_users = _normalized_interviewer_rows(interview_doc.get("interviewers") or [])
    user_map = _user_display_map(interviewer_users)
    location_name = (interview_doc.get("location") or "").strip()
    location_label = (_location_label_map([location_name]).get(location_name) if location_name else None) or None
    return {
        "name": interview_doc.name,
        "student_applicant": interview_doc.student_applicant,
        "interview_type": interview_doc.interview_type,
        "mode": interview_doc.mode,
        "location": location_name or None,
        "location_label": location_label,
        "confidentiality_level": interview_doc.confidentiality_level,
        "interview_date": str(interview_doc.interview_date) if interview_doc.interview_date else None,
        "interview_start": interview_doc.interview_start,
        "interview_end": interview_doc.interview_end,
        "interview_start_label": format_datetime(interview_doc.interview_start)
        if interview_doc.interview_start
        else None,
        "interview_end_label": format_datetime(interview_doc.interview_end) if interview_doc.interview_end else None,
        "school_event": interview_doc.school_event,
        "operational_notes": _rich_text_to_plain_text(interview_doc.notes),
        "interviewers": [
            {
                "user": user,
                "name": user_map.get(user) or user,
            }
            for user in interviewer_users
        ],
    }


def _rich_text_to_plain_text(value: str | None) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""

    parser = _RichTextPlainTextParser()
    parser.feed(raw)
    parser.close()
    parsed = parser.get_text()
    return parsed or raw


def _get_applicant_workspace_context(student_applicant: str) -> dict:
    row = frappe.db.get_value(
        "Student Applicant",
        student_applicant,
        [
            "name",
            "first_name",
            "middle_name",
            "last_name",
            "application_status",
            "organization",
            "school",
            "program",
            "program_offering",
            "academic_year",
            "applicant_email",
            "student_date_of_birth",
            "student_gender",
            "submitted_at",
            "creation",
            "modified",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(
            _("Student Applicant {student_applicant} was not found.").format(student_applicant=student_applicant),
            frappe.DoesNotExistError,
        )

    guardians = _load_applicant_guardians_for_workspace(student_applicant)
    display_name = _applicant_display_name(row)

    return {
        "name": row.get("name"),
        "display_name": display_name,
        "application_status": row.get("application_status"),
        "organization": row.get("organization"),
        "school": row.get("school"),
        "program": row.get("program"),
        "program_offering": row.get("program_offering"),
        "academic_year": row.get("academic_year"),
        "applicant_email": row.get("applicant_email"),
        "student_date_of_birth": row.get("student_date_of_birth"),
        "student_gender": row.get("student_gender"),
        "submitted_at": row.get("submitted_at"),
        "created_on": row.get("creation"),
        "updated_on": row.get("modified"),
        "guardians": guardians,
    }


def _load_applicant_guardians_for_workspace(student_applicant: str) -> list[dict]:
    rows = frappe.get_all(
        "Student Applicant Guardian",
        filters={
            "parent": student_applicant,
            "parenttype": "Student Applicant",
            "parentfield": "guardians",
        },
        fields=[
            "guardian",
            "contact",
            "use_applicant_contact",
            "relationship",
            "is_primary",
            "can_consent",
            "salutation",
            "guardian_full_name",
            "guardian_first_name",
            "guardian_last_name",
            "guardian_gender",
            "guardian_email",
            "guardian_mobile_phone",
            "guardian_work_email",
            "guardian_work_phone",
            "is_primary_guardian",
            "is_financial_guardian",
            "user",
            "guardian_image",
            "employment_sector",
            "work_place",
            "guardian_designation",
            "idx",
        ],
        order_by="idx asc",
        ignore_permissions=True,
    )

    out = []
    for row in rows:
        first_name = (row.get("guardian_first_name") or "").strip()
        last_name = (row.get("guardian_last_name") or "").strip()
        fallback_name = " ".join(part for part in (first_name, last_name) if part)
        full_name = (row.get("guardian_full_name") or "").strip() or fallback_name or (row.get("guardian") or "")
        out.append(
            {
                "guardian": row.get("guardian"),
                "contact": row.get("contact"),
                "use_applicant_contact": bool(row.get("use_applicant_contact")),
                "full_name": full_name,
                "first_name": first_name or None,
                "last_name": last_name or None,
                "relationship": row.get("relationship"),
                "is_primary": bool(row.get("is_primary")),
                "can_consent": bool(row.get("can_consent")),
                "salutation": row.get("salutation"),
                "gender": row.get("guardian_gender"),
                "email": row.get("guardian_email"),
                "mobile_phone": row.get("guardian_mobile_phone"),
                "work_email": row.get("guardian_work_email"),
                "work_phone": row.get("guardian_work_phone"),
                "is_primary_guardian": bool(row.get("is_primary_guardian")),
                "is_financial_guardian": bool(row.get("is_financial_guardian")),
                "user": row.get("user"),
                "image": row.get("guardian_image"),
                "employment_sector": row.get("employment_sector"),
                "work_place": row.get("work_place"),
                "designation": row.get("guardian_designation"),
            }
        )
    return out


def _load_applicant_timeline(student_applicant: str) -> list[dict]:
    rows = frappe.get_all(
        "Comment",
        filters={
            "reference_doctype": "Student Applicant",
            "reference_name": student_applicant,
        },
        fields=["name", "creation", "comment_by", "comment_email", "comment_type", "content"],
        order_by="creation desc",
        limit=INTERVIEW_TIMELINE_LIMIT,
        ignore_permissions=True,
    )
    return [
        {
            "name": row.get("name"),
            "creation": row.get("creation"),
            "comment_by": row.get("comment_by"),
            "comment_email": row.get("comment_email"),
            "comment_type": row.get("comment_type"),
            "content": row.get("content") or "",
        }
        for row in rows
    ]


def _load_applicant_documents_for_workspace(
    student_applicant: str,
    *,
    context_doctype: str,
    context_name: str,
) -> dict:
    doc_rows = frappe.get_all(
        "Applicant Document",
        filters={"student_applicant": student_applicant},
        fields=[
            "name",
            "document_type",
            "document_label",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "modified",
        ],
        order_by="modified desc",
        limit=INTERVIEW_WORKSPACE_DOC_LIMIT,
        ignore_permissions=True,
    )
    if not doc_rows:
        return {"rows": [], "count": 0}

    doc_names = [row.get("name") for row in doc_rows if row.get("name")]
    item_rows = frappe.get_all(
        "Applicant Document Item",
        filters={"applicant_document": ["in", doc_names]},
        fields=[
            "name",
            "applicant_document",
            "item_key",
            "item_label",
            "review_status",
            "reviewed_by",
            "reviewed_on",
            "modified",
        ],
        order_by="modified desc",
        limit=max(1, INTERVIEW_WORKSPACE_DOC_LIMIT * 3),
        ignore_permissions=True,
    )
    item_names = [row.get("name") for row in item_rows if row.get("name")]

    latest_file_by_item: dict[str, dict] = {}
    if item_names:
        item_file_rows = frappe.get_all(
            "File",
            filters={
                "attached_to_doctype": "Applicant Document Item",
                "attached_to_name": ["in", item_names],
            },
            fields=["name", "attached_to_name", "file_name", "file_url", "creation"],
            order_by="creation desc",
            limit=0,
            ignore_permissions=True,
        )
        for row in item_file_rows:
            attached = row.get("attached_to_name")
            if not attached or attached in latest_file_by_item:
                continue
            latest_file_by_item[attached] = row

    items_by_doc: dict[str, list[dict]] = {}
    for row in item_rows:
        parent = row.get("applicant_document")
        if not parent:
            continue
        latest_file = latest_file_by_item.get(row.get("name"), {})
        items_by_doc.setdefault(parent, []).append(
            {
                "name": row.get("name"),
                "item_key": row.get("item_key"),
                "item_label": row.get("item_label"),
                "review_status": row.get("review_status") or "Pending",
                "reviewed_by": row.get("reviewed_by"),
                "reviewed_on": row.get("reviewed_on"),
                "file_name": latest_file.get("file_name"),
                "file_url": resolve_admissions_file_open_url(
                    file_name=latest_file.get("name"),
                    file_url=latest_file.get("file_url"),
                    context_doctype=context_doctype,
                    context_name=context_name,
                ),
                "uploaded_at": latest_file.get("creation"),
            }
        )

    payload_rows = []
    for doc_row in doc_rows:
        doc_name = doc_row.get("name")
        items = items_by_doc.get(doc_name, [])

        payload_rows.append(
            {
                "name": doc_name,
                "document_type": doc_row.get("document_type"),
                "document_label": doc_row.get("document_label"),
                "review_status": doc_row.get("review_status") or "Pending",
                "reviewed_by": doc_row.get("reviewed_by"),
                "reviewed_on": doc_row.get("reviewed_on"),
                "items": items,
            }
        )

    return {"rows": payload_rows, "count": len(payload_rows)}


def _load_recommendations_for_workspace(student_applicant: str) -> dict:
    summary = get_recommendation_status_for_applicant(
        student_applicant=student_applicant,
        include_confidential=True,
    )
    review_rows = list(summary.get("review_rows") or [])
    requests = [
        {
            "name": row.get("recommendation_request"),
            "recommendation_template": row.get("recommendation_template"),
            "request_status": row.get("request_status"),
            "recommender_name": row.get("recommender_name"),
            "recommender_email": row.get("recommender_email"),
            "recommender_relationship": row.get("recommender_relationship"),
            "sent_on": row.get("sent_on"),
            "opened_on": row.get("opened_on"),
            "consumed_on": row.get("submitted_on"),
            "expires_on": row.get("expires_on"),
            "submission": row.get("recommendation_submission"),
        }
        for row in review_rows
        if row.get("recommendation_request")
    ][:INTERVIEW_WORKSPACE_DOC_LIMIT]
    submissions = [
        {
            "name": row.get("recommendation_submission"),
            "recommendation_request": row.get("recommendation_request"),
            "recommendation_template": row.get("recommendation_template"),
            "recommender_name": row.get("recommender_name"),
            "recommender_email": row.get("recommender_email"),
            "submitted_on": row.get("submitted_on"),
            "has_file": bool(row.get("has_file")),
            "applicant_document_item": row.get("applicant_document_item"),
            "item_label": row.get("item_label"),
            "review_status": row.get("review_status"),
            "reviewed_by": row.get("reviewed_by"),
            "reviewed_on": row.get("reviewed_on"),
            "file_name": row.get("file_name"),
            "file_url": row.get("file_url"),
        }
        for row in review_rows
        if row.get("recommendation_submission")
    ][:INTERVIEW_WORKSPACE_DOC_LIMIT]

    return {
        "summary": summary,
        "requests": requests,
        "submissions": submissions,
        "review_rows": review_rows[:INTERVIEW_WORKSPACE_DOC_LIMIT],
    }


def _load_interviews_for_applicant_workspace(*, student_applicant: str) -> list[dict]:
    rows = frappe.get_all(
        "Applicant Interview",
        filters={"student_applicant": student_applicant},
        fields=[
            "name",
            "interview_type",
            "mode",
            "location",
            "confidentiality_level",
            "interview_date",
            "interview_start",
            "interview_end",
            "school_event",
            "modified",
        ],
        order_by="interview_start desc, modified desc",
        limit=INTERVIEW_WORKSPACE_INTERVIEW_LIMIT,
        ignore_permissions=True,
    )
    if not rows:
        return []

    interview_names = [row.get("name") for row in rows if row.get("name")]
    if not interview_names:
        return []

    interviewer_rows = frappe.get_all(
        "Applicant Interviewer",
        filters={
            "parent": ["in", interview_names],
            "parenttype": "Applicant Interview",
            "parentfield": "interviewers",
        },
        fields=["parent", "interviewer", "idx"],
        order_by="parent asc, idx asc",
        limit=max(50, INTERVIEW_WORKSPACE_INTERVIEW_LIMIT * 4),
        ignore_permissions=True,
    )
    users = [row.get("interviewer") for row in interviewer_rows if row.get("interviewer")]
    user_map = _user_display_map(users)
    location_names = [row.get("location") for row in rows if row.get("location")]
    location_map = _location_label_map(location_names)

    users_by_interview: dict[str, list[str]] = {}
    for row in interviewer_rows:
        interview_name = (row.get("parent") or "").strip()
        interviewer_user = (row.get("interviewer") or "").strip()
        if not interview_name or not interviewer_user:
            continue
        users_by_interview.setdefault(interview_name, []).append(interviewer_user)

    submitted_users_by_interview: dict[str, set[str]] = {}
    if frappe.db.table_exists(INTERVIEW_FEEDBACK_DOCTYPE):
        feedback_rows = frappe.get_all(
            INTERVIEW_FEEDBACK_DOCTYPE,
            filters={
                "applicant_interview": ["in", interview_names],
                "feedback_status": "Submitted",
            },
            fields=["applicant_interview", "interviewer_user"],
            limit=max(50, INTERVIEW_WORKSPACE_INTERVIEW_LIMIT * 4),
            ignore_permissions=True,
        )
        for row in feedback_rows:
            interview_name = (row.get("applicant_interview") or "").strip()
            interviewer_user = (row.get("interviewer_user") or "").strip()
            if not interview_name or not interviewer_user:
                continue
            submitted_users_by_interview.setdefault(interview_name, set()).add(interviewer_user)

    payload: list[dict] = []
    for row in rows:
        interview_name = (row.get("name") or "").strip()
        if not interview_name:
            continue
        interviewer_users = users_by_interview.get(interview_name, [])
        assigned_users = {user for user in interviewer_users if user}
        submitted_count = len(assigned_users & submitted_users_by_interview.get(interview_name, set()))
        expected_count = len(assigned_users)
        payload.append(
            {
                "name": interview_name,
                "student_applicant": student_applicant,
                "interview_type": row.get("interview_type"),
                "mode": row.get("mode"),
                "location": row.get("location"),
                "location_label": location_map.get(row.get("location")) if row.get("location") else None,
                "confidentiality_level": row.get("confidentiality_level"),
                "interview_date": str(row.get("interview_date")) if row.get("interview_date") else None,
                "interview_start": row.get("interview_start"),
                "interview_end": row.get("interview_end"),
                "interview_start_label": format_datetime(row.get("interview_start"))
                if row.get("interview_start")
                else None,
                "interview_end_label": format_datetime(row.get("interview_end")) if row.get("interview_end") else None,
                "school_event": row.get("school_event"),
                "feedback_submitted_count": submitted_count,
                "feedback_expected_count": expected_count,
                "feedback_complete": bool(expected_count and submitted_count >= expected_count),
                "feedback_status_label": (
                    _("{submitted_count}/{expected_count} submitted").format(
                        submitted_count=submitted_count,
                        expected_count=expected_count,
                    )
                    if expected_count
                    else _("No interviewers assigned")
                ),
                "interviewers": [
                    {
                        "user": interviewer_user,
                        "name": user_map.get(interviewer_user) or interviewer_user,
                    }
                    for interviewer_user in interviewer_users
                ],
            }
        )

    return payload


def _load_feedback_panel_for_workspace(*, interview_name: str) -> dict:
    interviewer_users = frappe.get_all(
        "Applicant Interviewer",
        filters={
            "parent": interview_name,
            "parenttype": "Applicant Interview",
            "parentfield": "interviewers",
        },
        pluck="interviewer",
        ignore_permissions=True,
    )
    interviewer_users = [user for user in interviewer_users if user]

    rows = []
    if frappe.db.table_exists(INTERVIEW_FEEDBACK_DOCTYPE):
        rows = frappe.get_all(
            INTERVIEW_FEEDBACK_DOCTYPE,
            filters={"applicant_interview": interview_name},
            fields=[
                "name",
                "interviewer_user",
                "feedback_status",
                "submitted_on",
                "strengths",
                "concerns",
                "shared_values",
                "other_notes",
                "recommendation",
                "modified",
            ],
            order_by="modified desc",
            limit=max(20, len(interviewer_users) + 5),
            ignore_permissions=True,
        )

    by_user = {row.get("interviewer_user"): row for row in rows if row.get("interviewer_user")}
    all_users = list(
        dict.fromkeys(
            [*interviewer_users, *[row.get("interviewer_user") for row in rows if row.get("interviewer_user")]]
        )
    )
    user_names = _user_display_map(all_users)

    panel = []
    for user in all_users:
        row = by_user.get(user) or {}
        panel.append(
            {
                "name": row.get("name"),
                "interviewer_user": user,
                "interviewer_name": user_names.get(user) or user,
                "feedback_status": row.get("feedback_status") or "Pending",
                "submitted_on": row.get("submitted_on"),
                "modified": row.get("modified"),
            }
        )

    current_user = (frappe.session.user or "").strip()
    my_row = by_user.get(current_user) or {}
    my_feedback = {
        "name": my_row.get("name"),
        "interviewer_user": current_user,
        "interviewer_name": user_names.get(current_user) or current_user,
        "feedback_status": my_row.get("feedback_status") or "Draft",
        "submitted_on": my_row.get("submitted_on"),
        "strengths": my_row.get("strengths") or "",
        "concerns": my_row.get("concerns") or "",
        "shared_values": my_row.get("shared_values") or "",
        "other_notes": my_row.get("other_notes") or "",
        "recommendation": my_row.get("recommendation") or "",
    }

    return {
        "panel": panel,
        "my_feedback": my_feedback,
        "can_edit": _is_interview_privileged_user(current_user)
        or _is_interviewer_on_interview(user=current_user, interview_name=interview_name),
        "allowed_statuses": sorted(INTERVIEW_FEEDBACK_STATUS),
    }


def _user_display_map(users: Sequence[str]) -> dict[str, str]:
    user_list = [user for user in users if user]
    if not user_list:
        return {}
    rows = frappe.get_all(
        "User",
        filters={"name": ["in", list(sorted(set(user_list)))]},
        fields=["name", "full_name"],
        limit=0,
        ignore_permissions=True,
    )
    return {row.get("name"): (row.get("full_name") or row.get("name")) for row in rows if row.get("name")}


def _location_label_map(locations: Sequence[str]) -> dict[str, str]:
    location_list = [location for location in locations if location]
    if not location_list:
        return {}
    rows = frappe.get_all(
        "Location",
        filters={"name": ["in", list(sorted(set(location_list)))]},
        fields=["name", "location_name"],
        limit=max(len(set(location_list)), 1),
        ignore_permissions=True,
    )
    return {row.get("name"): (row.get("location_name") or row.get("name")) for row in rows if row.get("name")}


def _get_applicant_context(student_applicant: str | None) -> frappe._dict:
    applicant_name = (student_applicant or "").strip()
    if not applicant_name:
        frappe.throw(_("Student Applicant is required."), title=_("Missing Applicant"))

    row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        ["name", "school", "application_status", "first_name", "middle_name", "last_name"],
        as_dict=True,
    )
    if not row:
        frappe.throw(
            _("Student Applicant {student_applicant} was not found.").format(student_applicant=applicant_name),
            frappe.DoesNotExistError,
        )

    if row.get("application_status") in TERMINAL_APPLICANT_STATES:
        frappe.throw(_("Applicant is read-only in terminal states."))

    return row


def _serialize_room_option(row: dict) -> dict:
    name = (row.get("name") or "").strip()
    label = (row.get("location_name") or name).strip()
    return {
        "value": name,
        "label": label or name,
        "school": row.get("school"),
        "parent_location": row.get("parent_location"),
        "location_type": row.get("location_type"),
        "location_type_name": row.get("location_type_name"),
        "max_capacity": row.get("maximum_capacity"),
    }


def _resolve_schedule_location(
    *,
    location: str | None,
    mode: str | None,
    applicant_row: frappe._dict | None,
    require_for_in_person: bool,
) -> str | None:
    mode_value = (mode or "").strip()
    location_name = (location or "").strip()

    if mode_value == "In Person" and require_for_in_person and not location_name:
        frappe.throw(
            _("Select a room for in-person interviews."),
            title=_("Room Required"),
        )

    if not location_name:
        return None

    if not is_schedulable_location(location_name):
        frappe.throw(
            _("Selected room is not schedulable."),
            title=_("Invalid Room"),
        )

    selected_school = (applicant_row.get("school") if applicant_row else None) or ""
    if not selected_school:
        if require_for_in_person:
            frappe.throw(
                _("Set the applicant school before selecting an interview room."),
                title=_("School Required"),
            )
        return location_name

    visible_rows = get_visible_location_rows_for_school(
        selected_school,
        include_groups=False,
        only_schedulable=True,
        fields=["name", "location_name", "school", "parent_location", "location_type", "maximum_capacity"],
        limit=2000,
    )
    visible_names = {row.get("name") for row in visible_rows if row.get("name")}
    if location_name not in visible_names:
        frappe.throw(
            _("Selected room is not available for this applicant school."),
            title=_("Invalid Room"),
        )

    return location_name


def _assert_users_exist_and_enabled(user_ids: Sequence[str]) -> None:
    if not user_ids:
        frappe.throw(_("At least one interviewer is required."), title=_("Missing Interviewers"))

    rows = frappe.get_all(
        "User",
        filters={"name": ["in", list(user_ids)], "enabled": 1},
        pluck="name",
    )
    enabled_users = set(rows or [])
    missing = [user for user in user_ids if user not in enabled_users]
    if missing:
        frappe.throw(
            _("These interviewers are missing or disabled: {users}").format(users=", ".join(sorted(set(missing)))),
            title=_("Invalid Interviewers"),
        )


def _resolve_employee_rows_for_users(user_ids: Sequence[str]) -> list[frappe._dict]:
    rows = frappe.get_all(
        "Employee",
        filters={
            "user_id": ["in", list(user_ids)],
            "employment_status": ["!=", "Inactive"],
        },
        fields=["name", "user_id", "employee_full_name"],
    )

    by_user = {row.user_id: row for row in rows if row.get("user_id")}
    missing = [user for user in user_ids if user not in by_user]

    if missing:
        frappe.throw(
            _("Interviewers must be linked to active Employee records. Missing: {users}").format(
                users=", ".join(sorted(set(missing)))
            ),
            title=_("Missing Employee Link"),
        )

    return [by_user[user] for user in user_ids]


def _collect_employee_conflicts(
    *,
    employee_rows: Sequence[frappe._dict],
    start_dt: datetime,
    end_dt: datetime,
    exclude_source: dict | None,
) -> list[dict]:
    out: list[dict] = []

    for employee_row in employee_rows:
        employee_name = employee_row["name"]
        employee_label = employee_row.get("employee_full_name") or employee_name

        conflicts = find_employee_conflicts(
            employee=employee_name,
            start=start_dt,
            end=end_dt,
            include_soft=False,
            exclude=exclude_source,
        )

        for hit in conflicts:
            out.append(
                {
                    "kind": "employee",
                    "employee": employee_name,
                    "employee_name": employee_label,
                    "booking_type": hit.booking_type,
                    "source_doctype": hit.source_doctype,
                    "source_name": hit.source_name,
                    "start": hit.start.isoformat(),
                    "end": hit.end.isoformat(),
                    "start_label": format_datetime(hit.start),
                    "end_label": format_datetime(hit.end),
                }
            )

    out.sort(key=lambda row: (row["start"], row["employee"]))
    return out


def _collect_room_conflicts(
    *,
    location: str | None,
    start_dt: datetime,
    end_dt: datetime,
    exclude_source: dict | None,
) -> list[dict]:
    location_name = (location or "").strip()
    if not location_name:
        return []

    hits = find_room_conflicts(
        location_name,
        start_dt,
        end_dt,
        include_children=False,
        exclude=exclude_source,
    )
    location_labels = _location_label_map(
        [location_name, *[hit.get("location") for hit in hits if hit.get("location")]]
    )

    out: list[dict] = []
    for hit in hits:
        hit_location = (hit.get("location") or location_name).strip()
        hit_start = get_datetime(hit.get("from"))
        hit_end = get_datetime(hit.get("to"))
        if not hit_start or not hit_end:
            continue

        out.append(
            {
                "kind": "room",
                "location": hit_location,
                "location_label": location_labels.get(hit_location) or hit_location,
                "occupancy_type": (hit.get("extra") or {}).get("occupancy_type") or "Room Booking",
                "source_doctype": hit.get("source_doctype"),
                "source_name": hit.get("source_name"),
                "start": hit_start.isoformat(),
                "end": hit_end.isoformat(),
                "start_label": format_datetime(hit_start),
                "end_label": format_datetime(hit_end),
            }
        )

    out.sort(key=lambda row: (row["start"], row["location"]))
    return out


def _combine_conflict_rows(*, employee_conflict_rows: Sequence[dict], room_conflict_rows: Sequence[dict]) -> list[dict]:
    rows: list[dict] = []
    for row in employee_conflict_rows or []:
        item = dict(row)
        item.setdefault("kind", "employee")
        rows.append(item)
    rows.extend(dict(row) for row in room_conflict_rows or [])
    rows.sort(key=lambda row: (row.get("start") or "", row.get("kind") or "", row.get("source_name") or ""))
    return rows


def _schedule_conflict_code(*, employee_conflict_rows: Sequence[dict], room_conflict_rows: Sequence[dict]) -> str:
    has_employee = bool(employee_conflict_rows)
    has_room = bool(room_conflict_rows)
    if has_employee and has_room:
        return "SCHEDULING_CONFLICT"
    if has_room:
        return "ROOM_CONFLICT"
    return "EMPLOYEE_CONFLICT"


def _schedule_conflict_message(code: str) -> str:
    if code == "ROOM_CONFLICT":
        return _("The selected room is already booked for the selected time.")
    if code == "SCHEDULING_CONFLICT":
        return _("One or more interviewers and the selected room are already booked for the selected time.")
    return _("One or more interviewers are already booked for the selected time.")


def _create_school_event_for_interview(
    *,
    interview_doc: ApplicantInterview,
    applicant_row: frappe._dict,
    interviewer_users: Sequence[str],
    starts_on: datetime,
    ends_on: datetime,
    location: str | None = None,
):
    applicant_label = _applicant_display_name(applicant_row)

    school_event = frappe.new_doc("School Event")
    school_event.subject = _("Admission Interview - {applicant}").format(applicant=applicant_label)
    school_event.event_category = "Appointment"
    school_event.all_day = 0
    school_event.starts_on = starts_on
    school_event.ends_on = ends_on
    school_event.school = applicant_row.get("school")
    school_event.location = (location or "").strip() or None
    school_event.reference_type = INTERVIEW_EVENT_REFERENCE_TYPE
    school_event.reference_name = interview_doc.name

    school_event.append("audience", {"audience_type": "Custom Users"})
    for user in interviewer_users:
        school_event.append("participants", {"participant": user})

    school_event.flags.ignore_permissions = True
    school_event.insert()

    return school_event


def _applicant_display_name(applicant_row: frappe._dict) -> str:
    parts = [
        (applicant_row.get("first_name") or "").strip(),
        (applicant_row.get("middle_name") or "").strip(),
        (applicant_row.get("last_name") or "").strip(),
    ]
    display = " ".join(part for part in parts if part)
    return display or applicant_row.get("name") or _("Applicant")


def _normalize_interviewer_users(
    *,
    primary_interviewer: str | None,
    interviewer_users: Sequence[str] | str | None,
) -> list[str]:
    users = []

    primary = (primary_interviewer or "").strip()
    if primary:
        users.append(primary)

    users.extend(_normalize_user_sequence(interviewer_users))

    seen: set[str] = set()
    out: list[str] = []
    for user in users:
        if user in seen:
            continue
        seen.add(user)
        out.append(user)

    return out


def _normalize_user_sequence(raw: Sequence[str] | str | None) -> list[str]:
    if not raw:
        return []

    items: list[str] = []

    if isinstance(raw, str):
        parsed = None
        try:
            parsed = frappe.parse_json(raw)
        except Exception:
            parsed = None

        if isinstance(parsed, list):
            iterable = parsed
        else:
            iterable = [piece.strip() for piece in raw.replace("\n", ",").split(",")]

        for value in iterable:
            text = str(value or "").strip()
            if text:
                items.append(text)
        return items

    for value in raw:
        text = str(value or "").strip()
        if text:
            items.append(text)

    return items


def _to_datetime_or_throw(value, *, fieldname: str) -> datetime:
    try:
        dt = get_datetime(value)
    except Exception:
        dt = None

    if not dt:
        debug_payload = {
            "field": fieldname,
            "value": str(value),
            "python_type": type(value).__name__,
        }
        frappe.throw(
            _("Unable to resolve datetime for {fieldname}. Debug: {debug_payload}").format(
                fieldname=fieldname,
                debug_payload=frappe.as_json(debug_payload),
            ),
            title=_("Invalid Datetime"),
        )

    return dt


def _to_date_or_throw(value, *, fieldname: str):
    try:
        resolved = getdate(value)
    except Exception:
        resolved = None

    if not resolved:
        debug_payload = {
            "field": fieldname,
            "value": str(value),
            "python_type": type(value).__name__,
        }
        frappe.throw(
            _("Unable to resolve date for {fieldname}. Debug: {debug_payload}").format(
                fieldname=fieldname,
                debug_payload=frappe.as_json(debug_payload),
            ),
            title=_("Invalid Date"),
        )

    return resolved


def _to_positive_int(*, value, default: int, fieldname: str) -> int:
    if value in (None, ""):
        return default

    try:
        parsed = int(value)
    except Exception:
        parsed = 0

    if parsed <= 0:
        frappe.throw(
            _("{fieldname} must be a positive integer.").format(fieldname=fieldname),
            title=_("Invalid Number"),
        )

    return parsed


def _coerce_time(value, *, fieldname: str) -> time:
    if isinstance(value, time):
        return value

    if isinstance(value, datetime):
        return value.time()

    if isinstance(value, timedelta):
        total = int(value.total_seconds())
        hours = (total // 3600) % 24
        minutes = (total % 3600) // 60
        seconds = total % 60
        return time(hour=hours, minute=minutes, second=seconds)

    if isinstance(value, str):
        raw = value.strip()
        parts = raw.split(":")
        try:
            hours = int(parts[0])
            minutes = int(parts[1]) if len(parts) > 1 else 0
            seconds = int(parts[2]) if len(parts) > 2 else 0
            return time(hour=hours, minute=minutes, second=seconds)
        except Exception:
            pass

    debug_payload = {
        "field": fieldname,
        "value": str(value),
        "python_type": type(value).__name__,
    }
    frappe.throw(
        _("Unable to resolve time for {fieldname}. Debug: {debug_payload}").format(
            fieldname=fieldname,
            debug_payload=frappe.as_json(debug_payload),
        ),
        title=_("Invalid Time"),
    )


def _build_window_datetimes_for_date(*, target_date, start_time: time, end_time: time) -> tuple[datetime, datetime]:
    start_dt = get_datetime(f"{target_date} {start_time.strftime('%H:%M:%S')}")
    end_dt = get_datetime(f"{target_date} {end_time.strftime('%H:%M:%S')}")

    if end_dt <= start_dt:
        frappe.throw(
            _("Suggestion window end time must be after start time."),
            title=_("Invalid Suggestion Window"),
        )

    return start_dt, end_dt


def _suggest_common_free_slots(
    *,
    employees: Sequence[str],
    location: str | None = None,
    window_start: datetime,
    window_end: datetime,
    duration_minutes: int,
    step_minutes: int,
    limit: int,
) -> list[dict]:
    if not employees:
        return []

    if window_end <= window_start:
        return []

    if duration_minutes <= 0:
        return []

    slot_duration = timedelta(minutes=duration_minutes)
    step_duration = timedelta(minutes=max(1, step_minutes))

    conflict_map = _load_conflict_windows_for_employees(
        employees=employees,
        window_start=window_start,
        window_end=window_end,
    )
    room_conflicts = _load_conflict_windows_for_room(
        location=location,
        window_start=window_start,
        window_end=window_end,
    )

    suggestions: list[dict] = []
    cursor = window_start

    while cursor + slot_duration <= window_end and len(suggestions) < limit:
        slot_end = cursor + slot_duration

        blocked = False
        for employee in employees:
            if _slot_overlaps_any(
                slot_start=cursor,
                slot_end=slot_end,
                conflicts=conflict_map.get(employee, []),
            ):
                blocked = True
                break

        if not blocked and _slot_overlaps_any(
            slot_start=cursor,
            slot_end=slot_end,
            conflicts=room_conflicts,
        ):
            blocked = True

        if not blocked:
            suggestions.append(
                {
                    "start": cursor.isoformat(),
                    "end": slot_end.isoformat(),
                    "label": _("{start} to {end}").format(
                        start=format_datetime(cursor),
                        end=format_datetime(slot_end),
                    ),
                }
            )

        cursor = cursor + step_duration

    return suggestions


def _load_conflict_windows_for_employees(
    *,
    employees: Sequence[str],
    window_start: datetime,
    window_end: datetime,
) -> dict[str, list[tuple[datetime, datetime]]]:
    out: dict[str, list[tuple[datetime, datetime]]] = {employee: [] for employee in employees}

    if not employees:
        return out

    if not frappe.db.table_exists("Employee Booking"):
        return out

    rows = frappe.db.sql(
        """
        SELECT employee, from_datetime, to_datetime
        FROM `tabEmployee Booking`
        WHERE employee IN %(employees)s
          AND blocks_availability = 1
          AND from_datetime < %(window_end)s
          AND to_datetime > %(window_start)s
        """,
        {
            "employees": tuple(sorted(set(employees))),
            "window_start": window_start,
            "window_end": window_end,
        },
        as_dict=True,
    )

    for row in rows:
        employee = row.get("employee")
        start = row.get("from_datetime")
        end = row.get("to_datetime")
        if not employee or not start or not end:
            continue

        start_dt = get_datetime(start)
        end_dt = get_datetime(end)
        if end_dt <= start_dt:
            continue

        out.setdefault(employee, []).append((start_dt, end_dt))

    for employee in out:
        out[employee].sort(key=lambda item: item[0])

    return out


def _load_conflict_windows_for_room(
    *,
    location: str | None,
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[datetime, datetime]]:
    location_name = (location or "").strip()
    if not location_name:
        return []

    rows = find_room_conflicts(
        location_name,
        window_start,
        window_end,
        include_children=False,
    )
    out: list[tuple[datetime, datetime]] = []
    for row in rows:
        start = row.get("from")
        end = row.get("to")
        if not start or not end:
            continue
        start_dt = get_datetime(start)
        end_dt = get_datetime(end)
        if end_dt <= start_dt:
            continue
        out.append((start_dt, end_dt))

    out.sort(key=lambda item: item[0])
    return out


def _slot_overlaps_any(
    *,
    slot_start: datetime,
    slot_end: datetime,
    conflicts: Iterable[tuple[datetime, datetime]],
) -> bool:
    for conflict_start, conflict_end in conflicts:
        if _overlaps(
            a_start=slot_start,
            a_end=slot_end,
            b_start=conflict_start,
            b_end=conflict_end,
        ):
            return True
    return False


def _overlaps(*, a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    # Half-open interval overlap: [a_start, a_end) vs [b_start, b_end)
    return not (a_end <= b_start or b_end <= a_start)
