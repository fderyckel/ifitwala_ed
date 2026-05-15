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


def slugify_route_segment(value: str | None, *, fallback: str = "item") -> str:
    clean = re.sub(r"[^a-z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return clean or fallback


def resolve_school_from_route(route: str):
    segments = [seg for seg in route.split("/") if seg]
    if len(segments) < 2 or segments[0] != "schools":
        frappe.throw(
            _("Website page not found for route: {route}.").format(route=normalize_route(route)),
            frappe.DoesNotExistError,
        )

    slug = segments[1]
    school_name = frappe.db.get_value("School", {"website_slug": slug}, "name")
    if not school_name:
        frappe.throw(
            _("School not found for slug: {slug}.").format(slug=slug),
            frappe.DoesNotExistError,
        )
    return frappe.get_doc("School", school_name)


def is_school_public(school) -> bool:
    if not school:
        return False
    return bool(school.website_slug) and int(getattr(school, "is_published", 0) or 0) == 1


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
                _("Invalid block props JSON: {error}").format(error=str(exc)),
                frappe.ValidationError,
            )
    if isinstance(raw_props, bytes):
        try:
            return json.loads(raw_props.decode("utf-8"))
        except Exception as exc:
            frappe.throw(
                _("Invalid block props JSON: {error}").format(error=str(exc)),
                frappe.ValidationError,
            )
    frappe.throw(
        _("Unsupported block props type: {props_type}").format(props_type=type(raw_props)),
        frappe.ValidationError,
    )


def _get_block_row_value(row: Any, fieldname: str):
    if isinstance(row, dict):
        return row.get(fieldname)
    return getattr(row, fieldname, None)


def is_block_enabled(row: Any) -> bool:
    value = _get_block_row_value(row, "is_enabled")
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return bool(str(_get_block_row_value(row, "block_type") or "").strip())
    return int(value or 0) == 1


def apply_missing_block_enabled_defaults(rows: Any) -> None:
    for row in rows or []:
        value = _get_block_row_value(row, "is_enabled")
        if value not in (None, ""):
            continue
        if not str(_get_block_row_value(row, "block_type") or "").strip():
            continue
        if isinstance(row, dict):
            row["is_enabled"] = 1
            continue
        setattr(row, "is_enabled", 1)


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
                _("Invalid props schema JSON: {error}").format(error=str(exc)),
                frappe.ValidationError,
            )
    frappe.throw(
        _("Unsupported props schema type: {schema_type}").format(schema_type=type(raw_schema)),
        frappe.ValidationError,
    )


def _json_type_matches(value: Any, expected_type: str) -> bool:
    if expected_type == "object":
        return isinstance(value, dict)
    if expected_type == "array":
        return isinstance(value, list)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "null":
        return value is None
    return True


def _format_error_path(path: tuple[Any, ...]) -> str:
    return ".".join([str(part) for part in path]) if path else "(root)"


def _basic_schema_errors(value: Any, schema: dict, path: tuple[Any, ...] = ()) -> list[tuple[tuple[Any, ...], str]]:
    errors: list[tuple[tuple[Any, ...], str]] = []
    if not isinstance(schema, dict):
        return errors

    expected = schema.get("type")
    if expected:
        expected_types = expected if isinstance(expected, list) else [expected]
        if not any(_json_type_matches(value, t) for t in expected_types):
            expected_text = ", ".join(str(t) for t in expected_types)
            errors.append((path, f"Expected type: {expected_text}."))
            return errors

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and value not in enum_values:
        errors.append((path, f"Value must be one of: {enum_values}."))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            errors.append((path, f"Value must be greater than or equal to {minimum}."))
        if maximum is not None and value > maximum:
            errors.append((path, f"Value must be less than or equal to {maximum}."))

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < int(min_items):
            errors.append((path, f"At least {int(min_items)} item(s) are required."))
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item_value in enumerate(value):
                errors.extend(_basic_schema_errors(item_value, item_schema, path + (index,)))

    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        required = schema.get("required") or []
        for required_key in required:
            if required_key not in value:
                errors.append((path + (required_key,), "This field is required."))

        additional = schema.get("additionalProperties", True)
        if additional is False:
            for key in value:
                if key not in properties:
                    errors.append((path + (key,), "Additional properties are not allowed."))

        for key, child_value in value.items():
            child_schema = properties.get(key)
            if isinstance(child_schema, dict):
                errors.extend(_basic_schema_errors(child_value, child_schema, path + (key,)))

    return errors


def validate_props_schema(props: dict, raw_schema: Any, *, block_type: str):
    schema = _load_schema(raw_schema)
    if not schema:
        frappe.throw(
            _("Missing props schema for block type: {block_type}").format(block_type=block_type),
            frappe.ValidationError,
        )

    errors: list[tuple[tuple[Any, ...], str]] = []
    try:
        from jsonschema import Draft7Validator

        validator = Draft7Validator(schema)
        errors = sorted(
            [(tuple(err.path), err.message) for err in validator.iter_errors(props)],
            key=lambda item: list(item[0]),
        )
    except Exception:
        errors = sorted(_basic_schema_errors(props, schema), key=lambda item: list(item[0]))

    if errors:
        formatted = []
        for path, message in errors:
            formatted.append(f"{_format_error_path(path)}: {message}")
        message = "\n".join(formatted)
        frappe.throw(
            _("Invalid props for block '{block_type}':\n{message}").format(
                block_type=block_type,
                message=message,
            ),
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
        _("CTA link must be an internal path or https URL: {link}").format(link=clean),
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
    return normalize_route(f"/schools/{school_slug}/programs/{program_slug}")


def build_courses_index_url(*, school_slug: str) -> str:
    return normalize_route(f"/schools/{school_slug}/courses")


def build_course_profile_url(*, school_slug: str, course_slug: str) -> str:
    return normalize_route(f"/schools/{school_slug}/courses/{course_slug}")


def build_story_url(*, school_slug: str, story_slug: str) -> str:
    return normalize_route(f"/schools/{school_slug}/stories/{story_slug}")


def build_employee_profile_url(*, school_slug: str, employee_slug: str) -> str:
    return normalize_route(f"/schools/{school_slug}/people/{employee_slug}")


def resolve_admissions_cta_url(*, school, intent: str) -> str:
    field_priority_map = {
        "inquire": ("admissions_inquiry_route", "/apply/inquiry"),
        "visit": ("admissions_visit_route", "admissions_inquiry_route", "admissions_apply_route", "/apply/inquiry"),
        "apply": ("admissions_apply_route", "admissions_inquiry_route", "/admissions"),
    }
    candidates = field_priority_map.get(intent)
    if not candidates:
        frappe.throw(
            _("Unknown admissions intent: {intent}").format(intent=intent),
            frappe.ValidationError,
        )

    for candidate in candidates:
        if candidate.startswith("/"):
            return validate_cta_link(candidate)

        link = school.get(candidate)
        if link:
            return validate_cta_link(link)

    frappe.throw(
        _("Admissions CTA target missing for intent: {intent}.").format(intent=intent),
        frappe.ValidationError,
    )
