from __future__ import annotations

from datetime import timedelta
from typing import Sequence

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import format_datetime, getdate, now_datetime, nowdate

from ifitwala_ed.admission.admission_utils import READ_LIKE_PERMISSION_TYPES, get_admissions_file_staff_scope
from ifitwala_ed.admission.admissions_crm_domain import (
    assert_school_in_organization_scope,
    clean,
    get_school_organization,
)
from ifitwala_ed.admission.admissions_crm_permissions import (
    conversation_has_permission,
    doc_is_in_admissions_crm_scope,
    ensure_admissions_crm_permission,
    is_admissions_crm_user,
)
from ifitwala_ed.admission.doctype.applicant_interview.applicant_interview import (
    DEFAULT_SUGGESTION_LIMIT,
    DEFAULT_SUGGESTION_STEP_MINUTES,
    DEFAULT_SUGGESTION_WINDOW_END,
    DEFAULT_SUGGESTION_WINDOW_START,
    _build_window_datetimes_for_date,
    _coerce_time,
    _collect_employee_conflicts,
    _collect_room_conflicts,
    _combine_conflict_rows,
    _normalize_user_sequence,
    _schedule_conflict_code,
    _suggest_common_free_slots,
    _to_date_or_throw,
    _to_datetime_or_throw,
    _to_positive_int,
)
from ifitwala_ed.stock.doctype.location_booking.location_booking import delete_location_bookings_for_source
from ifitwala_ed.utilities.employee_booking import delete_employee_bookings_for_source
from ifitwala_ed.utilities.location_utils import get_visible_location_rows_for_school, is_schedulable_location

ADMISSION_VISIT_REFERENCE_TYPE = "Admission Visit"
DEFAULT_VISIT_DURATION_MINUTES = 60
TERMINAL_APPLICANT_STATES = {"Rejected", "Promoted"}
VISIT_PROJECTION_FIELDS = {
    "visit_title",
    "school",
    "starts_on",
    "ends_on",
    "building",
    "location",
    "lead_user",
    "visitor_name",
    "party_size",
    "visit_type",
    "visit_mode",
    "status",
}


class AdmissionVisit(Document):
    def validate(self):
        self._apply_context_scope()
        self._validate_session_scope()
        self._validate_time_window()
        self._validate_locations()
        self._validate_staff_users()
        self._set_title_if_missing()

    def after_insert(self):
        self._sync_school_event_projection()
        self._record_booked_activity_if_needed()

    def on_update(self):
        if getattr(self.flags, "in_insert", False):
            return
        previous = self.get_doc_before_save()
        if not previous:
            return

        if self.status == "Cancelled":
            self._remove_school_event_projection()
            if previous.status != "Cancelled":
                self._record_cancelled_activity_if_needed()
            return

        if self._school_event_projection_changed(previous):
            self._sync_school_event_projection()

        if self.status == "Completed" and previous.status != "Completed":
            self._record_attended_activity_if_needed()
        elif self.status == "No Show" and previous.status != "No Show":
            self._record_no_show_activity_if_needed()

    def _apply_context_scope(self) -> None:
        context = _resolve_visit_context(
            conversation=self.conversation,
            inquiry=self.inquiry,
            student_applicant=self.student_applicant,
            organization=self.organization,
            school=self.school,
        )

        self.conversation = context.get("conversation") or self.conversation
        self.inquiry = context.get("inquiry") or self.inquiry
        self.student_applicant = context.get("student_applicant") or self.student_applicant
        self.organization = context.get("organization") or self.organization
        self.school = context.get("school") or self.school

        if self.school and not self.organization:
            self.organization = get_school_organization(self.school)

        assert_school_in_organization_scope(school=self.school, organization=self.organization)
        if not clean(self.organization):
            frappe.throw(_("Organization is required for an admission visit."))

        if not clean(self.visitor_name):
            self.visitor_name = context.get("visitor_name")
        if not clean(self.visitor_email):
            self.visitor_email = context.get("visitor_email")
        if not clean(self.visitor_phone):
            self.visitor_phone = context.get("visitor_phone")
        if not clean(self.requested_grade_level):
            self.requested_grade_level = context.get("requested_grade_level")
        if not clean(self.program_interest):
            self.program_interest = context.get("program_interest")

    def _validate_session_scope(self) -> None:
        user = clean(frappe.session.user)
        if user == "Administrator":
            return
        if not is_admissions_crm_user(user):
            frappe.throw(_("You do not have permission to manage admission visits."), frappe.PermissionError)
        if not doc_is_in_admissions_crm_scope(user=user, organization=self.organization, school=self.school):
            frappe.throw(_("You do not have permission for this admission visit scope."), frappe.PermissionError)
        if self.conversation and not conversation_has_permission(self.conversation, ptype="write", user=user):
            frappe.throw(
                _("You do not have permission to schedule visits for this conversation."), frappe.PermissionError
            )

    def _validate_time_window(self) -> None:
        if not self.starts_on or not self.ends_on:
            frappe.throw(_("Visit start and end are required."), title=_("Missing Visit Time"))

        start_dt = _to_datetime_or_throw(self.starts_on, fieldname="starts_on")
        end_dt = _to_datetime_or_throw(self.ends_on, fieldname="ends_on")
        if end_dt <= start_dt:
            frappe.throw(_("Visit end must be after visit start."), title=_("Invalid Time Window"))

    def _validate_locations(self) -> None:
        _resolve_visit_locations(
            location=self.location,
            building=self.building,
            mode=self.visit_mode,
            school=self.school,
            require_for_in_person=True,
        )

    def _validate_staff_users(self) -> None:
        selected_users = _visit_staff_users_from_doc(self)
        _assert_visit_users_exist_and_enabled(selected_users, label=_("visit staff"))
        _resolve_employee_rows_for_users(selected_users)
        informed_users = _visit_informed_users_from_doc(self)
        if informed_users:
            _assert_visit_users_exist_and_enabled(informed_users, label=_("informed users"))

    def _set_title_if_missing(self) -> None:
        if clean(self.visit_title):
            return

        label = clean(self.visitor_name)
        if not label and self.student_applicant:
            label = _student_applicant_display_name(self.student_applicant)
        if not label:
            label = self.inquiry or self.conversation or _("Admissions Visitor")

        self.visit_title = _("Admission Visit - {visitor}").format(visitor=label)

    def _school_event_projection_changed(self, previous) -> bool:
        for fieldname in VISIT_PROJECTION_FIELDS:
            if self.get(fieldname) != previous.get(fieldname):
                return True

        return _child_user_table_changed(
            before=previous.get("staff") or [],
            after=self.get("staff") or [],
            user_field="user",
            extra_fields=("role",),
        )

    def _sync_school_event_projection(self):
        if self.status == "Cancelled":
            self._remove_school_event_projection()
            return None

        participant_users = _visit_staff_users_from_doc(self)
        if not participant_users:
            frappe.throw(_("At least one visit staff user is required."), title=_("Missing Visit Staff"))

        if self.school_event and frappe.db.exists("School Event", self.school_event):
            school_event = frappe.get_doc("School Event", self.school_event)
        else:
            school_event = frappe.new_doc("School Event")

        school_event.subject = clean(self.visit_title) or _("Admission Visit")
        school_event.event_category = "Admissions Event"
        school_event.all_day = 0
        school_event.starts_on = self.starts_on
        school_event.ends_on = self.ends_on
        school_event.school = self.school
        school_event.location = clean(self.location) or None
        school_event.reference_type = ADMISSION_VISIT_REFERENCE_TYPE
        school_event.reference_name = self.name
        school_event.description = _school_event_description_for_visit(self)

        school_event.set("audience", [])
        school_event.append("audience", {"audience_type": "Custom Users"})
        school_event.set("participants", [])
        for user in participant_users:
            school_event.append("participants", {"participant": user})

        school_event.flags.ignore_permissions = True
        if school_event.is_new():
            school_event.insert(ignore_permissions=True)
        else:
            school_event.save(ignore_permissions=True)

        if self.school_event != school_event.name:
            self.db_set("school_event", school_event.name, update_modified=False)

        return school_event

    def _remove_school_event_projection(self) -> None:
        event_name = clean(self.school_event)
        if not event_name:
            return

        if self.school_event:
            self.db_set("school_event", None, update_modified=False)

        delete_employee_bookings_for_source("School Event", event_name)
        delete_location_bookings_for_source(source_doctype="School Event", source_name=event_name)
        if frappe.db.exists("School Event", event_name):
            frappe.delete_doc("School Event", event_name, ignore_permissions=True, force=True)

    def _record_booked_activity_if_needed(self) -> None:
        if self.booked_crm_activity or not self.conversation:
            return

        activity = _create_visit_crm_activity(
            conversation=self.conversation,
            activity_type="Booked Tour",
            activity_channel=_activity_channel_for_visit(self.visit_mode),
            note=_("Visit booked for {window}.").format(window=_format_visit_window(self.starts_on, self.ends_on)),
            next_action_on=getdate(self.starts_on),
        )
        self.db_set("booked_crm_activity", activity.name, update_modified=False)

    def _record_attended_activity_if_needed(self) -> None:
        if self.attended_crm_activity or not self.conversation:
            return

        activity = _create_visit_crm_activity(
            conversation=self.conversation,
            activity_type="Attended Tour",
            activity_channel=_activity_channel_for_visit(self.visit_mode),
            outcome="Completed",
            note=_("Visit marked completed for {window}.").format(
                window=_format_visit_window(self.starts_on, self.ends_on)
            ),
        )
        self.db_set("attended_crm_activity", activity.name, update_modified=False)

    def _record_no_show_activity_if_needed(self) -> None:
        if self.no_show_crm_activity or not self.conversation:
            return

        activity = _create_visit_crm_activity(
            conversation=self.conversation,
            activity_type="Note",
            activity_channel=_activity_channel_for_visit(self.visit_mode),
            outcome="No Show",
            note=_("Visit marked no-show for {window}.").format(
                window=_format_visit_window(self.starts_on, self.ends_on)
            ),
        )
        self.db_set("no_show_crm_activity", activity.name, update_modified=False)

    def _record_cancelled_activity_if_needed(self) -> None:
        if self.cancelled_crm_activity or not self.conversation:
            return

        reason = clean(self.cancellation_reason)
        note = _("Visit cancelled for {window}.").format(window=_format_visit_window(self.starts_on, self.ends_on))
        if reason:
            note = _("{note} Reason: {reason}").format(note=note, reason=reason)

        activity = _create_visit_crm_activity(
            conversation=self.conversation,
            activity_type="Note",
            activity_channel=_activity_channel_for_visit(self.visit_mode),
            outcome="Cancelled",
            note=note,
        )
        self.db_set("cancelled_crm_activity", activity.name, update_modified=False)


