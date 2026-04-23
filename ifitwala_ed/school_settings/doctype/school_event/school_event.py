# Copyright (c) 2024, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/school_settings/doctype/school_event/school_event.py

import json
from collections import defaultdict
from typing import Dict, Set

import frappe
from frappe import _
from frappe.desk.reportview import get_filters_cond
from frappe.model.document import Document
from frappe.utils import (
    cint,
    get_datetime,
    get_system_timezone,
    now_datetime,
)
from frappe.utils.caching import redis_cache

from ifitwala_ed.stock.doctype.location_booking.location_booking import (
    build_slot_key_single,
    build_source_key,
    delete_location_bookings_for_source,
    upsert_location_booking,
)

WHOLE_SCHOOL_AUDIENCE = "All Students, Guardians, and Employees"

BROAD_AUDIENCE_TYPES = {
    WHOLE_SCHOOL_AUDIENCE,
    "All Students",
    "All Guardians",
    "All Employees",
}

ADMIN_AUDIENCE_ROLES = {
    "System Manager",
    "Academic Admin",
    "Academic Assistant",
}
ORG_COMMUNICATION_REFERENCE_TYPE = "Org Communication"
COMPANION_COMMUNICATION_TYPE = "Event Announcement"
LINKED_SCHOOL_EVENT_NOTE_PREFIX = "[Linked School Event]"


def _doc_row_value(source, fieldname: str):
    getter = getattr(source, "get", None)
    if callable(getter):
        return getter(fieldname)
    return getattr(source, fieldname, None)


def _safe_text(value) -> str:
    return str(value or "").strip()


def _linked_school_event_note(event_name: str) -> str:
    return f"{LINKED_SCHOOL_EVENT_NOTE_PREFIX} {event_name}"


def _normalize_linked_school_event_note(current_note: str | None, event_name: str) -> str:
    note_value = _safe_text(current_note)
    legacy_note = f"Published from School Event {event_name}."
    if not note_value or note_value == legacy_note or note_value.startswith(LINKED_SCHOOL_EVENT_NOTE_PREFIX):
        return _linked_school_event_note(event_name)
    return note_value


def _resolve_school_event_organization(event_doc) -> str:
    school_name = _safe_text(_doc_row_value(event_doc, "school"))
    if not school_name:
        frappe.throw(
            _("School is required before linking an announcement to this event."),
            title=_("Missing School"),
        )

    organization = _safe_text(frappe.db.get_value("School", school_name, "organization"))
    if organization:
        return organization

    frappe.throw(
        _("School {school} is missing an organization, so the linked announcement cannot be managed.").format(
            school=school_name
        ),
        title=_("Missing Organization"),
    )


def _pick_companion_portal_surface(audiences: list[dict], *, current_surface: str | None = None) -> str:
    from ifitwala_ed.setup.doctype.org_communication.org_communication import (
        get_org_communication_allowed_portal_surfaces,
        resolve_org_communication_delivery_profile,
    )

    profile = resolve_org_communication_delivery_profile(audiences)
    allowed_surfaces = set(get_org_communication_allowed_portal_surfaces(profile))
    current_value = _safe_text(current_surface)

    if current_value and current_value in allowed_surfaces:
        return current_value
    if "Portal Feed" in allowed_surfaces and profile == "portal_only":
        return "Portal Feed"
    if "Everywhere" in allowed_surfaces:
        return "Everywhere"
    if "Portal Feed" in allowed_surfaces:
        return "Portal Feed"
    if "Desk" in allowed_surfaces:
        return "Desk"
    if "Morning Brief" in allowed_surfaces:
        return "Morning Brief"
    return "Portal Feed"


