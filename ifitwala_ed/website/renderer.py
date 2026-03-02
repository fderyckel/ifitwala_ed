# ifitwala_ed/website/renderer.py

import re

import frappe
from frappe import _

from ifitwala_ed.website.block_registry import get_block_definition_map
from ifitwala_ed.website.utils import (
    build_story_url,
    is_school_public,
    normalize_route,
    parse_props,
    resolve_admissions_cta_url,
    resolve_school_from_route,
    truncate_text,
    validate_cta_link,
    validate_props_schema,
)
from ifitwala_ed.website.validators import normalize_block_props

ROOT_ROUTE_ALIASES = {
    "/",
    "/home",
    "/index",
    "/index.html",
}
SCHOOL_ROUTE_PREFIX = "schools"

HEX_COLOR_PATTERN = re.compile(r"^#(?:[0-9a-f]{3}|[0-9a-f]{6})$")
THEME_DEFAULTS = {
    "profile_name": "Default K-12 Theme",
    "preset_type": "K-12",
    "scope_type": "Global",
    "primary_color": "#1d4ed8",
    "accent_color": "#16a34a",
    "surface_color": "#f8fafc",
    "text_color": "#0f172a",
    "type_scale": "standard",
    "spacing_density": "standard",
    "hero_style": "spotlight",
    "enable_motion": 1,
}
TYPE_SCALE_FACTORS = {
    "compact": "0.94",
    "standard": "1.00",
    "large": "1.10",
}
SPACING_GAPS = {
    "compact": "4.5rem",
    "standard": "6rem",
    "relaxed": "7.5rem",
}
HERO_RADIUS = {
    "classic": "0rem",
    "split": "0.9rem",
    "spotlight": "1.4rem",
}