@frappe.whitelist()
def get_admission_visit_schedule_options(
    *,
    conversation: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    organization: str | None = None,
    school: str | None = None,
):
    user = ensure_admissions_crm_permission()
    context = _resolve_visit_context(
        conversation=conversation,
        inquiry=inquiry,
        student_applicant=student_applicant,
        organization=organization,
        school=school,
    )
    _assert_visit_manage_permission(user=user, context=context)
    return _build_visit_schedule_options_payload(context=context)


@frappe.whitelist()
def get_admission_visit_detail(*, admission_visit: str):
    visit_name = clean(admission_visit)
    if not visit_name:
        frappe.throw(_("Admission visit is required."), title=_("Missing Admission Visit"))

    visit_doc = frappe.get_doc("Admission Visit", visit_name)
    if not has_permission(visit_doc, ptype="read", user=frappe.session.user):
        frappe.throw(_("You do not have permission to view this admission visit."), frappe.PermissionError)

    can_write = has_permission(visit_doc, ptype="write", user=frappe.session.user)
    context = {
        "conversation": visit_doc.conversation,
        "inquiry": visit_doc.inquiry,
        "student_applicant": visit_doc.student_applicant,
        "organization": visit_doc.organization,
        "school": visit_doc.school,
        "visitor_name": visit_doc.visitor_name,
        "visitor_email": visit_doc.visitor_email,
        "visitor_phone": visit_doc.visitor_phone,
        "requested_grade_level": visit_doc.requested_grade_level,
        "program_interest": visit_doc.program_interest,
    }
    options = _build_visit_schedule_options_payload(context=context)
    return {
        "ok": True,
        "can_write": bool(can_write),
        "visit": _serialize_admission_visit(visit_doc, include_internal=can_write),
        "options": options,
    }


