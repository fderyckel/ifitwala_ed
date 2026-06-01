# ifitwala_ed/schedule/api/test_calendar_quick_create.py

from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.schedule.api.calendar import quick_create as calendar_quick_create
from ifitwala_ed.schedule.api.calendar.quick_create import create_meeting_quick, create_school_event_quick


class _DummyLock:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyCache:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get_value(self, key):
        return self.store.get(key)

    def set_value(self, key, value, expires_in_sec=None):
        self.store[key] = value

    def lock(self, key, timeout=15):
        return _DummyLock()


class _FakeDoc:
    def __init__(self, payload: dict, name: str):
        self.name = name
        for key, value in payload.items():
            setattr(self, key, value)

        if payload.get("meeting_name"):
            self.meeting_name = payload.get("meeting_name")
            self.from_datetime = f"{payload.get('date')} {payload.get('start_time')}:00"
            self.to_datetime = f"{payload.get('date')} {payload.get('end_time')}:00"

        if payload.get("subject"):
            self.subject = payload.get("subject")
            self.starts_on = payload.get("starts_on")
            self.ends_on = payload.get("ends_on")

    def insert(self):
        return self

    def get(self, key, default=None):
        return getattr(self, key, default)


class TestCalendarQuickCreate(TestCase):
    def test_create_meeting_quick_is_idempotent(self):
        cache = _DummyCache()
        captured_payloads = []
        user_rows = {
            "staff@example.com": frappe._dict({"name": "staff@example.com", "full_name": "Staff Example"}),
            "student@example.com": frappe._dict({"name": "student@example.com", "full_name": "Student Example"}),
        }

        def _fake_get_doc(*args, **kwargs):
            if len(args) == 1 and isinstance(args[0], dict):
                payload = args[0]
                captured_payloads.append(payload)
                return _FakeDoc(payload, "MTG-TEST-0001")
            if args == ("System Settings", "System Settings"):
                return frappe._dict({"time_zone": "Asia/Bangkok"})
            raise AssertionError(f"Unexpected get_doc call: args={args!r} kwargs={kwargs!r}")

        def _fake_get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype == "Employee":
                return []
            if doctype == "Student":
                requested = (filters or {}).get("student_email", [None, []])[1] or []
                return [
                    frappe._dict(
                        {
                            "name": "STU-1",
                            "student_email": name,
                            "student_full_name": user_rows[name]["full_name"],
                            "student_preferred_name": None,
                            "anchor_school": "SCHOOL-1",
                        }
                    )
                    for name in requested
                    if name == "student@example.com"
                ]
            if doctype == "Guardian":
                return []
            if doctype == "Student Group Student":
                return []
            if doctype == "User":
                requested = (filters or {}).get("name", [None, []])[1] or []
                return [user_rows[name] for name in requested if name in user_rows]
            raise AssertionError(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.cache", return_value=cache),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.get_doc", side_effect=_fake_get_doc),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.get_all", side_effect=_fake_get_all),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_location", return_value=None
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_school",
                return_value="SCHOOL-1",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._get_quick_create_scope",
                return_value={
                    "base_school": "SCHOOL-1",
                    "school_scope": ["SCHOOL-1"],
                    "student_scope": ["SCHOOL-1"],
                    "is_admin_like": False,
                },
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings._assert_students_available_for_meeting"),
        ):
            first = create_meeting_quick(
                client_request_id="req-1",
                meeting_name="Weekly Check-in",
                date="2026-02-01",
                start_time="09:00",
                end_time="10:00",
                school="SCHOOL-1",
                participants=[{"user": "student@example.com", "kind": "student", "label": "Student Example"}],
                include_students=1,
            )
            second = create_meeting_quick(
                client_request_id="req-1",
                meeting_name="Weekly Check-in",
                date="2026-02-01",
                start_time="09:00",
                end_time="10:00",
                school="SCHOOL-1",
                participants=[{"user": "student@example.com", "kind": "student", "label": "Student Example"}],
                include_students=1,
            )

        self.assertEqual(first.get("status"), "created")
        self.assertEqual(second.get("status"), "already_processed")
        self.assertEqual(second.get("idempotent"), True)
        self.assertEqual(len(captured_payloads), 1)
        self.assertEqual(captured_payloads[0].get("school"), "SCHOOL-1")
        self.assertEqual(captured_payloads[0].get("visibility_scope"), "Participants Only")
        self.assertEqual(
            captured_payloads[0].get("participants"),
            [
                {"participant": "student@example.com", "participant_name": "Student Example"},
                {"participant": "staff@example.com", "participant_name": "Staff Example"},
            ],
        )

    def test_create_meeting_quick_rejects_student_without_scope_opt_in(self):
        cache = _DummyCache()

        def _fake_get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype == "Employee":
                return []
            if doctype == "Student":
                requested = (filters or {}).get("student_email", [None, []])[1] or []
                return [
                    frappe._dict(
                        {
                            "name": "STU-1",
                            "student_email": "student@example.com",
                            "student_full_name": "Student Example",
                            "student_preferred_name": None,
                            "anchor_school": "SCHOOL-1",
                        }
                    )
                    for name in requested
                    if name == "student@example.com"
                ]
            if doctype == "Guardian":
                return []
            if doctype == "Student Group Student":
                return []
            if doctype == "User":
                requested = (filters or {}).get("name", [None, []])[1] or []
                return [
                    frappe._dict({"name": name, "full_name": "Student Example"})
                    for name in requested
                    if name == "student@example.com"
                ]
            raise AssertionError(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.cache", return_value=cache),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.get_all", side_effect=_fake_get_all),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.get_doc") as mocked_get_doc,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_location", return_value=None
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_school",
                return_value="SCHOOL-1",
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_team", return_value=None),
        ):
            with self.assertRaises(frappe.ValidationError) as exc:
                create_meeting_quick(
                    client_request_id="req-student-guard",
                    meeting_name="Private Staff Meeting",
                    date="2026-02-01",
                    start_time="09:00",
                    end_time="10:00",
                    school="SCHOOL-1",
                    participants=[{"user": "student@example.com"}],
                )

        self.assertIn("Enable Students", str(exc.exception))
        mocked_get_doc.assert_not_called()

    def test_create_meeting_quick_rejects_guardian_without_scope_opt_in(self):
        cache = _DummyCache()

        def _fake_get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype == "Employee":
                return []
            if doctype == "Student":
                return []
            if doctype == "Guardian":
                requested = (filters or {}).get("user", [None, []])[1] or []
                return [
                    frappe._dict(
                        {
                            "name": "GUARD-1",
                            "user": "guardian@example.com",
                            "guardian_full_name": "Guardian Example",
                        }
                    )
                    for name in requested
                    if name == "guardian@example.com"
                ]
            if doctype == "Guardian Student":
                return []
            if doctype == "User":
                requested = (filters or {}).get("name", [None, []])[1] or []
                return [
                    frappe._dict({"name": name, "full_name": "Guardian Example"})
                    for name in requested
                    if name == "guardian@example.com"
                ]
            raise AssertionError(f"Unexpected get_all call: doctype={doctype!r}")

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.cache", return_value=cache),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.get_all", side_effect=_fake_get_all),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.get_doc") as mocked_get_doc,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_location", return_value=None
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_school",
                return_value="SCHOOL-1",
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_team", return_value=None),
        ):
            with self.assertRaises(frappe.ValidationError) as exc:
                create_meeting_quick(
                    client_request_id="req-guardian-guard",
                    meeting_name="Private Staff Meeting",
                    date="2026-02-01",
                    start_time="09:00",
                    end_time="10:00",
                    school="SCHOOL-1",
                    participants=[{"user": "guardian@example.com"}],
                )

        self.assertIn("Enable Guardians", str(exc.exception))
        mocked_get_doc.assert_not_called()

    def test_create_meeting_quick_checks_student_availability_before_insert(self):
        cache = _DummyCache()

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.cache", return_value=cache),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.meetings.frappe.get_doc") as mocked_get_doc,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_location", return_value=None
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._ensure_allowed_school",
                return_value="SCHOOL-1",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._get_quick_create_scope",
                return_value={
                    "base_school": "SCHOOL-1",
                    "school_scope": ["SCHOOL-1"],
                    "student_scope": ["SCHOOL-1"],
                    "is_admin_like": False,
                },
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.meetings._assert_students_available_for_meeting",
                side_effect=frappe.ValidationError("Student busy"),
            ) as mocked_student_check,
        ):
            with self.assertRaises(frappe.ValidationError):
                create_meeting_quick(
                    client_request_id="req-busy-student",
                    meeting_name="Weekly Check-in",
                    date="2026-02-01",
                    start_time="09:00",
                    end_time="10:00",
                    school="SCHOOL-1",
                    participants=[{"user": "student@example.com", "kind": "student", "label": "Student Example"}],
                    include_students=1,
                )

        mocked_student_check.assert_called_once()
        mocked_get_doc.assert_not_called()

    def test_create_school_event_quick_defaults_custom_users_to_session_user(self):
        cache = _DummyCache()
        captured_payloads = []

        def _fake_get_doc(*args, **kwargs):
            if len(args) == 1 and isinstance(args[0], dict):
                payload = args[0]
                captured_payloads.append(payload)
                return _FakeDoc(payload, "SEVENT-2026-000001")
            if args == ("System Settings", "System Settings"):
                return frappe._dict({"time_zone": "Asia/Bangkok"})
            raise AssertionError(f"Unexpected get_doc call: args={args!r} kwargs={kwargs!r}")

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.has_permission", return_value=True
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.get_doc", side_effect=_fake_get_doc
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events._ensure_allowed_school",
                return_value="SCHOOL-1",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events._ensure_allowed_location",
                return_value=None,
            ),
        ):
            response = create_school_event_quick(
                client_request_id="req-custom-1",
                subject="Parent Coffee Morning",
                school="SCHOOL-1",
                starts_on="2026-02-01T09:00",
                ends_on="2026-02-01T10:00",
                audience_type="Custom Users",
                event_category="Other",
            )

        self.assertEqual(response.get("status"), "created")
        self.assertEqual(len(captured_payloads), 1)
        self.assertEqual(captured_payloads[0].get("participants"), [{"participant": "staff@example.com"}])

    def test_get_event_quick_create_options_includes_announcement_publish_capability(self):
        cache = _DummyCache()

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options.frappe.has_permission",
                side_effect=lambda doctype, ptype=None, user=None: doctype == "School Event",
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.options.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options._get_quick_create_scope",
                return_value={
                    "roles": ["Academic Assistant"],
                    "base_school": "ISS",
                    "school_scope": ["ISS", "IHS", "IMS"],
                    "is_admin_like": False,
                },
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options._cached_select_options",
                side_effect=lambda doctype, fieldname: {
                    ("Meeting", "meeting_category"): ["General"],
                    ("School Event", "event_category"): ["Other"],
                    ("School Event Audience", "audience_type"): ["All Guardians", "Students in Student Group"],
                }[(doctype, fieldname)],
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options._school_options_for_scope",
                return_value=[
                    {"value": "ISS", "label": "Ifitwala Secondary School"},
                    {"value": "IHS", "label": "Ifitwala High School"},
                ],
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options._location_options_map_for_schools",
                return_value={"ISS": []},
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options._location_type_options_map_for_schools",
                return_value={"ISS": []},
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.options._team_options_for_scope", return_value=[]),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options._student_group_options_for_scope",
                return_value=[],
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options.get_org_communication_quick_create_capability",
                return_value={
                    "enabled": False,
                    "blocked_reason": "Set a default organization before publishing announcements.",
                },
            ),
        ):
            payload = calendar_quick_create.get_event_quick_create_options()

        self.assertEqual(
            payload["announcement_publish"],
            {
                "enabled": False,
                "blocked_reason": "Set a default organization before publishing announcements.",
            },
        )

    def test_team_options_include_school_and_organization_scoped_teams(self):
        def fake_get_all(doctype, filters=None, fields=None, order_by=None, limit=None, **kwargs):
            self.assertEqual(doctype, "Team")
            if filters.get("school"):
                return [
                    frappe._dict(
                        name="TEAM-SCHOOL",
                        team_name="School Team",
                        school="ISS",
                        organization="ORG-1",
                    )
                ]
            if filters.get("organization"):
                return [
                    frappe._dict(
                        name="TEAM-ORG",
                        team_name="Organization Team",
                        school="",
                        organization="ORG-1",
                    ),
                    frappe._dict(
                        name="TEAM-SIBLING",
                        team_name="Sibling Team",
                        school="SIBLING",
                        organization="ORG-1",
                    ),
                ]
            raise AssertionError(f"Unexpected filters: {filters!r}")

        with patch("ifitwala_ed.schedule.api.calendar.quick_create.options.frappe.get_all", side_effect=fake_get_all):
            options = calendar_quick_create._team_options_for_scope(
                "staff@example.com",
                ["ISS"],
                False,
                ["ORG-1"],
            )

        self.assertEqual(
            options,
            [
                {"value": "TEAM-ORG", "label": "Organization Team"},
                {"value": "TEAM-SCHOOL", "label": "School Team"},
            ],
        )

    def test_employee_attendee_search_uses_descendant_organization_scope(self):
        observed_params = []

        def fake_sql(sql, params=None, as_dict=False, **kwargs):
            self.assertIn("e.organization IN %(organizations)s", sql)
            observed_params.append(dict(params or {}))
            return [
                frappe._dict(
                    {
                        "user_id": "interviewer@example.com",
                        "label": "Interview Reviewer",
                        "school": "Child School",
                    }
                )
            ]

        with patch("ifitwala_ed.schedule.api.calendar.quick_create.attendees.frappe.db.sql", side_effect=fake_sql):
            results = calendar_quick_create._search_employee_attendees(
                user="admission@example.com",
                organization_scope=["Parent Org", "Child Org"],
                query="inter",
                limit=8,
            )

        self.assertEqual(observed_params[0]["organizations"], ("Parent Org", "Child Org"))
        self.assertEqual(
            results,
            [
                {
                    "value": "interviewer@example.com",
                    "label": "Interview Reviewer",
                    "meta": "Child School",
                    "kind": "employee",
                    "availability_mode": "authoritative",
                }
            ],
        )

    def test_employee_collaboration_scope_expands_to_real_parent_organization(self):
        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.scope.get_ancestor_organizations",
                return_value=["IHS Organization", "Ifitwala Organization", "All Organizations"],
            ) as mocked_ancestors,
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.scope.get_descendant_organizations",
                return_value=["Ifitwala Organization", "IHS Organization", "IMS Organization"],
            ) as mocked_descendants,
        ):
            scope = calendar_quick_create._employee_collaboration_organization_scope("IHS Organization")

        mocked_ancestors.assert_called_once_with("IHS Organization")
        mocked_descendants.assert_called_once_with("Ifitwala Organization")
        self.assertEqual(scope, ["Ifitwala Organization", "IHS Organization", "IMS Organization"])

    def test_search_meeting_attendees_passes_collaboration_scope_to_employee_search(self):
        cache = _DummyCache()

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.attendees.frappe.session",
                frappe._dict({"user": "admission@example.com"}),
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.attendees.frappe.has_permission", return_value=True),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.attendees.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.attendees._get_quick_create_scope",
                return_value={
                    "organization": "Parent Org",
                    "organization_scope": ["Parent Org", "Child Org"],
                    "employee_collaboration_organization_scope": [
                        "Parent Org",
                        "Child Org",
                        "Sibling School Org",
                    ],
                    "student_scope": ["School A"],
                },
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.attendees._search_employee_attendees",
                return_value=[
                    {
                        "value": "interviewer@example.com",
                        "label": "Interview Reviewer",
                        "meta": "Child School",
                        "kind": "employee",
                        "availability_mode": "authoritative",
                    }
                ],
            ) as mocked_search,
        ):
            payload = calendar_quick_create.search_meeting_attendees(
                query="inter",
                attendee_kinds=["employee"],
                limit=8,
            )

        mocked_search.assert_called_once_with(
            user="admission@example.com",
            organization_scope=["Parent Org", "Child Org", "Sibling School Org"],
            query="inter",
            limit=8,
        )
        self.assertEqual(payload["results"][0]["value"], "interviewer@example.com")

    def test_team_options_membership_fallback_uses_employee_link_when_member_is_blank(self):
        def fake_get_all(doctype, filters=None, fields=None, or_filters=None, pluck=None, **kwargs):
            if doctype == "Team Member":
                self.assertEqual(filters, {"parenttype": "Team"})
                self.assertEqual(or_filters, {"member": "staff@example.com", "employee": "EMP-0001"})
                self.assertEqual(pluck, "parent")
                return ["TEAM-EMPLOYEE"]
            if doctype == "Team":
                self.assertEqual(filters, {"name": ["in", ["TEAM-EMPLOYEE"]]})
                return [
                    frappe._dict(
                        name="TEAM-EMPLOYEE",
                        team_name="Employee Team",
                        school="",
                        organization="ORG-1",
                    )
                ]
            raise AssertionError(f"Unexpected doctype: {doctype}")

        with (
            patch("ifitwala_ed.schedule.api.calendar.quick_create.options.frappe.get_all", side_effect=fake_get_all),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.options._resolve_employee_for_user",
                return_value={"name": "EMP-0001"},
            ),
        ):
            options = calendar_quick_create._team_options_for_scope(
                "staff@example.com",
                [],
                False,
                [],
            )

        self.assertEqual(options, [{"value": "TEAM-EMPLOYEE", "label": "Employee Team"}])

    def test_create_school_event_quick_can_publish_matching_org_communication(self):
        cache = _DummyCache()
        captured_event_payloads = []

        def _fake_get_doc(*args, **kwargs):
            if len(args) == 1 and isinstance(args[0], dict):
                payload = args[0]
                captured_event_payloads.append(payload)
                return _FakeDoc(payload, "SE-26-04-00001")
            if args == ("System Settings", "System Settings"):
                return frappe._dict({"time_zone": "Asia/Bangkok"})
            raise AssertionError(f"Unexpected get_doc call: args={args!r} kwargs={kwargs!r}")

        with (
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.session",
                frappe._dict({"user": "staff@example.com"}),
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.has_permission", return_value=True
            ),
            patch("ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.cache", return_value=cache),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.frappe.get_doc", side_effect=_fake_get_doc
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events._ensure_allowed_school",
                return_value="ISS",
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events._ensure_allowed_location",
                return_value=None,
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.get_org_communication_quick_create_capability",
                return_value={"enabled": True, "blocked_reason": None},
            ),
            patch(
                "ifitwala_ed.schedule.api.calendar.quick_create.school_events.publish_companion_org_communication_for_event",
                return_value={
                    "status": "created",
                    "name": "ORG-COMM-26-04-00001",
                    "title": "Parent MYP Workshop",
                },
            ) as mocked_publish,
        ):
            response = create_school_event_quick(
                client_request_id="req-publish-1",
                subject="Parent MYP Workshop",
                school="ISS",
                starts_on="2026-04-22T08:00",
                ends_on="2026-04-22T09:00",
                audience_type="All Guardians",
                event_category="Parent Engagement",
                publish_announcement=1,
                announcement_message="Workshop presentation",
            )

        self.assertEqual(response.get("status"), "created")
        self.assertEqual(response.get("published_communication", {}).get("name"), "ORG-COMM-26-04-00001")
        self.assertEqual(len(captured_event_payloads), 1)
        self.assertEqual(captured_event_payloads[0].get("school"), "ISS")
        mocked_publish.assert_called_once()
        self.assertEqual(mocked_publish.call_args.kwargs["event_doc"].name, "SE-26-04-00001")
        self.assertEqual(mocked_publish.call_args.kwargs["request_id"], "req-publish-1")
        self.assertEqual(mocked_publish.call_args.kwargs["announcement_message"], "Workshop presentation")
