import unittest
from types import SimpleNamespace

from jinja2 import Environment

from ifitwala_ed.hr.print_format.sync import (
    EMPLOYEE_CSS_PATH,
    EMPLOYEE_PRINT_FORMAT_PATH,
    EMPLOYEE_TEMPLATE_PATH,
    get_employee_print_format_values,
    load_employee_print_format_payload,
)


class TestEmployeePrintFormat(unittest.TestCase):
    def test_sync_module_targets_exported_paths(self):
        self.assertTrue(EMPLOYEE_PRINT_FORMAT_PATH.exists())
        self.assertTrue(EMPLOYEE_TEMPLATE_PATH.exists())
        self.assertTrue(EMPLOYEE_CSS_PATH.exists())

    def test_loaded_payload_matches_contract(self):
        payload = load_employee_print_format_payload()
        values = get_employee_print_format_values()

        self.assertEqual(payload["doctype"], "Print Format")
        self.assertEqual(payload["doc_type"], "Employee")
        self.assertEqual(payload["print_format_type"], "Jinja")
        self.assertEqual(payload["module"], "HR")
        self.assertEqual(payload["name"], "Employee Print")
        self.assertEqual(payload["standard"], "Yes")
        self.assertTrue(payload["custom_format"])
        self.assertTrue(payload["html"])
        self.assertTrue(payload["css"])
        self.assertEqual(values["doc_type"], "Employee")
        self.assertEqual(values["html"], payload["html"])
        self.assertEqual(values["css"], payload["css"])

    def test_template_parses_as_valid_jinja(self):
        html = EMPLOYEE_TEMPLATE_PATH.read_text(encoding="utf-8")
        Environment().parse(html)

    def test_template_covers_expected_employee_fields(self):
        html = EMPLOYEE_TEMPLATE_PATH.read_text(encoding="utf-8")

        for token in (
            "employee_salutation",
            "employee_first_name",
            "employee_middle_name",
            "employee_last_name",
            "employee_full_name",
            "employee_preferred_name",
            "employee_gender",
            "employee_date_of_birth",
            "nationality",
            "employee_second_nationality",
            "first_language",
            "employee_second_language",
            "employee_professional_email",
            "employee_personal_email",
            "employee_mobile_phone",
            "phone_ext",
            "preferred_contact_email",
            "preferred_email",
            "empl_primary_contact",
            "emergency_contact_person",
            "emergency_contact_relation",
            "emergency_contact_details",
            "user_id",
            "create_user_permission",
            "date_of_joining",
            "employment_status",
            "employment_type",
            "designation",
            "department",
            "employee_group",
            "organization",
            "school",
            "reports_to",
            "current_holiday_lis",
            "is_group",
            "expense_approver",
            "leave_approver",
            "show_on_website",
            "show_public_profile_page",
            "featured_on_website",
            "public_profile_slug",
            "small_bio",
            "notice_date",
            "relieving_date",
            "exit_interview_date",
            "exit_interview",
            "employee_history",
            "row.access_mode",
            "row.role_profile",
            "row.workspace_override",
            "row.priority",
            "row.note",
        ):
            self.assertIn(token, html)

        for token in (
            "website_sort_order",
            "old_parent",
            "lft",
            "rgt",
            "contact_html",
            "address_html",
        ):
            self.assertNotIn(token, html)

    def test_template_reuses_student_profile_visual_language_without_duplicating_brand_header(self):
        css = EMPLOYEE_CSS_PATH.read_text(encoding="utf-8")
        html = EMPLOYEE_TEMPLATE_PATH.read_text(encoding="utf-8")

        for token in (
            ".profile-header",
            ".document-banner",
            ".section-card",
            ".status-pill",
            ".crm-grid",
            ".history-entry",
            ".hero-card",
            ".history-detail-table",
            ".profile-photo",
            "Employee Profile",
            "Linked Contact and Address",
            "Internal Work History",
        ):
            self.assertIn(token, css if token.startswith(".") else html)

        self.assertNotIn("Not provided", html)

    def test_template_integrates_managed_letterhead_and_footer(self):
        html = EMPLOYEE_TEMPLATE_PATH.read_text(encoding="utf-8")

        for token in (
            "using_managed_letterhead",
            "{{ letter_head | safe }}",
            "{{ footer | safe }}",
            "no_letterhead",
            "employee-profile--with-letterhead",
            "document-banner",
        ):
            self.assertIn(token, html)

    def test_template_renders_expected_markup(self):
        html = EMPLOYEE_TEMPLATE_PATH.read_text(encoding="utf-8")
        template = Environment().from_string(html)

        rendered = template.render(
            frappe=_FakeFrappe(),
            doc=_FakeEmployeeDoc(
                name="HR-EMP-0001",
                employee_salutation="Ms",
                employee_first_name="Amina",
                employee_middle_name="Grace",
                employee_last_name="Okello",
                employee_full_name="Amina Grace Okello",
                employee_preferred_name="Amina",
                employee_gender="Female",
                employee_date_of_birth="1990-05-04",
                nationality="Uganda",
                employee_second_nationality="Kenya",
                first_language="English",
                employee_second_language="French",
                employee_professional_email="amina@example.com",
                employee_personal_email="amina.personal@example.com",
                employee_mobile_phone="+855123456",
                phone_ext="204",
                employee_image="/files/employee-photo.png",
                user_id="amina@example.com",
                create_user_permission=1,
                preferred_contact_email="Professional Email",
                preferred_email="amina@example.com",
                empl_primary_contact="CONTACT-EMP-0001",
                emergency_contact_person="Daniel Okello",
                emergency_contact_relation="Sibling",
                emergency_contact_details="Mobile: +855998877",
                date_of_joining="2024-08-01",
                employment_status="Active",
                employment_type="Full Time",
                designation="Operations Manager",
                department="Operations",
                employee_group="Leadership",
                organization="Ifitwala Education Group",
                school="Lwitwala International School",
                reports_to="HR-EMP-0009",
                current_holiday_lis="2025 Staff Calendar",
                is_group=0,
                expense_approver="finance@example.com",
                leave_approver="principal@example.com",
                show_on_website=1,
                show_public_profile_page=1,
                featured_on_website=0,
                public_profile_slug="amina-okello",
                small_bio="Leads operations across the school.",
                notice_date="",
                relieving_date="",
                exit_interview_date="",
                exit_interview="",
                employee_history=[
                    SimpleNamespace(
                        designation="Operations Manager",
                        organization="Ifitwala Education Group",
                        school="Lwitwala International School",
                        from_date="2024-08-01",
                        to_date="",
                        is_current=1,
                        access_mode="Follow Designation",
                        role_profile="HR User",
                        workspace_override="HR",
                        priority=1,
                        note="Initial appointment",
                    )
                ],
            ),
            letter_head="",
            footer="",
            no_letterhead=0,
        )

        for token in (
            "Employee Profile",
            "Amina Grace Okello",
            "Operations Manager",
            "Ifitwala Education Group",
            "Linked Contact and Address",
            "CONTACT-EMP-0001",
            "123 Campus Road",
            "Initial appointment",
            "Employee Image",
            "history-entry",
        ):
            self.assertIn(token, rendered)

        self.assertNotIn("Not provided", rendered)

    def test_template_renders_managed_letterhead_banner(self):
        html = EMPLOYEE_TEMPLATE_PATH.read_text(encoding="utf-8")
        template = Environment().from_string(html)

        rendered = template.render(
            frappe=_FakeFrappe(),
            doc=_FakeEmployeeDoc(
                name="HR-EMP-0002",
                employee_first_name="John",
                employee_middle_name="",
                employee_last_name="Neumann",
                employee_full_name="John Neumann",
                employee_preferred_name="",
                employee_gender="Male",
                employee_professional_email="john@example.com",
                date_of_joining="2026-03-24",
                employment_status="Active",
                designation="Assistant Principal",
                organization="Ifitwala Roots Campus",
                school="Ifitwala Secondary School",
                employee_history=[],
            ),
            letter_head="<div class='ifitwala-letterhead'>Letterhead</div>",
            footer="<div class='ifitwala-letterhead-footer'>Footer</div>",
            no_letterhead=0,
        )

        self.assertIn("ifitwala-letterhead", rendered)
        self.assertIn("ifitwala-letterhead-footer", rendered)
        self.assertIn("employee-profile--with-letterhead", rendered)
        self.assertIn("document-banner", rendered)
        self.assertIn("hero-card", rendered)
        self.assertIn("John Neumann", rendered)