def _map_school_event_audience_row_to_org_communication_rows(*, school: str, audience_row) -> list[dict]:
    audience_type = _safe_text(_doc_row_value(audience_row, "audience_type"))
    team_name = _safe_text(_doc_row_value(audience_row, "team")) or None
    student_group_name = _safe_text(_doc_row_value(audience_row, "student_group")) or None
    include_guardians = cint(_doc_row_value(audience_row, "include_guardians"))
    include_students = cint(_doc_row_value(audience_row, "include_students"))

    if audience_type == WHOLE_SCHOOL_AUDIENCE:
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 1,
                "to_students": 1,
                "to_guardians": 1,
                "note": None,
            }
        ]

    if audience_type == "All Students":
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 0,
                "to_students": 1,
                "to_guardians": 1 if include_guardians else 0,
                "note": None,
            }
        ]

    if audience_type == "All Guardians":
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 0,
                "to_students": 1 if include_students else 0,
                "to_guardians": 1,
                "note": None,
            }
        ]

    if audience_type == "All Employees":
        return [
            {
                "target_mode": "School Scope",
                "school": school,
                "team": None,
                "student_group": None,
                "include_descendants": 1,
                "to_staff": 1,
                "to_students": 1 if include_students else 0,
                "to_guardians": 0,
                "note": None,
            }
        ]

    if audience_type == "Students in Student Group":
        if not student_group_name:
            frappe.throw(_("Student Group is required to sync the linked announcement."), frappe.ValidationError)
        return [
            {
                "target_mode": "Student Group",
                "school": None,
                "team": None,
                "student_group": student_group_name,
                "include_descendants": 0,
                "to_staff": 0,
                "to_students": 1,
                "to_guardians": 1 if include_guardians else 0,
                "note": None,
            }
        ]

    if audience_type == "Employees in Team":
        if include_students:
            frappe.throw(
                _(
                    "Linked announcements do not support 'Include Students' when the audience type is 'Employees in Team'."
                ),
                frappe.ValidationError,
            )
        if not team_name:
            frappe.throw(_("Team is required to sync the linked announcement."), frappe.ValidationError)
        return [
            {
                "target_mode": "Team",
                "school": None,
                "team": team_name,
                "student_group": None,
                "include_descendants": 0,
                "to_staff": 1,
                "to_students": 0,
                "to_guardians": 0,
                "note": None,
            }
        ]

    if audience_type == "Custom Users":
        frappe.throw(
            _(
                "Linked announcements are not supported for 'Custom Users'. Remove the linked Org Communication or use a publishable event audience."
            ),
            frappe.ValidationError,
        )

    frappe.throw(
        _("Audience type {audience_type} is not supported for linked announcements.").format(
            audience_type=audience_type
        ),
        frappe.ValidationError,
    )


def build_companion_org_communication_audiences(event_doc) -> list[dict]:
    school_name = _safe_text(_doc_row_value(event_doc, "school"))
    rows = list(_doc_row_value(event_doc, "audience") or [])
    if not rows:
        frappe.throw(_("School Event requires at least one audience row."), frappe.ValidationError)

    mapped_rows: list[dict] = []
    seen_keys: set[tuple] = set()

    for row in rows:
        for mapped_row in _map_school_event_audience_row_to_org_communication_rows(
            school=school_name,
            audience_row=row,
        ):
            dedupe_key = (
                mapped_row.get("target_mode"),
                mapped_row.get("school"),
                mapped_row.get("team"),
                mapped_row.get("student_group"),
                cint(mapped_row.get("include_descendants")),
                cint(mapped_row.get("to_staff")),
                cint(mapped_row.get("to_students")),
                cint(mapped_row.get("to_guardians")),
            )
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            mapped_rows.append(mapped_row)

    return mapped_rows


def _syncable_school_event_message(
    *, current_message: str | None, before_description: str | None, new_description: str | None
) -> str:
    current_value = current_message or ""
    if _safe_text(current_value):
        if (
            _safe_text(before_description)
            and _safe_text(current_value) == _safe_text(before_description)
            and _safe_text(new_description)
        ):
            return new_description or ""
        return current_value
    if _safe_text(new_description):
        return new_description or ""
    return current_value


def _get_linked_org_communication_name(event_doc) -> str | None:
    if _safe_text(_doc_row_value(event_doc, "reference_type")) != ORG_COMMUNICATION_REFERENCE_TYPE:
        return None
    communication_name = _safe_text(_doc_row_value(event_doc, "reference_name"))
    return communication_name or None


def _raise_linked_announcement_permission_error(*, action: str) -> None:
    frappe.throw(
        _(
            "This school event is linked to an announcement. You do not have permission to {action} that announcement. Open the linked Org Communication or ask an administrator to help."
        ).format(action=action),
        frappe.PermissionError,
    )


