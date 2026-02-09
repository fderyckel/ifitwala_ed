# ifitwala_ed/website/renderer.py

import frappe
from frappe import _

from ifitwala_ed.website.utils import (
	build_story_url,
	is_school_public,
	normalize_route,
	parse_props,
	resolve_school_from_route,
	truncate_text,
	validate_props_schema,
)


ROOT_ROUTE_ALIASES = {
	"/",
	"/home",
	"/index",
	"/index.html",
}


def _fallback_nav_label(*, route: str, page_type: str | None) -> str:
	if route == "/":
		return _("Home")
	if page_type == "Admissions":
		return _("Admissions")
	segment = route.split("/")[-1] if route else ""
	if not segment:
		return _("Page")
	return segment.replace("-", " ").replace("_", " ").title()


def _get_navigation_items(*, school):
	rows = frappe.get_all(
		"School Website Page",
		filters={
			"school": school.name,
			"is_published": 1,
			"show_in_navigation": 1,
		},
		fields=["title", "full_route", "route", "page_type", "navigation_order"],
		order_by="ifnull(navigation_order, 9999) asc, route asc",
	)

	items = []
	for row in rows:
		url = normalize_route(row.full_route)
		if row.route == "/":
			label = _("Home")
		else:
			label = (row.title or "").strip() or _fallback_nav_label(
				route=row.route,
				page_type=row.page_type,
			)
		items.append({"label": label, "url": url})

	if items:
		return items

	school_slug = (school.website_slug or "").strip()
	home_url = normalize_route(f"/{school_slug}") if school_slug else "/"
	return [{"label": _("Home"), "url": home_url}]


def _build_site_shell_context(*, school, route: str) -> dict:
	school_slug = (school.website_slug or "").strip()
	brand_url = normalize_route(f"/{school_slug}") if school_slug else "/"
	navigation = _get_navigation_items(school=school)
	footer_links = navigation[:4]

	return {
		"brand_name": school.school_name or school.name,
		"brand_url": brand_url,
		"brand_logo": getattr(school, "school_logo", None),
		"navigation": navigation,
		"footer_links": footer_links,
		"current_route": normalize_route(route),
		"current_year": frappe.utils.now_datetime().year,
	}


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
			"script_path",
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
			_("The first enabled block must own the H1."),
			frappe.ValidationError,
		)


def _normalize_block_props(*, block_type: str, props: dict) -> dict:
	"""
	Backward-compatible prop aliases for legacy website records.
	Normalization happens before schema validation so old pages keep rendering.
	"""
	normalized = dict(props or {})

	if block_type == "cta":
		if not normalized.get("button_label"):
			normalized["button_label"] = (
				normalized.get("cta_label")
				or normalized.get("label")
				or ""
			)
		if not normalized.get("button_link"):
			normalized["button_link"] = (
				normalized.get("cta_link")
				or normalized.get("url")
				or normalized.get("link")
				or ""
			)

	elif block_type == "rich_text":
		if not normalized.get("content_html") and normalized.get("content"):
			normalized["content_html"] = normalized.get("content")

	elif block_type == "admissions_overview":
		if not normalized.get("content_html") and normalized.get("content"):
			normalized["content_html"] = normalized.get("content")

	elif block_type == "hero":
		primary_cta = normalized.get("primary_cta")
		cta = normalized.get("cta")
		if isinstance(primary_cta, dict):
			if not normalized.get("cta_label"):
				normalized["cta_label"] = primary_cta.get("label")
			if not normalized.get("cta_link"):
				normalized["cta_link"] = primary_cta.get("link") or primary_cta.get("url")
		if isinstance(cta, dict):
			if not normalized.get("cta_label"):
				normalized["cta_label"] = cta.get("label")
			if not normalized.get("cta_link"):
				normalized["cta_link"] = cta.get("link") or cta.get("url")

	return normalized


def _build_blocks(*, page, school):
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
	scripts = []
	for block in blocks:
		definition = definitions[block.block_type]
		props = parse_props(block.props)
		props = _normalize_block_props(block_type=block.block_type, props=props)
		validate_props_schema(props, definition.props_schema, block_type=block.block_type)
		provider = _resolve_provider(definition.provider_path, block.block_type)
		ctx = provider(school=school, page=page, block_props=props) or {}
		data = ctx.get("data") if isinstance(ctx, dict) else None
		if data is None:
			frappe.throw(
				_("Provider for block '{0}' did not return data.").format(block.block_type),
				frappe.ValidationError,
			)

		if definition.script_path and definition.script_path not in scripts:
			scripts.append(definition.script_path)

		render_blocks.append(
			{
				"template": definition.template_path,
				"props": props,
				"data": data,
			}
		)

	return render_blocks, scripts


