# ifitwala_ed/website/utils.py

import json
import re
from typing import Any

import frappe
from frappe import _
from frappe.utils import strip_html

from ifitwala_ed.utilities.image_utils import slugify


def normalize_route(route: str | None) -> str:
	if not route:
		return "/"
	route = route.strip()
	if not route.startswith("/"):
		route = f"/{route}"
	if route != "/" and route.endswith("/"):
		route = route[:-1]
	return route


def resolve_default_school():
	school = frappe.get_all(
		"School",
		filters={"is_group": 1},
		fields=["name"],
		order_by="lft asc",
		limit_page_length=1,
	)
	if not school:
		frappe.throw(
			_("No root School found. Create a School group to serve as website root."),
			frappe.DoesNotExistError,
		)
	return frappe.get_doc("School", school[0].name)


def resolve_school_from_route(route: str):
	segments = [seg for seg in route.split("/") if seg]
	if segments:
		slug = segments[0]
		school_name = frappe.db.get_value("School", {"website_slug": slug}, "name")
		if school_name:
			return frappe.get_doc("School", school_name)
	return resolve_default_school()


def is_school_public(school) -> bool:
	if not school:
		return False
	return bool(school.website_slug) and int(school.is_group or 0) == 0


def parse_props(raw_props: Any) -> dict:
	if not raw_props:
		return {}
	if isinstance(raw_props, dict):
		return raw_props
	if isinstance(raw_props, str):
		try:
			return json.loads(raw_props)
		except Exception as exc:
			frappe.throw(
				_("Invalid block props JSON: {0}").format(str(exc)),
				frappe.ValidationError,
			)
	if isinstance(raw_props, bytes):
		try:
			return json.loads(raw_props.decode("utf-8"))
		except Exception as exc:
			frappe.throw(
				_("Invalid block props JSON: {0}").format(str(exc)),
				frappe.ValidationError,
			)
	frappe.throw(
		_("Unsupported block props type: {0}").format(type(raw_props)),
		frappe.ValidationError,
	)


def _load_schema(raw_schema: Any) -> dict | None:
	if not raw_schema:
		return None
	if isinstance(raw_schema, dict):
		return raw_schema
	if isinstance(raw_schema, str):
		try:
			return json.loads(raw_schema)
		except Exception as exc:
			frappe.throw(
				_("Invalid props schema JSON: {0}").format(str(exc)),
				frappe.ValidationError,
			)
	frappe.throw(
		_("Unsupported props schema type: {0}").format(type(raw_schema)),
		frappe.ValidationError,
	)


def validate_props_schema(props: dict, raw_schema: Any, *, block_type: str):
	schema = _load_schema(raw_schema)
	if not schema:
		frappe.throw(
			_("Missing props schema for block type: {0}").format(block_type),
			frappe.ValidationError,
		)
	try:
		from jsonschema import Draft7Validator
	except Exception:
		frappe.throw(
			_("jsonschema is required to validate block props for {0}.").format(block_type),
			frappe.ValidationError,
		)

	validator = Draft7Validator(schema)
	errors = sorted(validator.iter_errors(props), key=lambda e: list(e.path))
	if errors:
		formatted = []
		for err in errors:
			path = ".".join([str(p) for p in err.path]) if err.path else "(root)"
			formatted.append(f"{path}: {err.message}")
		message = "\n".join(formatted)
		frappe.throw(
			_("Invalid props for block '{0}':\n{1}").format(block_type, message),
			frappe.ValidationError,
		)

	return props


def build_resized_url(original_url: str | None, doctype_folder: str, size_label: str) -> str | None:
	if not original_url:
		return None
	filename = original_url.split("/")[-1]
	base = filename.rsplit(".", 1)[0]
	folder_slug = slugify(doctype_folder)
	file_slug = slugify(base)
	return f"/files/gallery_resized/{folder_slug}/{size_label}_{file_slug}.webp"


def build_image_variants(original_url: str | None, doctype_folder: str) -> dict:
	return {
		"original": original_url,
		"hero": build_resized_url(original_url, doctype_folder, "hero"),
		"medium": build_resized_url(original_url, doctype_folder, "medium"),
		"card": build_resized_url(original_url, doctype_folder, "card"),
		"thumb": build_resized_url(original_url, doctype_folder, "thumb"),
	}


def validate_cta_link(link: str | None) -> str | None:
	if not link:
		return None
	clean = link.strip()
	if clean.startswith("/"):
		return clean
	if clean.startswith("https://"):
		return clean
	frappe.throw(
		_("CTA link must be an internal path or https URL: {0}").format(clean),
		frappe.ValidationError,
	)


def truncate_text(text: str, length: int) -> str:
	text = strip_html(text or "")
	text = re.sub(r"\s+", " ", text).strip()
	if len(text) <= length:
		return text
	return text[:length].rstrip() + "..."


def build_program_url(program: dict) -> str:
	route = (program.get("route") or "").strip()
	if route:
		return normalize_route(route)
	slug = (program.get("program_slug") or "").strip()
	if slug:
		return normalize_route(f"/programs/{slug}")
	return normalize_route(f"/programs/{program.get('name')}")


def build_program_profile_url(*, school_slug: str, program_slug: str) -> str:
	return normalize_route(f"/{school_slug}/programs/{program_slug}")


def build_story_url(*, school_slug: str, story_slug: str) -> str:
	return normalize_route(f"/{school_slug}/stories/{story_slug}")


def resolve_admissions_cta_url(*, school, intent: str) -> str:
	field_map = {
		"inquire": "admissions_inquiry_route",
		"visit": "admissions_visit_route",
		"apply": "admissions_apply_route",
	}
	field = field_map.get(intent)
	if not field:
		frappe.throw(
			_("Unknown admissions intent: {0}").format(intent),
			frappe.ValidationError,
		)

	link = school.get(field)
	if not link:
		frappe.throw(
			_("Admissions CTA target missing for intent: {0}.").format(intent),
			frappe.ValidationError,
		)
	return validate_cta_link(link)
