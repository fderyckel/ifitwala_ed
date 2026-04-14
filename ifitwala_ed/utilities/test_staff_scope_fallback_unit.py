from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _employee_permission_module():
    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.add_years = lambda value, years=0: value
    frappe_utils.cstr = lambda value: str(value or "")
    frappe_utils.getdate = lambda value=None: value
    frappe_utils.today = lambda: "2026-04-14"
    frappe_utils.validate_email_address = lambda value, throw=False: value

    frappe_contacts = ModuleType("frappe.contacts")
    address_and_contact = ModuleType("frappe.contacts.address_and_contact")
    address_and_contact.load_address_and_contact = lambda doc: None

    frappe_permissions = ModuleType("frappe.permissions")
    frappe_permissions.get_doc_permissions = lambda doc, user=None, ptype=None: {ptype or "read": True}

    frappe_utils_nestedset = ModuleType("frappe.utils.nestedset")

    class NestedSet:
        pass

    frappe_utils_nestedset.NestedSet = NestedSet

    employee_utils = ModuleType("ifitwala_ed.utilities.employee_utils")
    employee_utils.get_descendant_organizations = lambda org: [org]
    employee_utils.get_user_base_org = lambda user=None: None

    image_utils = ModuleType("ifitwala_ed.utilities.image_utils")
    image_utils.get_preferred_employee_image_url = lambda *args, **kwargs: None

    transaction_base = ModuleType("ifitwala_ed.utilities.transaction_base")
    transaction_base.delete_events = lambda *args, **kwargs: None

    website_utils = ModuleType("ifitwala_ed.website.utils")
    website_utils.slugify_route_segment = lambda value, fallback=None: value or fallback or "employee"

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "frappe.contacts": frappe_contacts,
            "frappe.contacts.address_and_contact": address_and_contact,
            "frappe.permissions": frappe_permissions,
            "frappe.utils.nestedset": frappe_utils_nestedset,
            "ifitwala_ed.utilities.employee_utils": employee_utils,
            "ifitwala_ed.utilities.image_utils": image_utils,
            "ifitwala_ed.utilities.transaction_base": transaction_base,
            "ifitwala_ed.website.utils": website_utils,
        }
    ) as frappe:
        frappe.scrub = lambda value: str(value or "").strip().lower().replace(" ", "_")
        frappe.get_roles = lambda user: []
        frappe.get_all = lambda *args, **kwargs: []
        frappe.db.escape = lambda value, percent=True: f"'{value}'"
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.db.get_single_value = lambda *args, **kwargs: None
        yield import_fresh("ifitwala_ed.hr.doctype.employee.employee")


@contextmanager
def _contact_utils_module():
    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.cstr = lambda value: str(value or "")

    frappe_contacts = ModuleType("frappe.contacts")
    address_and_contact = ModuleType("frappe.contacts.address_and_contact")
    address_and_contact.has_permission = lambda doc, ptype, user: True

    school_tree = ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_descendant_schools = lambda school: [school]

    employee_module = ModuleType("ifitwala_ed.hr.doctype.employee.employee")
    employee_module._get_user_default_from_db = lambda user, key: None
    employee_module._resolve_academic_admin_school_scope = lambda user: None
    employee_module._resolve_academic_admin_org_scope = lambda user: []
    employee_module._resolve_self_employee = lambda user: None

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "frappe.contacts": frappe_contacts,
            "frappe.contacts.address_and_contact": address_and_contact,
            "ifitwala_ed.utilities.school_tree": school_tree,
            "ifitwala_ed.hr.doctype.employee.employee": employee_module,
        }
    ) as frappe:
        frappe.scrub = lambda value: str(value or "").strip().lower().replace(" ", "_")
        frappe.get_roles = lambda user: []
        frappe.get_all = lambda *args, **kwargs: []
        frappe.db.escape = lambda value, percent=True: f"'{value}'"
        yield import_fresh("ifitwala_ed.utilities.contact_utils")


