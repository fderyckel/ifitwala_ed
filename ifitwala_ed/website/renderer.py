# ifitwala_ed/website/renderer.py

import frappe
from frappe import _

from ifitwala_ed.website.utils import (
	normalize_route,
	parse_props,
	resolve_school_from_route,
	validate_props_schema,
)


def _get_block_definitions(block_types: list[str]) -> dict:
	if not block_types:
		return {}
	definitions = frappe.get_all(
		"Website Block Definition",
		filters={"block_type": ["in", block_types]},
		fields=[
			"block_type",
			"template_path",
			"provider_path",
			"props_schema",
			"seo_role",
		],
	)
	return {row.block_type: row for row in definitions}


def _resolve_provider(provider_path: str, block_type: str):
	if not provider_path:
		frappe.throw(
			_("Missing provider for block type: {0}").format(block_type),
			frappe.ValidationError,
		)
	try:
		provider = frappe.get_attr(provider_path)
	except Exception as exc:
		frappe.throw(
			_("Unable to load provider for block '{0}': {1}").format(block_type, str(exc)),
			frappe.ValidationError,
		)
	if not callable(provider):
		frappe.throw(
			_("Provider for block '{0}' is not callable.").format(block_type),
			frappe.ValidationError,
		)
	return provider


def _fetch_page(route: str, school):
	page_name = frappe.db.get_value(
		"School Website Page",
		{"school": school.name, "route": route, "is_published": 1},
		"name",
	)
	if not page_name:
		frappe.throw(
			_("Website page not found for {0} ({1}).").format(route, school.name),
			frappe.DoesNotExistError,
		)
	return frappe.get_doc("School Website Page", page_name)


def _sorted_blocks(page):
	blocks = [row for row in (page.blocks or []) if row.is_enabled]
	return sorted(blocks, key=lambda row: (row.order if row.order is not None else (row.idx or 0)))


def _enforce_seo_rules(blocks, definitions):
	if not blocks:
		frappe.throw(
			_("Page has no enabled blocks. Add at least one block before publishing."),
			frappe.ValidationError,
		)

	seo_roles = [definitions[block.block_type].seo_role for block in blocks]
	owns_h1 = [role for role in seo_roles if role == "owns_h1"]
	if len(owns_h1) != 1:
		frappe.throw(
			_("Exactly one block must own the H1. Found {0}.").format(len(owns_h1)),
			frappe.ValidationError,
		)

	first_role = definitions[blocks[0].block_type].seo_role
	if first_role != "owns_h1":
		frappe.throw(
			_("The first enabled block must own the H1 (hero)."),
			frappe.ValidationError,
		)


def build_render_context(*, route: str):
	route = normalize_route(route)
	school = resolve_school_from_route(route)
	page = _fetch_page(route, school)

	blocks = _sorted_blocks(page)
	block_types = [block.block_type for block in blocks]
	definitions = _get_block_definitions(block_types)

	missing = [bt for bt in block_types if bt not in definitions]
	if missing:
		frappe.throw(
			_("Missing block definitions: {0}").format(", ".join(sorted(set(missing)))),
			frappe.ValidationError,
		)

	_enforce_seo_rules(blocks, definitions)

	render_blocks = []
	for block in blocks:
		definition = definitions[block.block_type]
		props = parse_props(block.props)
		validate_props_schema(props, definition.props_schema, block_type=block.block_type)
		provider = _resolve_provider(definition.provider_path, block.block_type)
		ctx = provider(school=school, page=page, block_props=props) or {}
		data = ctx.get("data") if isinstance(ctx, dict) else None
		if data is None:
			frappe.throw(
				_("Provider for block '{0}' did not return data.").format(block.block_type),
				frappe.ValidationError,
			)

		render_blocks.append(
			{
				"template": definition.template_path,
				"props": props,
				"data": data,
			}
		)

	return {
		"page": page,
		"school": school,
		"blocks": render_blocks,
	}


def render_page(*, route: str) -> str:
	context = build_render_context(route=route)
	return frappe.render_template("ifitwala_ed/website/templates/page.html", context)
