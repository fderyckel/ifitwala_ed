from unittest import TestCase
from unittest.mock import patch

import frappe

from ifitwala_ed.api import calendar_subscription


class TestCalendarSubscriptionFacade(TestCase):
    def test_subscription_management_methods_remain_whitelisted(self):
        self.assertIn(calendar_subscription.get_my_staff_calendar_subscription, frappe.whitelisted)
        self.assertIn(calendar_subscription.create_or_get_my_staff_calendar_subscription, frappe.whitelisted)
        self.assertIn(calendar_subscription.reset_my_staff_calendar_subscription, frappe.whitelisted)
        self.assertFalse(bool(getattr(calendar_subscription.get_my_staff_calendar_subscription, "allow_guest", False)))
        self.assertFalse(
            bool(getattr(calendar_subscription.create_or_get_my_staff_calendar_subscription, "allow_guest", False))
        )
        self.assertFalse(
            bool(getattr(calendar_subscription.reset_my_staff_calendar_subscription, "allow_guest", False))
        )

    def test_download_route_remains_guest_whitelisted(self):
        self.assertIn(calendar_subscription.download_staff_calendar_subscription, frappe.whitelisted)
        self.assertTrue(bool(getattr(calendar_subscription.download_staff_calendar_subscription, "allow_guest", False)))

    def test_download_delegates_to_schedule_owner(self):
        with patch(
            "ifitwala_ed.schedule.api.calendar.subscription.download_staff_calendar_subscription",
            return_value=None,
        ) as impl:
            calendar_subscription.download_staff_calendar_subscription(token="token-1")

        impl.assert_called_once_with(token="token-1")

    def test_website_route_delegates_to_schedule_owner(self):
        with patch(
            "ifitwala_ed.schedule.api.calendar.subscription.serve_staff_calendar_subscription",
            return_value=None,
        ) as impl:
            calendar_subscription.serve_staff_calendar_subscription("token-1")

        impl.assert_called_once_with("token-1")
