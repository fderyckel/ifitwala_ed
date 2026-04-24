# ifitwala_ed/api/test_portal_calendar.py

from datetime import date, datetime, time, timedelta
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.calendar import get_staff_calendar
from ifitwala_ed.api.calendar_core import _resolve_employee_for_user, _system_tzinfo
from ifitwala_ed.api.calendar_staff_feed import (
    _collect_school_events,
    _collect_staff_holiday_events,
    _collect_student_group_events_from_bookings,
)
from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window


def _insert_user_without_notifications(user):
    # User field values can shadow same-named methods on the document instance.
    with (
        patch.object(user, "send_password_notification"),
        patch.object(user, "send_welcome_mail_to_user"),
        patch("frappe.core.doctype.user.user.User.send_password_notification"),
        patch("frappe.core.doctype.user.user.User.send_welcome_mail_to_user"),
    ):
        return user.insert(ignore_permissions=True)


class TestPortalCalendar(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self.organization = self._create_organization()
        self.parent_school = self._create_school("Portal Parent", "PP", self.organization, is_group=1)
        self.child_school = self._create_school(
            "Portal Child",
            "PC",
            self.organization,
            parent=self.parent_school,
            is_group=0,
        )
        self.academic_year = self._create_academic_year(
            self.parent_school,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 8, 31),
        )
        self.holiday_date = date(2026, 1, 8)
        self.parent_calendar = self._create_school_calendar(
            self.parent_school,
            self.academic_year,
            self.holiday_date,
        )

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_resolve_school_calendars_for_window_uses_nearest_ancestor(self):
        rows = resolve_school_calendars_for_window(
            self.child_school,
            self.holiday_date,
            self.holiday_date,
        )
        self.assertTrue(rows)
        self.assertEqual(rows[0]["name"], self.parent_calendar)
        self.assertEqual(rows[0]["school"], self.parent_school)

    def test_staff_holidays_fallback_to_school_calendar_lineage(self):
        employee = self._create_employee(self.child_school)
        tzinfo = _system_tzinfo()
        window_start = tzinfo.localize(datetime.combine(self.holiday_date, time(0, 0, 0)))
        window_end = window_start + timedelta(days=1)

        events = _collect_staff_holiday_events(
            "user@example.com",
            window_start,
            window_end,
            tzinfo,
            employee_id=employee,
        )
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event.source, "staff_holiday")
        self.assertEqual(event.meta.get("fallback"), "school_calendar")
        self.assertEqual(event.meta.get("school_calendar"), self.parent_calendar)

    def test_staff_holidays_use_employee_link_when_employee_school_is_blank(self):
        employee_group = self._create_employee_group("Leadership")
        staff_calendar = self._create_staff_calendar(
            self.parent_school,
            employee_group,
            self.holiday_date,
        )
        employee = self._create_employee(None, employee_group=employee_group)
        frappe.db.set_value("Employee", employee, "current_holiday_lis", staff_calendar, update_modified=False)

        tzinfo = _system_tzinfo()
        window_start = tzinfo.localize(datetime.combine(self.holiday_date, time(0, 0, 0)))
        window_end = window_start + timedelta(days=1)

        events = _collect_staff_holiday_events(
            "user@example.com",
            window_start,
            window_end,
            tzinfo,
            employee_id=employee,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].meta.get("staff_calendar"), staff_calendar)
        self.assertEqual(events[0].meta.get("resolution"), "employee_link")

    def test_staff_holidays_do_not_fallback_to_school_calendar_when_staff_calendar_resolves(self):
        employee_group = self._create_employee_group("Leadership")
        self._create_staff_calendar(
            self.parent_school,
            employee_group,
            holiday_date=None,
        )
        employee = self._create_employee(self.child_school, employee_group=employee_group)

        tzinfo = _system_tzinfo()
        window_start = tzinfo.localize(datetime.combine(self.holiday_date, time(0, 0, 0)))
        window_end = window_start + timedelta(days=1)

        events = _collect_staff_holiday_events(
            "user@example.com",
            window_start,
            window_end,
            tzinfo,
            employee_id=employee,
        )

        self.assertEqual(events, [])

    def test_staff_calendar_requires_canonical_employee_link_when_user_id_is_missing(self):
        user = self._create_user()
        self._create_employee(self.child_school, professional_email=user.name)

        resolved = _resolve_employee_for_user(
            user.name,
            fields=["name", "school"],
            employment_status_filter=["!=", "Inactive"],
        )
        self.assertIsNone(resolved)

        frappe.set_user(user.name)
        with self.assertRaises(frappe.PermissionError):
            get_staff_calendar(
                from_datetime="2026-01-07T00:00:00",
                to_datetime="2026-01-10T00:00:00",
                sources=["staff_holiday"],
                force_refresh=True,
            )

    def test_administrator_staff_calendar_without_employee_link_returns_empty_payload(self):
        payload = get_staff_calendar(
            from_datetime="2026-01-07T00:00:00",
            to_datetime="2026-01-10T00:00:00",
            sources=["student_group", "meeting", "school_event", "staff_holiday"],
            force_refresh=True,
        )

        self.assertEqual(payload.get("timezone"), _system_tzinfo().zone)
        self.assertEqual(payload.get("events"), [])
        self.assertEqual(payload.get("counts"), {})
        self.assertEqual(payload.get("sources"), ["student_group", "meeting", "school_event", "staff_holiday"])

    def test_non_administrator_without_employee_link_is_blocked(self):
        user = self._create_user()
        frappe.set_user(user.name)

        with self.assertRaises(frappe.PermissionError):
            get_staff_calendar(
                from_datetime="2026-01-07T00:00:00",
                to_datetime="2026-01-10T00:00:00",
                sources=["student_group", "meeting", "school_event", "staff_holiday"],
                force_refresh=True,
            )

    def test_booking_backed_class_events_include_location_meta(self):
        tzinfo = _system_tzinfo()
        window_start = tzinfo.localize(datetime(2026, 1, 7, 8, 0, 0))
        window_end = tzinfo.localize(datetime(2026, 1, 7, 12, 0, 0))

        booking_row = frappe._dict(
            {
                "booking_name": "EB-0001",
                "from_datetime": window_start,
                "to_datetime": tzinfo.localize(datetime(2026, 1, 7, 9, 30, 0)),
                "location": "ROOM-101",
                "student_group": "SG-ALG-1",
                "student_group_name": "Algebra A",
                "course": "COURSE-ALG",
                "program": None,
                "program_offering": None,
                "school": self.child_school,
                "school_schedule": None,
                "academic_year": self.academic_year,
                "status": "Active",
            }
        )

        with (
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.db.table_exists", return_value=True),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.db.sql", return_value=[booking_row]),
            patch("ifitwala_ed.api.calendar_staff_feed._course_meta_map", return_value={}),
        ):
            events = _collect_student_group_events_from_bookings(
                "EMP-0001",
                window_start,
                window_end,
                tzinfo,
            )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].meta.get("location"), "ROOM-101")

    def test_staff_calendar_school_events_ignore_guardian_only_audiences(self):
        tzinfo = _system_tzinfo()
        window_start = tzinfo.localize(datetime(2026, 1, 7, 8, 0, 0))
        window_end = tzinfo.localize(datetime(2026, 1, 7, 12, 0, 0))

        event_row = frappe._dict(
            {
                "name": "SE-0001",
                "subject": "Parent Workshop",
                "starts_on": window_start,
                "ends_on": tzinfo.localize(datetime(2026, 1, 7, 9, 0, 0)),
                "all_day": 0,
                "location": "Hall",
                "color": "#e64040",
                "school": self.parent_school,
                "reference_type": None,
                "reference_name": None,
                "participant_name": None,
            }
        )

        def fake_get_all(doctype, filters=None, fields=None, limit=None):
            if doctype == "School Event Audience":
                return [
                    {
                        "parent": "SE-0001",
                        "audience_type": "All Guardians",
                        "team": None,
                    }
                ]
            self.fail(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch(
                "ifitwala_ed.api.calendar_staff_feed._resolve_employee_for_user",
                return_value={"name": "EMP-0001", "school": self.child_school},
            ),
            patch(
                "ifitwala_ed.api.calendar_staff_feed.get_ancestor_schools",
                return_value=[self.child_school, self.parent_school],
            ),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.db.sql", return_value=[event_row]),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.get_roles", return_value=["Employee"]),
            patch("ifitwala_ed.api.calendar_staff_feed.get_user_membership", return_value={"teams": set()}),
        ):
            events = _collect_school_events("staff@example.com", window_start, window_end, tzinfo)

        self.assertEqual(events, [])

    def test_staff_calendar_school_events_keep_employee_audiences_with_ancestor_school_scope(self):
        tzinfo = _system_tzinfo()
        window_start = tzinfo.localize(datetime(2026, 1, 7, 8, 0, 0))
        window_end = tzinfo.localize(datetime(2026, 1, 7, 12, 0, 0))

        event_row = frappe._dict(
            {
                "name": "SE-0002",
                "subject": "Staff Briefing",
                "starts_on": window_start,
                "ends_on": tzinfo.localize(datetime(2026, 1, 7, 9, 0, 0)),
                "all_day": 0,
                "location": "Hall",
                "color": "#2563eb",
                "school": self.parent_school,
                "reference_type": None,
                "reference_name": None,
                "participant_name": None,
            }
        )

        def fake_get_all(doctype, filters=None, fields=None, limit=None):
            if doctype == "School Event Audience":
                return [
                    {
                        "parent": "SE-0002",
                        "audience_type": "All Employees",
                        "team": None,
                    }
                ]
            self.fail(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch(
                "ifitwala_ed.api.calendar_staff_feed._resolve_employee_for_user",
                return_value={"name": "EMP-0001", "school": self.child_school},
            ),
            patch(
                "ifitwala_ed.api.calendar_staff_feed.get_ancestor_schools",
                return_value=[self.child_school, self.parent_school],
            ),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.db.sql", return_value=[event_row]),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.get_roles", return_value=["Employee"]),
            patch("ifitwala_ed.api.calendar_staff_feed.get_user_membership", return_value={"teams": set()}),
        ):
            events = _collect_school_events("staff@example.com", window_start, window_end, tzinfo)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, "school_event::SE-0002")

    def test_staff_calendar_school_events_include_team_audience_via_employee_membership(self):
        user = self._create_user()
        employee = self._create_employee(self.child_school, professional_email=user.name)
        team = self._create_team(
            self.child_school,
            members=[
                {
                    "employee": employee,
                }
            ],
        )

        tzinfo = _system_tzinfo()
        window_start = tzinfo.localize(datetime(2026, 1, 7, 8, 0, 0))
        window_end = tzinfo.localize(datetime(2026, 1, 7, 12, 0, 0))

        event_row = frappe._dict(
            {
                "name": "SE-TEAM-1",
                "subject": "Team Briefing",
                "starts_on": window_start,
                "ends_on": tzinfo.localize(datetime(2026, 1, 7, 9, 0, 0)),
                "all_day": 0,
                "location": "Staff Room",
                "color": "#0f766e",
                "school": self.parent_school,
                "reference_type": None,
                "reference_name": None,
                "participant_name": None,
            }
        )

        original_get_all = frappe.get_all

        def fake_get_all(doctype, *args, **kwargs):
            if doctype == "School Event Audience":
                return [
                    {
                        "parent": "SE-TEAM-1",
                        "audience_type": "Employees in Team",
                        "team": team,
                    }
                ]

            return original_get_all(doctype, *args, **kwargs)

        with (
            patch(
                "ifitwala_ed.api.calendar_staff_feed._resolve_employee_for_user",
                return_value={"name": employee, "school": self.child_school},
            ),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.db.sql", return_value=[event_row]),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.api.calendar_staff_feed.frappe.get_roles", return_value=["Employee"]),
            patch(
                "ifitwala_ed.api.calendar_staff_feed.get_ancestor_schools",
                return_value=[self.child_school, self.parent_school],
            ),
            patch("ifitwala_ed.api.calendar_staff_feed.get_user_membership", return_value={"teams": {team}}),
        ):
            events = _collect_school_events(user.name, window_start, window_end, tzinfo)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, "school_event::SE-TEAM-1")

    def _create_organization(self) -> str:
        hash_key = frappe.generate_hash(length=6).upper()
        doc = frappe.get_doc(
            {
                "doctype": "Organization",
                "organization_name": f"Portal Org {hash_key}",
                "abbr": f"PO{hash_key[:4]}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Organization", doc.name))
        return doc.name

    def _create_school(
        self,
        school_name: str,
        abbr_prefix: str,
        organization: str,
        *,
        parent: str | None = None,
        is_group: int = 0,
    ) -> str:
        hash_key = frappe.generate_hash(length=4).upper()
        abbr = f"{abbr_prefix[:1]}{hash_key}"
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{school_name} {hash_key}",
                "abbr": abbr,
                "organization": organization,
                "is_group": 1 if is_group else 0,
                "parent_school": parent,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School", doc.name))
        return doc.name

    def _create_academic_year(self, school: str, start_date: date, end_date: date) -> str:
        hash_key = frappe.generate_hash(length=5).upper()
        doc = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": f"Portal AY {hash_key}",
                "school": school,
                "year_start_date": start_date,
                "year_end_date": end_date,
                "archived": 0,
                "visible_to_admission": 1,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Academic Year", doc.name))
        return doc.name

    def _create_user(self):
        hash_key = frappe.generate_hash(length=6).lower()
        doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"portal-calendar-{hash_key}@example.com",
                "first_name": "Portal",
                "last_name": "Calendar",
                "enabled": 1,
                "send_welcome_email": 0,
            }
        )
        doc.flags.no_welcome_mail = True
        doc = _insert_user_without_notifications(doc)
        self._created.append(("User", doc.name))
        return doc

    def _create_team(
        self,
        school: str | None,
        *,
        members: list[dict] | None = None,
        is_group: int = 1,
    ) -> str:
        hash_key = frappe.generate_hash(length=6).upper()
        payload = {
            "doctype": "Team",
            "team_name": f"Portal Team {hash_key}",
            "organization": self.organization,
            "is_group": 1 if is_group else 0,
            "members": members or [],
        }
        if school:
            payload["school"] = school

        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self._created.append(("Team", doc.name))
        return doc.name

    def _create_employee_group(self, group_name: str) -> str:
        hash_key = frappe.generate_hash(length=5).upper()
        doc = frappe.get_doc(
            {
                "doctype": "Employee Group",
                "employee_group_name": f"{group_name} {hash_key}",
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee Group", doc.name))
        return doc.name

    def _create_staff_calendar(self, school: str, employee_group: str, holiday_date: date | None) -> str:
        holidays = []
        if holiday_date:
            holidays.append(
                {
                    "holiday_date": holiday_date,
                    "description": "Staff Calendar Holiday",
                    "weekly_off": 0,
                }
            )

        doc = frappe.get_doc(
            {
                "doctype": "Staff Calendar",
                "staff_calendar_name": f"Portal Staff Calendar {frappe.generate_hash(length=6).upper()}",
                "school": school,
                "employee_group": employee_group,
                "from_date": date(2025, 9, 1),
                "to_date": date(2026, 8, 31),
                "holidays": holidays,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Staff Calendar", doc.name))
        return doc.name

    def _create_school_calendar(self, school: str, academic_year: str, holiday_date: date) -> str:
        doc = frappe.get_doc(
            {
                "doctype": "School Calendar",
                "school": school,
                "academic_year": academic_year,
                "holidays": [
                    {
                        "holiday_date": holiday_date,
                        "description": "Portal Holiday",
                        "weekly_off": 0,
                    }
                ],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("School Calendar", doc.name))
        return doc.name

    def _create_employee(
        self,
        school: str | None,
        *,
        professional_email: str | None = None,
        employee_group: str | None = None,
    ) -> str:
        hash_key = frappe.generate_hash(length=6).upper()
        email = professional_email or f"portal-staff-{hash_key.lower()}@example.com"
        payload = {
            "doctype": "Employee",
            "employee_first_name": "Portal",
            "employee_last_name": f"Staff {hash_key}",
            "employee_gender": "Prefer not to say",
            "employee_professional_email": email,
            "organization": self.organization,
            "date_of_joining": frappe.utils.nowdate(),
            "employment_status": "Active",
        }
        if school:
            payload["school"] = school
        if employee_group:
            payload["employee_group"] = employee_group

        doc = frappe.get_doc(payload).insert(ignore_permissions=True)
        self._created.append(("Employee", doc.name))
        return doc.name
