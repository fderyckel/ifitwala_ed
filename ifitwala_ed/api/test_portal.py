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
        image_mock.assert_called_once_with(
            "GRD-0001",
            original_url="/private/files/guardian-original.png",
            slots=portal.PROFILE_IMAGE_DERIVATIVE_SLOTS,
            fallback_to_original=True,
            request_missing_derivatives=True,
        )

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

    def test_get_student_portal_chrome_returns_unread_communication_count(self):
        with patch(
            "ifitwala_ed.api.portal.student_communications_api.get_student_portal_communication_unread_count",
            return_value=4,
        ):
            payload = portal.get_student_portal_chrome()

        self.assertEqual(payload, {"counts": {"unread_communications": 4}})

    def test_get_guardian_portal_chrome_returns_unread_communication_count(self):
        with patch(
            "ifitwala_ed.api.portal.guardian_communications_api.get_guardian_portal_communication_unread_count",
            return_value=3,
        ):
            payload = portal.get_guardian_portal_chrome()

        self.assertEqual(payload, {"counts": {"unread_communications": 3}})


class TestStaffHomeHeader(FrappeTestCase):
    def test_get_staff_home_header_includes_disabled_org_communication_quick_action_state(self):
        cache = frappe.cache()

        with (
            patch("ifitwala_ed.api.portal.frappe.session", frappe._dict({"user": "staff@example.com"})),
            patch("ifitwala_ed.api.portal.frappe.cache", return_value=cache),
            patch.object(cache, "get_value", return_value=None),
            patch.object(cache, "set_value"),
            patch(
                "ifitwala_ed.api.portal.frappe.db.get_value",
                return_value={
                    "name": "staff@example.com",
                    "first_name": "Mali",
                    "full_name": "Mali Bangkok",
                },
            ),
            patch("ifitwala_ed.api.portal.frappe.get_roles", return_value=["Employee"]),
            patch("ifitwala_ed.api.portal._resolve_staff_first_name", return_value="Mali"),
            patch(
                "ifitwala_ed.api.portal.get_org_communication_quick_create_capability",
                return_value={
                    "enabled": False,
                    "blocked_reason": "Set a default organization first.",
                },
            ),
        ):
            payload = portal.get_staff_home_header()

        self.assertEqual(payload["first_name"], "Mali")
        self.assertFalse(payload["capabilities"]["quick_action_org_communication"])
        self.assertEqual(
            payload["quick_actions"]["org_communication"]["blocked_reason"],
            "Set a default organization first.",
        )
