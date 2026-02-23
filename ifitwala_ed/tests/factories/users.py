# ifitwala_ed/tests/factories/users.py

from __future__ import annotations

import frappe


def make_user(email: str | None = None, roles: list[str] | None = None):
    user_email = email or f"user-{frappe.generate_hash(length=6)}@ifitwala.test"
    user = frappe.get_doc(
        {
            "doctype": "User",
            "email": user_email,
            "first_name": "Ifitwala",
            "last_name": "Tester",
            "send_welcome_email": 0,
        }
    )
    user.insert(ignore_permissions=True)

    for role in roles or []:
        if not frappe.db.exists("Has Role", {"parent": user.name, "role": role}):
            user.append("roles", {"role": role})
    if roles:
        user.save(ignore_permissions=True)

    return user