class _FakeFrappeDB:
    def get_value(self, doctype, filters, fieldname, as_dict=False):
        if doctype == "Dynamic Link" and fieldname == "parent":
            return "CONTACT-EMP-0001"
        return None


class _FakeFrappeUtils:
    @staticmethod
    def nowdate():
        return "2026-04-16"

    @staticmethod
    def formatdate(value):
        if not value:
            return ""
        return str(value)

    @staticmethod
    def escape_html(value):
        return "" if value is None else str(value)


class _FakeFrappe:
    def __init__(self):
        self.db = _FakeFrappeDB()
        self.utils = _FakeFrappeUtils()

    def get_doc(self, doctype, name):
        if doctype == "Contact" and name == "CONTACT-EMP-0001":
            return SimpleNamespace(first_name="Amina", last_name="Okello")
        raise AssertionError(f"Unexpected get_doc({doctype!r}, {name!r})")

    def get_all(self, doctype, filters=None, fields=None, order_by=None):
        if doctype == "Contact Email":
            return [SimpleNamespace(email_id="amina@example.com", is_primary=1, idx=1)]
        if doctype == "Contact Phone":
            return [SimpleNamespace(phone="+855123456", is_primary_mobile_no=1, idx=1)]
        if doctype == "Dynamic Link":
            return [SimpleNamespace(parent="ADDR-EMP-0001")]
        if doctype == "Address":
            return [
                SimpleNamespace(
                    name="ADDR-EMP-0001",
                    address_title="Home Address",
                    address_type="Home",
                    address_line1="123 Campus Road",
                    address_line2="Apartment 4",
                    city="Bangkok",
                    state="Bangkok",
                    country="Thailand",
                    pincode="10110",
                )
            ]
        return []


class _FakeEmployeeDoc(SimpleNamespace):
    def get_formatted(self, fieldname):
        value = getattr(self, fieldname, None)
        return "" if value is None else str(value)


if __name__ == "__main__":
    unittest.main()
