# ifitwala_ed/website/seo_checks.py

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import strip_html

from ifitwala_ed.website.block_registry import get_block_definition_map


SEO_TITLE_MAX = 60
SEO_DESCRIPTION_MAX = 160
ALLOWED_PARENT_DOCTYPES = {
	"School Website Page",
	"Program Website Profile",
	"Website Story",
}


def _coerce_doc_payload(doc_json: Any) -> dict:
	if not doc_json:
		return {}
	if isinstance(doc_json, dict):
		return doc_json
	if isinstance(doc_json, str):
		try:
			parsed = frappe.parse_json(doc_json)
		except Exception:
			try:
				parsed = json.loads(doc_json)
			except Exception as exc:
				frappe.throw(
					_("Invalid SEO check payload: {0}").format(str(exc)),
					frappe.ValidationError,
				)
		if isinstance(parsed, dict):
			return parsed
	frappe.throw(
		_("Invalid SEO check payload shape."),
		frappe.ValidationError,
	)


def _coerce_blocks(rows: Any) -> list[dict]:
	if not isinstance(rows, list):
		return []
	result = []
	for row in rows:
		if isinstance(row, dict):
			result.append(row)
	return result


def _is_enabled(row: dict) -> bool:
	value = row.get("is_enabled")
	if isinstance(value, bool):
		return value
	return int(value or 0) == 1


def _sort_rank(row: dict) -> float:
	for key in ("order", "idx"):
		value = row.get(key)
		try:
			return float(value)
		except Exception:
			pass
	return 999999.0


def _enabled_blocks(payload: dict) -> list[dict]:
	rows = [row for row in _coerce_blocks(payload.get("blocks")) if _is_enabled(row)]
	return sorted(rows, key=_sort_rank)


def _safe_parse_props(raw_props: Any) -> tuple[dict, bool]:
	if not raw_props:
		return {}, False
	if isinstance(raw_props, dict):
		return raw_props, False
	if isinstance(raw_props, str):
		try:
			parsed = json.loads(raw_props)
		except Exception:
			return {}, True
		return (parsed if isinstance(parsed, dict) else {}), False
	return {}, True


def _load_seo_profile(seo_profile: str | None) -> dict:
	seo_profile = (seo_profile or "").strip()
	if not seo_profile:
		return {}
	row = frappe.db.get_value(
		"Website SEO Profile",
		seo_profile,
		[
			"meta_title",
			"meta_description",
			"og_title",
			"og_description",
			"og_image",
			"canonical_url",
			"noindex",
		],
		as_dict=True,
	)
	return dict(row or {})


def _get_program_title(program_name: str | None) -> str | None:
	program_name = (program_name or "").strip()
	if not program_name:
		return None
	value = frappe.db.get_value("Program", program_name, "program_name")
	return (value or "").strip() or program_name


def _resolve_meta_fields(*, parent_doctype: str, payload: dict, seo_profile: dict) -> dict:
	meta_title = (seo_profile.get("meta_title") or "").strip()
	meta_description = (seo_profile.get("meta_description") or "").strip()
	og_image = (seo_profile.get("og_image") or "").strip()

	if not meta_title:
		if parent_doctype == "School Website Page":
			meta_title = (payload.get("title") or "").strip()
		elif parent_doctype == "Program Website Profile":
			meta_title = _get_program_title(payload.get("program")) or ""
		elif parent_doctype == "Website Story":
			meta_title = (payload.get("title") or "").strip()

	if not meta_description:
		if parent_doctype == "School Website Page":
			meta_description = (payload.get("meta_description") or "").strip()
		elif parent_doctype == "Program Website Profile":
			meta_description = strip_html(payload.get("intro_text") or "").strip()

	return {
		"meta_title": meta_title,
		"meta_description": meta_description,
		"og_image": og_image,
		"noindex": bool(seo_profile.get("noindex")),
	}


def _add_check(checks: list[dict], *, code: str, severity: str, message: str):
	checks.append(
		{
			"code": code,
			"severity": severity,
			"message": message,
		}
	)


def _check_h1_ownership(*, checks: list[dict], enabled_blocks: list[dict], definitions: dict):
	if not enabled_blocks:
		_add_check(
			checks,
			code="h1_no_enabled_blocks",
			severity="error",
			message=_("No enabled blocks found. Add at least one block."),
		)
		return

	unknown = sorted(
		{
			(row.get("block_type") or "").strip()
			for row in enabled_blocks
			if (row.get("block_type") or "").strip() not in definitions
		}
	)
	if unknown:
		_add_check(
			checks,
			code="h1_unknown_block_type",
			severity="warning",
			message=_("Unknown block type(s) in enabled rows: {0}").format(", ".join(unknown)),
		)
		return

	roles = [definitions[(row.get("block_type") or "").strip()]["seo_role"] for row in enabled_blocks]
	owns_h1_count = sum(1 for role in roles if role == "owns_h1")
	if owns_h1_count != 1:
		_add_check(
			checks,
			code="h1_owner_count",
			severity="error",
			message=_("Exactly one enabled block must own the H1. Found {0}.").format(owns_h1_count),
		)

	first_type = (enabled_blocks[0].get("block_type") or "").strip()
	first_role = definitions.get(first_type, {}).get("seo_role")
	if first_role != "owns_h1":
		_add_check(
			checks,
			code="h1_first_block",
			severity="error",
			message=_("The first enabled block must own the H1."),
		)