def _get_seo_profile(page):
	seo_profile = getattr(page, "seo_profile", None)
	if not seo_profile:
		return None
	return frappe.get_doc("Website SEO Profile", seo_profile)


def _build_seo_context(*, route: str, fallback_title: str | None, fallback_description: str | None, seo_profile):
	meta_title = (seo_profile.meta_title if seo_profile else None) or fallback_title
	meta_description = (seo_profile.meta_description if seo_profile else None) or fallback_description
	og_title = (seo_profile.og_title if seo_profile else None) or meta_title
	og_description = (seo_profile.og_description if seo_profile else None) or meta_description
	og_image = seo_profile.og_image if seo_profile else None
	canonical_url = (seo_profile.canonical_url if seo_profile else None) or frappe.utils.get_url(route)
	noindex = bool(seo_profile.noindex) if seo_profile else False

	return {
		"meta_title": meta_title,
		"meta_description": meta_description,
		"og_title": og_title,
		"og_description": og_description,
		"og_image": og_image,
		"canonical_url": canonical_url,
		"noindex": noindex,
	}


def _preview_allowed(doc) -> bool:
	if frappe.session.user == "Guest":
		return False
	return frappe.has_permission(doc=doc, ptype="read")


def _fetch_school_page(route: str, school, preview: bool):
	if preview:
		page_name = frappe.db.get_value(
			"School Website Page",
			{"school": school.name, "full_route": route},
			"name",
		)
		if page_name:
			page = frappe.get_doc("School Website Page", page_name)
			if page.is_published or _preview_allowed(page):
				return page
			frappe.throw(_("Preview not permitted."), frappe.PermissionError)

	page_name = frappe.db.get_value(
		"School Website Page",
		{"school": school.name, "full_route": route, "is_published": 1},
		"name",
	)
	if not page_name:
		frappe.throw(
			_("Website page not found for {0} ({1}).").format(route, school.name),
			frappe.DoesNotExistError,
		)
	return frappe.get_doc("School Website Page", page_name)


def _fetch_program_profile(school, program_slug: str, preview: bool):
	program_name = frappe.db.get_value(
		"Program",
		{"program_slug": program_slug},
		"name",
	)
	if not program_name:
		frappe.throw(
			_("Program not found for slug: {0}.").format(program_slug),
			frappe.DoesNotExistError,
		)

	program = frappe.get_doc("Program", program_name)
	if not preview:
		if not getattr(program, "is_published", 0):
			frappe.throw(
				_("Program not published."),
				frappe.DoesNotExistError,
			)
		if getattr(program, "archive", 0):
			frappe.throw(
				_("Program is archived."),
				frappe.DoesNotExistError,
			)

		offered = frappe.db.exists(
			"Program Offering",
			{"program": program_name, "school": school.name},
		)
		if not offered:
			frappe.throw(
				_("Program not offered by this school."),
				frappe.DoesNotExistError,
			)

	filters = {"school": school.name, "program": program_name}
	if not preview:
		filters["status"] = "Published"

	profile_name = frappe.db.get_value("Program Website Profile", filters, "name")
	if not profile_name:
		frappe.throw(
			_("Program page not found for {0}.").format(program_slug),
			frappe.DoesNotExistError,
		)
	profile = frappe.get_doc("Program Website Profile", profile_name)
	if preview and profile.status != "Published" and not _preview_allowed(profile):
		frappe.throw(_("Preview not permitted."), frappe.PermissionError)
	return profile, program


def _fetch_story(school, story_slug: str, preview: bool):
	filters = {"school": school.name, "slug": story_slug}
	if not preview:
		filters["status"] = "Published"

	story_name = frappe.db.get_value("Website Story", filters, "name")
	if not story_name:
		frappe.throw(
			_("Story not found for {0}.").format(story_slug),
			frappe.DoesNotExistError,
		)
	story = frappe.get_doc("Website Story", story_name)
	if preview and story.status != "Published" and not _preview_allowed(story):
		frappe.throw(_("Preview not permitted."), frappe.PermissionError)
	return story