@frappe.whitelist()
def suggest_admission_visit_slots(
    *,
    conversation: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    visit_date: str | None = None,
    lead_user: str | None = None,
    staff_users: Sequence[str] | str | None = None,
    visit_mode: str | None = None,
    building: str | None = None,
    location: str | None = None,
    duration_minutes: int | str | None = None,
    window_start_time=None,
    window_end_time=None,
    limit: int | str | None = None,
):
    user = ensure_admissions_crm_permission()
    context = _resolve_visit_context(
        conversation=conversation,
        inquiry=inquiry,
        student_applicant=student_applicant,
        organization=organization,
        school=school,
    )
    _assert_visit_manage_permission(user=user, context=context)

    location_value, _building_value = _resolve_visit_locations(
        location=location,
        building=building,
        mode=visit_mode,
        school=context.get("school"),
        require_for_in_person=False,
    )
    selected_users = _normalize_visit_staff_users(lead_user=lead_user, staff_users=staff_users)
    if not selected_users:
        selected_users = [frappe.session.user]
    _assert_visit_users_exist_and_enabled(selected_users, label=_("visit staff"))
    employee_rows = _resolve_employee_rows_for_users(selected_users)

    if not visit_date:
        frappe.throw(_("Visit date is required."), title=_("Missing Visit Date"))
    target_date = _to_date_or_throw(visit_date, fieldname="visit_date")

    duration = _to_positive_int(
        value=duration_minutes, default=DEFAULT_VISIT_DURATION_MINUTES, fieldname="duration_minutes"
    )
    start_time = _coerce_time(window_start_time or DEFAULT_SUGGESTION_WINDOW_START, fieldname="window_start_time")
    end_time = _coerce_time(window_end_time or DEFAULT_SUGGESTION_WINDOW_END, fieldname="window_end_time")
    window_start, window_end = _build_window_datetimes_for_date(
        target_date=target_date,
        start_time=start_time,
        end_time=end_time,
    )

    slots = _suggest_common_free_slots(
        employees=[row["name"] for row in employee_rows],
        location=location_value,
        window_start=window_start,
        window_end=window_end,
        duration_minutes=duration,
        step_minutes=DEFAULT_SUGGESTION_STEP_MINUTES,
        limit=_to_positive_int(value=limit, default=DEFAULT_SUGGESTION_LIMIT, fieldname="limit"),
    )

    return {
        "ok": True,
        "staff": [_serialize_employee_option(row) for row in employee_rows],
        "window": {
            "start": window_start.isoformat(),
            "end": window_end.isoformat(),
            "duration_minutes": duration,
            "step_minutes": DEFAULT_SUGGESTION_STEP_MINUTES,
            "location": location_value,
        },
        "slots": slots,
    }


@frappe.whitelist()
def schedule_admission_visit(
    *,
    conversation: str | None = None,
    inquiry: str | None = None,
    student_applicant: str | None = None,
    organization: str | None = None,
    school: str | None = None,
    starts_on: str,
    ends_on: str | None = None,
    duration_minutes: int | str | None = None,
    visit_type: str | None = None,
    visit_mode: str | None = None,
    building: str | None = None,
    location: str | None = None,
    lead_user: str | None = None,
    staff_users: Sequence[str] | str | None = None,
    informed_users: Sequence[str] | str | None = None,
    visitor_name: str | None = None,
    visitor_email: str | None = None,
    visitor_phone: str | None = None,
    relationship_to_student: str | None = None,
    requested_grade_level: str | None = None,
    program_interest: str | None = None,
    party_size: int | str | None = None,
    internal_notes: str | None = None,
    suggestion_window_start_time=None,
    suggestion_window_end_time=None,
    suggestion_limit: int | str | None = None,
):
    user = ensure_admissions_crm_permission()
    context = _resolve_visit_context(
        conversation=conversation,
        inquiry=inquiry,
        student_applicant=student_applicant,
        organization=organization,
        school=school,
    )
    _assert_visit_manage_permission(user=user, context=context)

    visit_mode_value = clean(visit_mode) or "In Person"
    location_value, building_value = _resolve_visit_locations(
        location=location,
        building=building,
        mode=visit_mode_value,
        school=context.get("school"),
        require_for_in_person=True,
    )

    selected_users = _normalize_visit_staff_users(lead_user=lead_user, staff_users=staff_users)
    if not selected_users:
        selected_users = [frappe.session.user]
    _assert_visit_users_exist_and_enabled(selected_users, label=_("visit staff"))
    employee_rows = _resolve_employee_rows_for_users(selected_users)

    informed_user_rows = _normalize_user_sequence(informed_users)
    if informed_user_rows:
        _assert_visit_users_exist_and_enabled(informed_user_rows, label=_("informed users"))

    start_dt = _to_datetime_or_throw(starts_on, fieldname="starts_on")
    if ends_on:
        end_dt = _to_datetime_or_throw(ends_on, fieldname="ends_on")
    else:
        minutes = _to_positive_int(
            value=duration_minutes, default=DEFAULT_VISIT_DURATION_MINUTES, fieldname="duration_minutes"
        )
        end_dt = start_dt + timedelta(minutes=minutes)
    if end_dt <= start_dt:
        frappe.throw(_("Visit end must be after visit start."), title=_("Invalid Time Window"))

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
            "message": _visit_schedule_conflict_message(conflict_code),
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

    savepoint = "schedule_admission_visit"
    frappe.db.savepoint(savepoint)
    try:
        conversation_name = _ensure_visit_conversation(user=user, context=context)
        if conversation_name:
            context = _resolve_visit_context(
                conversation=conversation_name,
                inquiry=context.get("inquiry"),
                student_applicant=context.get("student_applicant"),
                organization=context.get("organization"),
                school=context.get("school"),
            )
            _assert_visit_manage_permission(user=user, context=context)

        visit_doc = frappe.new_doc("Admission Visit")
        visit_doc.organization = context.get("organization")
        visit_doc.school = context.get("school")
        visit_doc.conversation = context.get("conversation")
        visit_doc.inquiry = context.get("inquiry")
        visit_doc.student_applicant = context.get("student_applicant")
        visit_doc.status = "Scheduled"
        visit_doc.visit_type = clean(visit_type) or "Family Tour"
        visit_doc.visit_mode = visit_mode_value
        visit_doc.starts_on = start_dt
        visit_doc.ends_on = end_dt
        visit_doc.building = building_value
        visit_doc.location = location_value
        visit_doc.lead_user = selected_users[0]
        visit_doc.visitor_name = clean(visitor_name) or context.get("visitor_name")
        visit_doc.visitor_email = clean(visitor_email) or context.get("visitor_email")
        visit_doc.visitor_phone = clean(visitor_phone) or context.get("visitor_phone")
        visit_doc.relationship_to_student = clean(relationship_to_student)
        visit_doc.requested_grade_level = clean(requested_grade_level) or context.get("requested_grade_level")
        visit_doc.program_interest = clean(program_interest) or context.get("program_interest")
        visit_doc.party_size = _to_non_negative_int_or_none(party_size, fieldname="party_size")
        visit_doc.internal_notes = internal_notes

        for staff_user in selected_users[1:]:
            visit_doc.append("staff", {"user": staff_user, "role": "Co-host"})
        for informed_user in _dedupe_keep_order(informed_user_rows):
            if informed_user not in selected_users:
                visit_doc.append("informed_users", {"user": informed_user})

        visit_doc.flags.from_schedule_admission_visit = True
        visit_doc.insert(ignore_permissions=True)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

    return {
        "ok": True,
        "admission_visit": visit_doc.name,
        "school_event": visit_doc.school_event,
        "conversation": visit_doc.conversation,
        "window": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "location": location_value,
            "building": building_value,
        },
    }