class TestStaffScopeFallbackUnit(TestCase):
    def test_resolve_academic_admin_school_scope_ignores_stale_default_when_active_profile_school_is_blank(self):
        with _employee_permission_module() as employee_module:
            with (
                patch.object(
                    employee_module.frappe.db,
                    "get_value",
                    return_value={"name": "EMP-0001", "school": ""},
                ),
                patch.object(employee_module, "_get_user_default_from_db", return_value="SCH-STALE"),
            ):
                school_scope = employee_module._resolve_academic_admin_school_scope("academic.admin@example.com")

        self.assertIsNone(school_scope)

    def test_resolve_academic_admin_school_scope_uses_default_when_no_active_profile_exists(self):
        with _employee_permission_module() as employee_module:
            with (
                patch.object(employee_module.frappe.db, "get_value", return_value=None),
                patch.object(employee_module, "_get_user_default_from_db", return_value="SCH-ROOT"),
            ):
                school_scope = employee_module._resolve_academic_admin_school_scope("academic.admin@example.com")

        self.assertEqual(school_scope, "SCH-ROOT")

    def test_employee_pqc_keeps_academic_admin_school_scope_when_default_school_exists(self):
        with _employee_permission_module() as employee_module:
            with (
                patch.object(employee_module.frappe, "get_roles", return_value=["Academic Admin"]),
                patch.object(employee_module, "_resolve_academic_admin_school_scope", return_value="SCH-ROOT"),
            ):
                condition = employee_module.get_permission_query_conditions("academic.admin@example.com")

        self.assertEqual(condition, "`tabEmployee`.`school` = 'SCH-ROOT'")

    def test_employee_pqc_falls_back_to_org_scope_when_academic_admin_has_no_school(self):
        with _employee_permission_module() as employee_module:
            with (
                patch.object(employee_module.frappe, "get_roles", return_value=["Academic Admin"]),
                patch.object(employee_module, "_resolve_academic_admin_school_scope", return_value=None),
                patch.object(
                    employee_module, "_resolve_academic_admin_org_scope", return_value=["ORG-ROOT", "ORG-CHILD"]
                ),
            ):
                condition = employee_module.get_permission_query_conditions("academic.admin@example.com")

        self.assertEqual(condition, "`tabEmployee`.`organization` IN ('ORG-ROOT', 'ORG-CHILD')")

    def test_employee_has_permission_falls_back_to_org_scope_when_academic_admin_has_no_school(self):
        with _employee_permission_module() as employee_module:
            allowed_doc = SimpleNamespace(organization="ORG-CHILD", school="")
            blocked_doc = SimpleNamespace(organization="ORG-OTHER", school="")

            with (
                patch.object(employee_module.frappe, "get_roles", return_value=["Academic Admin"]),
                patch.object(employee_module, "_resolve_academic_admin_school_scope", return_value=None),
                patch.object(
                    employee_module, "_resolve_academic_admin_org_scope", return_value=["ORG-ROOT", "ORG-CHILD"]
                ),
            ):
                self.assertTrue(
                    employee_module.employee_has_permission(allowed_doc, "read", "academic.admin@example.com")
                )
                self.assertFalse(
                    employee_module.employee_has_permission(blocked_doc, "read", "academic.admin@example.com")
                )

    def test_contact_permission_query_conditions_fall_back_to_org_scope_when_no_school(self):
        with _contact_utils_module() as contact_utils:
            with (
                patch.object(contact_utils.frappe, "get_roles", return_value=["Academic Admin"]),
                patch.object(contact_utils, "_resolve_academic_contact_school_scope", return_value=[]),
                patch.object(
                    contact_utils, "_resolve_academic_contact_org_scope", return_value=["ORG-ROOT", "ORG-CHILD"]
                ),
            ):
                condition = contact_utils.contact_permission_query_conditions("academic.admin@example.com")

        self.assertIn("ORG-ROOT", condition)
        self.assertIn("ORG-CHILD", condition)
        self.assertIn("NOT", condition)

    def test_employee_contact_scope_matches_falls_back_to_org_scope_when_no_school(self):
        with _contact_utils_module() as contact_utils:
            with (
                patch.object(contact_utils.frappe, "get_roles", return_value=["Academic Admin"]),
                patch.object(contact_utils, "_resolve_academic_contact_school_scope", return_value=[]),
                patch.object(
                    contact_utils, "_resolve_academic_contact_org_scope", return_value=["ORG-ROOT", "ORG-CHILD"]
                ),
                patch.object(
                    contact_utils.frappe,
                    "get_all",
                    side_effect=[
                        ["EMP-0001"],
                        [{"organization": "ORG-CHILD"}],
                    ],
                ),
            ):
                allowed = contact_utils._employee_contact_scope_matches("CONTACT-0001", "academic.admin@example.com")

        self.assertTrue(allowed)
