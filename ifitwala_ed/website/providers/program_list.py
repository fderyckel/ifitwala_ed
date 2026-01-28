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
	filters = {"status": "Published"}
	if school_scope != "all":
		filters["school"] = school_name

	profiles = frappe.get_all(
		"Program Website Profile",
		filters=filters,
		fields=["name", "program", "school", "hero_image", "intro_text"],
		order_by="modified desc",
		limit_page_length=limit,
	)
	if not profiles:
		return []

	program_names = sorted({row.program for row in profiles if row.program})
	programs = frappe.get_all(
		"Program",
		filters={"name": ["in", program_names]},
		fields=["name", "program_name", "program_image", "program_slug"],
	)
	program_map = {row.name: row for row in programs}

	school_names = sorted({row.school for row in profiles if row.school})
	schools = frappe.get_all(
		"School",
		filters={"name": ["in", school_names]},
		fields=["name", "school_name", "website_slug"],
	)
	school_map = {row.name: row for row in schools}

	items = []
	for profile in profiles:
		program = program_map.get(profile.program)
		school = school_map.get(profile.school)
		if not program or not school or not school.website_slug:
			frappe.throw(
				"Program profile is missing program or school slug configuration.",
				frappe.ValidationError,
			)

		program_title = program.program_name or program.name
		if not program.program_slug:
			frappe.throw(
				"Program slug is required to build program URLs.",
				frappe.ValidationError,
			)
		program_slug = program.program_slug
		url = build_program_profile_url(
			school_slug=school.website_slug,
			program_slug=program_slug,
		)

		image_source = profile.hero_image or program.program_image
		items.append(
			{
				"title": program_title,
				"url": url,
				"intro": truncate_text(profile.intro_text or "", 160),
				"image": build_image_variants(image_source, "program"),
				"school_name": school.school_name if school_scope == "all" else None,
			}
		)
	return items


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
