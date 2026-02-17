# ifitwala_ed/website/bootstrap.py

import json
import re

import frappe
from frappe.utils import strip_html

from ifitwala_ed.website.utils import normalize_route


def _slugify_for_route(value: str | None) -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return clean or "school"


def _next_available_school_slug(base_slug: str, *, school_name: str) -> str:
    base = _slugify_for_route(base_slug)
    candidate = base
    index = 2
    while frappe.db.exists("School", {"website_slug": candidate, "name": ["!=", school_name]}):
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def _trim_meta_text(raw_html: str | None, *, limit: int = 160) -> str:
    clean = re.sub(r"\s+", " ", strip_html(raw_html or "")).strip()
    if len(clean) <= limit:
        return clean
    return clean[:limit].rstrip() + "..."


def _safe_link(value: str | None, *, fallback: str) -> str:
    link = (value or "").strip()
    if link.startswith("/") or link.startswith("https://"):
        return link
    return fallback


def _school_page_url(*, school_slug: str, route: str) -> str:
    if route == "/":
        return normalize_route(f"/schools/{school_slug}")
    return normalize_route(f"/schools/{school_slug}/{route}")


def _build_home_blocks(*, school) -> list[dict]:
    admissions_page_url = _school_page_url(school_slug=school.website_slug, route="admissions")
    intro_html = (school.about_snippet or "").strip()
    if not intro_html:
        intro_html = f"<p>Welcome to {school.school_name}.</p>"

    return [
        {
            "block_type": "hero",
            "order": 1,
            "props": {
                "title": school.school_name,
                "subtitle": (school.school_tagline or "").strip() or None,
                "images": [],
                "autoplay": True,
                "interval": 6000,
                "cta_label": "Explore Admissions",
                "cta_link": admissions_page_url,
            },
        },
        {
            "block_type": "rich_text",
            "order": 2,
            "props": {
                "content_html": intro_html,
                "max_width": "normal",
            },
        },
        {
            "block_type": "program_list",
            "order": 3,
            "props": {
                "school_scope": "current",
                "show_intro": True,
                "card_style": "standard",
                "limit": 6,
            },
        },
        {
            "block_type": "leadership",
            "order": 4,
            "props": {
                "title": "Leadership & Administration",
                "roles": ["Head", "Principal"],
                "limit": 6,
            },
        },
        {
            "block_type": "cta",
            "order": 5,
            "props": {
                "title": "Ready to apply?",
                "text": "Start your admissions journey today.",
                "button_label": "Apply Now",
                "button_link": _safe_link(
                    school.admissions_apply_route,
                    fallback=admissions_page_url,
                ),
            },
        },
    ]


def _build_about_blocks(*, school) -> list[dict]:
    admissions_page_url = _school_page_url(school_slug=school.website_slug, route="admissions")
    content_html = (school.more_info or "").strip() or (school.about_snippet or "").strip()
    if not content_html:
        content_html = (
            f"<h2>About {school.school_name}</h2>"
            "<p>We are building a learning community rooted in curiosity, care, and growth.</p>"
        )

    return [
        {
            "block_type": "hero",
            "order": 1,
            "props": {
                "title": f"About {school.school_name}",
                "subtitle": (school.school_tagline or "").strip() or None,
                "images": [],
            },
        },
        {
            "block_type": "rich_text",
            "order": 2,
            "props": {
                "content_html": content_html,
                "max_width": "wide",
            },
        },
        {
            "block_type": "leadership",
            "order": 3,
            "props": {
                "title": "Leadership & Administration",
                "roles": ["Head", "Principal"],
                "limit": 12,
            },
        },
        {
            "block_type": "cta",
            "order": 4,
            "props": {
                "title": "Questions about enrollment?",
                "text": "Our admissions team is ready to support your family.",
                "button_label": "Admissions",
                "button_link": admissions_page_url,
            },
        },
    ]


def _build_admissions_blocks(*, school) -> list[dict]:
    apply_link = _safe_link(school.admissions_apply_route, fallback="/admissions")
    inquiry_link = _safe_link(school.admissions_inquiry_route, fallback="/apply/inquiry")

    return [
        {
            "block_type": "hero",
            "order": 1,
            "props": {
                "title": "Admissions",
                "subtitle": "A clear, supportive application process.",
                "images": [],
                "cta_label": "Start Application",
                "cta_link": apply_link,
            },
        },
        {
            "block_type": "rich_text",
            "order": 2,
            "props": {
                "content_html": (
                    "<ol>"
                    "<li>Submit an inquiry</li>"
                    "<li>Schedule a visit</li>"
                    "<li>Complete application steps</li>"
                    "<li>Receive admission decision</li>"
                    "</ol>"
                ),
                "max_width": "narrow",
            },
        },
        {
            "block_type": "program_list",
            "order": 3,
            "props": {
                "school_scope": "current",
                "show_intro": False,
                "card_style": "standard",
                "limit": 6,
            },
        },
        {
            "block_type": "cta",
            "order": 4,
            "props": {
                "title": "Need help deciding?",
                "text": "Speak with our admissions team and ask any question.",
                "button_label": "Contact Admissions",
                "button_link": inquiry_link,
            },
        },
    ]


def _build_programs_blocks(*, school) -> list[dict]:
    return [
        {
            "block_type": "hero",
            "order": 1,
            "props": {
                "title": "Programs",
                "subtitle": f"Explore the programs offered at {school.school_name}.",
                "images": [],
            },
        },
        {
            "block_type": "program_list",
            "order": 2,
            "props": {
                "school_scope": "current",
                "show_intro": True,
                "card_style": "standard",
                "limit": 12,
            },
        },
    ]


