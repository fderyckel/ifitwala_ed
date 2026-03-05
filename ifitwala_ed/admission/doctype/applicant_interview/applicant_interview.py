# ifitwala_ed/admission/doctype/applicant_interview/applicant_interview.py

from __future__ import annotations

from datetime import datetime, time, timedelta
from typing import Iterable, Sequence

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import format_datetime, get_datetime, get_link_to_form, getdate, now_datetime

from ifitwala_ed.admission.admission_utils import ADMISSIONS_ROLES
from ifitwala_ed.utilities.employee_booking import find_employee_conflicts

STAFF_ROLES = ADMISSIONS_ROLES | {"Academic Admin", "System Manager"}
TERMINAL_APPLICANT_STATES = {"Rejected", "Promoted"}
DEFAULT_INTERVIEW_DURATION_MINUTES = 30
DEFAULT_SUGGESTION_WINDOW_START = "07:00:00"
DEFAULT_SUGGESTION_WINDOW_END = "17:00:00"
DEFAULT_SUGGESTION_LIMIT = 8
DEFAULT_SUGGESTION_STEP_MINUTES = 15
INTERVIEW_EVENT_REFERENCE_TYPE = "Applicant Interview"
INTERVIEWER_SELF_EDITABLE_FIELDS = frozenset({"notes", "outcome_impression"})


class ApplicantInterview(Document):
    def validate(self):
        self._validate_permissions()
        self._validate_applicant_state()
        self._validate_time_window()
        self._sync_interview_date_from_start()
        self._validate_interviewer_edit_scope()

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
            allow_interviewer_write=not self.is_new(),
            interview_name=self.name if not self.is_new() else None,
        )

    def _validate_interviewer_edit_scope(self):
        user = frappe.session.user
        if self.is_new() or _is_interview_privileged_user(user):
            return

        if not _is_interviewer_on_interview(user=user, interview_name=self.name):
            return

        before = self.get_doc_before_save()
        if not before:
            return

        protected_fieldnames = (
            "student_applicant",
            "interview_type",
            "interview_date",
            "interview_start",
            "interview_end",
            "mode",
            "confidentiality_level",
            "school_event",
        )

        for fieldname in protected_fieldnames:
            if _coerce_compare_value(getattr(before, fieldname, None)) != _coerce_compare_value(
                getattr(self, fieldname, None)
            ):
                frappe.throw(
                    _("Interviewers can only edit: {0}.").format(", ".join(sorted(INTERVIEWER_SELF_EDITABLE_FIELDS))),
                    frappe.PermissionError,
                )

        before_interviewers = _normalized_interviewer_rows(before.get("interviewers") or [])
        current_interviewers = _normalized_interviewer_rows(self.get("interviewers") or [])
        if before_interviewers != current_interviewers:
            frappe.throw(
                _("Interviewers can only edit: {0}.").format(", ".join(sorted(INTERVIEWER_SELF_EDITABLE_FIELDS))),
                frappe.PermissionError,
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

    def _add_audit_comment(self, label):
        if not self.student_applicant:
            return
        applicant = frappe.get_doc("Student Applicant", self.student_applicant)
        interview_link = get_link_to_form("Applicant Interview", self.name)
        applicant.add_comment(
            "Comment",
            text=_("{0}: {1} by {2} on {3}.").format(
                label,
                interview_link,
                frappe.bold(frappe.session.user),
                now_datetime(),
            ),
        )


@frappe.whitelist()
def suggest_interview_slots(
    *,
    interview_date: str | None = None,
    primary_interviewer: str | None = None,
    interviewer_users: Sequence[str] | str | None = None,
    duration_minutes: int | str | None = None,
    window_start_time=None,
    window_end_time=None,
    limit: int | str | None = None,
):
    """
    Return common free slot suggestions for selected interviewers on a given date.

    This endpoint is reusable by Desk dialogs and SPA overlays.
    """

    _assert_manage_interview_permission()

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
        },
        "slots": slots,
    }


