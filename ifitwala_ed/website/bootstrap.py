# ifitwala_ed/website/bootstrap.py

import json
import re

import frappe
from frappe.utils import escape_html, strip_html

from ifitwala_ed.website.utils import (
    build_course_profile_url,
    build_program_profile_url,
    normalize_route,
)


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


def _next_available_program_slug(base_slug: str, *, program_name: str) -> str:
    base = _slugify_for_route(base_slug)
    candidate = base
    index = 2
    while frappe.db.exists("Program", {"program_slug": candidate, "name": ["!=", program_name]}):
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def _next_available_course_slug(base_slug: str, *, school_name: str, profile_name: str | None = None) -> str:
    base = _slugify_for_route(base_slug)
    candidate = base
    index = 2
    filters = {"school": school_name, "course_slug": candidate}
    if profile_name:
        filters["name"] = ["!=", profile_name]
    while frappe.db.exists("Course Website Profile", filters):
        candidate = f"{base}-{index}"
        index += 1
        filters = {"school": school_name, "course_slug": candidate}
        if profile_name:
            filters["name"] = ["!=", profile_name]
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


def _full_url(route: str | None) -> str | None:
    route = normalize_route(route or "")
    if not route:
        return None
    return frappe.utils.get_url(route)


def _derive_page_title(*, page, school) -> str:
    title = (getattr(page, "title", None) or "").strip()
    if title:
        return title

    route = (getattr(page, "route", None) or "").strip()
    if route == "/":
        return (getattr(school, "school_name", None) or getattr(school, "name", None) or "").strip()

    last_segment = route.split("/")[-1] if route else ""
    if not last_segment:
        return (getattr(school, "school_name", None) or getattr(school, "name", None) or "").strip()
    return last_segment.replace("-", " ").replace("_", " ").title()


def _ensure_website_seo_profile(
    *,
    profile_name: str | None,
    meta_title: str | None,
    meta_description: str | None,
    og_image: str | None,
    canonical_url: str | None,
) -> tuple[str, bool]:
    if profile_name:
        profile = frappe.get_doc("Website SEO Profile", profile_name)
        is_new = False
    else:
        profile = frappe.new_doc("Website SEO Profile")
        is_new = True

    changed = False
    normalized_meta_title = (meta_title or "").strip()
    normalized_meta_description = (meta_description or "").strip()
    normalized_og_image = (og_image or "").strip()
    normalized_canonical_url = (canonical_url or "").strip()

    defaults = {
        "meta_title": normalized_meta_title,
        "meta_description": normalized_meta_description,
        "og_title": normalized_meta_title,
        "og_description": normalized_meta_description,
        "og_image": normalized_og_image,
        "canonical_url": normalized_canonical_url,
    }

    for fieldname, value in defaults.items():
        if not value:
            continue
        if not (getattr(profile, fieldname, None) or "").strip():
            setattr(profile, fieldname, value)
            changed = True

    if is_new:
        profile.noindex = 0
        profile.insert(ignore_permissions=True)
    elif changed:
        profile.save(ignore_permissions=True)

    return profile.name, bool(is_new or changed)


def _ensure_school_page_seo_profile(*, page, school) -> tuple[str | None, bool]:
    route = (getattr(page, "full_route", None) or "").strip()
    if not route and getattr(school, "website_slug", None):
        route = _school_page_url(
            school_slug=school.website_slug,
            route=getattr(page, "route", None) or "/",
        )

    profile_name, profile_changed = _ensure_website_seo_profile(
        profile_name=getattr(page, "seo_profile", None),
        meta_title=_derive_page_title(page=page, school=school),
        meta_description=(getattr(page, "meta_description", None) or "").strip(),
        og_image=(getattr(school, "school_logo", None) or "").strip(),
        canonical_url=_full_url(route),
    )

    page_changed = False
    if getattr(page, "seo_profile", None) != profile_name:
        frappe.db.set_value("School Website Page", page.name, "seo_profile", profile_name, update_modified=False)
        page.seo_profile = profile_name
        page_changed = True
    return profile_name, bool(profile_changed or page_changed)


def _default_program_intro_text(program) -> str:
    for value in (program.program_overview, program.program_aims, program.description):
        text = (value or "").strip()
        if text:
            return text
    return f"<p>Explore the learning journey offered through {program.program_name or program.name}.</p>"


