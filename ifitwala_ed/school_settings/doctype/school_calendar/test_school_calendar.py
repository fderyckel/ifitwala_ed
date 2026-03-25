# Copyright (c) 2024, fdR and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestSchoolCalendar(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_holidays_are_sorted_by_date_ascending_on_save(self):
        organization = make_organization(prefix="Calendar Org")
        school = make_school(organization.name, prefix="Calendar School")

        with patch(
            "ifitwala_ed.school_settings.doctype.academic_year.academic_year.AcademicYear.create_calendar_events"
        ):
            academic_year = frappe.get_doc(
                {
                    "doctype": "Academic Year",
                    "academic_year_name": f"AY {frappe.generate_hash(length=6)}",
                    "school": school.name,
                    "year_start_date": "2025-08-01",
                    "year_end_date": "2026-06-30",
                    "archived": 0,
                    "visible_to_admission": 1,
                }
            ).insert(ignore_permissions=True)

        with patch(
            "ifitwala_ed.school_settings.doctype.school_calendar.school_calendar.resolve_terms_for_school_calendar",
            return_value=[],
        ):
            calendar = frappe.get_doc(
                {
                    "doctype": "School Calendar",
                    "calendar_name": f"Calendar {frappe.generate_hash(length=6)}",
                    "school": school.name,
                    "academic_year": academic_year.name,
                    "holidays": [
                        {
                            "holiday_date": "2025-10-14",
                            "description": "Mid Term Break",
                        },
                        {
                            "holiday_date": "2025-08-12",
                            "description": "Opening Ceremony",
                        },
                        {
                            "holiday_date": "2025-09-01",
                            "description": "National Day",
                        },
                    ],
                }
            ).insert(ignore_permissions=True)

        calendar.reload()

        self.assertEqual(
            [str(row.holiday_date) for row in calendar.holidays],
            ["2025-08-12", "2025-09-01", "2025-10-14"],
        )
        self.assertEqual([row.idx for row in calendar.holidays], [1, 2, 3])
