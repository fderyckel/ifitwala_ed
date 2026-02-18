# Copyright (c) 2024, François de Ryckel and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestGuardian(FrappeTestCase):
    pass


class TestGuardianUserCreation(FrappeTestCase):
    """Test guardian user creation and portal routing."""

    def test_create_guardian_user_sets_home_page(self):
        """Creating a guardian user should set their home_page to /portal/guardian."""
        # Create a guardian without a user first
        guardian = frappe.new_doc("Guardian")
        guardian.guardian_first_name = "Test"
        guardian.guardian_last_name = "Guardian Portal"
        guardian.guardian_email = "test_guardian_portal@example.com"
        guardian.save()

        # Verify no user exists yet
        self.assertFalse(guardian.user)
        self.assertFalse(frappe.db.exists("User", guardian.guardian_email))

        # Create the user via the guardian method
        user_name = guardian.create_guardian_user()

        # Verify user was created
        self.assertTrue(frappe.db.exists("User", user_name))
        user = frappe.get_doc("User", user_name)

        # Verify Guardian role was assigned
        roles = [r.role for r in user.roles]
        self.assertIn("Guardian", roles)

        # MOST IMPORTANT: Verify home_page is set to /portal/guardian for automatic portal routing
        self.assertEqual(user.home_page, "/portal/guardian")

        # Verify guardian record was updated with user link
        guardian.reload()
        self.assertEqual(guardian.user, user_name)

        # Cleanup
        frappe.delete_doc("Guardian", guardian.name, force=True)
        frappe.delete_doc("User", user_name, force=True)

    def test_create_guardian_user_links_existing_user(self):
        """If user already exists, it should be linked and home_page set."""
        # Create user first
        user = frappe.new_doc("User")
        user.email = "existing_guardian_user@example.com"
        user.first_name = "Existing"
        user.last_name = "Guardian"
        user.enabled = 1
        user.add_roles("Guardian")
        user.save()

        # Create guardian pointing to same email
        guardian = frappe.new_doc("Guardian")
        guardian.guardian_first_name = "Existing"
        guardian.guardian_last_name = "Guardian"
        guardian.guardian_email = user.email
        guardian.save()

        # Try to create user - should link existing
        result = guardian.create_guardian_user()

        # Should return existing user name
        self.assertEqual(result, user.email)

        # Guardian should be linked
        guardian.reload()
        self.assertEqual(guardian.user, user.email)

        # Cleanup
        frappe.delete_doc("Guardian", guardian.name, force=True)
        frappe.delete_doc("User", user.email, force=True)

    def test_existing_user_gets_home_page_and_role(self):
        """Existing users without Guardian role or home_page should get both set."""
        # Create a user WITHOUT Guardian role and WITHOUT home_page
        user = frappe.new_doc("User")
        user.email = "existing_user_no_guardian@example.com"
        user.first_name = "NoGuardian"
        user.last_name = "Role"
        user.enabled = 1
        user.user_type = "Website User"
        # Intentionally NOT adding Guardian role
        user.save()

        # Verify initial state
        user_roles = [r.role for r in user.roles]
        self.assertNotIn("Guardian", user_roles)
        self.assertNotEqual(user.home_page, "/portal/guardian")

        # Create guardian and link to existing user
        guardian = frappe.new_doc("Guardian")
        guardian.guardian_first_name = "NoGuardian"
        guardian.guardian_last_name = "Role"
        guardian.guardian_email = user.email
        guardian.save()

        # Create guardian user - should link existing and fix role/home_page
        result = guardian.create_guardian_user()
        self.assertEqual(result, user.email)

        # Reload user to get updated values
        user.reload()

        # Verify Guardian role was added
        user_roles = [r.role for r in user.roles]
        self.assertIn("Guardian", user_roles)

        # MOST IMPORTANT: Verify home_page is set for automatic portal routing
        self.assertEqual(user.home_page, "/portal/guardian")

        # Cleanup
        guardian.reload()
        frappe.delete_doc("Guardian", guardian.name, force=True)
        frappe.delete_doc("User", user.email, force=True)


