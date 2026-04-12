import unittest

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
        ):
            self.assertIn(token, html)

        for token in (
            "row.title",
            "row.type",
            "doc.organization_logo",
            "doc.school_logo",
        ):
            self.assertNotIn(token, html)

    def test_css_includes_print_branding_and_table_styles(self):
        css = STAFF_CALENDAR_CSS_PATH.read_text(encoding="utf-8")

        for token in (
            ".brand-mark img",
            ".hero-card",
            ".summary-card",
            ".calendar-table",
            ".date-chip",
            ".type-pill",
        ):
            self.assertIn(token, css)


if __name__ == "__main__":
    unittest.main()
