from __future__ import annotations

import types
from unittest import TestCase

from ifitwala_ed.tests.frappe_stubs import import_fresh, stubbed_frappe


def _unexpected(message: str):
    raise AssertionError(message)


class TestBackfillPublicEmployeeProfileImages(TestCase):
    def test_execute_repairs_public_employee_images_without_linked_user(self):
        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        public_people = types.ModuleType("ifitwala_ed.website.public_people")
        ensure_calls: list[tuple[str, str, str]] = []
        variant_calls: list[tuple[list[str], tuple[str, ...], bool]] = []
        invalidation_calls: list[bool] = []
        get_all_calls: list[dict] = []

        image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = (
            "profile_image_thumb",
            "profile_image_card",
            "profile_image_medium",
        )

        def ensure_employee_profile_image(employee_name, **kwargs):
            ensure_calls.append(
                (
                    employee_name,
                    kwargs.get("original_url"),
                    kwargs.get("upload_source"),
                )
            )
            return f"/private/files/governed-{employee_name}.png"

        def get_employee_image_variants_map(employee_names, **kwargs):
            variant_calls.append(
                (
                    list(employee_names),
                    tuple(kwargs.get("slots") or ()),
                    bool(kwargs.get("request_missing_derivatives")),
                )
            )
            return {}

        image_utils.ensure_employee_profile_image = ensure_employee_profile_image
        image_utils.get_employee_image_variants_map = get_employee_image_variants_map
        public_people.invalidate_public_people_cache = lambda: invalidation_calls.append(True)

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.utilities.image_utils": image_utils,
                "ifitwala_ed.website.public_people": public_people,
            }
        ) as frappe:
            frappe.db.table_exists = lambda doctype: doctype == "Employee"

            def fake_get_all(doctype, **kwargs):
                get_all_calls.append({"doctype": doctype, **kwargs})
                return [
                    {
                        "name": "EMP-PUBLIC-1",
                        "employee_image": "/private/files/katherine.png",
                    },
                    {
                        "name": "EMP-PUBLIC-2",
                        "employee_image": "/files/public-staff.png",
                    },
                ]

            frappe.get_all = fake_get_all
            module = import_fresh("ifitwala_ed.patches.backfill_public_employee_profile_images")

            module.execute()

        self.assertEqual(get_all_calls[0]["doctype"], "Employee")
        self.assertEqual(
            get_all_calls[0]["filters"],
            {
                "show_on_website": 1,
                "employee_image": ["is", "set"],
            },
        )
        self.assertEqual(
            ensure_calls,
            [
                ("EMP-PUBLIC-1", "/private/files/katherine.png", "Patch"),
                ("EMP-PUBLIC-2", "/files/public-staff.png", "Patch"),
            ],
        )
        self.assertEqual(
            variant_calls,
            [
                (["EMP-PUBLIC-1"], image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS, True),
                (["EMP-PUBLIC-2"], image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS, True),
            ],
        )
        self.assertEqual(invalidation_calls, [True])

    def test_execute_returns_when_employee_table_is_missing(self):
        image_utils = types.ModuleType("ifitwala_ed.utilities.image_utils")
        public_people = types.ModuleType("ifitwala_ed.website.public_people")
        image_utils.PROFILE_IMAGE_DERIVATIVE_SLOTS = ()
        image_utils.ensure_employee_profile_image = lambda *args, **kwargs: _unexpected(
            "ensure_employee_profile_image should not run"
        )
        image_utils.get_employee_image_variants_map = lambda *args, **kwargs: _unexpected(
            "get_employee_image_variants_map should not run"
        )
        public_people.invalidate_public_people_cache = lambda: _unexpected(
            "invalidate_public_people_cache should not run"
        )

        with stubbed_frappe(
            extra_modules={
                "ifitwala_ed.utilities.image_utils": image_utils,
                "ifitwala_ed.website.public_people": public_people,
            }
        ) as frappe:
            frappe.db.table_exists = lambda doctype: False
            frappe.get_all = lambda *args, **kwargs: _unexpected("get_all should not run")
            module = import_fresh("ifitwala_ed.patches.backfill_public_employee_profile_images")

            module.execute()