def publish_companion_org_communication_for_event(
    *, event_doc, request_id: str, announcement_message: str | None = None
) -> dict:
    from ifitwala_ed.api.org_communication_quick_create import create_org_communication_quick

    organization = _resolve_school_event_organization(event_doc)
    message_value = (
        announcement_message if _safe_text(announcement_message) else _doc_row_value(event_doc, "description")
    )
    if not _safe_text(message_value):
        frappe.throw(
            _("Add an announcement message or event description before publishing the linked announcement."),
            frappe.ValidationError,
        )

    audiences = build_companion_org_communication_audiences(event_doc)
    response = create_org_communication_quick(
        title=_safe_text(_doc_row_value(event_doc, "subject")) or _safe_text(_doc_row_value(event_doc, "name")),
        communication_type=COMPANION_COMMUNICATION_TYPE,
        status="Published",
        priority="Normal",
        portal_surface=_pick_companion_portal_surface(audiences),
        organization=organization,
        school=_safe_text(_doc_row_value(event_doc, "school")),
        message=message_value,
        internal_note=_linked_school_event_note(_safe_text(_doc_row_value(event_doc, "name"))),
        interaction_mode="None",
        allow_private_notes=0,
        allow_public_thread=0,
        audiences=audiences,
        client_request_id=f"{request_id}:publish",
    )

    communication_name = _safe_text(response.get("name"))
    if communication_name and _safe_text(_doc_row_value(event_doc, "name")):
        frappe.db.set_value(
            "School Event",
            _safe_text(_doc_row_value(event_doc, "name")),
            {
                "reference_type": ORG_COMMUNICATION_REFERENCE_TYPE,
                "reference_name": communication_name,
            },
            update_modified=False,
        )
        event_doc.reference_type = ORG_COMMUNICATION_REFERENCE_TYPE
        event_doc.reference_name = communication_name

    return {
        "name": communication_name,
        "title": response.get("title"),
        "status": response.get("status"),
    }


def sync_linked_org_communication_for_event(event_doc) -> str | None:
    communication_name = _get_linked_org_communication_name(event_doc)
    if not communication_name or not frappe.db.exists(ORG_COMMUNICATION_REFERENCE_TYPE, communication_name):
        return None

    communication_doc = frappe.get_doc(ORG_COMMUNICATION_REFERENCE_TYPE, communication_name)
    try:
        communication_doc.check_permission("write")
    except frappe.PermissionError:
        _raise_linked_announcement_permission_error(action="update")

    before_event = None
    if hasattr(event_doc, "get_doc_before_save") and callable(event_doc.get_doc_before_save):
        try:
            before_event = event_doc.get_doc_before_save()
        except Exception:
            before_event = None

    audiences = build_companion_org_communication_audiences(event_doc)
    communication_doc.title = _safe_text(_doc_row_value(event_doc, "subject")) or communication_doc.title
    communication_doc.communication_type = COMPANION_COMMUNICATION_TYPE
    communication_doc.organization = _resolve_school_event_organization(event_doc)
    communication_doc.school = _safe_text(_doc_row_value(event_doc, "school"))
    communication_doc.portal_surface = _pick_companion_portal_surface(
        audiences,
        current_surface=_safe_text(_doc_row_value(communication_doc, "portal_surface")),
    )
    communication_doc.interaction_mode = "None"
    communication_doc.allow_private_notes = 0
    communication_doc.allow_public_thread = 0
    communication_doc.internal_note = _normalize_linked_school_event_note(
        _doc_row_value(communication_doc, "internal_note"),
        _safe_text(_doc_row_value(event_doc, "name")),
    )
    communication_doc.message = _syncable_school_event_message(
        current_message=_doc_row_value(communication_doc, "message"),
        before_description=_doc_row_value(before_event, "description") if before_event else None,
        new_description=_doc_row_value(event_doc, "description"),
    )
    communication_doc.set("audiences", [])
    for row in audiences:
        communication_doc.append("audiences", row)
    communication_doc.save()
    return communication_doc.name


def archive_linked_org_communication_for_event(event_doc) -> str | None:
    communication_name = _get_linked_org_communication_name(event_doc)
    if not communication_name or not frappe.db.exists(ORG_COMMUNICATION_REFERENCE_TYPE, communication_name):
        return None

    communication_doc = frappe.get_doc(ORG_COMMUNICATION_REFERENCE_TYPE, communication_name)
    try:
        communication_doc.check_permission("write")
    except frappe.PermissionError:
        _raise_linked_announcement_permission_error(action="archive")
    communication_doc.internal_note = _normalize_linked_school_event_note(
        _doc_row_value(communication_doc, "internal_note"),
        _safe_text(_doc_row_value(event_doc, "name")),
    )
    if _safe_text(_doc_row_value(communication_doc, "status")) != "Archived":
        communication_doc.status = "Archived"
        communication_doc.save()
    return communication_doc.name