def _build_program_profile_blocks(*, school, program) -> list[dict]:
    blocks = [
        {
            "block_type": "program_intro",
            "order": 1,
            "props": {
                "heading": program.program_name or program.name,
                "cta_intent": "apply",
            },
        }
    ]

    aims_html = (program.program_aims or "").strip()
    overview_html = (program.program_overview or "").strip()
    if aims_html and aims_html != overview_html:
        blocks.append(
            {
                "block_type": "rich_text",
                "order": 2,
                "props": {
                    "content_html": aims_html,
                    "max_width": "wide",
                },
            }
        )

    blocks.append(
        {
            "block_type": "cta",
            "order": len(blocks) + 1,
            "props": {
                "title": "Interested in this program?",
                "text": "Start the admissions conversation with our team.",
                "button_label": (school.label_cta_inquiry or "").strip() or "Inquire",
                "button_link": _safe_link(school.admissions_inquiry_route, fallback="/apply/inquiry"),
            },
        }
    )
    return blocks


def _ensure_program_profile_seo_profile(*, profile, school, program) -> tuple[str | None, bool]:
    if not (school.website_slug or "").strip() or not (program.program_slug or "").strip():
        return None, False

    description = _trim_meta_text(profile.intro_text or _default_program_intro_text(program))
    profile_name, profile_changed = _ensure_website_seo_profile(
        profile_name=getattr(profile, "seo_profile", None),
        meta_title=(program.program_name or program.name or "").strip(),
        meta_description=description,
        og_image=(profile.hero_image or program.program_image or "").strip(),
        canonical_url=_full_url(
            build_program_profile_url(
                school_slug=school.website_slug,
                program_slug=program.program_slug,
            )
        ),
    )

    linked_changed = False
    if getattr(profile, "seo_profile", None) != profile_name:
        profile.seo_profile = profile_name
        linked_changed = True
    return profile_name, bool(profile_changed or linked_changed)


def _default_course_intro_text(course) -> str:
    description = (course.description or "").strip()
    if description:
        return f"<p>{escape_html(description)}</p>"
    return f"<p>Discover what students experience in {escape_html(course.course_name or course.name)}.</p>"


def _default_course_overview_html(course) -> str:
    description = (course.description or "").strip()
    if description:
        return f"<p>{escape_html(description)}</p>"
    return ""


def _default_course_assessment_summary_html(course) -> str:
    cadence = "across the academic year" if int(course.term_long or 0) == 1 else "across the term"
    return (
        "<p>"
        f"Assessment in this course is designed to support growth {cadence}, "
        "with a balance of feedback, practice, and demonstration of learning."
        "</p>"
    )


def _seed_course_learning_highlights(*, profile, course) -> bool:
    if profile.learning_highlights:
        return False

    rows = frappe.get_all(
        "Learning Unit",
        filters={"course": course.name, "is_published": 1},
        fields=["unit_name", "unit_order", "unit_status", "unit_overview", "essential_understanding"],
        order_by="unit_order asc, unit_name asc",
        limit=6,
    )
    if not rows:
        return False

    for row in rows:
        if (row.get("unit_status") or "").strip() == "Archived":
            continue
        title = (row.unit_name or "").strip()
        if not title:
            continue
        summary_source = row.unit_overview or row.essential_understanding or ""
        profile.append(
            "learning_highlights",
            {
                "title": title,
                "summary": _trim_meta_text(summary_source, limit=220),
                "display_order": row.unit_order,
            },
        )
    return bool(profile.learning_highlights)


def _build_course_profile_blocks(*, school, course, include_highlights: bool) -> list[dict]:
    blocks = [
        {
            "block_type": "course_intro",
            "order": 1,
            "props": {
                "heading": course.course_name or course.name,
                "cta_intent": "inquire",
            },
        }
    ]

    if include_highlights:
        blocks.append(
            {
                "block_type": "learning_highlights",
                "order": 2,
                "props": {
                    "heading": "Learning Highlights",
                },
            }
        )

    blocks.append(
        {
            "block_type": "cta",
            "order": len(blocks) + 1,
            "props": {
                "title": "Questions about this course?",
                "text": "Talk with our admissions team about fit, pathways, and next steps.",
                "button_label": (school.label_cta_inquiry or "").strip() or "Inquire",
                "button_link": _safe_link(school.admissions_inquiry_route, fallback="/apply/inquiry"),
            },
        }
    )
    return blocks