def _default_page_specs(*, school) -> list[dict]:
    home_meta = _trim_meta_text(school.about_snippet or school.more_info)
    about_meta = _trim_meta_text(school.more_info or school.about_snippet)
    admissions_meta = "Admissions information, steps, and application links."
    programs_meta = "Explore available academic programs and pathways."

    return [
        {
            "route": "/",
            "title": school.school_name,
            "meta_description": home_meta,
            "show_in_navigation": 1,
            "navigation_order": 1,
            "blocks": _build_home_blocks(school=school),
        },
        {
            "route": "about",
            "title": "About Us",
            "meta_description": about_meta,
            "show_in_navigation": 1,
            "navigation_order": 2,
            "blocks": _build_about_blocks(school=school),
        },
        {
            "route": "admissions",
            "title": "Admissions",
            "meta_description": admissions_meta,
            "show_in_navigation": 1,
            "navigation_order": 3,
            "blocks": _build_admissions_blocks(school=school),
        },
        {
            "route": "programs",
            "title": "Programs",
            "meta_description": programs_meta,
            "show_in_navigation": 1,
            "navigation_order": 4,
            "blocks": _build_programs_blocks(school=school),
        },
    ]


def _append_blocks(page, block_specs: list[dict]):
    for row in block_specs:
        page.append(
            "blocks",
            {
                "block_type": row["block_type"],
                "order": row["order"],
                "props": json.dumps(row["props"]),
                "is_enabled": 1,
            },
        )


def _create_page_if_missing(*, school_name: str, spec: dict) -> str | None:
    existing = frappe.db.get_value(
        "School Website Page",
        {"school": school_name, "route": spec["route"]},
        "name",
    )
    if existing:
        return None

    page = frappe.new_doc("School Website Page")
    page.school = school_name
    page.route = spec["route"]
    page.page_type = "Standard"
    page.title = spec["title"]
    page.meta_description = spec["meta_description"]
    page.show_in_navigation = int(spec.get("show_in_navigation") or 0)
    page.navigation_order = spec.get("navigation_order")
    _append_blocks(page, spec["blocks"])
    page.insert(ignore_permissions=True)
    return page.name


def ensure_programs_index_page(*, school_name: str) -> dict:
    """
    Guarantee a school-scoped Programs page that is visible in navigation and
    renders program cards via the program_list block.
    """
    school = frappe.get_doc("School", school_name)
    page_name = frappe.db.get_value(
        "School Website Page",
        {"school": school.name, "route": "programs"},
        "name",
    )

    created = False
    updated = False
    if not page_name:
        spec = {
            "route": "programs",
            "title": "Programs",
            "meta_description": "Explore available academic programs and pathways.",
            "show_in_navigation": 1,
            "navigation_order": 4,
            "blocks": _build_programs_blocks(school=school),
        }
        page_name = _create_page_if_missing(school_name=school.name, spec=spec)
        if not page_name:
            page_name = frappe.db.get_value(
                "School Website Page",
                {"school": school.name, "route": "programs"},
                "name",
            )
        if not page_name:
            frappe.throw(
                f"Unable to resolve Programs page for school {school.name}.",
                frappe.ValidationError,
            )
        created = bool(page_name)
        page = frappe.get_doc("School Website Page", page_name)
    else:
        page = frappe.get_doc("School Website Page", page_name)

    if not page.title:
        page.title = "Programs"
        updated = True

    if int(page.show_in_navigation or 0) != 1:
        page.show_in_navigation = 1
        updated = True

    if page.navigation_order in (None, "", "Null"):
        page.navigation_order = 4
        updated = True

    has_program_list = any((row.block_type == "program_list") for row in (page.blocks or []))
    if not has_program_list:
        next_order = max([int(row.order or row.idx or 0) for row in (page.blocks or [])] or [0]) + 1
        page.append(
            "blocks",
            {
                "block_type": "program_list",
                "order": next_order,
                "props": json.dumps(
                    {
                        "school_scope": "current",
                        "show_intro": True,
                        "card_style": "standard",
                        "limit": 12,
                    }
                ),
                "is_enabled": 1,
            },
        )
        updated = True

    if updated:
        page.save(ignore_permissions=True)

    return {
        "school": school.name,
        "page": page.name,
        "full_route": page.full_route,
        "created": created,
        "updated": updated,
    }


def _ensure_default_school_for_organization(*, school):
    organization = (school.organization or "").strip()
    if not organization:
        return

    current = frappe.db.get_value("Organization", organization, "default_website_school")
    if current:
        return

    frappe.db.set_value(
        "Organization",
        organization,
        "default_website_school",
        school.name,
        update_modified=False,
    )


def ensure_default_school_website(*, school_name: str, set_default_organization: bool = True) -> dict:
    """
    Ensure a school has a web identity and the default website pages.
    Idempotent: existing pages are preserved.
    """
    school = frappe.get_doc("School", school_name)

    updates = {}
    if not (school.website_slug or "").strip():
        updates["website_slug"] = _next_available_school_slug(
            school.abbr or school.school_name or school.name,
            school_name=school.name,
        )
    if not int(school.is_published or 0):
        updates["is_published"] = 1

    if updates:
        for key, value in updates.items():
            setattr(school, key, value)
        school.save(ignore_permissions=True)
        school = frappe.get_doc("School", school_name)

    if set_default_organization:
        _ensure_default_school_for_organization(school=school)

    created_pages = []
    for spec in _default_page_specs(school=school):
        created = _create_page_if_missing(school_name=school.name, spec=spec)
        if created:
            created_pages.append(created)

    return {
        "school": school.name,
        "website_slug": school.website_slug,
        "created_pages": created_pages,
    }