# ============================================================================
#  SCHOOL EVENT DOCUMENT
# ============================================================================


class SchoolEvent(Document):
    def validate(self):
        self.validate_time()
        self.validate_audience_presence()
        self.validate_audience_permissions()
        self.validate_audience_rows()
        self.validate_custom_users_require_participants()
        self.apply_event_color_from_audience()

    def after_insert(self):
        self.sync_employee_bookings()
        self.sync_location_booking()

    def on_update(self):
        self.validate_date()
        self.sync_employee_bookings()
        self.sync_location_booking()
        self.sync_linked_announcement()

    def on_cancel(self):
        delete_location_bookings_for_source(source_doctype=self.doctype, source_name=self.name)
        self.archive_linked_announcement()

    def on_trash(self):
        delete_location_bookings_for_source(source_doctype=self.doctype, source_name=self.name)
        self.archive_linked_announcement()

    def validate_date(self):
        """Non-'Other' categories must be in the future."""
        if self.event_category != "Other" and get_datetime(self.starts_on) < get_datetime(now_datetime()):
            frappe.throw(_(f"The date {self.starts_on} of the event must be in the future. Please adjust the date."))

    def validate_time(self):
        """Start must be <= end."""
        if get_datetime(self.starts_on) > get_datetime(self.ends_on):
            frappe.throw(
                _(f"Start time {self.starts_on} must be earlier than end time {self.ends_on}. Please adjust the time.")
            )

    def validate_audience_presence(self):
        """
        Every School Event must have at least one audience row.

        Exception:
        - doc.flags.allow_empty_audience = True
          for system-generated events that you want to handle differently.
        """
        if getattr(self.flags, "allow_empty_audience", False):
            return

        if not getattr(self, "audience", None) or len(self.audience) == 0:
            frappe.throw(
                _("School Event requires at least one audience row."),
                title=_("Missing Audience"),
            )

    def validate_audience_permissions(self):
        """
        Only privileged roles may use broad audience types:

        - All Students, Guardians, and Employees
        - All Students
        - All Guardians
        - All Employees

        Allowed roles:
        - Administrator (always)
        - Any role in ADMIN_AUDIENCE_ROLES

        All other users must use Student Group / Team / Custom Users audiences.
        """

        # Bypass for scripted inserts
        if getattr(self, "flags", None) and getattr(self.flags, "ignore_audience_permissions", False):
            return

        user = frappe.session.user

        # Administrator / Guest guard:
        # - Administrator → fully allowed
        # - Guest → cannot create events anyway in normal flows, but don't block here
        if user == "Administrator":
            return

        if not getattr(self, "audience", None):
            return

        user_roles = set(frappe.get_roles(user))

        # Privileged roles = any role in ADMIN_AUDIENCE_ROLES
        if user_roles.intersection(ADMIN_AUDIENCE_ROLES):
            return

        # Others cannot use broad audience types
        for row in self.audience:
            if row.audience_type in BROAD_AUDIENCE_TYPES:
                frappe.throw(
                    _(
                        "You are not permitted to use the audience type '{audience}'. "
                        "Choose a specific Student Group / Team / Custom Users, or ask an Academic Admin."
                    ).format(audience=row.audience_type),
                    title=_("Not permitted"),
                )

    def validate_audience_rows(self):
        """Ensure each audience row has the right structural fields set / empty."""
        for row in getattr(self, "audience", []) or []:
            a_type = row.audience_type

            # Students in Student Group → require student_group, no team
            if a_type == "Students in Student Group":
                if not row.student_group:
                    frappe.throw(
                        _("Audience row #{idx}: Please select a Student Group.").format(idx=row.idx),
                        title=_("Missing Student Group"),
                    )
                if row.team:
                    frappe.throw(
                        _("Audience row #{idx}: Team must be empty for 'Students in Student Group'.").format(
                            idx=row.idx
                        ),
                        title=_("Invalid Audience Row"),
                    )

            # Employees in Team → require team, no student_group
            elif a_type == "Employees in Team":
                if not row.team:
                    frappe.throw(
                        _("Audience row #{idx}: Please select a Team.").format(idx=row.idx),
                        title=_("Missing Team"),
                    )
                if row.student_group:
                    frappe.throw(
                        _("Audience row #{idx}: Student Group must be empty for 'Employees in Team'.").format(
                            idx=row.idx
                        ),
                        title=_("Invalid Audience Row"),
                    )

            # Broad types + Custom Users → no links
            elif a_type in {
                WHOLE_SCHOOL_AUDIENCE,
                "All Students",
                "All Guardians",
                "All Employees",
                "Custom Users",
            }:
                if row.student_group or row.team:
                    frappe.throw(
                        _("Audience row #{idx}: Student Group and Team must be empty for '{audience}'.").format(
                            idx=row.idx,
                            audience=a_type,
                        ),
                        title=_("Invalid Audience Row"),
                    )

            # Unknown type (in case options drift)
            else:
                frappe.throw(
                    _("Audience row #{idx}: Unsupported audience type '{audience}'.").format(
                        idx=row.idx,
                        audience=a_type,
                    ),
                    title=_("Invalid Audience Type"),
                )

    def validate_custom_users_require_participants(self):
        """
        If an audience row uses 'Custom Users', we require:
        - the participants table is not empty
        - no duplicate users
        - participants are valid User IDs
        """

        if not getattr(self, "audience", None):
            return

        has_custom = any(row.audience_type == "Custom Users" for row in self.audience)
        if not has_custom:
            return

        # Participants required
        if not getattr(self, "participants", None) or len(self.participants) == 0:
            frappe.throw(
                _("Audience type 'Custom Users' requires at least one participant."),
                title=_("Missing Participants"),
            )

        seen: set[str] = set()

        for p in self.participants:
            user = (p.participant or "").strip()

            if not user:
                frappe.throw(
                    _("Participant row #{idx}: Missing user.").format(idx=p.idx),
                    title=_("Invalid Participant"),
                )

            # Duplicate check
            if user in seen:
                frappe.throw(
                    _("Duplicate participant '{user}' in row #{idx}.").format(
                        user=user,
                        idx=p.idx,
                    ),
                    title=_("Duplicate Participant"),
                )
            seen.add(user)

            # Validate the user exists
            if not frappe.db.exists("User", user):
                frappe.throw(
                    _("Participant row #{idx}: User '{user}' does not exist.").format(idx=p.idx, user=user),
                    title=_("Invalid Participant"),
                )

    def apply_event_color_from_audience(self) -> None:
        """
        Derive event color from audience if no manual color is set.

        Precedence:
        1) If self.color is already set → keep it (respect manual choice).
        2) If there is any 'Employees in Team' audience row:
             use Team.meeting_color (first non-empty).
        3) Else, if there is any 'Students in Student Group' audience row:
             go Student Group → Course → Course.calendar_event_color.
        """

        # Respect an explicitly chosen color
        if getattr(self, "color", None):
            return

        if not getattr(self, "audience", None):
            return

        # -------------------------------------------------
        # 1) Team-based color: Employees in Team
        # -------------------------------------------------
        team_names = [row.team for row in self.audience if row.audience_type == "Employees in Team" and row.team]

        for team in team_names:
            try:
                team_color = frappe.get_cached_value("Team", team, "meeting_color")
            except Exception:
                team_color = None

            if team_color:
                self.color = team_color
                return

        # -------------------------------------------------
        # 2) Student Group-based color: via Course
        # -------------------------------------------------
        sg_names = [
            row.student_group
            for row in self.audience
            if row.audience_type == "Students in Student Group" and row.student_group
        ]

        for sg in sg_names:
            try:
                sg_doc = frappe.get_cached_doc("Student Group", sg)
            except Exception:
                continue

            # We don't assume a single hardcoded fieldname; try a few common ones.
            course_name = None
            for field in ("course", "course_name", "linked_course"):
                if field in sg_doc.as_dict() and sg_doc.get(field):
                    course_name = sg_doc.get(field)
                    break

            if not course_name:
                continue

            try:
                course_color = frappe.get_cached_value(
                    "Course",
                    course_name,
                    "calendar_event_color",
                )
            except Exception:
                course_color = None

            if course_color:
                self.color = course_color
                return

    def _get_employees_for_booking(self) -> Set[str]:
        """
        Resolve all employees that should be booked for this event, based on:

        - PARTICIPANTS child table (small, ad-hoc, Custom Users / PTC / visits).
        - AUDIENCE rows with audience_type == 'Employees in Team'.

        We deliberately do NOT expand:
        - 'All Employees' in v1 (to avoid exploding bookings).
        """

        employees: Set[str] = set()

        # A) From PARTICIPANTS (User → Employee.user_id)
        if getattr(self, "participants", None):
            user_ids = [p.participant for p in self.participants if p.participant]
            if user_ids:
                emp_list = frappe.get_all(
                    "Employee",
                    filters={"user_id": ["in", user_ids]},
                    pluck="name",
                )
                employees.update(emp_list)

        # B) From AUDIENCE → Employees in Team
        if getattr(self, "audience", None):
            team_names = [row.team for row in self.audience if row.audience_type == "Employees in Team" and row.team]

            if team_names:
                # Team Member rows already carry the canonical employee link.
                team_employees = frappe.get_all(
                    "Team Member",
                    filters={
                        "parent": ["in", team_names],
                        "parenttype": "Team",
                        "parentfield": "members",
                    },
                    pluck="employee",
                )
                if team_employees:
                    employees.update(team_employees)

        return employees

    def sync_employee_bookings(self):
        """
        v1 unified booking sync:

        - Resolve employees via:
            * participants (User → Employee)
            * audience rows (Employees in Team → Team Member → Employee)
        - Delete all existing Employee Booking rows for this event.
        - Re-insert one booking per employee, asserting availability.

        We explicitly do NOT expand 'All Employees' in v1.
        """

        from ifitwala_ed.utilities.employee_booking import (
            assert_employee_free,
            delete_employee_bookings_for_source,
            upsert_employee_booking,
        )

        # No valid time → wipe bookings and exit
        if not self.starts_on or not self.ends_on:
            delete_employee_bookings_for_source("School Event", self.name)
            return

        # 1) Resolve employees to book
        employees = self._get_employees_for_booking()

        # Nothing to book → clear and exit
        if not employees:
            delete_employee_bookings_for_source("School Event", self.name)
            return

        # 2) Reset existing bookings for this event
        delete_employee_bookings_for_source("School Event", self.name)

        # 3) Re-insert with conflict protection
        for emp in employees:
            assert_employee_free(
                employee=emp,
                start=self.starts_on,
                end=self.ends_on,
                exclude={"doctype": "School Event", "name": self.name},
                allow_double_booking=False,
            )

            upsert_employee_booking(
                employee=emp,
                start=self.starts_on,
                end=self.ends_on,
                source_doctype="School Event",
                source_name=self.name,
                booking_type="Other",  # later: derive from event_category if needed
                blocks_availability=1,
                school=self.school if getattr(self, "school", None) else None,
                academic_year=None,  # no AY field on School Event yet
                unique_by_slot=False,
            )

    def sync_location_booking(self) -> None:
        """
        Project this School Event into Location Booking (single stable slot).
        """
        if not (self.location and self.starts_on and self.ends_on):
            delete_location_bookings_for_source(source_doctype=self.doctype, source_name=self.name)
            return

        start_dt = get_datetime(self.starts_on)
        end_dt = get_datetime(self.ends_on)
        if not start_dt or not end_dt or end_dt <= start_dt:
            delete_location_bookings_for_source(source_doctype=self.doctype, source_name=self.name)
            return

        source_key = build_source_key(self.doctype, self.name)
        slot_key = build_slot_key_single(source_key, self.location)

        upsert_location_booking(
            location=self.location,
            from_datetime=start_dt,
            to_datetime=end_dt,
            occupancy_type="School Event",
            source_doctype=self.doctype,
            source_name=self.name,
            slot_key=slot_key,
            school=self.school if getattr(self, "school", None) else None,
            academic_year=None,
        )

        # Clean up any stale rows from prior locations.
        frappe.db.delete(
            "Location Booking",
            {
                "source_doctype": self.doctype,
                "source_name": self.name,
                "slot_key": ["!=", slot_key],
            },
        )

    def sync_linked_announcement(self) -> None:
        sync_linked_org_communication_for_event(self)

    def archive_linked_announcement(self) -> None:
        archive_linked_org_communication_for_event(self)