def _ensure_course_profile_seo_profile(*, profile, school, course) -> tuple[str | None, bool]:
    if not (school.website_slug or "").strip() or not (profile.course_slug or "").strip():
        return None, False

    description = _trim_meta_text(profile.intro_text or _default_course_intro_text(course))
    profile_name, profile_changed = _ensure_website_seo_profile(
        profile_name=getattr(profile, "seo_profile", None),
        meta_title=(course.course_name or course.name or "").strip(),
        meta_description=description,
        og_image=(profile.hero_image or course.course_image or "").strip(),
        canonical_url=_full_url(
            build_course_profile_url(
                school_slug=school.website_slug,
                course_slug=profile.course_slug,
            )
        ),
    )

    linked_changed = False
    if getattr(profile, "seo_profile", None) != profile_name:
        profile.seo_profile = profile_name
        linked_changed = True
    return profile_name, bool(profile_changed or linked_changed)


def build_default_staff_showcase_props(*, route: str) -> dict:
    props = {
        "title": "Leadership & Administration",
        "leadership_title": "Academic Leadership",
        "staff_title": "Faculty & Staff",
        "role_profiles": ["Academic Admin"],
        "show_staff_carousel": True,
    }

    if route == "/":
        props.update(
            {
                "description": "Meet the academic leaders and school professionals shaping learning each day.",
                "limit": 4,
                "staff_limit": 8,
            }
        )
        return props

    props.update(
        {
            "description": "Meet the academic leaders, faculty, and staff who shape the character of our school.",
            "limit": 6,
            "staff_limit": 12,
        }
    )
    return props


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
            "props": build_default_staff_showcase_props(route="/"),
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
            "props": build_default_staff_showcase_props(route="about"),
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
    return [
        {
            "block_type": "admissions_overview",
            "order": 1,
            "props": {
                "heading": "Admissions",
                "content_html": (
                    f"<p>{school.school_name} welcomes families who value curiosity, care, and growth.</p>"
                ),
                "max_width": "normal",
            },
        },
        {
            "block_type": "admissions_steps",
            "order": 2,
            "props": {
                "steps": [
                    {
                        "key": "inquire",
                        "title": "Inquire",
                        "description": "Start the conversation.",
                        "icon": "mail",
                    },
                    {
                        "key": "visit",
                        "title": "Visit",
                        "description": "Experience our campus.",
                        "icon": "map",
                    },
                    {
                        "key": "apply",
                        "title": "Apply",
                        "description": "Begin the application.",
                        "icon": "file-text",
                    },
                ],
                "layout": "horizontal",
            },
        },
        {
            "block_type": "admission_cta",
            "order": 3,
            "props": {
                "intent": "inquire",
                "style": "primary",
                "label_override": (school.label_cta_inquiry or "").strip() or "Inquire",
            },
        },
        {
            "block_type": "admission_cta",
            "order": 4,
            "props": {
                "intent": "visit",
                "style": "secondary",
                "label_override": (school.label_cta_roi or "").strip() or "Visit",
            },
        },
        {
            "block_type": "admission_cta",
            "order": 5,
            "props": {
                "intent": "apply",
                "style": "outline",
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


def _build_courses_blocks(*, school) -> list[dict]:
    return [
        {
            "block_type": "hero",
            "order": 1,
            "props": {
                "title": "Courses",
                "subtitle": f"Explore signature courses and learning experiences at {school.school_name}.",
                "images": [],
            },
        },
        {
            "block_type": "course_catalog",
            "order": 2,
            "props": {
                "show_intro": True,
                "show_course_group": True,
                "show_related_programs": True,
                "card_style": "standard",
                "limit": 24,
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
            "page_type": "Admissions",
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

    school = frappe.get_doc("School", school_name)
    page = frappe.new_doc("School Website Page")
    page.school = school_name
    page.route = spec["route"]
    page.page_type = spec.get("page_type") or "Standard"
    page.title = spec["title"]
    page.meta_description = spec["meta_description"]
    page.show_in_navigation = int(spec.get("show_in_navigation") or 0)
    page.navigation_order = spec.get("navigation_order")
    if int(school.is_published or 0) == 1 and (school.website_slug or "").strip():
        page.workflow_state = "Published"
    _append_blocks(page, spec["blocks"])
    page.insert(ignore_permissions=True)
    _ensure_school_page_seo_profile(page=page, school=school)
    return page.name


def _sync_canonical_school_page_publication(*, school, routes: list[str]) -> list[str]:
    if int(school.is_published or 0) != 1 or not (school.website_slug or "").strip():
        return []

    page_names = frappe.get_all(
        "School Website Page",
        filters={"school": school.name, "route": ["in", routes]},
        pluck="name",
    )
    updated_pages = []
    for page_name in page_names:
        page = frappe.get_doc("School Website Page", page_name)
        if page.workflow_state == "Published" and int(page.is_published or 0) == 1:
            continue
        page.workflow_state = "Published"
        page.save(ignore_permissions=True)
        updated_pages.append(page.name)
    return updated_pages


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


def ensure_courses_index_page(*, school_name: str) -> dict:
    """
    Guarantee a school-scoped Courses page that is visible in navigation and
    renders course cards via the course_catalog block.
    """
    school = frappe.get_doc("School", school_name)
    page_name = frappe.db.get_value(
        "School Website Page",
        {"school": school.name, "route": "courses"},
        "name",
    )

    created = False
    updated = False
    if not page_name:
        spec = {
            "route": "courses",
            "title": "Courses",
            "meta_description": "Explore featured courses, descriptions, and learning highlights.",
            "show_in_navigation": 1,
            "navigation_order": 5,
            "blocks": _build_courses_blocks(school=school),
        }
        page_name = _create_page_if_missing(school_name=school.name, spec=spec)
        if not page_name:
            page_name = frappe.db.get_value(
                "School Website Page",
                {"school": school.name, "route": "courses"},
                "name",
            )
        if not page_name:
            frappe.throw(
                f"Unable to resolve Courses page for school {school.name}.",
                frappe.ValidationError,
            )
        created = bool(page_name)
        page = frappe.get_doc("School Website Page", page_name)
    else:
        page = frappe.get_doc("School Website Page", page_name)

    if not page.title:
        page.title = "Courses"
        updated = True

    if int(page.show_in_navigation or 0) != 1:
        page.show_in_navigation = 1
        updated = True

    if page.navigation_order in (None, "", "Null"):
        page.navigation_order = 5
        updated = True

    has_course_catalog = any((row.block_type == "course_catalog") for row in (page.blocks or []))
    if not has_course_catalog:
        next_order = max([int(row.order or row.idx or 0) for row in (page.blocks or [])] or [0]) + 1
        page.append(
            "blocks",
            {
                "block_type": "course_catalog",
                "order": next_order,
                "props": json.dumps(
                    {
                        "show_intro": True,
                        "show_course_group": True,
                        "show_related_programs": True,
                        "card_style": "standard",
                        "limit": 24,
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
    page_specs = _default_page_specs(school=school)
    for spec in page_specs:
        created = _create_page_if_missing(school_name=school.name, spec=spec)
        if created:
            created_pages.append(created)

    repaired_pages = _sync_canonical_school_page_publication(
        school=school,
        routes=[spec["route"] for spec in page_specs],
    )

    page_names = frappe.get_all(
        "School Website Page",
        filters={"school": school.name},
        pluck="name",
    )
    linked_seo_profiles = []
    for page_name in page_names:
        page = frappe.get_doc("School Website Page", page_name)
        profile_name, _profile_changed = _ensure_school_page_seo_profile(page=page, school=school)
        if profile_name:
            linked_seo_profiles.append(profile_name)

    program_names = frappe.get_all(
        "Program Offering",
        filters={"school": school.name},
        pluck="program",
        distinct=True,
    )
    for program_name in program_names:
        if not frappe.db.get_value("Program", program_name, "is_published"):
            continue
        ensure_default_program_website_profiles(program_name=program_name)

    course_names = frappe.get_all(
        "Course",
        filters={"school": school.name, "is_published": 1},
        pluck="name",
    )
    for course_name in course_names:
        ensure_default_course_website_profile(course_name=course_name)

    return {
        "school": school.name,
        "website_slug": school.website_slug,
        "created_pages": created_pages,
        "repaired_pages": repaired_pages,
        "seo_profiles": linked_seo_profiles,
    }


def ensure_default_program_website_profiles(*, program_name: str) -> dict:
    """
    Ensure every offered school gets a draft-ready Program Website Profile with
    starter content and SEO defaults. Existing content is preserved.
    """
    program = frappe.get_doc("Program", program_name)

    updates = {}
    if not (program.program_slug or "").strip():
        updates["program_slug"] = _next_available_program_slug(
            program.program_name or program.name,
            program_name=program.name,
        )

    if updates:
        frappe.db.set_value("Program", program.name, updates, update_modified=False)
        program.reload()

    school_names = frappe.get_all(
        "Program Offering",
        filters={"program": program.name},
        pluck="school",
        distinct=True,
    )

    created_profiles = []
    touched_profiles = []
    for school_name in school_names:
        school = frappe.get_doc("School", school_name)
        profile_name = frappe.db.get_value(
            "Program Website Profile",
            {"program": program.name, "school": school.name},
            "name",
        )

        created = False
        if profile_name:
            profile = frappe.get_doc("Program Website Profile", profile_name)
        else:
            profile = frappe.new_doc("Program Website Profile")
            profile.school = school.name
            profile.program = program.name
            created = True

        changed = False

        if not (profile.hero_image or "").strip() and (program.program_image or "").strip():
            profile.hero_image = program.program_image
            changed = True

        if not (profile.intro_text or "").strip():
            profile.intro_text = _default_program_intro_text(program)
            changed = True

        if not profile.blocks:
            for row in _build_program_profile_blocks(school=school, program=program):
                profile.append(
                    "blocks",
                    {
                        "block_type": row["block_type"],
                        "order": row["order"],
                        "props": json.dumps(row["props"]),
                        "is_enabled": 1,
                    },
                )
            changed = True

        _profile_name, seo_changed = _ensure_program_profile_seo_profile(
            profile=profile,
            school=school,
            program=program,
        )
        if seo_changed:
            changed = True

        if created:
            profile.insert(ignore_permissions=True)
            created_profiles.append(profile.name)
        elif changed:
            profile.save(ignore_permissions=True)

        touched_profiles.append(profile.name)

    return {
        "program": program.name,
        "program_slug": program.program_slug,
        "profiles": touched_profiles,
        "created_profiles": created_profiles,
    }


def ensure_default_course_website_profile(*, course_name: str) -> dict:
    """
    Ensure a published Course gets a draft-ready Course Website Profile with
    starter content, curated highlights, and SEO defaults. Existing content is preserved.
    """
    course = frappe.get_doc("Course", course_name)
    school_name = (course.school or "").strip()
    if not school_name or int(course.is_published or 0) != 1:
        return {
            "course": course.name,
            "course_slug": None,
            "profile": None,
            "created": False,
        }

    school = frappe.get_doc("School", school_name)
    profile_name = frappe.db.get_value(
        "Course Website Profile",
        {"course": course.name, "school": school.name},
        "name",
    )

    created = False
    if profile_name:
        profile = frappe.get_doc("Course Website Profile", profile_name)
    else:
        profile = frappe.new_doc("Course Website Profile")
        profile.school = school.name
        profile.course = course.name
        created = True

    changed = False

    if not (profile.course_slug or "").strip():
        profile.course_slug = _next_available_course_slug(
            course.course_name or course.name,
            school_name=school.name,
            profile_name=profile.name,
        )
        changed = True

    if not (profile.hero_image or "").strip() and (course.course_image or "").strip():
        profile.hero_image = course.course_image
        changed = True

    if not (profile.intro_text or "").strip():
        profile.intro_text = _default_course_intro_text(course)
        changed = True

    if not (profile.overview_html or "").strip():
        overview_html = _default_course_overview_html(course)
        if overview_html:
            profile.overview_html = overview_html
            changed = True

    if not (profile.assessment_summary_html or "").strip():
        profile.assessment_summary_html = _default_course_assessment_summary_html(course)
        changed = True

    if _seed_course_learning_highlights(profile=profile, course=course):
        changed = True

    if not profile.blocks:
        for row in _build_course_profile_blocks(
            school=school,
            course=course,
            include_highlights=bool(profile.learning_highlights),
        ):
            profile.append(
                "blocks",
                {
                    "block_type": row["block_type"],
                    "order": row["order"],
                    "props": json.dumps(row["props"]),
                    "is_enabled": 1,
                },
            )
        changed = True

    _profile_name, seo_changed = _ensure_course_profile_seo_profile(
        profile=profile,
        school=school,
        course=course,
    )
    if seo_changed:
        changed = True

    if created:
        profile.insert(ignore_permissions=True)
    elif changed:
        profile.save(ignore_permissions=True)

    ensure_courses_index_page(school_name=school.name)

    return {
        "course": course.name,
        "course_slug": profile.course_slug,
        "profile": profile.name,
        "created": created,
    }
