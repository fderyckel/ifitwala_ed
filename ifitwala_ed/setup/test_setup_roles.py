# ifitwala_ed/setup/test_setup_roles.py

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.setup.setup import create_roles_with_homepage


class TestSetupRoles(FrappeTestCase):
    def test_create_roles_with_homepage_normalizes_academic_staff_home_page(self):
        if frappe.db.exists("Role", "Academic Staff"):
            role = frappe.get_doc("Role", "Academic Staff")
        else:
            role = frappe.get_doc({"doctype": "Role", "role_name": "Academic Staff"}).insert(ignore_permissions=True)

        role.home_page = "/portal/staff"
        role.desk_access = 1
        role.save(ignore_permissions=True)

        create_roles_with_homepage()

        role.reload()
        self.assertEqual(role.home_page, "/hub/staff")
        self.assertEqual(int(role.desk_access or 0), 1)
