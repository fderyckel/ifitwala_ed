# Copyright (c) 2024, fdR and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school


class TestCourse(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_publishing_course_prepares_school_profile_and_catalog_page(self):
        organization = make_organization(prefix="Course Org")
        school = make_school(organization.name, prefix="Course School")
        school.is_published = 1
        school.save(ignore_permissions=True)

        course = frappe.get_doc(
            {
                "doctype": "Course",
                "course_name": f"Public Course {frappe.generate_hash(length=6)}",
                "school": school.name,
                "course_image": "/files/course-hero.jpg",
                "description": "Families can explore how this course develops knowledge and confidence.",
            }
        ).insert(ignore_permissions=True)

        course_plan = frappe.get_doc(
            {
                "doctype": "Course Plan",
                "title": f"Course Plan {frappe.generate_hash(length=4)}",
                "course": course.name,
                "plan_status": "Active",
            }
        ).insert(ignore_permissions=True)

        frappe.get_doc(
            {
                "doctype": "Unit Plan",
                "course_plan": course_plan.name,
                "title": f"Unit One {frappe.generate_hash(length=4)}",
                "is_published": 1,
                "overview": "<p>Students launch with inquiry, discussion, and foundational concepts.</p>",
            }
        ).insert(ignore_permissions=True)
        frappe.get_doc(
            {
                "doctype": "Unit Plan",
                "course_plan": course_plan.name,
                "title": f"Unit Two {frappe.generate_hash(length=4)}",
                "is_published": 1,
                "essential_understanding": "<p>Students deepen understanding through application and reflection.</p>",
            }
        ).insert(ignore_permissions=True)

        course.reload()
        course.is_published = 1
        course.save(ignore_permissions=True)

        profile_name = frappe.db.get_value(
            "Course Website Profile",
            {"course": course.name, "school": school.name},
            "name",
        )
        self.assertTrue(profile_name)

        profile = frappe.get_doc("Course Website Profile", profile_name)
        self.assertEqual(profile.workflow_state, "Draft")
        self.assertEqual(profile.status, "Draft")
        self.assertTrue(bool((profile.course_slug or "").strip()))
        self.assertEqual(profile.hero_image, course.course_image)
        self.assertIn("Families can explore", profile.intro_text)
        self.assertEqual([row.block_type for row in profile.blocks], ["course_intro", "learning_highlights", "cta"])
        self.assertEqual(len(profile.learning_highlights), 2)
        self.assertTrue(bool((profile.seo_profile or "").strip()))

        seo_profile = frappe.get_doc("Website SEO Profile", profile.seo_profile)
        self.assertEqual(seo_profile.meta_title, course.course_name)
        self.assertEqual(
            seo_profile.canonical_url,
            frappe.utils.get_url(f"/schools/{school.website_slug}/courses/{profile.course_slug}"),
        )

        courses_page_name = frappe.db.get_value(
            "School Website Page",
            {"school": school.name, "route": "courses"},
            "name",
        )
        self.assertTrue(courses_page_name)

        courses_page = frappe.get_doc("School Website Page", courses_page_name)
        self.assertIn("course_catalog", [row.block_type for row in courses_page.blocks])
