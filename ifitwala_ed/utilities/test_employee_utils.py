from __future__ import annotations

from contextlib import contextmanager
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


@contextmanager
def _employee_utils_module():
    tree_utils = ModuleType("ifitwala_ed.utilities.tree_utils")
    tree_utils.get_ancestors_inclusive = lambda *args, **kwargs: []
    tree_utils.get_descendants_inclusive = lambda doctype, node, cache_ttl=None: [node]

    with stubbed_frappe(extra_modules={"ifitwala_ed.utilities.tree_utils": tree_utils}) as frappe:
        frappe.defaults = SimpleNamespace(get_user_default=lambda key, user=None: None)
        frappe.db.get_value = lambda *args, **kwargs: None
        frappe.get_all = lambda *args, **kwargs: []
        yield import_fresh("ifitwala_ed.utilities.employee_utils")


class TestEmployeeUtilsScope(TestCase):
    def test_get_user_visible_schools_uses_active_employee_school_descendants(self):
        with _employee_utils_module() as employee_utils:
            with (
                patch.object(
                    employee_utils.frappe.db,
                    "get_value",
                    return_value={"name": "EMP-0001", "school": "SCH-ROOT", "organization": "ORG-ROOT"},
                ),
                patch.object(
                    employee_utils,
                    "get_descendants_inclusive",
                    return_value=["SCH-ROOT", "SCH-CHILD"],
                ) as descendants,
            ):
                schools = employee_utils.get_user_visible_schools("staff@example.com")

        self.assertEqual(schools, ["SCH-ROOT", "SCH-CHILD"])
        descendants.assert_called_once_with("School", "SCH-ROOT", cache_ttl=employee_utils.CACHE_TTL)

    def test_get_user_visible_schools_falls_back_to_org_scope_when_active_employee_school_is_blank(self):
        with _employee_utils_module() as employee_utils:
            employee_utils.frappe.defaults.get_user_default = lambda key, user=None: (
                "SCH-STALE" if key == "school" else None
            )

            with (
                patch.object(
                    employee_utils.frappe.db,
                    "get_value",
                    return_value={"name": "EMP-0001", "school": "", "organization": "ORG-ROOT"},
                ),
                patch.object(
                    employee_utils,
                    "get_descendant_organizations",
                    return_value=["ORG-ROOT", "ORG-CHILD"],
                ) as org_scope,
                patch.object(employee_utils, "get_descendants_inclusive") as school_descendants,
                patch.object(employee_utils.frappe, "get_all", return_value=["SCH-A", "SCH-B"]) as get_all,
            ):
                schools = employee_utils.get_user_visible_schools("staff@example.com")

        self.assertEqual(schools, ["SCH-A", "SCH-B"])
        org_scope.assert_called_once_with("ORG-ROOT")
        school_descendants.assert_not_called()
        get_all.assert_called_once_with(
            "School",
            filters={"organization": ["in", ["ORG-ROOT", "ORG-CHILD"]]},
            pluck="name",
            order_by="lft asc, name asc",
            limit=0,
        )

    def test_get_user_visible_schools_uses_default_school_when_no_active_employee_exists(self):
        with _employee_utils_module() as employee_utils:
            employee_utils.frappe.defaults.get_user_default = lambda key, user=None: (
                "SCH-ROOT" if key == "school" else None
            )

            with (
                patch.object(employee_utils.frappe.db, "get_value", return_value=None),
                patch.object(
                    employee_utils,
                    "get_descendants_inclusive",
                    return_value=["SCH-ROOT", "SCH-CHILD"],
                ) as descendants,
            ):
                schools = employee_utils.get_user_visible_schools("staff@example.com")

        self.assertEqual(schools, ["SCH-ROOT", "SCH-CHILD"])
        descendants.assert_called_once_with("School", "SCH-ROOT", cache_ttl=employee_utils.CACHE_TTL)
