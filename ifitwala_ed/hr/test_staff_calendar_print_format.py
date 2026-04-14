import unittest
from datetime import date, datetime
from types import SimpleNamespace

from jinja2 import Environment

from ifitwala_ed.hr.print_format.sync import (
    STAFF_CALENDAR_CSS_PATH,
    STAFF_CALENDAR_PRINT_FORMAT_PATH,
    STAFF_CALENDAR_TEMPLATE_PATH,
    get_staff_calendar_print_format_values,
    load_staff_calendar_print_format_payload,
)


class TestStaffCalendarPrintFormat(unittest.TestCase):
    def test_sync_module_targets_exported_paths(self):
        self.assertTrue(STAFF_CALENDAR_PRINT_FORMAT_PATH.exists())
        self.assertTrue(STAFF_CALENDAR_TEMPLATE_PATH.exists())
        self.assertTrue(STAFF_CALENDAR_CSS_PATH.exists())

    def test_loaded_payload_matches_contract(self):
        payload = load_staff_calendar_print_format_payload()
        values = get_staff_calendar_print_format_values()

        self.assertEqual(payload["doctype"], "Print Format")
        self.assertEqual(payload["doc_type"], "Staff Calendar")
        self.assertEqual(payload["print_format_type"], "Jinja")
        self.assertEqual(payload["module"], "HR")
        self.assertEqual(payload["name"], "Staff Calendar Print")
        self.assertEqual(payload["standard"], "Yes")
        self.assertTrue(payload["custom_format"])
        self.assertEqual(values["doc_type"], "Staff Calendar")
        self.assertEqual(values["html"], payload["html"])
        self.assertEqual(values["css"], payload["css"])
        self.assertIn("<style>", payload["html"])
        self.assertIn("@page", payload["html"])

    def test_template_parses_as_valid_jinja(self):
        html = STAFF_CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")
        Environment().parse(html)

    def test_template_uses_branding_and_real_staff_calendar_fields(self):
        html = STAFF_CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")

        for token in (
            "school_logo",
            "organization_logo",
            "frappe.db.get_value",
            "doc.staff_calendar_name",
            "doc.school",
            "doc.employee_group",
            "doc.total_holidays",
            "doc.total_working_day",
            "row.holiday_date",
            "row.description",
            "row.color",
            "row.weekly_off",
            "calendar-page",
            "calendar-grid",
            "calendar-day__notes",
            "range(month_count)",
        ):
            self.assertIn(token, html)

        for token in (
            "row.title",
            "row.type",
            "doc.organization_logo",
            "doc.school_logo",
            "month-calendar-table",
            "date-chip",
            "type-pill",
            "month-grid",
            "day-box",
        ):
            self.assertNotIn(token, html)

    def test_template_renders_visual_calendar_markup(self):
        html = STAFF_CALENDAR_TEMPLATE_PATH.read_text(encoding="utf-8")
        template = Environment().from_string(html)

        rendered = template.render(
            frappe=_FakeFrappe(),
            doc=_FakeStaffCalendarDoc(
                name="25-26 - Academic Staff",
                staff_calendar_name="25-26 - Academic Staff",
                school="Lwitwala International School",
                employee_group="Academic Staff",
                academic_year="2025-2026",
                from_date=date(2025, 8, 1),
                to_date=date(2025, 9, 30),
                total_working_day=52,
                total_holidays=8,
                holidays=[
                    SimpleNamespace(
                        holiday_date=date(2025, 8, 12),
                        description="School Closed",
                        color="#2A9D8F",
                        weekly_off=0,
                    ),
                    SimpleNamespace(
                        holiday_date=date(2025, 8, 17),
                        description="Sunday",
                        color="#E9C46A",
                        weekly_off=1,
                    ),
                ],
            ),
            range=range,
        )

        for token in (
            "August 2025",
            "September 2025",
            "Staff Calendar",
            "School Closed",
            "Sunday",
            "Outside Range",
            "calendar-day__note-line",
            "calendar-page",
        ):
            self.assertIn(token, rendered)

    def test_css_includes_print_branding_and_calendar_styles(self):
        css = STAFF_CALENDAR_CSS_PATH.read_text(encoding="utf-8")

        for token in (
            "@page",
            "A4 landscape",
            ".calendar-header",
            ".calendar-summary",
            ".calendar-grid",
            ".calendar-day__notes",
            ".legend-chip",
            "page-break-after: always",
        ):
            self.assertIn(token, css)


class _FakeFrappeDB:
    def get_value(self, doctype, name, fields, as_dict=False):
        if doctype == "School":
            return SimpleNamespace(
                school_name="Lwitwala International School",
                school_logo="/files/school-logo.png",
                organization="Ifitwala Education Group",
            )
        if doctype == "Organization":
            return SimpleNamespace(
                organization_name="Ifitwala Education Group",
                organization_logo="/files/org-logo.png",
            )
        return None


class _FakeFrappeUtils:
    @staticmethod
    def nowdate():
        return "2026-04-13"

    @staticmethod
    def formatdate(value):
        return _to_date(value).strftime("%d %b %Y")

    @staticmethod
    def getdate(value):
        return _to_date(value)

    @staticmethod
    def escape_html(value):
        return "" if value is None else str(value)

    @staticmethod
    def add_to_date(value, months=0, days=0, as_datetime=False):
        current = _to_date(value)
        month_index = (current.year * 12 + current.month - 1) + months
        year = month_index // 12
        month = month_index % 12 + 1
        day = min(current.day, _days_in_month(year, month))
        shifted = date(year, month, day)
        if days:
            from datetime import timedelta

            shifted = shifted + timedelta(days=days)
        return shifted


class _FakeFrappe:
    def __init__(self):
        self.db = _FakeFrappeDB()
        self.utils = _FakeFrappeUtils()


class _FakeStaffCalendarDoc(SimpleNamespace):
    def get_formatted(self, fieldname):
        value = getattr(self, fieldname, None)
        if isinstance(value, date):
            return value.strftime("%d %b %Y")
        return "" if value is None else str(value)


def _to_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value), "%Y-%m-%d").date()


def _days_in_month(year, month):
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)
    return (next_month - date(year, month, 1)).days


if __name__ == "__main__":
    unittest.main()
