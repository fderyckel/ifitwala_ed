# Copyright (c) 2025, François de Ryckel and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestSchoolSchedule(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_missing_rotation_days_shows_actionable_validation_message(self):
        organization = make_organization(prefix="Schedule Org")
        school = make_school(organization.name, prefix="Schedule School")

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
                    "holidays": [],
                }
            ).insert(ignore_permissions=True)

        schedule = frappe.get_doc(
            {
                "doctype": "School Schedule",
                "schedule_name": f"Schedule {frappe.generate_hash(length=6)}",
                "school_calendar": calendar.name,
                "school": school.name,
                "first_day_rotation_day": 1,
                "include_holidays_in_rotation": 0,
            }
        )

        with self.assertRaisesRegex(
            frappe.ValidationError,
            "Please set Number of Rotation days to a value greater than 0 before saving this schedule.",
        ):
            schedule.insert(ignore_permissions=True)
