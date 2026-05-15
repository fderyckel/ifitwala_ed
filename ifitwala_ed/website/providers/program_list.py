# ifitwala_ed/website/providers/program_list.py

import frappe
from frappe.utils import cint
from frappe.utils.caching import redis_cache

from ifitwala_ed.website.utils import (
    build_image_variants,
    build_program_profile_url,
    truncate_text,
)


def _normalize_limit(raw_limit):
    if raw_limit is None:
        return 6
    limit = max(cint(raw_limit), 1)
    return limit


@redis_cache(ttl=3600)
def _get_program_profiles(school_scope: str, school_name: str, limit: int):
    schools = []
    if school_scope == "all":
        schools = frappe.get_all(
            "School",
            filters={"is_published": 1, "website_slug": ["!=", ""]},
            fields=["name", "school_name", "website_slug"],
        )
    else:
        schools = frappe.get_all(
            "School",
            filters={"name": school_name},
            fields=["name", "school_name", "website_slug"],
        )

    school_map = {row.name: row for row in schools}
    school_names = [row.name for row in schools]
    if not school_names:
        return []

    offering_rows = frappe.get_all(
        "Program Offering",
        filters={"school": ["in", school_names]},
        fields=["program", "school"],
    )
    offered_pairs = {(row.school, row.program) for row in offering_rows if row.program and row.school}
    if not offered_pairs:
        return []

    program_names = sorted({program for _school, program in offered_pairs if program})
    programs = frappe.get_all(
        "Program",
        filters={
            "name": ["in", program_names],
            "is_published": 1,
            "archive": 0,
        },
        fields=["name", "program_name", "program_image", "program_slug", "is_featured", "lft"],
    )
    if not programs:
        return []

    profiles = frappe.get_all(
        "Program Website Profile",
        filters={"school": ["in", school_names], "program": ["in", [row.name for row in programs]]},
        fields=["name", "program", "school", "hero_image", "intro_text", "status"],
    )

    profile_map = {}
    for profile in profiles:
        profile_map[(profile.school, profile.program)] = profile

    sorted_programs = sorted(
        programs,
        key=lambda row: (-int(row.is_featured or 0), int(row.lft or 0)),
    )
    sorted_school_names = sorted(
        school_names,
        key=lambda name: (
            (getattr(school_map.get(name), "school_name", None) or name or "").lower(),
            name,
        ),
    )

    items = []
    for program in sorted_programs:
        program_title = program.program_name or program.name
        for school_name in sorted_school_names:
            if (school_name, program.name) not in offered_pairs:
                continue

            school = school_map.get(school_name)
            if not school or not school.website_slug:
                continue

            profile = profile_map.get((school_name, program.name))
            has_detail_page = bool(
                profile
                and profile.status == "Published"
                and (program.program_slug or "").strip()
                and (school.website_slug or "").strip()
            )
            url = (
                build_program_profile_url(
                    school_slug=school.website_slug,
                    program_slug=program.program_slug,
                )
                if has_detail_page
                else None
            )
            image_source = (profile.hero_image if profile else None) or program.program_image
            items.append(
                {
                    "title": program_title,
                    "url": url,
                    "intro": truncate_text(profile.intro_text or "", 160) if has_detail_page else None,
                    "image": build_image_variants(image_source, "program"),
                    "school_name": school.school_name if school_scope == "all" else None,
                    "is_teaser": not has_detail_page,
                }
            )
            if len(items) >= limit:
                return items
    return items


def invalidate_program_list_cache():
    clear_cache = getattr(_get_program_profiles, "clear_cache", None)
    if callable(clear_cache):
        clear_cache()


def get_context(*, school, page, block_props):
    """
    Program list - dynamic but crawlable.
    """
    school_scope = block_props.get("school_scope") or "current"
    limit = _normalize_limit(block_props.get("limit"))

    programs = _get_program_profiles(
        school_scope=school_scope,
        school_name=school.name,
        limit=limit,
    )

    return {
        "data": {
            "programs": programs,
            "show_intro": bool(block_props.get("show_intro")),
            "card_style": block_props.get("card_style") or "standard",
            "school_scope": school_scope,
        }
    }
