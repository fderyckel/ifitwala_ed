# ifitwala_ed/website/block_registry.py

import copy
import json
from typing import Any

import frappe
from frappe import _


WEBSITE_BLOCK_DEFINITIONS = [
	{
		"block_type": "hero",
		"label": "Hero",
		"template_path": "ifitwala_ed/website/blocks/hero.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.hero.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"title": {"type": "string"},
				"subtitle": {"type": "string"},
				"background_image": {"type": "string"},
				"images": {
					"type": "array",
					"items": {
						"type": "object",
						"properties": {
							"image": {"type": "string"},
							"alt": {"type": "string"},
							"caption": {"type": "string"},
						},
						"required": ["image"],
						"additionalProperties": False,
					},
				},
				"autoplay": {"type": "boolean"},
				"interval": {"type": "integer", "minimum": 1000},
				"variant": {"type": "string", "enum": ["default", "split", "centered"]},
				"cta_label": {"type": "string"},
				"cta_link": {"type": "string"},
			},
			"required": ["title"],
			"additionalProperties": False,
		},
		"seo_role": "owns_h1",
		"is_core": 1,
	},
	{
		"block_type": "admissions_overview",
		"label": "Admissions Overview",
		"template_path": "ifitwala_ed/website/blocks/admissions_overview.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.admissions_overview.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"heading": {"type": "string"},
				"content_html": {"type": "string"},
				"max_width": {"type": "string", "enum": ["narrow", "normal", "wide"]},
			},
			"required": ["heading", "content_html"],
			"additionalProperties": False,
		},
		"seo_role": "owns_h1",
		"is_core": 1,
	},
	{
		"block_type": "admissions_steps",
		"label": "Admissions Steps",
		"template_path": "ifitwala_ed/website/blocks/admissions_steps.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.admissions_steps.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"steps": {
					"type": "array",
					"minItems": 2,
					"items": {
						"type": "object",
						"properties": {
							"key": {"type": "string"},
							"title": {"type": "string"},
							"description": {"type": "string"},
							"icon": {"type": ["string", "null"]},
						},
						"required": ["key", "title"],
						"additionalProperties": False,
					},
				},
				"layout": {"type": "string", "enum": ["horizontal", "vertical"]},
			},
			"required": ["steps"],
			"additionalProperties": False,
		},
		"seo_role": "supporting",
		"is_core": 1,
	},
	{
		"block_type": "admission_cta",
		"label": "Admission CTA",
		"template_path": "ifitwala_ed/website/blocks/admission_cta.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.admission_cta.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"intent": {"type": "string", "enum": ["inquire", "visit", "apply"]},
				"label_override": {"type": ["string", "null"]},
				"style": {"type": "string", "enum": ["primary", "secondary", "outline"]},
				"icon": {"type": ["string", "null"], "enum": ["mail", "map", "file-text", None]},
				"tracking_id": {"type": ["string", "null"]},
			},
			"required": ["intent"],
			"additionalProperties": False,
		},
		"seo_role": "supporting",
		"is_core": 1,
	},
	{
		"block_type": "faq",
		"label": "FAQ",
		"template_path": "ifitwala_ed/website/blocks/faq.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.faq.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"items": {
					"type": "array",
					"minItems": 1,
					"items": {
						"type": "object",
						"properties": {
							"question": {"type": "string"},
							"answer_html": {"type": "string"},
						},
						"required": ["question", "answer_html"],
						"additionalProperties": False,
					},
				},
				"enable_schema": {"type": "boolean"},
				"collapsed_by_default": {"type": "boolean"},
			},
			"required": ["items"],
			"additionalProperties": False,
		},
		"seo_role": "supporting",
		"is_core": 1,
	},
	{
		"block_type": "rich_text",
		"label": "Rich Text",
		"template_path": "ifitwala_ed/website/blocks/rich_text.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.rich_text.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"content_html": {"type": "string"},
				"max_width": {"type": "string", "enum": ["narrow", "normal", "wide"]},
			},
			"required": ["content_html"],
			"additionalProperties": False,
		},
		"seo_role": "content",
		"is_core": 1,
	},
	{
		"block_type": "content_snippet",
		"label": "Content Snippet",
		"template_path": "ifitwala_ed/website/blocks/content_snippet.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.content_snippet.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"snippet_id": {"type": "string"},
				"allow_override": {"type": "boolean"},
			},
			"required": ["snippet_id"],
			"additionalProperties": False,
		},
		"seo_role": "content",
		"is_core": 1,
	},
	{
		"block_type": "program_list",
		"label": "Program List",
		"template_path": "ifitwala_ed/website/blocks/program_list.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.program_list.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"school_scope": {"type": "string", "enum": ["current", "all"]},
				"show_intro": {"type": "boolean"},
				"card_style": {"type": "string", "enum": ["standard", "compact"]},
				"limit": {"type": ["integer", "null"], "minimum": 1},
			},
			"additionalProperties": False,
		},
		"seo_role": "supporting",
		"is_core": 1,
	},
	{
		"block_type": "program_intro",
		"label": "Program Intro",
		"template_path": "ifitwala_ed/website/blocks/program_intro.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.program_intro.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"heading": {"type": "string"},
				"content_html": {"type": "string"},
				"hero_image": {"type": ["string", "null"]},
				"cta_intent": {
					"type": ["string", "null"],
					"enum": ["inquire", "visit", "apply", None],
				},
			},
			"required": ["heading"],
			"additionalProperties": False,
		},
		"seo_role": "owns_h1",
		"is_core": 1,
	},
	{
		"block_type": "leadership",
		"label": "Leadership",
		"template_path": "ifitwala_ed/website/blocks/leadership.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.leadership.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"title": {"type": "string"},
				"roles": {"type": "array", "items": {"type": "string"}},
				"limit": {"type": "integer", "minimum": 1},
			},
			"additionalProperties": False,
		},
		"seo_role": "supporting",
		"is_core": 1,
	},
	{
		"block_type": "cta",
		"label": "CTA",
		"template_path": "ifitwala_ed/website/blocks/cta.html",
		"script_path": None,
		"provider_path": "ifitwala_ed.website.providers.cta.get_context",
		"props_schema": {
			"type": "object",
			"properties": {
				"title": {"type": "string"},
				"text": {"type": "string"},
				"button_label": {"type": "string"},
				"button_link": {"type": "string"},
			},
			"required": ["button_label", "button_link"],
			"additionalProperties": False,
		},
		"seo_role": "supporting",
		"is_core": 1,
	},
]