@frappe.whitelist()
def reschedule_admission_visit(
    *,
    admission_visit: str,
    starts_on: str,
    ends_on: str | None = None,
    duration_minutes: int | str | None = None,
    visit_type: str | None = None,
    visit_mode: str | None = None,
    building: str | None = None,
    location: str | None = None,
    lead_user: str | None = None,
    staff_users: Sequence[str] | str | None = None,
    informed_users: Sequence[str] | str | None = None,
    visitor_name: str | None = None,
    visitor_email: str | None = None,
    visitor_phone: str | None = None,
    relationship_to_student: str | None = None,
    requested_grade_level: str | None = None,
    program_interest: str | None = None,
    party_size: int | str | None = None,
    internal_notes: str | None = None,
    suggestion_window_start_time=None,
    suggestion_window_end_time=None,
    suggestion_limit: int | str | None = None,
):
    visit_doc = _get_admission_visit_for_write(admission_visit)
    context = _resolve_visit_context(
        conversation=visit_doc.conversation,
        inquiry=visit_doc.inquiry,
        student_applicant=visit_doc.student_applicant,
        organization=visit_doc.organization,
        school=visit_doc.school,
    )

    visit_mode_value = clean(visit_mode) or clean(visit_doc.visit_mode) or "In Person"
    location_value, building_value = _resolve_visit_locations(
        location=location if location is not None else visit_doc.location,
        building=building if building is not None else visit_doc.building,
        mode=visit_mode_value,
        school=context.get("school"),
        require_for_in_person=True,
    )
    selected_users = _normalize_visit_staff_users(lead_user=lead_user, staff_users=staff_users)
    if not selected_users:
        selected_users = _visit_staff_users_from_doc(visit_doc)
    _assert_visit_users_exist_and_enabled(selected_users, label=_("visit staff"))
    employee_rows = _resolve_employee_rows_for_users(selected_users)

    informed_user_rows = _normalize_user_sequence(informed_users)
    if informed_user_rows:
        _assert_visit_users_exist_and_enabled(informed_user_rows, label=_("informed users"))

    start_dt = _to_datetime_or_throw(starts_on, fieldname="starts_on")
    if ends_on:
        end_dt = _to_datetime_or_throw(ends_on, fieldname="ends_on")
    else:
        minutes = _to_positive_int(
            value=duration_minutes, default=DEFAULT_VISIT_DURATION_MINUTES, fieldname="duration_minutes"
        )
        end_dt = start_dt + timedelta(minutes=minutes)
    if end_dt <= start_dt:
        frappe.throw(_("Visit end must be after visit start."), title=_("Invalid Time Window"))

    exclude_source = _visit_projection_exclude_source(visit_doc)
    employee_conflict_rows = _collect_employee_conflicts(
        employee_rows=employee_rows,
        start_dt=start_dt,
        end_dt=end_dt,
        exclude_source=exclude_source,
    )
    room_conflict_rows = _collect_room_conflicts(
        location=location_value,
        start_dt=start_dt,
        end_dt=end_dt,
        exclude_source=exclude_source,
    )
    conflict_rows = _combine_conflict_rows(
        employee_conflict_rows=employee_conflict_rows,
        room_conflict_rows=room_conflict_rows,
    )
    if conflict_rows:
        return _visit_conflict_response(
            employee_rows=employee_rows,
            location=location_value,
            start_dt=start_dt,
            end_dt=end_dt,
            employee_conflict_rows=employee_conflict_rows,
            room_conflict_rows=room_conflict_rows,
            suggestion_window_start_time=suggestion_window_start_time,
            suggestion_window_end_time=suggestion_window_end_time,
            suggestion_limit=suggestion_limit,
        )

    savepoint = "reschedule_admission_visit"
    frappe.db.savepoint(savepoint)
    try:
        visit_doc.status = "Scheduled"
        visit_doc.visit_type = clean(visit_type) or visit_doc.visit_type or "Family Tour"
        visit_doc.visit_mode = visit_mode_value
        visit_doc.starts_on = start_dt
        visit_doc.ends_on = end_dt
        visit_doc.building = building_value
        visit_doc.location = location_value
        visit_doc.lead_user = selected_users[0]
        visit_doc.visitor_name = clean(visitor_name) or visit_doc.visitor_name
        visit_doc.visitor_email = clean(visitor_email) or visit_doc.visitor_email
        visit_doc.visitor_phone = clean(visitor_phone) or visit_doc.visitor_phone
        visit_doc.relationship_to_student = clean(relationship_to_student)
        visit_doc.requested_grade_level = clean(requested_grade_level) or visit_doc.requested_grade_level
        visit_doc.program_interest = clean(program_interest) or visit_doc.program_interest
        visit_doc.party_size = (
            _to_non_negative_int_or_none(party_size, fieldname="party_size")
            if party_size is not None
            else visit_doc.party_size
        )
        visit_doc.internal_notes = internal_notes if internal_notes is not None else visit_doc.internal_notes
        visit_doc.cancelled_at = None
        visit_doc.cancelled_by = None
        visit_doc.cancellation_reason = None
        visit_doc.set("staff", [])
        for staff_user in selected_users[1:]:
            visit_doc.append("staff", {"user": staff_user, "role": "Co-host"})
        visit_doc.set("informed_users", [])
        for informed_user in _dedupe_keep_order(informed_user_rows):
            if informed_user not in selected_users:
                visit_doc.append("informed_users", {"user": informed_user})
        visit_doc.save(ignore_permissions=True)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

    return {
        "ok": True,
        "admission_visit": visit_doc.name,
        "school_event": visit_doc.school_event,
        "window": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat(),
            "location": location_value,
            "building": building_value,
        },
    }


@frappe.whitelist()
def cancel_admission_visit(*, admission_visit: str, reason: str | None = None):
    visit_doc = _get_admission_visit_for_write(admission_visit)
    if visit_doc.status == "Cancelled":
        return {"ok": True, "admission_visit": visit_doc.name, "status": visit_doc.status}

    savepoint = "cancel_admission_visit"
    frappe.db.savepoint(savepoint)
    try:
        visit_doc.status = "Cancelled"
        visit_doc.cancellation_reason = clean(reason)
        visit_doc.cancelled_at = now_datetime()
        visit_doc.cancelled_by = frappe.session.user
        visit_doc.save(ignore_permissions=True)
    except Exception:
        frappe.db.rollback(save_point=savepoint)
        raise

    return {"ok": True, "admission_visit": visit_doc.name, "status": visit_doc.status}