# ============================================================================
#  USER MEMBERSHIP HELPERS (STUDENT GROUPS, TEAMS, CHILDREN) + CACHING
# ============================================================================


def _get_custom_user_event_names_for_user(user: str, event_names: list[str]) -> set[str]:
    """
    Return the subset of event_names where the given user
    is explicitly listed as a participant.

    Used ONLY for the 'Custom Users' audience type.
    """
    if not event_names:
        return set()

    rows = frappe.get_all(
        "School Event Participant",
        filters={
            "participant": user,
            "parent": ["in", event_names],
        },
        pluck="parent",
    )

    return set(rows or [])


def _resolve_team_member_employee_names_for_user(user: str) -> list[str]:
    direct_names = frappe.get_all("Employee", filters={"user_id": user}, pluck="name")
    if direct_names:
        return [name for name in direct_names if name]

    login_email = (frappe.db.get_value("User", user, "email") or user or "").strip()
    if not login_email:
        return []

    fallback_rows = frappe.get_all(
        "Employee",
        filters={"employee_professional_email": login_email},
        fields=["name", "user_id"],
        limit=2,
    )
    if len(fallback_rows) != 1:
        return []

    row = fallback_rows[0]
    mapped_user = str(row.get("user_id") or "").strip()
    if mapped_user and mapped_user != user:
        return []

    employee_name = str(row.get("name") or "").strip()
    return [employee_name] if employee_name else []