def _has_cta(*, enabled_blocks: list[dict]) -> bool:
	for row in enabled_blocks:
		block_type = (row.get("block_type") or "").strip()
		props, _invalid = _safe_parse_props(row.get("props"))

		if block_type in {"cta", "admission_cta"}:
			return True
		if block_type == "hero" and (props.get("cta_link") or "").strip():
			return True
		if block_type == "program_intro" and (props.get("cta_intent") or "").strip():
			return True
	return False


def _check_missing_cta(*, checks: list[dict], parent_doctype: str, payload: dict, enabled_blocks: list[dict]):
	has_cta = _has_cta(enabled_blocks=enabled_blocks)
	if parent_doctype == "School Website Page":
		page_type = (payload.get("page_type") or "").strip()
		if page_type == "Admissions" and not has_cta:
			_add_check(
				checks,
				code="cta_missing_admissions",
				severity="warning",
				message=_("Admissions pages should include at least one CTA block."),
			)
	elif parent_doctype == "Program Website Profile":
		if not has_cta:
			_add_check(
				checks,
				code="cta_missing_program",
				severity="warning",
				message=_("Program pages should include at least one CTA."),
			)


def _check_schema_readiness(*, checks: list[dict], enabled_blocks: list[dict]):
	faq_rows = [row for row in enabled_blocks if (row.get("block_type") or "").strip() == "faq"]
	if not faq_rows:
		return

	has_schema_enabled = False
	for row in faq_rows:
		props, invalid_json = _safe_parse_props(row.get("props"))
		if invalid_json:
			_add_check(
				checks,
				code="schema_invalid_faq_props",
				severity="warning",
				message=_("FAQ block has invalid props JSON; schema readiness cannot be confirmed."),
			)
			continue
		if bool(props.get("enable_schema")):
			has_schema_enabled = True

	if not has_schema_enabled:
		_add_check(
			checks,
			code="schema_faq_disabled",
			severity="warning",
			message=_("FAQ schema is not enabled on FAQ blocks."),
		)


def _check_meta_quality(*, checks: list[dict], meta: dict):
	meta_title = meta.get("meta_title") or ""
	meta_description = meta.get("meta_description") or ""
	og_image = meta.get("og_image") or ""

	if not meta_title:
		_add_check(
			checks,
			code="meta_title_missing",
			severity="warning",
			message=_("Meta title is missing."),
		)
	elif len(meta_title) > SEO_TITLE_MAX:
		_add_check(
			checks,
			code="meta_title_too_long",
			severity="warning",
			message=_("Meta title should be <= {0} characters (current: {1}).").format(
				SEO_TITLE_MAX,
				len(meta_title),
			),
		)

	if not meta_description:
		_add_check(
			checks,
			code="meta_description_missing",
			severity="warning",
			message=_("Meta description is missing."),
		)
	elif len(meta_description) > SEO_DESCRIPTION_MAX:
		_add_check(
			checks,
			code="meta_description_too_long",
			severity="warning",
			message=_("Meta description should be <= {0} characters (current: {1}).").format(
				SEO_DESCRIPTION_MAX,
				len(meta_description),
			),
		)

	if not og_image:
		_add_check(
			checks,
			code="og_image_missing",
			severity="warning",
			message=_("OG image is missing."),
		)

	if meta.get("noindex"):
		_add_check(
			checks,
			code="noindex_enabled",
			severity="warning",
			message=_("Noindex is enabled for this page."),
		)


def build_seo_assistant_report(*, parent_doctype: str, doc_payload: dict) -> dict:
	parent_doctype = (parent_doctype or "").strip()
	if parent_doctype not in ALLOWED_PARENT_DOCTYPES:
		frappe.throw(
			_("Unsupported parent doctype for SEO checks: {0}").format(parent_doctype),
			frappe.ValidationError,
		)

	payload = doc_payload or {}
	enabled_blocks = _enabled_blocks(payload)
	definitions = get_block_definition_map()
	seo_profile = _load_seo_profile(payload.get("seo_profile"))
	meta = _resolve_meta_fields(
		parent_doctype=parent_doctype,
		payload=payload,
		seo_profile=seo_profile,
	)

	checks: list[dict] = []
	_check_h1_ownership(checks=checks, enabled_blocks=enabled_blocks, definitions=definitions)
	_check_meta_quality(checks=checks, meta=meta)
	_check_missing_cta(
		checks=checks,
		parent_doctype=parent_doctype,
		payload=payload,
		enabled_blocks=enabled_blocks,
	)
	_check_schema_readiness(checks=checks, enabled_blocks=enabled_blocks)

	error_count = sum(1 for row in checks if row.get("severity") == "error")
	warning_count = sum(1 for row in checks if row.get("severity") == "warning")
	status = "ok"
	if error_count:
		status = "error"
	elif warning_count:
		status = "warning"

	return {
		"status": status,
		"summary": {
			"errors": error_count,
			"warnings": warning_count,
		},
		"checks": checks,
		"meta": {
			"meta_title_length": len(meta.get("meta_title") or ""),
			"meta_description_length": len(meta.get("meta_description") or ""),
		},
	}


@frappe.whitelist()
def get_seo_assistant_report(parent_doctype: str, doc_json: Any = None) -> dict:
	doc_payload = _coerce_doc_payload(doc_json)
	return build_seo_assistant_report(
		parent_doctype=parent_doctype,
		doc_payload=doc_payload,
	)