@frappe.whitelist()
def mark_admission_visit_completed(*, admission_visit: str):
    visit_doc = _get_admission_visit_for_write(admission_visit)
    if visit_doc.status != "Completed":
        visit_doc.status = "Completed"
        visit_doc.save(ignore_permissions=True)
    return {"ok": True, "admission_visit": visit_doc.name, "status": visit_doc.status}


@frappe.whitelist()
def mark_admission_visit_no_show(*, admission_visit: str):
    visit_doc = _get_admission_visit_for_write(admission_visit)
    if visit_doc.status != "No Show":
        visit_doc.status = "No Show"
        visit_doc.save(ignore_permissions=True)
    return {"ok": True, "admission_visit": visit_doc.name, "status": visit_doc.status}


@frappe.whitelist()
def notify_admission_visit_informed_users(*, admission_visit: str, message: str | None = None):
    visit_doc = _get_admission_visit_for_write(admission_visit)
    users = _visit_informed_users_from_doc(visit_doc)
    if not users:
        return {"ok": True, "admission_visit": visit_doc.name, "notified_users": []}

    notice = clean(message) or _("Admission visit scheduled: {title}").format(
        title=clean(visit_doc.visit_title) or visit_doc.name
    )
    payload = {
        "type": "Alert",
        "subject": _("Admission Visit"),
        "message": notice,
        "reference_doctype": "Admission Visit",
        "reference_name": visit_doc.name,
        "starts_on": str(visit_doc.starts_on or ""),
        "school": visit_doc.school,
    }
    for user in users:
        frappe.publish_realtime(event="inbox_notification", message=payload, user=user, after_commit=True)

    if visit_doc.conversation:
        _create_visit_crm_activity(
            conversation=visit_doc.conversation,
            activity_type="Note",
            activity_channel="Other",
            outcome="Informed Staff",
            note=_("Admission visit heads-up sent to: {users}.").format(users=", ".join(users)),
        )

    return {"ok": True, "admission_visit": visit_doc.name, "notified_users": users}


def get_permission_query_conditions(user: str | None = None) -> str | None:
    resolved_user = clean(user or frappe.session.user)
    if not resolved_user or resolved_user == "Guest":
        return "1=0"

    conditions: list[str] = []
    if is_admissions_crm_user(resolved_user):
        scoped_condition = _admission_visit_scope_condition(user=resolved_user)
        if scoped_condition is None:
            return None
        if scoped_condition != "1=0":
            conditions.append(f"({scoped_condition})")

    escaped_user = frappe.db.escape(resolved_user)
    conditions.append(f"`tabAdmission Visit`.`lead_user` = {escaped_user}")
    conditions.append(
        "EXISTS ("
        "SELECT 1 FROM `tabAdmission Visit Staff` avs "
        "WHERE avs.parent = `tabAdmission Visit`.`name` "
        "AND avs.parenttype = 'Admission Visit' "
        "AND avs.parentfield = 'staff' "
        f"AND avs.user = {escaped_user}"
        ")"
    )
    return " OR ".join(f"({condition})" for condition in conditions)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
    resolved_user = clean(user or frappe.session.user)
    op = (ptype or "read").lower()
    if not resolved_user or resolved_user == "Guest":
        return False
    if resolved_user == "Administrator":
        return True
    if op == "create":
        return is_admissions_crm_user(resolved_user)
    if op in {"delete", "submit"}:
        return False
    if op not in READ_LIKE_PERMISSION_TYPES and op != "write":
        return False

    visit = _visit_permission_row(doc)
    if not visit:
        return op in READ_LIKE_PERMISSION_TYPES

    if op == "write":
        return is_admissions_crm_user(resolved_user) and doc_is_in_admissions_crm_scope(
            user=resolved_user,
            organization=visit.get("organization"),
            school=visit.get("school"),
        )

    if is_admissions_crm_user(resolved_user) and doc_is_in_admissions_crm_scope(
        user=resolved_user,
        organization=visit.get("organization"),
        school=visit.get("school"),
    ):
        return True

    visit_name = visit.get("name")
    if not visit_name:
        return False
    if visit.get("lead_user") == resolved_user:
        return True
    return bool(
        frappe.db.exists(
            "Admission Visit Staff",
            {
                "parent": visit_name,
                "parenttype": "Admission Visit",
                "parentfield": "staff",
                "user": resolved_user,
            },
        )
    )


def _resolve_visit_context(
    *,
    conversation: str | None,
    inquiry: str | None,
    student_applicant: str | None,
    organization: str | None,
    school: str | None,
) -> dict:
    out = {
        "conversation": clean(conversation),
        "inquiry": clean(inquiry),
        "student_applicant": clean(student_applicant),
        "organization": clean(organization),
        "school": clean(school),
    }

    conversation_row = _get_conversation_context(out.get("conversation"))
    if conversation_row:
        _apply_context_value(
            out, "organization", conversation_row.get("organization"), source_label=_("Admission Conversation")
        )
        _apply_context_value(out, "school", conversation_row.get("school"), source_label=_("Admission Conversation"))
        _apply_context_value(out, "inquiry", conversation_row.get("inquiry"), source_label=_("Admission Conversation"))
        _apply_context_value(
            out,
            "student_applicant",
            conversation_row.get("student_applicant"),
            source_label=_("Admission Conversation"),
        )
        out["visitor_name"] = clean(conversation_row.get("title"))

    inquiry_row = _get_inquiry_context(out.get("inquiry"))
    if inquiry_row:
        _apply_context_value(out, "organization", inquiry_row.get("organization"), source_label=_("Inquiry"))
        _apply_context_value(out, "school", inquiry_row.get("school"), source_label=_("Inquiry"))
        _apply_context_value(out, "student_applicant", inquiry_row.get("student_applicant"), source_label=_("Inquiry"))
        name_parts = [clean(inquiry_row.get("first_name")), clean(inquiry_row.get("last_name"))]
        out["visitor_name"] = out.get("visitor_name") or " ".join(part for part in name_parts if part)
        out["visitor_email"] = clean(inquiry_row.get("email"))
        out["visitor_phone"] = clean(inquiry_row.get("phone_number"))
        out["requested_grade_level"] = clean(inquiry_row.get("grade_level_interest"))
        out["program_interest"] = clean(inquiry_row.get("program_interest"))

    applicant_row = _get_student_applicant_context(out.get("student_applicant"))
    if applicant_row:
        _apply_context_value(
            out, "organization", applicant_row.get("organization"), source_label=_("Student Applicant")
        )
        _apply_context_value(out, "school", applicant_row.get("school"), source_label=_("Student Applicant"))
        _apply_context_value(out, "inquiry", applicant_row.get("inquiry"), source_label=_("Student Applicant"))
        out["visitor_name"] = out.get("visitor_name") or _applicant_display_name_from_row(applicant_row)
        out["visitor_email"] = out.get("visitor_email") or clean(applicant_row.get("applicant_email"))

    if out.get("school") and not out.get("organization"):
        out["organization"] = get_school_organization(out.get("school"))

    assert_school_in_organization_scope(school=out.get("school"), organization=out.get("organization"))
    return out


