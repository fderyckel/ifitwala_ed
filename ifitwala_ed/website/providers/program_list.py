# ifitwala_ed/website/providers/program_list.py

import frappe
from frappe.utils import cint
from frappe.utils.caching import redis_cache

from ifitwala_ed.website.utils import build_image_variants, build_program_url, truncate_text


@redis_cache(ttl=3600)
def _get_programs(school: str, category: str | None, limit: int):
	offerings = frappe.get_all(
		"Program Offering",
		filters={"school": school, "status": "Active"},
		fields=["program"],
	)
	program_names = sorted({row.program for row in offerings if row.program})
	if not program_names:
		return []

	filters = {
		"name": ["in", program_names],
		"is_published": 1,
	}
	if category:
		filters["parent_program"] = category

	programs = frappe.get_all(
		"Program",
		filters=filters,
		fields=["name", "program_name", "program_image", "description", "program_slug", "route"],
		order_by="program_name asc",
		limit_page_length=limit,
	)

	items = []
	for program in programs:
		description = truncate_text(program.get("description"), 140)
		items.append(
			{
				"title": program.get("program_name"),
				"url": build_program_url(program),
				"description": description,
				"image": build_image_variants(program.get("program_image"), "program"),
			}
		)
	return items


def get_context(*, school, page, block_props):
	"""
	Program list - dynamic but crawlable.
	"""
	limit = max(cint(block_props.get("limit") or 6), 1)
	category = block_props.get("program_category")
	programs = _get_programs(school=school.name, category=category, limit=limit)

	return {
		"data": {
			"title": block_props.get("title"),
			"programs": programs,
			"show_description": bool(block_props.get("show_description")),
		}
	}
