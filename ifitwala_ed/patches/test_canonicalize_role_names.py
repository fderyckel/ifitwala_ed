from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.patches.canonicalize_role_names import execute


class TestCanonicalizeRoleNames(FrappeTestCase):
    def test_execute_merges_legacy_roles_and_updates_role_links(self):
        if frappe.db.exists("User", "legacy-role-user@example.com"):
            frappe.delete_doc("User", "legacy-role-user@example.com", force=1, ignore_permissions=True)

        for role_name in ("Assistant Admin", "Academic Assistant", "Counsellor", "Counselor"):
            if not frappe.db.exists("Role", role_name):
                frappe.get_doc({"doctype": "Role", "role_name": role_name, "desk_access": 1}).insert(
                    ignore_permissions=True
                )

        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "legacy-role-user@example.com",
                "first_name": "Legacy",
                "last_name": "Role",
                "enabled": 1,
                "new_password": "legacy-role-user@example.com",
                "roles": [
                    {"role": "Assistant Admin"},
                    {"role": "Academic Assistant"},
                    {"role": "Counsellor"},
                ],
            }
        ).insert(ignore_permissions=True)

        settings = frappe.get_single("Referral Settings")
        settings.default_intake_owner_role = "Counsellor"
        settings.save(ignore_permissions=True)

        execute()

        self.assertFalse(frappe.db.exists("Role", "Assistant Admin"))
        self.assertFalse(frappe.db.exists("Role", "Counsellor"))
        self.assertTrue(frappe.db.exists("Role", "Academic Assistant"))
        self.assertTrue(frappe.db.exists("Role", "Counselor"))

        user_roles = frappe.get_all(
            "Has Role",
            filters={"parent": user.name, "role": ["in", ["Academic Assistant", "Counselor"]]},
            pluck="role",
        )
        self.assertEqual(user_roles.count("Academic Assistant"), 1)
        self.assertEqual(user_roles.count("Counselor"), 1)

        settings.reload()
        self.assertEqual(settings.default_intake_owner_role, "Counselor")