def get_permission_query_conditions(user: str | None = None) -> str | None:
    user = (user or frappe.session.user or "").strip()
    if not user or user == "Guest":
        return "1=0"
    if _is_interview_privileged_user(user):
        return None

    escaped_user = frappe.db.escape(user)
    return (
        "exists ("
        "select 1 from `tabApplicant Interviewer` ai "
        "where ai.parent = `tabApplicant Interview`.`name` "
        "and ai.parenttype = 'Applicant Interview' "
        "and ai.parentfield = 'interviewers' "
        f"and ai.interviewer = {escaped_user}"
        ")"
    )


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    user = (user or frappe.session.user or "").strip()
    op = (ptype or "read").lower()
    if not user or user == "Guest":
        return False
    if _is_interview_privileged_user(user):
        return True

    read_like = {"read", "report", "export", "print", "email"}
    if op == "create" or op == "delete" or op == "submit":
        return False
    if op not in read_like and op != "write":
        return False

    if not doc:
        if op not in read_like:
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
    confidentiality_level: str | None = None,
    notes: str | None = None,
    outcome_impression: str | None = None,
    primary_interviewer: str | None = None,
    interviewer_users: Sequence[str] | str | None = None,
    suggestion_window_start_time=None,
    suggestion_window_end_time=None,
    suggestion_limit: int | str | None = None,
):
    """
    Atomically create Applicant Interview + linked School Event.

    If the selected interviewers are busy, returns a structured conflict payload
    with suggested alternative times instead of throwing a hard validation error.
    """

    _assert_manage_interview_permission()

    applicant_row = _get_applicant_context(student_applicant)

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

    conflict_rows = _collect_employee_conflicts(
        employee_rows=employee_rows,
        start_dt=start_dt,
        end_dt=end_dt,
        exclude_source=None,
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

        return {
            "ok": False,
            "code": "EMPLOYEE_CONFLICT",
            "message": _("One or more interviewers are already booked for the selected time."),
            "conflicts": conflict_rows,
            "suggestions": suggestion_rows,
            "window": {
                "start": suggestion_window_start.isoformat(),
                "end": suggestion_window_end.isoformat(),
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
        interview_doc.confidentiality_level = confidentiality_level
        interview_doc.outcome_impression = outcome_impression
        interview_doc.notes = notes

        for user in selected_users:
            interview_doc.append("interviewers", {"interviewer": user})

        interview_doc.flags.ignore_permissions = True
        interview_doc.insert()

        school_event_doc = _create_school_event_for_interview(
            interview_doc=interview_doc,
            applicant_row=applicant_row,
            interviewer_users=selected_users,
            starts_on=start_dt,
            ends_on=end_dt,
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
        },
    }


def _assert_manage_interview_permission(
    *,
    allow_interviewer_write: bool = False,
    interview_name: str | None = None,
    user: str | None = None,
) -> None:
    current_user = (user or frappe.session.user or "").strip()
    if not current_user or current_user == "Guest":
        frappe.throw(_("You do not have permission to manage Applicant Interviews."), frappe.PermissionError)

    if _is_interview_privileged_user(current_user):
        return

    if allow_interviewer_write and interview_name:
        if _is_interviewer_on_interview(user=current_user, interview_name=interview_name):
            return

    frappe.throw(_("You do not have permission to manage Applicant Interviews."), frappe.PermissionError)


def _is_interview_privileged_user(user: str) -> bool:
    if not user:
        return False
    roles = set(frappe.get_roles(user))
    return user == "Administrator" or bool(roles & STAFF_ROLES)


def _is_interviewer_on_interview(*, user: str, interview_name: str) -> bool:
    resolved_user = (user or "").strip()
    resolved_name = (interview_name or "").strip()
    if not resolved_user or not resolved_name:
        return False
    return bool(
        frappe.db.exists(
            "Applicant Interviewer",
            {
                "parent": resolved_name,
                "parenttype": "Applicant Interview",
                "parentfield": "interviewers",
                "interviewer": resolved_user,
            },
        )
    )


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


def _coerce_compare_value(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value).strip()


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
            _("Student Applicant {0} was not found.").format(applicant_name),
            frappe.DoesNotExistError,
        )

    if row.get("application_status") in TERMINAL_APPLICANT_STATES:
        frappe.throw(_("Applicant is read-only in terminal states."))

    return row


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
            _("These interviewers are missing or disabled: {0}").format(", ".join(sorted(set(missing)))),
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
            _("Interviewers must be linked to active Employee records. Missing: {0}").format(
                ", ".join(sorted(set(missing)))
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


def _create_school_event_for_interview(
    *,
    interview_doc: ApplicantInterview,
    applicant_row: frappe._dict,
    interviewer_users: Sequence[str],
    starts_on: datetime,
    ends_on: datetime,
):
    applicant_label = _applicant_display_name(applicant_row)

    school_event = frappe.new_doc("School Event")
    school_event.subject = _("Admission Interview - {0}").format(applicant_label)
    school_event.event_category = "Appointment"
    school_event.all_day = 0
    school_event.starts_on = starts_on
    school_event.ends_on = ends_on
    school_event.school = applicant_row.get("school")
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
            _("Unable to resolve datetime for {0}. Debug: {1}").format(fieldname, frappe.as_json(debug_payload)),
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
            _("Unable to resolve date for {0}. Debug: {1}").format(fieldname, frappe.as_json(debug_payload)),
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
            _("{0} must be a positive integer.").format(fieldname),
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
        _("Unable to resolve time for {0}. Debug: {1}").format(fieldname, frappe.as_json(debug_payload)),
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

        if not blocked:
            suggestions.append(
                {
                    "start": cursor.isoformat(),
                    "end": slot_end.isoformat(),
                    "label": _("{0} to {1}").format(
                        format_datetime(cursor),
                        format_datetime(slot_end),
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
