from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website.providers import academic_calendar as provider


class TestAcademicCalendarProvider(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        provider.invalidate_academic_calendar_cache()

    def tearDown(self):
        provider.invalidate_academic_calendar_cache()

    def test_academic_calendar_returns_upcoming_holidays_for_selected_school_calendar(self):
        organization = make_organization(prefix="Calendar Org")
        school = make_school(organization.name, prefix="Calendar School")
        academic_year = frappe.get_doc(
            {
                "doctype": "Academic Year",
                "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
                "school": school.name,
                "year_start_date": "2026-01-01",
                "year_end_date": "2026-12-31",
                "archived": 0,
                "visible_to_admission": 1,
            }
        ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "School Calendar",
                "academic_year": academic_year.name,
                "school": school.name,
                "holidays": [
                    {
                        "holiday_date": "2026-10-12",
                        "description": "Midterm Break",
                    }
                ],
            }
        ).insert(ignore_permissions=True)

        payload = provider.get_context(
            school=frappe.get_doc("School", school.name),
            page=frappe._dict(),
            block_props={"include_terms": False, "include_holidays": True, "limit": 6},
        )

        self.assertTrue(payload["data"]["has_items"])
        self.assertEqual(payload["data"]["calendar_label"], academic_year.academic_year_name)
        self.assertEqual(payload["data"]["items"][0]["kind"], "holiday")
        self.assertEqual(payload["data"]["items"][0]["title"], "Midterm Break")
