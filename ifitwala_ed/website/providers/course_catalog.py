# ifitwala_ed/website/providers/course_catalog.py

import frappe
from frappe.utils import cint
from frappe.utils.caching import redis_cache

from ifitwala_ed.website.utils import (
    build_course_profile_url,
    build_image_variants,
    truncate_text,
)


def _normalize_limit(raw_limit):
    if raw_limit is None:
        return 24
    return max(cint(raw_limit), 1)


@redis_cache(ttl=3600)
def _get_school_courses(school_name: str, limit: int):
    school = frappe.db.get_value(
        "School",
        school_name,
        ["name", "school_name", "website_slug"],
        as_dict=True,
    )
    if not school or not school.website_slug:
        return []

    profiles = frappe.get_all(
        "Course Website Profile",
        filters={"school": school_name, "status": "Published"},
        fields=["name", "course", "course_slug", "hero_image", "intro_text"],
        order_by="modified desc",
    )
    if not profiles:
        return []

    course_names = sorted({row.course for row in profiles if row.course})
    courses = frappe.get_all(
        "Course",
        filters={"name": ["in", course_names], "school": school_name, "is_published": 1},
        fields=["name", "course_name", "course_group", "course_image", "term_long"],
    )
    if not courses:
        return []

    course_group_names = sorted({row.course_group for row in courses if row.course_group})
    course_groups = {}
    if course_group_names:
        course_groups = {
            row.name: row
            for row in frappe.get_all(
                "Course Group",
                filters={"name": ["in", course_group_names]},
                fields=["name", "subject_group_image"],
            )
        }

    program_links = frappe.get_all(
        "Program Course",
        filters={"course": ["in", course_names]},
        fields=["parent", "course"],
    )
    linked_program_names = sorted({row.parent for row in program_links if row.parent})
    program_map = {}
    if linked_program_names:
        offered_programs = set(
            frappe.get_all(
                "Program Offering",
                filters={"school": school_name, "program": ["in", linked_program_names]},
                pluck="program",
                distinct=True,
            )
        )
        for row in frappe.get_all(
            "Program",
            filters={"name": ["in", linked_program_names], "is_published": 1, "archive": 0},
            fields=["name", "program_name"],
        ):
            if row.name in offered_programs:
                program_map[row.name] = row.program_name or row.name

    program_labels_by_course = {}
    for row in program_links:
        label = program_map.get(row.parent)
        if not label:
            continue
        program_labels_by_course.setdefault(row.course, [])
        if label not in program_labels_by_course[row.course]:
            program_labels_by_course[row.course].append(label)

    profiles_by_course = {row.course: row for row in profiles if row.course and row.course_slug}
    ordered_courses = sorted(
        (row for row in courses if row.name in profiles_by_course),
        key=lambda row: ((row.course_group or "").lower(), (row.course_name or row.name).lower()),
    )

    items = []
    for course in ordered_courses:
        profile = profiles_by_course.get(course.name)
        if not profile or not profile.course_slug:
            continue

        group = course_groups.get(course.course_group)
        image_source = profile.hero_image or course.course_image or (group.subject_group_image if group else None)
        items.append(
            {
                "title": course.course_name or course.name,
                "url": build_course_profile_url(
                    school_slug=school.website_slug,
                    course_slug=profile.course_slug,
                ),
                "intro": truncate_text(profile.intro_text or "", 180),
                "image": build_image_variants(image_source, "course"),
                "course_group": course.course_group,
                "program_labels": program_labels_by_course.get(course.name, [])[:3],
                "term_long": bool(int(course.term_long or 0)),
            }
        )
        if len(items) >= limit:
            break

    return items


def invalidate_course_catalog_cache():
    clear_cache = getattr(_get_school_courses, "clear_cache", None)
    if callable(clear_cache):
        clear_cache()


def get_context(*, school, page, block_props):
    limit = _normalize_limit(block_props.get("limit"))
    courses = _get_school_courses(school.name, limit)

    return {
        "data": {
            "courses": courses,
            "show_intro": bool(block_props.get("show_intro", True)),
            "show_course_group": bool(block_props.get("show_course_group", True)),
            "show_related_programs": bool(block_props.get("show_related_programs", True)),
            "card_style": block_props.get("card_style") or "standard",
            "empty_state_title": (block_props.get("empty_state_title") or "Course catalog coming soon.").strip(),
            "empty_state_text": (
                block_props.get("empty_state_text")
                or "Published course pages will appear here as soon as they are approved."
            ).strip(),
        }
    }
