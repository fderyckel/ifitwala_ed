from __future__ import annotations

import json

import frappe
from frappe.tests.utils import FrappeTestCase

from ifitwala_ed.tests.factories.organization import make_organization, make_school
from ifitwala_ed.website.providers import story_feed as provider


class TestStoryFeedProvider(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        provider.invalidate_story_feed_cache()

    def tearDown(self):
        provider.invalidate_story_feed_cache()

    def test_story_feed_returns_only_published_school_stories(self):
        organization = make_organization(prefix="Story Feed Org")
        school = make_school(organization.name, prefix="Story Feed School")
        school.website_slug = f"story-{frappe.generate_hash(length=6)}"
        school.is_published = 1
        school.save(ignore_permissions=True)

        _make_story(
            school=school.name,
            title="Open House",
            slug="open-house",
            workflow_state="Published",
            publish_date="2026-04-01",
        )
        _make_story(
            school=school.name,
            title="Draft Story",
            slug="draft-story",
            workflow_state="Approved",
            publish_date="2026-04-02",
        )

        payload = provider.get_context(
            school=frappe.get_doc("School", school.name),
            page=frappe._dict(),
            block_props={"title": "Stories", "limit": 3, "show_excerpt": True},
        )

        self.assertEqual(len(payload["data"]["stories"]), 1)
        story = payload["data"]["stories"][0]
        self.assertEqual(story["title"], "Open House")
        self.assertEqual(story["url"], f"/schools/{school.website_slug}/stories/open-house")
        self.assertIn("community visit", story["excerpt"])
        self.assertEqual(payload["data"]["index_url"], f"/schools/{school.website_slug}/stories")


def _make_story(*, school: str, title: str, slug: str, workflow_state: str, publish_date: str):
    return frappe.get_doc(
        {
            "doctype": "Website Story",
            "school": school,
            "title": title,
            "slug": slug,
            "publish_date": publish_date,
            "workflow_state": workflow_state,
            "blocks": [
                {
                    "block_type": "hero",
                    "order": 1,
                    "is_enabled": 1,
                    "props": json.dumps({"title": title}),
                },
                {
                    "block_type": "rich_text",
                    "order": 2,
                    "is_enabled": 1,
                    "props": json.dumps(
                        {"content_html": "<p>Families joined a community visit and classroom showcase.</p>"}
                    ),
                },
            ],
        }
    ).insert(ignore_permissions=True)
