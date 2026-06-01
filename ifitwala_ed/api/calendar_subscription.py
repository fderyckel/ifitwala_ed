"""Staff calendar subscription public facade and compatibility boundary."""

from __future__ import annotations

import frappe

from ifitwala_ed.schedule.api.calendar import subscription as _implementation


def __getattr__(name: str):
    return getattr(_implementation, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_implementation)))


@frappe.whitelist()
def get_my_staff_calendar_subscription():
    return _implementation.get_my_staff_calendar_subscription()


@frappe.whitelist()
def create_or_get_my_staff_calendar_subscription():
    return _implementation.create_or_get_my_staff_calendar_subscription()


@frappe.whitelist()
def reset_my_staff_calendar_subscription():
    return _implementation.reset_my_staff_calendar_subscription()


def serve_staff_calendar_subscription(token: str | None) -> None:
    return _implementation.serve_staff_calendar_subscription(token)


@frappe.whitelist(allow_guest=True)
def download_staff_calendar_subscription(token: str | None = None) -> None:
    return _implementation.download_staff_calendar_subscription(token=token)


download_staff_calendar_subscription.allow_guest = True


__all__ = [
    "get_my_staff_calendar_subscription",
    "create_or_get_my_staff_calendar_subscription",
    "reset_my_staff_calendar_subscription",
    "serve_staff_calendar_subscription",
    "download_staff_calendar_subscription",
]