def _coerce_theme_color(value: str | None, fallback: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return fallback
    return text if HEX_COLOR_PATTERN.match(text) else fallback


def _pick_theme_profile_name(*, scope_type: str, organization: str | None = None, school_name: str | None = None):
    filters = {"scope_type": scope_type}
    if scope_type == "School":
        school_name = (school_name or "").strip()
        if not school_name:
            return None
        filters["school"] = school_name
    elif scope_type == "Organization":
        organization = (organization or "").strip()
        if not organization:
            return None
        filters["organization"] = organization

    name = frappe.db.get_value(
        "Website Theme Profile",
        {**filters, "is_default": 1},
        "name",
        order_by="modified desc",
    )
    if name:
        return name
    return frappe.db.get_value(
        "Website Theme Profile",
        filters,
        "name",
        order_by="modified desc",
    )


def _resolve_theme_profile(school):
    if not frappe.db.exists("DocType", "Website Theme Profile"):
        return None

    school_name = (getattr(school, "name", None) or "").strip()
    organization = (getattr(school, "organization", None) or "").strip()

    name = _pick_theme_profile_name(scope_type="School", school_name=school_name)
    if not name:
        name = _pick_theme_profile_name(scope_type="Organization", organization=organization)
    if not name:
        name = _pick_theme_profile_name(scope_type="Global")
    if not name:
        return None
    return frappe.get_doc("Website Theme Profile", name)


def _build_theme_context(*, school) -> dict:
    doc = _resolve_theme_profile(school)

    primary_color = _coerce_theme_color(
        getattr(doc, "primary_color", None),
        THEME_DEFAULTS["primary_color"],
    )
    accent_color = _coerce_theme_color(
        getattr(doc, "accent_color", None),
        THEME_DEFAULTS["accent_color"],
    )
    surface_color = _coerce_theme_color(
        getattr(doc, "surface_color", None),
        THEME_DEFAULTS["surface_color"],
    )
    text_color = _coerce_theme_color(
        getattr(doc, "text_color", None),
        THEME_DEFAULTS["text_color"],
    )

    type_scale = (getattr(doc, "type_scale", None) or "").strip() or THEME_DEFAULTS["type_scale"]
    if type_scale not in TYPE_SCALE_FACTORS:
        type_scale = THEME_DEFAULTS["type_scale"]

    spacing_density = (getattr(doc, "spacing_density", None) or "").strip() or THEME_DEFAULTS["spacing_density"]
    if spacing_density not in SPACING_GAPS:
        spacing_density = THEME_DEFAULTS["spacing_density"]

    hero_style = (getattr(doc, "hero_style", None) or "").strip() or THEME_DEFAULTS["hero_style"]
    if hero_style not in HERO_RADIUS:
        hero_style = THEME_DEFAULTS["hero_style"]

    enable_motion = int(getattr(doc, "enable_motion", THEME_DEFAULTS["enable_motion"]) or 0) == 1
    css_vars = {
        "--if-theme-primary": primary_color,
        "--if-theme-accent": accent_color,
        "--if-theme-surface": surface_color,
        "--if-theme-text": text_color,
        "--if-type-scale-factor": TYPE_SCALE_FACTORS[type_scale],
        "--if-block-gap": SPACING_GAPS[spacing_density],
        "--if-hero-radius": HERO_RADIUS[hero_style],
    }
    css_vars_inline = "; ".join(f"{key}: {value}" for key, value in css_vars.items())

    return {
        "profile_name": (getattr(doc, "profile_name", None) or "").strip() or THEME_DEFAULTS["profile_name"],
        "preset_type": (getattr(doc, "preset_type", None) or "").strip() or THEME_DEFAULTS["preset_type"],
        "scope_type": (getattr(doc, "scope_type", None) or "").strip() or THEME_DEFAULTS["scope_type"],
        "type_scale": type_scale,
        "spacing_density": spacing_density,
        "hero_style": hero_style,
        "enable_motion": enable_motion,
        "motion_mode": "on" if enable_motion else "off",
        "css_vars": css_vars,
        "css_vars_inline": css_vars_inline,
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
    home_url = normalize_route(f"/{SCHOOL_ROUTE_PREFIX}/{school_slug}") if school_slug else "/"
    return [{"label": _("Home"), "url": home_url}]


def _build_site_shell_context(*, school, route: str) -> dict:
    school_slug = (school.website_slug or "").strip()
    brand_url = normalize_route(f"/{SCHOOL_ROUTE_PREFIX}/{school_slug}") if school_slug else "/"
    navigation = _get_navigation_items(school=school)
    footer_links = navigation[:4]
    is_guest_user = (frappe.session.user or "Guest") == "Guest"
    organization_row = frappe.db.get_value(
        "Organization",
        school.organization,
        ["name", "organization_name", "organization_logo"],
        as_dict=True,
    )

    organization_name = (organization_row.get("organization_name") if organization_row else None) or school.organization
    organization_logo = organization_row.get("organization_logo") if organization_row else None

    inquiry_url = None
    try:
        inquiry_url = resolve_admissions_cta_url(school=school, intent="inquire")
    except frappe.ValidationError:
        inquiry_url = "/apply/inquiry"
    inquiry_url = validate_cta_link(inquiry_url) or "/apply/inquiry"

    apply_url = None
    try:
        apply_url = resolve_admissions_cta_url(school=school, intent="apply")
    except frappe.ValidationError:
        apply_url = "/admissions"
    apply_url = validate_cta_link(apply_url) or "/admissions"

    return {
        "brand_name": school.school_name or school.name,
        "brand_url": brand_url,
        "brand_logo": getattr(school, "school_logo", None),
        "organization_name": organization_name,
        "organization_logo": organization_logo,
        "navigation": navigation,
        "footer_links": footer_links,
        "current_route": normalize_route(route),
        "current_year": frappe.utils.now_datetime().year,
        "is_guest_user": is_guest_user,
        "login_url": "/login",
        "portal_login_url": "/hub",
        "other_organizations_url": "/",
        "inquiry_url": inquiry_url,
        "apply_url": apply_url,
    }


def _get_block_definitions(block_types: list[str]) -> dict:
    if not block_types:
        return {}
    canonical = get_block_definition_map()
    definitions = {}
    for block_type in block_types:
        row = canonical.get(block_type)
        if not row:
            continue
        definitions[block_type] = frappe._dict(row)
    return definitions


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
    return sorted(blocks, key=lambda row: row.order if row.order is not None else (row.idx or 0))


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
        try:
            props = parse_props(block.props)
        except frappe.ValidationError as exc:
            frappe.throw(
                _("Invalid block props JSON in row {0} ({1}): {2}").format(
                    block.idx or "?",
                    block.block_type or _("Unknown block"),
                    frappe.as_unicode(exc),
                ),
                frappe.ValidationError,
            )
        props = normalize_block_props(block_type=block.block_type, props=props)
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
    theme = _build_theme_context(school=school)
    return {
        "page": page,
        "school": school,
        "blocks": blocks,
        "block_scripts": scripts,
        "seo": seo,
        "theme": theme,
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
    theme = _build_theme_context(school=school)
    return {
        "page": profile,
        "school": school,
        "program": program,
        "blocks": blocks,
        "block_scripts": scripts,
        "seo": seo,
        "theme": theme,
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
    theme = _build_theme_context(school=school)
    return {
        "page": story,
        "school": school,
        "blocks": blocks,
        "block_scripts": scripts,
        "seo": seo,
        "theme": theme,
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
    theme = _build_theme_context(school=school)
    return {
        "page": {"route": route},
        "school": school,
        "stories": stories,
        "blocks": [],
        "block_scripts": [],
        "seo": seo,
        "theme": theme,
        "site_shell": _build_site_shell_context(school=school, route=route),
        "template": "ifitwala_ed/website/templates/stories_index.html",
    }


def _resolve_landing_organization():
    org = frappe.db.get_value(
        "Organization",
        {
            "archived": 0,
            "name": ["!=", "All Organizations"],
            "parent_organization": ["in", ["All Organizations", "", None]],
        },
        ["name", "organization_name", "organization_logo", "lft", "rgt"],
        as_dict=True,
        order_by="lft asc",
    )
    if org:
        return org

    org = frappe.db.get_value(
        "Organization",
        {"archived": 0, "name": ["!=", "All Organizations"]},
        ["name", "organization_name", "organization_logo", "lft", "rgt"],
        as_dict=True,
        order_by="lft asc",
    )
    if org:
        return org

    return frappe.db.get_value(
        "Organization",
        {"name": "All Organizations"},
        ["name", "organization_name", "organization_logo", "lft", "rgt"],
        as_dict=True,
    )


def _get_descendant_organization_names(organization) -> list[str]:
    if not organization:
        return []

    lft = organization.get("lft")
    rgt = organization.get("rgt")
    if lft is None or rgt is None:
        return [organization.get("name")] if organization.get("name") else []

    return frappe.get_all(
        "Organization",
        filters={"lft": [">=", lft], "rgt": ["<=", rgt], "archived": 0},
        pluck="name",
        order_by="lft asc",
    )


def _get_landing_school_cards(*, organization_names: list[str]) -> list[dict]:
    if not organization_names:
        return []

    schools = frappe.get_all(
        "School",
        filters={
            "organization": ["in", organization_names],
            "is_published": 1,
            "website_slug": ["!=", ""],
        },
        fields=["name", "school_name", "school_tagline", "school_logo", "website_slug", "organization"],
        order_by="lft asc, school_name asc",
    )
    if not schools:
        return []

    organization_labels = {
        row.name: (row.organization_name or row.name)
        for row in frappe.get_all(
            "Organization",
            filters={"name": ["in", organization_names]},
            fields=["name", "organization_name"],
        )
    }

    cards = []
    for school in schools:
        slug = (school.website_slug or "").strip()
        if not slug:
            continue
        cards.append(
            {
                "name": school.name,
                "label": school.school_name or school.name,
                "tagline": (school.school_tagline or "").strip(),
                "logo": school.school_logo,
                "url": normalize_route(f"/{SCHOOL_ROUTE_PREFIX}/{slug}"),
                "organization": organization_labels.get(school.organization) or school.organization,
            }
        )
    return cards


def _build_organization_landing_context(*, route: str):
    organization = _resolve_landing_organization() or {}
    organization_name = (organization.get("organization_name") or organization.get("name") or _("Organization")).strip()
    organization_names = _get_descendant_organization_names(organization)
    school_cards = _get_landing_school_cards(organization_names=organization_names)

    seo = _build_seo_context(
        route=route,
        fallback_title=organization_name,
        fallback_description=_("Explore our schools and programs."),
        seo_profile=None,
    )

    return {
        "landing": {
            "organization_name": organization_name,
            "organization_logo": organization.get("organization_logo"),
            "schools": school_cards,
        },
        "seo": seo,
        "is_guest_user": (frappe.session.user or "Guest") == "Guest",
        "login_url": "/login?redirect-to=/hub",
        "inquiry_url": "/apply/inquiry",
        "current_year": frappe.utils.now_datetime().year,
        "template": "ifitwala_ed/website/templates/organization_landing.html",
    }


def build_render_context(*, route: str, preview: bool = False):
    route = normalize_route(route)
    if route in ROOT_ROUTE_ALIASES:
        route = "/"

    if route == "/":
        return _build_organization_landing_context(route=route)

    segments = [seg for seg in route.split("/") if seg]
    if not segments:
        return _build_organization_landing_context(route="/")

    if segments[0] != SCHOOL_ROUTE_PREFIX:
        frappe.throw(
            _("Website page not found for route: {0}.").format(route),
            frappe.DoesNotExistError,
        )

    if len(segments) < 2:
        return _build_organization_landing_context(route="/")

    school = resolve_school_from_route(route)
    if not preview and not is_school_public(school):
        frappe.throw(
            _("School not published."),
            frappe.DoesNotExistError,
        )

    school_slug = (school.website_slug or "").strip()
    if segments[1] != school_slug:
        frappe.throw(
            _("Website page not found for route: {0}.").format(route),
            frappe.DoesNotExistError,
        )

    if len(segments) >= 4 and segments[2] == "programs":
        return _build_program_context(
            route=route,
            school=school,
            program_slug=segments[3],
            preview=preview,
        )

    if len(segments) >= 3 and segments[2] == "stories":
        if len(segments) == 3:
            try:
                return _build_school_page_context(route=route, school=school, preview=preview)
            except frappe.DoesNotExistError:
                return _build_story_index_context(route=route, school=school)
        return _build_story_context(
            route=route,
            school=school,
            story_slug=segments[3],
            preview=preview,
        )

    return _build_school_page_context(route=route, school=school, preview=preview)


def render_page(*, route: str, preview: bool = False) -> str:
    context = build_render_context(route=route, preview=preview)
    template = context.pop("template", "ifitwala_ed/website/templates/page.html")
    return frappe.render_template(template, context)
