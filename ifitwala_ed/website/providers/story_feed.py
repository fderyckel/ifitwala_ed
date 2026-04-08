# ifitwala_ed/website/providers/story_feed.py

from __future__ import annotations

import frappe
from frappe.utils import getdate
from frappe.utils.caching import redis_cache

from ifitwala_ed.website.utils import build_story_url, parse_props, truncate_text

DEFAULT_TITLE = "Stories & News"


def _normalize_limit(value) -> int:
    try:
        return max(int(value or 3), 1)
    except (TypeError, ValueError):
        return 3


def _extract_story_excerpt(story_name: str) -> str | None:
    story = frappe.get_doc("Website Story", story_name)
    for row in story.blocks or []:
        if not int(getattr(row, "is_enabled", 0) or 0):
            continue
        props = parse_props(getattr(row, "props", None))
        for key in ("content_html", "subtitle", "description", "answer_html"):
            value = truncate_text(str(props.get(key) or ""), 180)
            if value:
                return value
    return None


@redis_cache(ttl=1800)
def _get_story_rows(school_name: str, school_slug: str, limit: int, show_excerpt: bool) -> list[dict[str, object]]:
    rows = frappe.get_all(
        "Website Story",
        filters={"school": school_name, "status": "Published"},
        fields=["name", "title", "slug", "publish_date", "tags"],
        order_by="publish_date desc, modified desc",
        limit=limit,
    )

    stories = []
    for row in rows:
        story = {
            "title": (row.get("title") or "").strip(),
            "url": build_story_url(
                school_slug=school_slug,
                story_slug=row.get("slug"),
            ),
            "publish_date": str(getdate(row.get("publish_date"))) if row.get("publish_date") else None,
            "tags": [tag.strip() for tag in str(row.get("tags") or "").split(",") if tag.strip()],
        }
        if show_excerpt:
            story["excerpt"] = _extract_story_excerpt(row.get("name"))
        stories.append(story)
    return stories


def invalidate_story_feed_cache(*_args, **_kwargs):
    clear_cache = getattr(_get_story_rows, "clear_cache", None)
    if callable(clear_cache):
        clear_cache()


def get_context(*, school, page, block_props):
    limit = _normalize_limit(block_props.get("limit"))
    show_excerpt = bool(block_props.get("show_excerpt", True))
    stories = _get_story_rows(
        school_name=school.name,
        school_slug=school.website_slug,
        limit=limit,
        show_excerpt=show_excerpt,
    )

    return {
        "data": {
            "title": (block_props.get("title") or "").strip() or DEFAULT_TITLE,
            "description": (block_props.get("description") or "").strip() or None,
            "stories": stories,
            "has_stories": bool(stories),
            "index_url": f"/schools/{school.website_slug}/stories",
            "show_excerpt": show_excerpt,
        }
    }
