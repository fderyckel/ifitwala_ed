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

	profiles = frappe.get_all(
		"Program Website Profile",
		filters={"school": ["in", school_names], "status": "Published"},
		fields=["name", "program", "school", "hero_image", "intro_text"],
	)
	if not profiles:
		return []

	offering_rows = frappe.get_all(
		"Program Offering",
		filters={"school": ["in", school_names], "program": ["in", [p.program for p in profiles]]},
		fields=["program", "school"],
	)
	offered_pairs = {(row.school, row.program) for row in offering_rows if row.program and row.school}

	program_names = sorted({row.program for row in profiles if row.program})
	programs = frappe.get_all(
		"Program",
		filters={
			"name": ["in", program_names],
			"is_published": 1,
			"archive": 0,
		},
		fields=["name", "program_name", "program_image", "program_slug", "is_featured", "lft"],
	)

	profiles_by_program = {}
	for profile in profiles:
		profiles_by_program.setdefault(profile.program, []).append(profile)

	sorted_programs = sorted(
		(program for program in programs if program.name in profiles_by_program),
		key=lambda row: (-int(row.is_featured or 0), int(row.lft or 0)),
	)

	items = []
	for program in sorted_programs:
		if not program.program_slug:
			continue
		program_slug = program.program_slug
		program_title = program.program_name or program.name

		for profile in profiles_by_program.get(program.name, []):
			if (profile.school, profile.program) not in offered_pairs:
				continue

			school = school_map.get(profile.school)
			if not school or not school.website_slug:
				continue

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
			if len(items) >= limit:
				return items
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
