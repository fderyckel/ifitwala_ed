# ifitwala_ed/school_site/doctype/course_website_profile/test_course_website_profile.py

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.school_site.doctype.course_website_profile.course_website_profile import (
    compute_course_profile_status,
    normalize_workflow_state,
)


class TestCourseWebsiteProfile(FrappeTestCase):
    def test_workflow_state_normalization_rejects_invalid_state(self):
        with self.assertRaises(frappe.ValidationError):
            normalize_workflow_state("Invalid State")

    def test_course_profile_status_requires_workflow_published(self):
        status = compute_course_profile_status(
            school_is_public=True,
            course_is_published=True,
            course_scope_matches_school=True,
            has_course_slug=True,
            workflow_state="Approved",
        )
        self.assertEqual(status, "Draft")

    def test_course_profile_status_requires_school_and_course_readiness(self):
        status = compute_course_profile_status(
            school_is_public=False,
            course_is_published=False,
            course_scope_matches_school=False,
            has_course_slug=False,
            workflow_state="Published",
        )
        self.assertEqual(status, "Draft")

    def test_course_profile_status_respects_publication_window(self):
        status = compute_course_profile_status(
            school_is_public=True,
            course_is_published=True,
            course_scope_matches_school=True,
            has_course_slug=True,
            workflow_state="Published",
            expire_at="2000-01-01 08:00:00",
        )
        self.assertEqual(status, "Draft")