@redis_cache(ttl=600)
def get_user_membership(user: str) -> Dict[str, Set[str]]:
    """
    Return a normalized, cached view of this user's membership:

    - student_groups: all Student Groups where user is a student or instructor
    - teams: all Teams where user is a Team Member
    - children_students: for Guardian users, all Student IDs of their children
    - children_student_groups: all Student Groups where any of their children are members

    This result is cached for 10 minutes per user to reduce DB load
    from frequent calendar loads.
    """

    m: Dict[str, Set[str]] = {
        "student_groups": set(),
        "teams": set(),
        "children_students": set(),
        "children_student_groups": set(),
    }

    # Student Group Student (user as student)
    try:
        stu_groups = frappe.get_all(
            "Student Group Student",
            filters={"user_id": user},
            pluck="parent",
        )
        m["student_groups"].update(stu_groups)
    except frappe.DoesNotExistError:
        pass

    # Student Group Instructor (user as instructor)
    try:
        ins_groups = frappe.get_all(
            "Student Group Instructor",
            filters={"user_id": user},
            pluck="parent",
        )
        m["student_groups"].update(ins_groups)
    except frappe.DoesNotExistError:
        pass

    # Teams (Team Member child with canonical employee + member links)
    try:
        employee_names = _resolve_team_member_employee_names_for_user(user)

        team_or_filters: dict[str, str | list[str]] = {"member": user}
        if employee_names:
            team_or_filters["employee"] = ["in", employee_names]

        teams = frappe.get_all(
            "Team Member",
            filters={
                "parenttype": "Team",
                "parentfield": "members",
            },
            or_filters=team_or_filters,
            pluck="parent",
        )
        m["teams"].update(teams)
    except frappe.DoesNotExistError:
        pass

    # Guardian side: children + their student groups
    try:
        guardian_names = frappe.get_all(
            "Guardian",
            filters={"user": user},
            pluck="name",
        )
    except frappe.DoesNotExistError:
        guardian_names = []

    if guardian_names:
        try:
            children = frappe.get_all(
                "Guardian Student",
                filters={"parent": ["in", guardian_names]},
                pluck="student",
            )
        except frappe.DoesNotExistError:
            children = []

        if children:
            child_ids = set(children)
            m["children_students"].update(child_ids)

            try:
                child_groups = frappe.get_all(
                    "Student Group Student",
                    filters={"student": ["in", list(child_ids)]},
                    pluck="parent",
                )
                m["children_student_groups"].update(child_groups)
            except frappe.DoesNotExistError:
                pass

    return m