def _get_conversation_context(conversation: str | None) -> dict:
    conversation_name = clean(conversation)
    if not conversation_name:
        return {}
    row = frappe.db.get_value(
        "Admission Conversation",
        conversation_name,
        ["name", "organization", "school", "inquiry", "student_applicant", "title", "assigned_to", "owner"],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Admission Conversation not found: {conversation}").format(conversation=conversation_name))
    return dict(row)


def _get_inquiry_context(inquiry: str | None) -> dict:
    inquiry_name = clean(inquiry)
    if not inquiry_name:
        return {}
    row = frappe.db.get_value(
        "Inquiry",
        inquiry_name,
        [
            "name",
            "organization",
            "school",
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "student_applicant",
            "grade_level_interest",
            "program_interest",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Inquiry not found: {inquiry}").format(inquiry=inquiry_name))
    return dict(row)


def _get_student_applicant_context(student_applicant: str | None) -> dict:
    applicant_name = clean(student_applicant)
    if not applicant_name:
        return {}
    row = frappe.db.get_value(
        "Student Applicant",
        applicant_name,
        [
            "name",
            "organization",
            "school",
            "first_name",
            "middle_name",
            "last_name",
            "applicant_email",
            "inquiry",
            "application_status",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("Student Applicant not found: {student_applicant}").format(student_applicant=applicant_name))
    if row.get("application_status") in TERMINAL_APPLICANT_STATES:
        frappe.throw(_("Applicant is read-only in terminal states."))
    return dict(row)


def _apply_context_value(target: dict, fieldname: str, value: str | None, *, source_label: str) -> None:
    resolved_value = clean(value)
    if not resolved_value:
        return
    current_value = clean(target.get(fieldname))
    if current_value and current_value != resolved_value:
        frappe.throw(
            _("{fieldname} does not match {source_label}.").format(fieldname=fieldname, source_label=source_label)
        )
    target[fieldname] = resolved_value


def _assert_visit_manage_permission(*, user: str, context: dict) -> None:
    if user == "Administrator":
        return
    if not doc_is_in_admissions_crm_scope(
        user=user,
        organization=context.get("organization"),
        school=context.get("school"),
    ):
        frappe.throw(_("You do not have permission for this admission visit scope."), frappe.PermissionError)
    if context.get("conversation") and not conversation_has_permission(
        context.get("conversation"), ptype="write", user=user
    ):
        frappe.throw(_("You do not have permission to schedule visits for this conversation."), frappe.PermissionError)


def _get_admission_visit_for_write(admission_visit: str):
    user = ensure_admissions_crm_permission()
    visit_name = clean(admission_visit)
    if not visit_name:
        frappe.throw(_("Admission visit is required."), title=_("Missing Admission Visit"))
    visit_doc = frappe.get_doc("Admission Visit", visit_name)
    if not has_permission(visit_doc, ptype="write", user=user):
        frappe.throw(_("You do not have permission to update this admission visit."), frappe.PermissionError)
    return visit_doc


def _build_visit_schedule_options_payload(*, context: dict) -> dict:
    school_name = context.get("school")
    room_rows = []
    building_rows = []
    if school_name:
        room_rows = get_visible_location_rows_for_school(
            school_name,
            include_groups=False,
            only_schedulable=True,
            fields=[
                "name",
                "location_name",
                "school",
                "parent_location",
                "location_type",
                "is_group",
                "maximum_capacity",
            ],
            limit=200,
        )
        room_names = {row.get("name") for row in room_rows if row.get("name")}
        all_location_rows = get_visible_location_rows_for_school(
            school_name,
            include_groups=True,
            only_schedulable=False,
            fields=[
                "name",
                "location_name",
                "school",
                "parent_location",
                "location_type",
                "is_group",
                "maximum_capacity",
            ],
            limit=200,
        )
        building_rows = [
            row for row in all_location_rows if int(row.get("is_group") or 0) or row.get("name") not in room_names
        ]

    return {
        "ok": True,
        "context": {
            "conversation": context.get("conversation"),
            "inquiry": context.get("inquiry"),
            "student_applicant": context.get("student_applicant"),
            "organization": context.get("organization"),
            "school": context.get("school"),
            "visitor_name": context.get("visitor_name"),
            "visitor_email": context.get("visitor_email"),
            "visitor_phone": context.get("visitor_phone"),
            "requested_grade_level": context.get("requested_grade_level"),
            "program_interest": context.get("program_interest"),
        },
        "defaults": {
            "date": nowdate(),
            "start_time": "09:00:00",
            "duration_minutes": DEFAULT_VISIT_DURATION_MINUTES,
            "window_start_time": DEFAULT_SUGGESTION_WINDOW_START,
            "window_end_time": DEFAULT_SUGGESTION_WINDOW_END,
            "lead_user": frappe.session.user,
            "visit_type": "Family Tour",
            "visit_mode": "In Person",
        },
        "rooms": [_serialize_location_option(row) for row in room_rows],
        "buildings": [_serialize_location_option(row) for row in building_rows],
        "visit_types": [
            "Family Tour",
            "Student Tour",
            "Open Day",
            "School Visit",
            "College Visit",
            "Shadow Day",
            "Other",
        ],
        "visit_modes": ["In Person", "Online", "Phone"],
    }


def _serialize_admission_visit(doc, *, include_internal: bool) -> dict:
    staff_users = _visit_staff_users_from_doc(doc)
    informed_users = _visit_informed_users_from_doc(doc)
    return {
        "name": doc.name,
        "visit_title": doc.visit_title,
        "organization": doc.organization,
        "school": doc.school,
        "status": doc.status,
        "conversation": doc.conversation,
        "inquiry": doc.inquiry,
        "student_applicant": doc.student_applicant,
        "visit_type": doc.visit_type,
        "visit_mode": doc.visit_mode,
        "starts_on": doc.starts_on.isoformat() if hasattr(doc.starts_on, "isoformat") else doc.starts_on,
        "ends_on": doc.ends_on.isoformat() if hasattr(doc.ends_on, "isoformat") else doc.ends_on,
        "building": doc.building,
        "location": doc.location,
        "party_size": doc.party_size,
        "visitor_name": doc.visitor_name,
        "visitor_email": doc.visitor_email,
        "visitor_phone": doc.visitor_phone,
        "relationship_to_student": doc.relationship_to_student,
        "requested_grade_level": doc.requested_grade_level,
        "program_interest": doc.program_interest,
        "lead_user": doc.lead_user,
        "staff_users": staff_users,
        "informed_users": informed_users,
        "internal_notes": doc.internal_notes if include_internal else None,
        "school_event": doc.school_event,
        "cancelled_at": doc.cancelled_at.isoformat() if hasattr(doc.cancelled_at, "isoformat") else doc.cancelled_at,
        "cancelled_by": doc.cancelled_by,
        "cancellation_reason": doc.cancellation_reason if include_internal else None,
    }


def _visit_projection_exclude_source(doc) -> dict | None:
    event_name = clean(doc.school_event)
    if not event_name:
        return None
    return {"source_doctype": "School Event", "source_name": event_name}


def _visit_conflict_response(
    *,
    employee_rows: Sequence[frappe._dict],
    location: str | None,
    start_dt,
    end_dt,
    employee_conflict_rows: list[dict],
    room_conflict_rows: list[dict],
    suggestion_window_start_time,
    suggestion_window_end_time,
    suggestion_limit: int | str | None,
) -> dict:
    conflict_rows = _combine_conflict_rows(
        employee_conflict_rows=employee_conflict_rows,
        room_conflict_rows=room_conflict_rows,
    )
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
        location=location,
        window_start=suggestion_window_start,
        window_end=suggestion_window_end,
        duration_minutes=int((end_dt - start_dt).total_seconds() // 60),
        step_minutes=DEFAULT_SUGGESTION_STEP_MINUTES,
        limit=_to_positive_int(value=suggestion_limit, default=DEFAULT_SUGGESTION_LIMIT, fieldname="suggestion_limit"),
    )
    conflict_code = _schedule_conflict_code(
        employee_conflict_rows=employee_conflict_rows,
        room_conflict_rows=room_conflict_rows,
    )
    return {
        "ok": False,
        "code": conflict_code,
        "message": _visit_schedule_conflict_message(conflict_code),
        "conflicts": conflict_rows,
        "employee_conflicts": employee_conflict_rows,
        "room_conflicts": room_conflict_rows,
        "suggestions": suggestion_rows,
        "window": {
            "start": suggestion_window_start.isoformat(),
            "end": suggestion_window_end.isoformat(),
            "location": location,
        },
    }


def _ensure_visit_conversation(*, user: str, context: dict) -> str | None:
    if context.get("conversation"):
        return context.get("conversation")

    inquiry = clean(context.get("inquiry"))
    student_applicant = clean(context.get("student_applicant"))
    if not inquiry and not student_applicant:
        return None

    existing = _find_existing_visit_conversation(inquiry=inquiry, student_applicant=student_applicant)
    if existing:
        if not conversation_has_permission(existing, ptype="write", user=user):
            frappe.throw(
                _("You do not have permission to schedule visits for this conversation."), frappe.PermissionError
            )
        return existing

    doc = frappe.get_doc(
        {
            "doctype": "Admission Conversation",
            "inquiry": inquiry,
            "student_applicant": student_applicant,
            "organization": context.get("organization"),
            "school": context.get("school"),
            "assigned_to": user,
        }
    )
    doc.insert(ignore_permissions=True)
    return doc.name


def _find_existing_visit_conversation(*, inquiry: str | None, student_applicant: str | None) -> str | None:
    filters = []
    if inquiry:
        filters.append({"inquiry": inquiry, "status": ["!=", "Spam"]})
    if student_applicant:
        filters.append({"student_applicant": student_applicant, "status": ["!=", "Spam"]})

    for filter_row in filters:
        rows = frappe.get_all(
            "Admission Conversation",
            filters=filter_row,
            fields=["name"],
            order_by="modified desc",
            limit=1,
            ignore_permissions=True,
        )
        if rows:
            return rows[0].get("name")
    return None


def _resolve_visit_locations(
    *,
    location: str | None,
    building: str | None,
    mode: str | None,
    school: str | None,
    require_for_in_person: bool,
) -> tuple[str | None, str | None]:
    mode_value = clean(mode)
    location_name = clean(location)
    building_name = clean(building)
    school_name = clean(school)

    if mode_value == "In Person" and require_for_in_person and not (location_name or building_name):
        frappe.throw(
            _("Select a meeting room or building for an in-person visit."),
            title=_("Location Required"),
        )

    if not location_name and not building_name:
        return None, None

    if not school_name:
        frappe.throw(_("School is required before selecting visit locations."), title=_("School Required"))

    visible_rows = get_visible_location_rows_for_school(
        school_name,
        include_groups=True,
        only_schedulable=False,
        fields=["name", "location_name", "school", "parent_location", "location_type", "is_group", "maximum_capacity"],
        limit=2000,
    )
    visible_names = {row.get("name") for row in visible_rows if row.get("name")}
    if location_name:
        if location_name not in visible_names:
            frappe.throw(_("Selected meeting room is not available for this school."), title=_("Invalid Room"))
        if not is_schedulable_location(location_name):
            building_name = location_name
            location_name = ""
    if building_name and building_name not in visible_names:
        frappe.throw(_("Selected building is not available for this school."), title=_("Invalid Building"))

    return location_name or None, building_name or None


def _normalize_visit_staff_users(*, lead_user: str | None, staff_users: Sequence[str] | str | None) -> list[str]:
    users = []
    lead = clean(lead_user)
    if lead:
        users.append(lead)
    users.extend(_normalize_user_sequence(staff_users))
    return _dedupe_keep_order(users)


def _visit_staff_users_from_doc(doc) -> list[str]:
    users = []
    if clean(doc.lead_user):
        users.append(clean(doc.lead_user))
    for row in doc.get("staff") or []:
        user = clean(row.get("user"))
        if user:
            users.append(user)
    return _dedupe_keep_order(users)


def _visit_informed_users_from_doc(doc) -> list[str]:
    users = []
    for row in doc.get("informed_users") or []:
        user = clean(row.get("user"))
        if user:
            users.append(user)
    return _dedupe_keep_order(users)


def _assert_visit_users_exist_and_enabled(user_ids: Sequence[str], *, label: str) -> None:
    if not user_ids:
        frappe.throw(_("At least one {label} user is required.").format(label=label), title=_("Missing Users"))

    rows = frappe.get_all(
        "User",
        filters={"name": ["in", list(user_ids)], "enabled": 1},
        pluck="name",
        ignore_permissions=True,
    )
    enabled_users = set(rows or [])
    missing = [user for user in user_ids if user not in enabled_users]
    if missing:
        frappe.throw(
            _("These {label} are missing or disabled: {users}").format(
                label=label,
                users=", ".join(sorted(set(missing))),
            ),
            title=_("Invalid Users"),
        )


def _resolve_employee_rows_for_users(user_ids: Sequence[str]) -> list[frappe._dict]:
    rows = frappe.get_all(
        "Employee",
        filters={
            "user_id": ["in", list(user_ids)],
            "employment_status": ["!=", "Inactive"],
        },
        fields=["name", "user_id", "employee_full_name"],
        ignore_permissions=True,
    )
    by_user = {row.user_id: row for row in rows if row.get("user_id")}
    missing = [user for user in user_ids if user not in by_user]
    if missing:
        frappe.throw(
            _("Visit staff must be linked to active Employee records. Missing: {users}").format(
                users=", ".join(sorted(set(missing)))
            ),
            title=_("Missing Employee Link"),
        )
    return [by_user[user] for user in user_ids]


def _serialize_employee_option(row: frappe._dict) -> dict:
    return {
        "user": row.get("user_id"),
        "employee": row.get("name"),
        "employee_name": row.get("employee_full_name") or row.get("name"),
    }


def _serialize_location_option(row: dict) -> dict:
    name = clean(row.get("name"))
    label = clean(row.get("location_name")) or name
    return {
        "value": name,
        "label": label,
        "school": row.get("school"),
        "parent_location": row.get("parent_location"),
        "location_type": row.get("location_type"),
        "location_type_name": row.get("location_type_name"),
        "is_group": int(row.get("is_group") or 0),
        "max_capacity": row.get("maximum_capacity"),
    }


def _visit_schedule_conflict_message(code: str) -> str:
    if code == "ROOM_CONFLICT":
        return _("The selected room is already booked for the selected time.")
    if code == "SCHEDULING_CONFLICT":
        return _("One or more visit staff and the selected room are already booked for the selected time.")
    return _("One or more visit staff are already booked for the selected time.")


def _create_visit_crm_activity(
    *,
    conversation: str,
    activity_type: str,
    activity_channel: str | None = None,
    outcome: str | None = None,
    note: str | None = None,
    next_action_on=None,
):
    activity = frappe.get_doc(
        {
            "doctype": "Admission CRM Activity",
            "conversation": conversation,
            "activity_type": activity_type,
            "activity_channel": activity_channel,
            "outcome": outcome,
            "note": note,
            "next_action_on": next_action_on,
        }
    )
    activity.insert(ignore_permissions=True)
    return activity


def _activity_channel_for_visit(visit_mode: str | None) -> str:
    mode = clean(visit_mode)
    if mode == "In Person":
        return "In Person"
    if mode == "Online":
        return "Other"
    if mode == "Phone":
        return "Phone"
    return "Other"


def _format_visit_window(starts_on, ends_on) -> str:
    return _("{start} to {end}").format(start=format_datetime(starts_on), end=format_datetime(ends_on))


def _school_event_description_for_visit(doc) -> str:
    parts = []
    if clean(doc.visit_type):
        parts.append(_("Visit Type: {visit_type}").format(visit_type=doc.visit_type))
    if clean(doc.visit_mode):
        parts.append(_("Mode: {visit_mode}").format(visit_mode=doc.visit_mode))
    if clean(doc.building):
        parts.append(_("Building / Area: {building}").format(building=doc.building))
    if clean(doc.visitor_name):
        parts.append(_("Visitor: {visitor}").format(visitor=doc.visitor_name))
    if doc.party_size:
        parts.append(_("Party Size: {party_size}").format(party_size=doc.party_size))
    return "\n".join(parts)


def _student_applicant_display_name(student_applicant: str) -> str:
    row = _get_student_applicant_context(student_applicant)
    return _applicant_display_name_from_row(row)


def _applicant_display_name_from_row(row: dict) -> str:
    parts = [clean(row.get("first_name")), clean(row.get("middle_name")), clean(row.get("last_name"))]
    display = " ".join(part for part in parts if part)
    return display or clean(row.get("name")) or _("Applicant")


def _dedupe_keep_order(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values or []:
        item = clean(value)
        if not item or item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _to_non_negative_int_or_none(value, *, fieldname: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except Exception:
        parsed = -1
    if parsed < 0:
        frappe.throw(_("{fieldname} must be zero or greater.").format(fieldname=fieldname), title=_("Invalid Number"))
    return parsed


def _child_user_table_changed(*, before, after, user_field: str, extra_fields: Sequence[str]) -> bool:
    return _child_user_table_signature(
        before, user_field=user_field, extra_fields=extra_fields
    ) != _child_user_table_signature(
        after,
        user_field=user_field,
        extra_fields=extra_fields,
    )


def _child_user_table_signature(rows, *, user_field: str, extra_fields: Sequence[str]) -> list[tuple]:
    signature = []
    for row in rows or []:
        values = [clean(row.get(user_field))]
        values.extend(clean(row.get(fieldname)) for fieldname in extra_fields)
        if values[0]:
            signature.append(tuple(values))
    return signature


def _admission_visit_scope_condition(*, user: str) -> str | None:
    scope = get_admissions_file_staff_scope(user)
    if not scope.get("allowed"):
        return "1=0"
    if scope.get("bypass"):
        return None

    org_scope = set(scope.get("org_scope") or set())
    school_scope = set(scope.get("school_scope") or set())
    conditions = []

    org_values = _scope_values_to_sql(org_scope)
    if org_values:
        conditions.append(f"`tabAdmission Visit`.`organization` IN ({org_values})")

    school_values = _scope_values_to_sql(school_scope)
    if school_values:
        conditions.append(
            f"(IFNULL(`tabAdmission Visit`.`school`, '') = '' OR `tabAdmission Visit`.`school` IN ({school_values}))"
        )

    return " AND ".join(conditions) if conditions else "1=0"


def _scope_values_to_sql(values: set[str]) -> str:
    cleaned = sorted({clean(value) for value in values if clean(value)})
    return ", ".join(frappe.db.escape(value) for value in cleaned)


def _visit_permission_row(doc) -> dict | None:
    if not doc:
        return None
    if isinstance(doc, str):
        row = frappe.db.get_value(
            "Admission Visit",
            doc,
            ["name", "organization", "school", "lead_user"],
            as_dict=True,
        )
        return dict(row) if row else None
    if isinstance(doc, dict):
        return dict(doc)
    return {
        "name": getattr(doc, "name", None),
        "organization": getattr(doc, "organization", None),
        "school": getattr(doc, "school", None),
        "lead_user": getattr(doc, "lead_user", None),
    }
