from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _program_offering_module():
    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.cint = lambda value=0: int(value or 0)
    frappe_utils.flt = lambda value=0, precision=None: float(value or 0)
    frappe_utils.get_datetime = lambda value=None: value
    frappe_utils.get_link_to_form = lambda doctype, name=None: name or doctype
    frappe_utils.getdate = lambda value=None: value
    frappe_utils.now_datetime = lambda: "2026-04-23 10:00:00"

    account_holder_utils = ModuleType("ifitwala_ed.accounting.account_holder_utils")
    account_holder_utils.get_school_organization = lambda *args, **kwargs: None

    basket_group_utils = ModuleType("ifitwala_ed.schedule.basket_group_utils")
    basket_group_utils.get_program_course_basket_group_map = lambda *args, **kwargs: {}

    schedule_utils = ModuleType("ifitwala_ed.schedule.schedule_utils")
    schedule_utils.iter_student_group_room_slots = lambda *args, **kwargs: []

    student_group_employee_booking = ModuleType("ifitwala_ed.schedule.student_group_employee_booking")
    student_group_employee_booking.rebuild_employee_bookings_for_student_group = lambda *args, **kwargs: None

    employee_utils = ModuleType("ifitwala_ed.utilities.employee_utils")
    employee_utils.get_user_visible_schools = lambda user=None: []

    employee_booking = ModuleType("ifitwala_ed.utilities.employee_booking")
    employee_booking.find_employee_conflicts = lambda *args, **kwargs: []

    location_utils = ModuleType("ifitwala_ed.utilities.location_utils")
    location_utils.find_room_conflicts = lambda *args, **kwargs: []
    location_utils.is_bookable_room = lambda *args, **kwargs: True

    school_tree = ModuleType("ifitwala_ed.utilities.school_tree")
    school_tree.get_ancestor_schools = lambda school: [school] if school else []
    school_tree.is_leaf_school = lambda school: True

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "ifitwala_ed.accounting.account_holder_utils": account_holder_utils,
            "ifitwala_ed.schedule.basket_group_utils": basket_group_utils,
            "ifitwala_ed.schedule.schedule_utils": schedule_utils,
            "ifitwala_ed.schedule.student_group_employee_booking": student_group_employee_booking,
            "ifitwala_ed.utilities.employee_utils": employee_utils,
            "ifitwala_ed.utilities.employee_booking": employee_booking,
            "ifitwala_ed.utilities.location_utils": location_utils,
            "ifitwala_ed.utilities.school_tree": school_tree,
        }
    ) as frappe:
        frappe.get_roles = lambda user: []
        frappe.db.escape = lambda value, percent=True: f"'{value}'"
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.validate_and_sanitize_search_inputs = lambda fn: fn
        frappe.format = lambda value, df=None: value
        frappe.bold = lambda value: value
        frappe.msgprint = lambda *args, **kwargs: None
        yield import_fresh("ifitwala_ed.schedule.doctype.program_offering.program_offering")