# ============================================================================
#  AUDIENCE MATCHING (INCLUDING STUDENT–GUARDIAN PROPAGATION)
# ============================================================================


def _audience_row_matches_user(
    a_row,
    event_name: str,
    user_roles: set[str],
    membership: dict[str, set[str]],
    custom_user_events: set[str],
) -> bool:
    """
    Return True if this audience row applies to the current user.

    Handles:
    - All Students, Guardians, and Employees
    - All Students (+ optional include_guardians)
    - All Guardians (+ optional include_students)
    - All Employees (Employee role only)
    - Students in Student Group (+ optional include_guardians)
    - Employees in Team
    - Custom Users (participants-only visibility)

    Cohort / Program / Program Offering are now unused.
    """

    a_type = a_row.get("audience_type")
    if not a_type:
        return False

    include_guardians = bool(a_row.get("include_guardians"))
    include_students = bool(a_row.get("include_students"))

    is_student = "Student" in user_roles
    is_guardian = "Guardian" in user_roles

    # Broad types
    if a_type == WHOLE_SCHOOL_AUDIENCE:
        return True

    if a_type == "All Students":
        if is_student:
            return True
        if include_guardians and is_guardian and membership.get("children_students"):
            return True
        return False

    if a_type == "All Guardians":
        if is_guardian:
            return True
        if include_students and is_student:
            return True
        return False

    if a_type == "All Employees":
        return "Employee" in user_roles

    # Student Group-based audience
    if a_type == "Students in Student Group":
        sg = a_row.get("student_group")
        if not sg:
            return False

        if sg in membership.get("student_groups", set()):
            return True

        if include_guardians and is_guardian:
            if sg in membership.get("children_student_groups", set()):
                return True

        return False

    # Team-based audience
    if a_type == "Employees in Team":
        team = a_row.get("team")
        if not team:
            return False

        if team in membership.get("teams", set()):
            return True

        return False

    # Custom Users: visibility only for explicit participants
    if a_type == "Custom Users":
        # The event must have this audience row AND this user must be
        # an explicit participant in School Event Participant.
        return event_name in custom_user_events

    # Any other audience type is currently unused
    return False


