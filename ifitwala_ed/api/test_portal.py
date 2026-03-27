# ifitwala_ed/api/test_portal.py

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.api import portal


class TestPortalIdentity(FrappeTestCase):
    def test_get_guardian_portal_identity_prefers_guardian_profile_name_and_image(self):
        with (
            patch("ifitwala_ed.api.portal.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.portal.frappe.db.get_value",
                side_effect=[
                    {
                        "name": "guardian@example.com",
                        "first_name": "Mina",
                        "full_name": "Mina Dar",
                        "email": "guardian@example.com",
                    },
                    {
                        "name": "GRD-0001",
                        "guardian_full_name": "Mina Dar",
                        "guardian_first_name": "Mina",
                        "guardian_last_name": "Dar",
                        "guardian_image": "/private/files/guardian-original.png",
                    },
                ],
            ),
            patch(
                "ifitwala_ed.api.portal.get_preferred_guardian_image_url",
                return_value="/files/guardian-thumb.webp",
            ) as image_mock,
        ):
            payload = portal.get_guardian_portal_identity()

        self.assertEqual(payload["user"], "guardian@example.com")
        self.assertEqual(payload["guardian"], "GRD-0001")
        self.assertEqual(payload["display_name"], "Mina Dar")
        self.assertEqual(payload["full_name"], "Mina Dar")
        self.assertEqual(payload["email"], "guardian@example.com")
        self.assertEqual(payload["image_url"], "/files/guardian-thumb.webp")
        image_mock.assert_called_once_with("GRD-0001", original_url="/private/files/guardian-original.png")

    def test_get_guardian_portal_identity_falls_back_to_user_identity_when_guardian_row_missing(self):
        with (
            patch("ifitwala_ed.api.portal.frappe.session", frappe._dict({"user": "guardian@example.com"})),
            patch(
                "ifitwala_ed.api.portal.frappe.db.get_value",
                side_effect=[
                    {
                        "name": "guardian@example.com",
                        "first_name": "Mina",
                        "full_name": "Mina Dar",
                        "email": "guardian@example.com",
                    },
                    None,
                ],
            ),
            patch("ifitwala_ed.api.portal.get_preferred_guardian_image_url") as image_mock,
        ):
            payload = portal.get_guardian_portal_identity()

        self.assertEqual(payload["user"], "guardian@example.com")
        self.assertIsNone(payload["guardian"])
        self.assertEqual(payload["display_name"], "Mina Dar")
        self.assertEqual(payload["full_name"], "Mina Dar")
        self.assertEqual(payload["email"], "guardian@example.com")
        self.assertIsNone(payload["image_url"])
        image_mock.assert_not_called()