SYNC_FIELDS = (
	"label",
	"template_path",
	"script_path",
	"provider_path",
	"props_schema",
	"seo_role",
	"is_core",
)


def _normalize_schema(raw_schema: Any) -> str:
	if isinstance(raw_schema, str):
		try:
			raw_schema = json.loads(raw_schema)
		except Exception:
			return raw_schema
	return json.dumps(raw_schema or {}, sort_keys=True, separators=(",", ":"))


def _coerce_block_types(raw_block_types: Any) -> list[str]:
	if raw_block_types is None:
		return []
	if isinstance(raw_block_types, list):
		return [str(v).strip() for v in raw_block_types if str(v).strip()]
	if isinstance(raw_block_types, str):
		text = raw_block_types.strip()
		if not text:
			return []
		try:
			parsed = json.loads(text)
			if isinstance(parsed, list):
				return [str(v).strip() for v in parsed if str(v).strip()]
		except Exception:
			pass
		return [part.strip() for part in text.split(",") if part.strip()]
	return [str(raw_block_types).strip()]


def get_block_definition_map() -> dict[str, dict]:
	return {
		row["block_type"]: copy.deepcopy(row)
		for row in WEBSITE_BLOCK_DEFINITIONS
	}


def get_website_block_definition_records() -> list[dict]:
	records = []
	for row in WEBSITE_BLOCK_DEFINITIONS:
		record = copy.deepcopy(row)
		record["doctype"] = "Website Block Definition"
		record["props_schema"] = _normalize_schema(record.get("props_schema"))
		records.append(record)
	return records


def sync_website_block_definitions() -> dict:
	records = get_website_block_definition_records()
	records_by_type = {row["block_type"]: row for row in records}

	existing_rows = frappe.get_all(
		"Website Block Definition",
		fields=["name", "block_type"],
	)
	existing_by_type = {row.block_type: row.name for row in existing_rows}

	created = []
	updated = []
	for block_type, record in records_by_type.items():
		existing_name = existing_by_type.get(block_type)
		if not existing_name:
			frappe.get_doc(record).insert(ignore_permissions=True)
			created.append(block_type)
			continue

		doc = frappe.get_doc("Website Block Definition", existing_name)
		changed = False
		for field in SYNC_FIELDS:
			target = record.get(field)
			current = doc.get(field)
			if field == "props_schema":
				current = _normalize_schema(current)
			elif field == "is_core":
				current = int(current or 0)
				target = int(target or 0)
			elif field == "script_path":
				current = (current or "").strip() or None
				target = (target or "").strip() or None

			if current != target:
				doc.set(field, record.get(field))
				changed = True

		if changed:
			doc.save(ignore_permissions=True)
			updated.append(block_type)

	missing_in_registry = sorted(set(existing_by_type) - set(records_by_type))
	return {
		"created": created,
		"updated": updated,
		"missing_in_registry": missing_in_registry,
	}


@frappe.whitelist()
def get_block_definition_for_builder(block_type: str) -> dict:
	block_type = (block_type or "").strip()
	definition = get_block_definition_map().get(block_type)
	if not definition:
		frappe.throw(
			_("Unknown block type: {0}").format(block_type),
			frappe.ValidationError,
		)
	return {
		"block_type": definition["block_type"],
		"label": definition["label"],
		"props_schema": _normalize_schema(definition.get("props_schema")),
	}


@frappe.whitelist()
def get_block_definitions_for_builder(block_types=None) -> list[dict]:
	requested = _coerce_block_types(block_types)
	definitions = get_block_definition_map()
	if not requested:
		requested = list(definitions.keys())

	result = []
	for block_type in requested:
		definition = definitions.get(block_type)
		if not definition:
			continue
		result.append(
			{
				"block_type": definition["block_type"],
				"label": definition["label"],
				"props_schema": _normalize_schema(definition.get("props_schema")),
			}
		)
	return result