# ============================================================================
#  CENTRALIZED EVENT FETCH API
# ============================================================================


def get_school_events_for_user(start, end, user=None, filters=None):
    """
    Main API used by Desk + Portal calendars.

    Event is visible to user if:
    - audience rule matches (broad types + student group / team +
      student-guardian propagation + Custom Users), OR
    - user is Administrator / System Manager / Academic Admin / Academic Assistant
      (admin override)
    """

    if not user:
        user = frappe.session.user

    site_tz = get_system_timezone() or "UTC"

    # Normalize filters
    if isinstance(filters, str):
        filters = json.loads(filters)

    filter_cond = get_filters_cond("School Event", filters, [])

    start_local = "CONVERT_TZ(`tabSchool Event`.starts_on, 'UTC', %(site_tz)s)"
    end_local = "CONVERT_TZ(`tabSchool Event`.ends_on, 'UTC', %(site_tz)s)"

    # Main time-window query
    events = frappe.db.sql(
        f"""
		SELECT `tabSchool Event`.*
		FROM `tabSchool Event`
		WHERE
			(
				({start_local} BETWEEN %(start)s AND %(end)s)
				OR ({end_local} BETWEEN %(start)s AND %(end)s)
			)
			{filter_cond}
		ORDER BY `tabSchool Event`.starts_on
		""",
        {"start": start, "end": end, "site_tz": site_tz},
        as_dict=True,
    )

    if not events:
        return []

    user_roles = set(frappe.get_roles(user))
    is_admin_like = (
        user == "Administrator"
        or "System Manager" in user_roles
        or "Academic Admin" in user_roles
        or "Academic Assistant" in user_roles
    )

    # Admin / management override: see everything in the window
    if is_admin_like:
        return events

    event_names = [e["name"] for e in events]

    # Pull audience rows in one batch
    audience_rows = frappe.get_all(
        "School Event Audience",
        filters={"parent": ["in", event_names]},
        fields=[
            "parent",
            "audience_type",
            "student_group",
            "team",
            "include_guardians",
            "include_students",
        ],
    )

    by_event = defaultdict(list)
    for row in audience_rows:
        by_event[row.parent].append(row)

    # Cached membership (student groups, teams, children, etc.)
    membership = get_user_membership(user)

    # For Custom Users audience: which of these events is the user a participant on?
    custom_user_events = _get_custom_user_event_names_for_user(user, event_names)

    allowed = []

    for ev in events:
        name = ev["name"]
        a_rows = by_event.get(name, [])

        # If there are no audience rows at all, be strict: don't show.
        if not a_rows:
            continue

        if any(
            _audience_row_matches_user(
                r,
                name,
                user_roles,
                membership,
                custom_user_events,
            )
            for r in a_rows
        ):
            allowed.append(ev)

    return allowed


# ============================================================================
#  PUBLIC WRAPPER
# ============================================================================


@frappe.whitelist()
def get_school_events(start, end, user=None, filters=None):
    return get_school_events_for_user(start=start, end=end, user=user, filters=filters)
