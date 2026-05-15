# ifitwala_ed/tests/factories/users.py

from __future__ import annotations

from unittest.mock import patch

import frappe


def _insert_user_without_notifications(user):
    with (
        patch.object(user, "send_password_notification"),
        patch.object(user, "send_welcome_mail_to_user"),
        patch("frappe.core.doctype.user.user.User.send_password_notification"),
        patch("frappe.core.doctype.user.user.User.send_welcome_mail_to_user"),
    ):
        user.insert(ignore_permissions=True)


def _save_user_without_notifications(user):
    with (
        patch.object(user, "send_password_notification"),
        patch.object(user, "send_welcome_mail_to_user"),
        patch("frappe.core.doctype.user.user.User.send_password_notification"),
        patch("frappe.core.doctype.user.user.User.send_welcome_mail_to_user"),
    ):
        user.save(ignore_permissions=True)


def make_user(email: str | None = None, roles: list[str] | None = None):
    user_email = email or f"user-{frappe.generate_hash(length=6)}@ifitwala.test"
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": user_email,
            "first_name": "Ifitwala",
            "last_name": "Tester",
        }
    )
    user.flags.no_welcome_mail = True
    _insert_user_without_notifications(user)

    for role in roles or []:
        if not frappe.db.exists("Has Role", {"parent": user.name, "role": role}):
            user.append("roles", {"role": role})
    if roles:
        _save_user_without_notifications(user)

    return user
