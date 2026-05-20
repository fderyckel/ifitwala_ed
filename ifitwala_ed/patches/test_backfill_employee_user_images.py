from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _unexpected(message: str):
    raise AssertionError(message)


class TestBackfillEmployeeUserImages(TestCase):
    def test_execute_repairs_linked_employee_user_images(self):
        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        ensure_calls: list[tuple[str, str, str]] = []
        variant_calls: list[tuple[list[str], tuple[str, ...], bool]] = []
        image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = (
            "profile_image_thumb",
            "profile_image_card",
            "profile_image_medium",
        )
        image_utils.ensure_employee_profile_image = lambda employee_name, **kwargs: ensure_calls.append(
            (employee_name, kwargs.get("original_url"), kwargs.get("upload_source"))
        )
        image_utils.get_employee_image_variants_map = lambda employee_names, **kwargs: variant_calls.append(
            (
                list(employee_names),
                tuple(kwargs.get("slots") or ()),
                bool(kwargs.get("request_missing_derivatives")),
            )
        )
        image_utils.get_employee_user_avatar_url = lambda employee_name, **kwargs: (
            f"/api/method/ifitwala_ed.api.file_access.open_employee_user_avatar?employee={employee_name}"
        )

        set_values: list[tuple[str, str, str, str, bool]] = []

        with stubbed_frappe(extra_modules={"ifitwala_ed.utilities.image_utils": image_utils}) as frappe:
            frappe.db.table_exists = lambda doctype: doctype in {"Employee", "User"}
            frappe.db.exists = lambda doctype, name=None: (
                doctype == "User"
                and name
                in {
                    "staff.one@example.com",
                    "staff.two@example.com",
                }
            )
            frappe.db.get_value = lambda doctype, name, fieldname=None: None
            frappe.db.set_value = lambda doctype, name, fieldname, value, update_modified=True: set_values.append(
                (doctype, name, fieldname, value, update_modified)
            )
            frappe.get_all = lambda doctype, **kwargs: [
                {
                    "name": "EMP-0001",
                    "user_id": "staff.one@example.com",
                    "employee_image": "/private/files/employee-one.png",
                },
                {
                    "name": "EMP-0002",
                    "user_id": "staff.two@example.com",
                    "employee_image": "/files/employee-two.png",
                },
            ]
            module = import_fresh("ifitwala_ed.patches.backfill_employee_user_images")

            module.execute()

        self.assertEqual(
            ensure_calls,
            [
                ("EMP-0001", "/private/files/employee-one.png", "Patch"),
                ("EMP-0002", "/files/employee-two.png", "Patch"),
            ],
        )
        self.assertEqual(
            variant_calls,
            [
                (["EMP-0001"], image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS, True),
                (["EMP-0002"], image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS, True),
            ],
        )
        self.assertEqual(
            set_values,
            [
                (
                    "User",
                    "staff.one@example.com",
                    "user_image",
                    "/api/method/ifitwala_ed.api.file_access.open_employee_user_avatar?employee=EMP-0001",
                    False,
                ),
                (
                    "User",
                    "staff.two@example.com",
                    "user_image",
                    "/api/method/ifitwala_ed.api.file_access.open_employee_user_avatar?employee=EMP-0002",
                    False,
                ),
            ],
        )

    def test_execute_returns_when_employee_table_is_missing(self):
        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = ()
        image_utils.ensure_employee_profile_image = lambda *args, **kwargs: _unexpected(
            "ensure_employee_profile_image should not run"
        )
        image_utils.get_employee_image_variants_map = lambda *args, **kwargs: _unexpected(
            "get_employee_image_variants_map should not run"
        )
        image_utils.get_employee_user_avatar_url = lambda *args, **kwargs: _unexpected(
            "get_employee_user_avatar_url should not run"
        )

        with stubbed_frappe(extra_modules={"ifitwala_ed.utilities.image_utils": image_utils}) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: _unexpected("get_all should not run when Employee is missing")
            module = import_fresh("ifitwala_ed.patches.backfill_employee_user_images")

            module.execute()
