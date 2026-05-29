from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.website.permissions import (
    get_school_website_page_content_owner_options,
    get_website_story_content_owner_options,
    is_eligible_school_website_page_content_owner,
    is_eligible_website_story_content_owner,
    validate_school_website_page_content_owner,
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


class TestSchoolWebsitePageContentOwner(FrappeTestCase):
    def test_rejects_student_and_guardian_style_portal_users(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="student@example.com", enabled=1, user_type="Website User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Student"]),
        ):
            self.assertFalse(
                is_eligible_school_website_page_content_owner(user="student@example.com", school="Test School")
            )

    def test_allows_scoped_academic_assistant(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="assistant@example.com", enabled=1, user_type="System User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Academic Assistant"]),
            patch(
                "ifitwala_ed.website.permissions._get_user_school_scope",
                return_value=["Test School", "Child School"],
            ),
        ):
            self.assertTrue(
                is_eligible_school_website_page_content_owner(user="assistant@example.com", school="Test School")
            )

    def test_rejects_unlisted_system_user_role(self):
        with (
            patch(
                "ifitwala_ed.website.permissions.frappe.db.get_value",
                return_value=frappe._dict(name="teacher@example.com", enabled=1, user_type="System User"),
            ),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", return_value=["Instructor"]),
            patch(
                "ifitwala_ed.website.permissions._get_user_school_scope",
                return_value=["Test School"],
            ),
        ):
            with self.assertRaises(frappe.ValidationError):
                validate_school_website_page_content_owner(user="teacher@example.com", school="Test School")

    def test_query_returns_only_allowed_role_scoped_system_users(self):
        def fake_get_all(doctype, **kwargs):
            if doctype == "Has Role":
                self.assertEqual(
                    set(kwargs["filters"]["role"][1]),
                    {
                        "Website Manager",
                        "Academic Admin",
                        "Academic Assistant",
                        "Admission Officer",
                        "Admission Manager",
                        "Marketing User",
                        "Marketing Manager",
                    },
                )
                return [
                    "assistant@example.com",
                    "guardian@example.com",
                    "marketing-manager@example.com",
                    "teacher@example.com",
                    "outsider@example.com",
                ]
            if doctype == "User":
                return [
                    frappe._dict(name="assistant@example.com", full_name="Academic Assistant"),
                    frappe._dict(name="guardian@example.com", full_name="Guardian User"),
                    frappe._dict(name="marketing-manager@example.com", full_name="Marketing Manager"),
                    frappe._dict(name="teacher@example.com", full_name="Teacher User"),
                    frappe._dict(name="outsider@example.com", full_name="Outside User"),
                ]
            raise AssertionError(f"Unexpected doctype lookup: {doctype}")

        def fake_get_value(doctype, name, fields, as_dict=False):
            payloads = {
                "assistant@example.com": frappe._dict(enabled=1, user_type="System User"),
                "guardian@example.com": frappe._dict(enabled=1, user_type="Website User"),
                "marketing-manager@example.com": frappe._dict(enabled=1, user_type="System User"),
                "teacher@example.com": frappe._dict(enabled=1, user_type="System User"),
                "outsider@example.com": frappe._dict(enabled=1, user_type="System User"),
            }
            return payloads.get(name)

        def fake_get_roles(user=None):
            role_map = {
                "assistant@example.com": ["Academic Assistant"],
                "guardian@example.com": ["Guardian"],
                "marketing-manager@example.com": ["Marketing Manager"],
                "teacher@example.com": ["Instructor"],
                "outsider@example.com": ["Admission Officer"],
            }
            return role_map.get(user, [])

        def fake_scope(user=None):
            scope_map = {
                "assistant@example.com": ["Test School"],
                "guardian@example.com": ["Test School"],
                "marketing-manager@example.com": ["Test School"],
                "teacher@example.com": ["Test School"],
                "outsider@example.com": ["Other School"],
            }
            return scope_map.get(user, [])

        with (
            patch("ifitwala_ed.website.permissions.frappe.get_all", side_effect=fake_get_all),
            patch("ifitwala_ed.website.permissions.frappe.db.get_value", side_effect=fake_get_value),
            patch("ifitwala_ed.website.permissions.frappe.get_roles", side_effect=fake_get_roles),
            patch("ifitwala_ed.website.permissions._get_user_school_scope", side_effect=fake_scope),
        ):
            rows = get_school_website_page_content_owner_options(
                "User",
                "",
                "name",
                0,
                20,
                {"school": "Test School"},
            )

        self.assertEqual(
            rows,
            [
                ("assistant@example.com", "Academic Assistant"),
                ("marketing-manager@example.com", "Marketing Manager"),
            ],
        )
