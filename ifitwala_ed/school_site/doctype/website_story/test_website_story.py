from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website.permissions import (
    get_website_story_content_owner_options,
    is_eligible_website_story_content_owner,
    validate_website_story_content_owner,
)


class TestWebsiteStoryContentOwner(FrappeTestCase):
    def test_rejects_portal_website_user(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="portal@example.com", enabled=1, user_type="Website User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Marketing User"]),
        ):
            self.assertFalse(is_eligible_website_story_content_owner(user="portal@example.com", school="Test School"))

    def test_rejects_academic_admin_even_with_school_scope(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="academic@example.com", enabled=1, user_type="System User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Academic Admin"]),
            patch(
                "ifitwala_ed.website.permissions._get_user_school_scope",
                return_value=["Test School"],
            ),
        ):
            self.assertFalse(is_eligible_website_story_content_owner(user="academic@example.com", school="Test School"))

    def test_requires_school_scope_for_marketing_user(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="marketing@example.com", enabled=1, user_type="System User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Marketing User"]),
            patch(
                "ifitwala_ed.website.permissions._get_user_school_scope",
                return_value=["Other School"],
            ),
        ):
            self.assertFalse(
                is_eligible_website_story_content_owner(user="marketing@example.com", school="Test School")
            )

    def test_allows_scoped_marketing_user(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="marketing@example.com", enabled=1, user_type="System User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Marketing User"]),
            patch(
                "ifitwala_ed.website.permissions._get_user_school_scope",
                return_value=["Test School", "Child School"],
            ),
        ):
            self.assertTrue(is_eligible_website_story_content_owner(user="marketing@example.com", school="Test School"))

    def test_allows_system_manager_without_school_scope(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="sysmgr@example.com", enabled=1, user_type="System User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["System Manager"]),
            patch("ifitwala_ed.website.permissions._get_user_school_scope", return_value=[]),
        ):
            self.assertTrue(is_eligible_website_story_content_owner(user="sysmgr@example.com", school="Test School"))

    def test_validate_raises_for_invalid_content_owner(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="portal@example.com", enabled=1, user_type="Website User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Marketing User"]),
        ):
            with self.assertRaises(frappe.ValidationError):
                validate_website_story_content_owner(user="portal@example.com", school="Test School")

    def test_query_returns_only_eligible_internal_editors(self):
        def fake_get_all(doctype, **kwargs):
            if doctype == "Has Role":
                return ["marketing@example.com", "outsider@example.com", "portal@example.com"]
            if doctype == "User":
                return [
                    frappe._dict(name="marketing@example.com", full_name="Marketing User"),
                    frappe._dict(name="outsider@example.com", full_name="Outside Editor"),
                    frappe._dict(name="portal@example.com", full_name="Portal User"),
                ]
            raise AssertionError(f"Unexpected doctype lookup: {doctype}")

        def fake_get_value(doctype, name, fields, as_dict=False):
            payloads = {
                "marketing@example.com": frappe._dict(enabled=1, user_type="System User"),
                "outsider@example.com": frappe._dict(enabled=1, user_type="System User"),
                "portal@example.com": frappe._dict(enabled=1, user_type="Website User"),
            }
            return payloads.get(name)

        def fake_get_roles(user=None):
            role_map = {
                "marketing@example.com": ["Marketing User"],
                "outsider@example.com": ["Marketing User"],
                "portal@example.com": ["Marketing User"],
            }
            return role_map.get(user, [])

        def fake_scope(user=None):
            scope_map = {
                "marketing@example.com": ["Test School"],
                "outsider@example.com": ["Other School"],
                "portal@example.com": ["Test School"],
            }
            return scope_map.get(user, [])

        with (
            patch("ifitwala_ed.website.permissions.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.website.permissions.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", side_effect=fake_get_roles),
            patch("ifitwala_ed.website.permissions._get_user_school_scope", side_effect=fake_scope),
        ):
            rows = get_website_story_content_owner_options(
                "User",
                "marketing",
                "name",
                0,
                20,
                {"school": "Test School"},
            )

        self.assertEqual(rows, [("marketing@example.com", "Marketing User")])
