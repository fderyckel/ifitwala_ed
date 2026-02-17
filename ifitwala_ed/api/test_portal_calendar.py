# ifitwala_ed/api/test_portal_calendar.py

from datetime import date, datetime, time, timedelta

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api.calendar import _collect_staff_holiday_events, _system_tzinfo
from ifitwala_ed.school_settings.school_settings_utils import resolve_school_calendars_for_window


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
        doc = frappe.get_doc(
            {
                "doctype": "School",
                "school_name": f"{school_name} {hash_key}",
                "abbr": f"{abbr_prefix}{hash_key}",
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

    def _create_employee(self, school: str) -> str:
        hash_key = frappe.generate_hash(length=6).upper()
        doc = frappe.get_doc(
            {
                "doctype": "Employee",
                "first_name": "Portal",
                "last_name": f"Staff {hash_key}",
                "employment_status": "Active",
                "school": school,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Employee", doc.name))
        return doc.name