class TestGuardianPortalRouting(FrappeTestCase):
    """Test automatic portal routing when Guardian is created/updated with linked user."""

    def test_guardian_created_with_existing_user_sets_home_page(self):
        """
        When a Guardian is created with an existing user already linked,
        the user's home_page should be set to /portal/guardian automatically.
        """
        # Create a user first (without Guardian role or home_page)
        user_email = "guardian_with_user_link@example.com"
        user = frappe.new_doc("User")
        user.email = user_email
        user.first_name = "Guardian"
        user.last_name = "WithUserLink"
        user.enabled = 1
        user.user_type = "Website User"
        # Intentionally NOT adding Guardian role or home_page
        user.save()

        # Create guardian with user already linked
        guardian = frappe.new_doc("Guardian")
        guardian.guardian_first_name = "Guardian"
        guardian.guardian_last_name = "WithUserLink"
        guardian.guardian_email = user_email
        guardian.user = user_email  # Link user at creation time
        guardian.save()

        # Reload user to check updates
        user.reload()

        # Verify Guardian role was added
        user_roles = [r.role for r in user.roles]
        self.assertIn("Guardian", user_roles)

        # MOST IMPORTANT: Verify home_page was set automatically
        self.assertEqual(user.home_page, "/portal/guardian")

        # Cleanup
        frappe.delete_doc("Guardian", guardian.name, force=True)
        frappe.delete_doc("User", user_email, force=True)

    def test_guardian_user_field_update_sets_home_page(self):
        """
        When a Guardian's user field is updated to link a new user,
        the new user's home_page should be set to /portal/guardian.
        """
        # Create guardian WITHOUT user first
        guardian = frappe.new_doc("Guardian")
        guardian.guardian_first_name = "Guardian"
        guardian.guardian_last_name = "UserUpdateTest"
        guardian.guardian_email = "guardian_user_update@example.com"
        guardian.save()

        # Verify no user linked
        self.assertFalse(guardian.user)

        # Create a user separately (without home_page)
        user_email = "user_added_later@example.com"
        user = frappe.new_doc("User")
        user.email = user_email
        user.first_name = "User"
        user.last_name = "AddedLater"
        user.enabled = 1
        user.user_type = "Website User"
        # Intentionally NOT setting home_page
        user.save()

        # Verify initial state - no home_page
        self.assertNotEqual(user.home_page, "/portal/guardian")

        # Now update the guardian to link the user
        guardian.user = user_email
        guardian.save()

        # Reload user to check updates
        user.reload()

        # Verify Guardian role was added
        user_roles = [r.role for r in user.roles]
        self.assertIn("Guardian", user_roles)

        # MOST IMPORTANT: Verify home_page was set on user field update
        self.assertEqual(user.home_page, "/portal/guardian")

        # Cleanup
        frappe.delete_doc("Guardian", guardian.name, force=True)
        frappe.delete_doc("User", user_email, force=True)

    def test_guardian_does_not_override_staff_home_page(self):
        """
        When a user has staff roles, their home_page should NOT be overridden
        when linked to a Guardian.
        """
        # Create a user with staff role
        user_email = "staff_guardian@example.com"
        user = frappe.new_doc("User")
        user.email = user_email
        user.first_name = "Staff"
        user.last_name = "Guardian"
        user.enabled = 1
        user.user_type = "System User"
        user.add_roles("Teacher")  # Staff role
        user.save()

        # Set a custom home_page
        frappe.db.set_value("User", user_email, "home_page", "/app", update_modified=False)

        # Create guardian with this user linked
        guardian = frappe.new_doc("Guardian")
        guardian.guardian_first_name = "Staff"
        guardian.guardian_last_name = "Guardian"
        guardian.guardian_email = user_email
        guardian.user = user_email
        guardian.save()

        # Reload user to check
        user.reload()

        # Verify staff role is still present
        user_roles = [r.role for r in user.roles]
        self.assertIn("Teacher", user_roles)

        # IMPORTANT: home_page should NOT be changed for staff
        self.assertEqual(user.home_page, "/app")

        # Cleanup
        frappe.delete_doc("Guardian", guardian.name, force=True)
        frappe.delete_doc("User", user_email, force=True)