def _build_school_page_context(*, route: str, school, preview: bool):
	page = _fetch_school_page(route, school, preview)
	blocks, scripts = _build_blocks(page=page, school=school)
	seo_profile = _get_seo_profile(page)
	seo = _build_seo_context(
		route=route,
		fallback_title=page.title,
		fallback_description=page.meta_description,
		seo_profile=seo_profile,
	)
	return {
		"page": page,
		"school": school,
		"blocks": blocks,
		"block_scripts": scripts,
		"seo": seo,
		"site_shell": _build_site_shell_context(school=school, route=route),
		"template": "ifitwala_ed/website/templates/page.html",
	}


def _build_program_context(*, route: str, school, program_slug: str, preview: bool):
	profile, program = _fetch_program_profile(school, program_slug, preview)
	blocks, scripts = _build_blocks(page=profile, school=school)
	seo_profile = _get_seo_profile(profile)
	description = truncate_text(profile.intro_text or "", 160) if profile.intro_text else None
	seo = _build_seo_context(
		route=route,
		fallback_title=program.program_name or program.name,
		fallback_description=description,
		seo_profile=seo_profile,
	)
	return {
		"page": profile,
		"school": school,
		"program": program,
		"blocks": blocks,
		"block_scripts": scripts,
		"seo": seo,
		"site_shell": _build_site_shell_context(school=school, route=route),
		"template": "ifitwala_ed/website/templates/page.html",
	}


def _build_story_context(*, route: str, school, story_slug: str, preview: bool):
	story = _fetch_story(school, story_slug, preview)
	blocks, scripts = _build_blocks(page=story, school=school)
	seo_profile = _get_seo_profile(story)
	seo = _build_seo_context(
		route=route,
		fallback_title=story.title,
		fallback_description=None,
		seo_profile=seo_profile,
	)
	return {
		"page": story,
		"school": school,
		"blocks": blocks,
		"block_scripts": scripts,
		"seo": seo,
		"site_shell": _build_site_shell_context(school=school, route=route),
		"template": "ifitwala_ed/website/templates/page.html",
	}


def _build_story_index_context(*, route: str, school):
	stories = frappe.get_all(
		"Website Story",
		filters={"school": school.name, "status": "Published"},
		fields=["name", "title", "slug", "publish_date"],
		order_by="publish_date desc, modified desc",
	)
	for story in stories:
		story["url"] = build_story_url(
			school_slug=school.website_slug,
			story_slug=story.get("slug"),
		)

	seo = _build_seo_context(
		route=route,
		fallback_title=f"{school.school_name} Stories",
		fallback_description=None,
		seo_profile=None,
	)
	return {
		"page": {"route": route},
		"school": school,
		"stories": stories,
		"blocks": [],
		"block_scripts": [],
		"seo": seo,
		"site_shell": _build_site_shell_context(school=school, route=route),
		"template": "ifitwala_ed/website/templates/stories_index.html",
	}


def build_render_context(*, route: str, preview: bool = False):
	route = normalize_route(route)
	if route in ROOT_ROUTE_ALIASES:
		route = "/"
	school = resolve_school_from_route(route)
	segments = [seg for seg in route.split("/") if seg]
	if not segments:
		school_slug = (school.website_slug or "").strip()
		if not school_slug:
			frappe.throw(
				_("Default website school is missing a website slug."),
				frappe.DoesNotExistError,
			)
		route = normalize_route(f"/{school_slug}")
		segments = [school_slug]

	if not preview and not is_school_public(school):
		frappe.throw(
			_("School not published."),
			frappe.DoesNotExistError,
		)
	school_slug = segments[0] if segments else None

	if school_slug and school_slug == school.website_slug:
		if len(segments) >= 3 and segments[1] == "programs":
			return _build_program_context(
				route=route,
				school=school,
				program_slug=segments[2],
				preview=preview,
			)
		if len(segments) >= 2 and segments[1] == "stories":
			if len(segments) == 2:
				try:
					return _build_school_page_context(route=route, school=school, preview=preview)
				except frappe.DoesNotExistError:
					return _build_story_index_context(route=route, school=school)
			return _build_story_context(
				route=route,
				school=school,
				story_slug=segments[2],
				preview=preview,
			)

	return _build_school_page_context(route=route, school=school, preview=preview)


def render_page(*, route: str, preview: bool = False) -> str:
	context = build_render_context(route=route, preview=preview)
	template = context.pop("template", "ifitwala_ed/website/templates/page.html")
	return frappe.render_template(template, context)
