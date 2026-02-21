# ifitwala_ed/students/doctype/guardian/test_guardian.py

import frappe
from frappe.tests.utils import FrappeTestCase


class TestGuardian(FrappeTestCase):
    pass


class TestGuardianUserCreation(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Guardian")

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_create_guardian_user_assigns_guardian_role(self):
        guardian = self._create_guardian(email=f"test-guardian-{frappe.generate_hash(length=6)}@example.com")

        self.assertFalse(guardian.user)
        self.assertFalse(frappe.db.exists("User", guardian.guardian_email))

        user_name = guardian.create_guardian_user()
        self.assertTrue(frappe.db.exists("User", user_name))

        user = frappe.get_doc("User", user_name)
        roles = [r.role for r in user.roles]
        self.assertIn("Guardian", roles)

        guardian.reload()
        self.assertEqual(guardian.user, user_name)
        self._created.append(("User", user_name))

    def test_create_guardian_user_links_existing_user(self):
        user = self._create_user("existing-guardian", roles=["Guardian"])
        guardian = self._create_guardian(email=user.name)

        result = guardian.create_guardian_user()
        self.assertEqual(result, user.name)

        guardian.reload()
        self.assertEqual(guardian.user, user.name)

    def test_existing_user_gets_guardian_role(self):
        user = self._create_user("existing-no-guardian")
        roles_before = [r.role for r in user.roles]
        self.assertNotIn("Guardian", roles_before)

        guardian = self._create_guardian(email=user.name)
        result = guardian.create_guardian_user()
        self.assertEqual(result, user.name)

        user.reload()
        roles_after = [r.role for r in user.roles]
        self.assertIn("Guardian", roles_after)

        guardian.reload()
        self.assertEqual(guardian.user, user.name)

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _create_user(self, prefix: str, roles: list[str] | None = None):
        roles = roles or []
        for role in roles:
            self._ensure_role(role)
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"{prefix}-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Guardian",
                "last_name": "User",
                "enabled": 1,
                "user_type": "Website User",
                "roles": [{"role": role} for role in roles],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user

    def _create_guardian(self, *, email: str, user: str | None = None):
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Test",
                "guardian_last_name": "Guardian",
                "guardian_email": email,
                "guardian_mobile_phone": "5550000001",
                "user": user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Guardian", guardian.name))
        return guardian


class TestGuardianPortalRouting(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self._created: list[tuple[str, str]] = []
        self._ensure_role("Guardian")

    def tearDown(self):
        frappe.set_user("Administrator")
        for doctype, name in reversed(self._created):
            if frappe.db.exists(doctype, name):
                frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    def test_guardian_created_with_existing_user_assigns_guardian_role(self):
        user = self._create_user("with-user-link")
        guardian = self._create_guardian(email=user.name, user=user.name)

        user.reload()
        self.assertIn("Guardian", [r.role for r in user.roles])

        self.assertEqual(guardian.user, user.name)

    def test_guardian_user_field_update_assigns_guardian_role(self):
        guardian = self._create_guardian(email=f"guardian-update-{frappe.generate_hash(length=6)}@example.com")
        user = self._create_user("added-later")

        guardian.user = user.name
        guardian.save(ignore_permissions=True)

        user.reload()
        self.assertIn("Guardian", [r.role for r in user.roles])

    def test_guardian_does_not_override_staff_roles(self):
        self._ensure_role("Teacher")
        user = self._create_user("staff-guardian", roles=["Teacher"])

        guardian = self._create_guardian(email=user.name, user=user.name)
        user.reload()

        self.assertIn("Teacher", [r.role for r in user.roles])
        self.assertEqual(guardian.user, user.name)

    def _ensure_role(self, role_name: str):
        if frappe.db.exists("Role", role_name):
            return
        role = frappe.get_doc({"doctype": "Role", "role_name": role_name}).insert(ignore_permissions=True)
        self._created.append(("Role", role.name))

    def _create_user(self, prefix: str, roles: list[str] | None = None):
        roles = roles or []
        for role in roles:
            self._ensure_role(role)
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": f"{prefix}-{frappe.generate_hash(length=8)}@example.com",
                "first_name": "Guardian",
                "last_name": "Portal",
                "enabled": 1,
                "user_type": "Website User",
                "roles": [{"role": role} for role in roles],
            }
        ).insert(ignore_permissions=True)
        self._created.append(("User", user.name))
        return user

    def _create_guardian(self, *, email: str, user: str | None = None):
        guardian = frappe.get_doc(
            {
                "doctype": "Guardian",
                "guardian_first_name": "Guardian",
                "guardian_last_name": "Routing",
                "guardian_email": email,
                "guardian_mobile_phone": "5550000002",
                "user": user,
            }
        ).insert(ignore_permissions=True)
        self._created.append(("Guardian", guardian.name))
        return guardian
