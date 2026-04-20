# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from unittest.mock import patch

from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.utilities import image_utils


class TestEmployeeImageUtils(FrappeTestCase):
    def test_get_preferred_employee_image_url_prefers_thumb_variant(self):
        with patch(
            "ifitwala_ed.utilities.image_utils._get_governed_image_variants_map",
            return_value={
                "EMP-0001": {
                    "profile_image_thumb": "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-THUMB&context_doctype=Employee&context_name=EMP-0001&derivative_role=thumb",
                    "profile_image_card": "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-CARD&context_doctype=Employee&context_name=EMP-0001&derivative_role=card",
                }
            },
        ):
            image_url = image_utils.get_preferred_employee_image_url(
                "EMP-0001",
                original_url="/private/files/employee/original_employee.png",
            )

        self.assertEqual(
            image_url,
            "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-THUMB&context_doctype=Employee&context_name=EMP-0001&derivative_role=thumb",
        )

    def test_get_preferred_employee_image_url_falls_back_to_governed_original(self):
        with (
            patch("ifitwala_ed.utilities.image_utils._get_governed_image_variants_map", return_value={"EMP-0001": {}}),
            patch(
                "ifitwala_ed.utilities.image_utils._resolve_original_governed_image_url",
                return_value="/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-ORIGINAL&context_doctype=Employee&context_name=EMP-0001",
            ) as resolve_original,
        ):
            image_url = image_utils.get_preferred_employee_image_url(
                "EMP-0001",
                original_url="/private/files/employee/original_employee.png",
            )

        resolve_original.assert_called_once_with(
            "Employee", "EMP-0001", "/private/files/employee/original_employee.png"
        )
        self.assertEqual(
            image_url,
            "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-ORIGINAL&context_doctype=Employee&context_name=EMP-0001",
        )

    def test_apply_preferred_employee_images_keeps_variant_priority(self):
        rows = [
            {"id": "EMP-0001", "image": "/private/files/employee/original_employee_1.png"},
            {"id": "EMP-0002", "image": "/private/files/employee/original_employee_2.png"},
            {"id": "EMP-0003", "image": "/private/files/employee/original_employee_3.png"},
        ]

        with (
            patch(
                "ifitwala_ed.utilities.image_utils._get_governed_image_variants_map",
                return_value={
                    "EMP-0001": {
                        "profile_image_card": "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-CARD-1&context_doctype=Employee&context_name=EMP-0001&derivative_role=card"
                    },
                    "EMP-0002": {
                        "profile_image_thumb": "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-THUMB-2&context_doctype=Employee&context_name=EMP-0002&derivative_role=thumb"
                    },
                },
            ),
            patch(
                "ifitwala_ed.utilities.image_utils._resolve_original_governed_image_url",
                side_effect=lambda _doctype, _name, original_url: original_url,
            ),
        ):
            resolved = image_utils.apply_preferred_employee_images(rows)

        self.assertEqual(
            resolved[0]["image"],
            "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-CARD-1&context_doctype=Employee&context_name=EMP-0001&derivative_role=card",
        )
        self.assertEqual(
            resolved[1]["image"],
            "/api/method/ifitwala_ed.api.file_access.download_employee_file?file=FILE-THUMB-2&context_doctype=Employee&context_name=EMP-0002&derivative_role=thumb",
        )
        self.assertEqual(resolved[2]["image"], "/private/files/employee/original_employee_3.png")

    def test_apply_preferred_employee_images_can_skip_original_fallback(self):
        rows = [{"id": "EMP-0001", "image": "/private/files/employee/original_employee.png"}]

        with patch(
            "ifitwala_ed.utilities.image_utils._get_governed_image_variants_map",
            return_value={"EMP-0001": {}},
        ):
            resolved = image_utils.apply_preferred_employee_images(
                rows,
                slots=("profile_image_thumb", "profile_image_card", "profile_image_medium"),
                fallback_to_original=False,
            )

        self.assertIsNone(resolved[0]["image"])