@contextmanager
def _program_enrollment_module():
    frappe_utils = ModuleType("frappe.utils")
    frappe_utils.get_fullname = lambda user=None: user or ""
    frappe_utils.get_link_to_form = lambda doctype, name=None: name or doctype
    frappe_utils.getdate = lambda value=None: value
    frappe_utils.nowdate = lambda: "2026-04-23"

    frappe_utils_nestedset = ModuleType("frappe.utils.nestedset")
    frappe_utils_nestedset.get_ancestors_of = lambda *args, **kwargs: []

    basket_group_utils = ModuleType("ifitwala_ed.schedule.basket_group_utils")
    basket_group_utils.get_offering_course_semantics = lambda *args, **kwargs: {}

    schedule_utils = ModuleType("ifitwala_ed.schedule.schedule_utils")
    schedule_utils.get_school_term_bounds = lambda *args, **kwargs: (None, None)

    employee_utils = ModuleType("ifitwala_ed.utilities.employee_utils")
    employee_utils.get_user_visible_schools = lambda user=None: []

    school_tree = ModuleType("ifitwala_ed.utilities.school_tree")

    class ParentRuleViolation(Exception):
        pass

    school_tree.ParentRuleViolation = ParentRuleViolation
    school_tree.get_effective_record = lambda *args, **kwargs: None

    with stubbed_frappe(
        extra_modules={
            "frappe.utils": frappe_utils,
            "frappe.utils.nestedset": frappe_utils_nestedset,
            "ifitwala_ed.schedule.basket_group_utils": basket_group_utils,
            "ifitwala_ed.schedule.schedule_utils": schedule_utils,
            "ifitwala_ed.utilities.employee_utils": employee_utils,
            "ifitwala_ed.utilities.school_tree": school_tree,
        }
    ) as frappe:
        frappe.get_roles = lambda user: []
        frappe.db.escape = lambda value, percent=True: f"'{value}'"
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.validate_and_sanitize_search_inputs = lambda fn: fn
        frappe.format = lambda value, df=None: value
        frappe.bold = lambda value: value
        frappe.msgprint = lambda *args, **kwargs: None
        yield import_fresh("ifitwala_ed.schedule.doctype.program_enrollment.program_enrollment")


class TestProgramOfferingPermissionScopeUnit(TestCase):
    def test_permission_query_conditions_use_visible_school_scope(self):
        with _program_offering_module() as program_offering:
            with (
                patch.object(program_offering.frappe, "get_roles", return_value=["Admission Manager"]),
                patch.object(program_offering, "get_user_visible_schools", return_value=["SCH-ROOT", "SCH-1"]),
            ):
                condition = program_offering.get_permission_query_conditions("manager@example.com")

        self.assertEqual(condition, "`tabProgram Offering`.`school` in ('SCH-ROOT', 'SCH-1')")

    def test_has_permission_allows_school_from_org_fallback_scope(self):
        with _program_offering_module() as program_offering:
            allowed_doc = SimpleNamespace(school="SCH-1")
            blocked_doc = SimpleNamespace(school="SCH-OTHER")

            with (
                patch.object(program_offering.frappe, "get_roles", return_value=["Admission Manager"]),
                patch.object(program_offering, "get_user_visible_schools", return_value=["SCH-ROOT", "SCH-1"]),
            ):
                self.assertTrue(program_offering.has_permission(allowed_doc, "read", "manager@example.com"))
                self.assertFalse(program_offering.has_permission(blocked_doc, "read", "manager@example.com"))


class TestProgramEnrollmentPermissionScopeUnit(TestCase):
    def test_permission_query_conditions_use_visible_school_scope(self):
        with _program_enrollment_module() as program_enrollment:
            with (
                patch.object(program_enrollment.frappe, "get_roles", return_value=["Admission Manager"]),
                patch.object(program_enrollment, "get_user_visible_schools", return_value=["SCH-ROOT", "SCH-1"]),
            ):
                condition = program_enrollment.get_permission_query_conditions("manager@example.com")

        self.assertEqual(condition, "`tabProgram Enrollment`.`school` IN ('SCH-ROOT', 'SCH-1')")

    def test_has_permission_allows_school_from_org_fallback_scope(self):
        with _program_enrollment_module() as program_enrollment:
            allowed_doc = SimpleNamespace(school="SCH-1")
            blocked_doc = SimpleNamespace(school="SCH-OTHER")

            with (
                patch.object(program_enrollment.frappe, "get_roles", return_value=["Admission Manager"]),
                patch.object(program_enrollment, "get_user_visible_schools", return_value=["SCH-ROOT", "SCH-1"]),
            ):
                self.assertTrue(program_enrollment.has_permission(allowed_doc, user="manager@example.com"))
                self.assertFalse(program_enrollment.has_permission(blocked_doc, user="manager@example.com"))
