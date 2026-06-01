# ifitwala_ed/admission/api/recommendation_intake/dto.py

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, get_datetime


def _normalize_payload(payload, kwargs):
    if isinstance(payload, str):
        payload = frappe.parse_json(payload)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        frappe.throw(_("payload must be a JSON object."))
    data = dict(payload)
    for key, value in (kwargs or {}).items():
        if key in data:
            continue
        data[key] = value
    return data


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _text(value) -> str:
    return str(value or "").strip()


def _parse_select_options(text: str | None) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    try:
        parsed = frappe.parse_json(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item or "").strip()]
    except Exception:
        pass
    tokens = []
    for line in raw.split("\n"):
        for chunk in line.split(","):
            token = chunk.strip()
            if token:
                tokens.append(token)
    return tokens


def _normalize_keyed_option_list(values) -> list[dict]:
    if not isinstance(values, list):
        return []

    normalized = []
    seen = set()
    for value in values:
        if isinstance(value, dict):
            label = _text(value.get("label") or value.get("key"))
            key = frappe.scrub(_text(value.get("key") or label))[:80]
        else:
            label = _text(value)
            key = frappe.scrub(label)[:80]

        if not key or not label or key in seen:
            continue
        seen.add(key)
        normalized.append({"key": key, "label": label})

    return normalized


def _parse_likert_options(text: str | None) -> dict:
    raw = _text(text)
    if not raw:
        return {"version": 1, "columns": [], "rows": []}
    try:
        parsed = frappe.parse_json(raw)
    except Exception:
        parsed = None
    if not isinstance(parsed, dict):
        return {"version": 1, "columns": [], "rows": []}

    return {
        "version": 1,
        "columns": _normalize_keyed_option_list(parsed.get("columns")),
        "rows": _normalize_keyed_option_list(parsed.get("rows")),
    }


def _parse_template_field_options(*, field_type: str, options_json: str | None):
    if field_type == "Likert Scale":
        return _parse_likert_options(options_json)
    return _parse_select_options(options_json)


def _normalize_answers(snapshot: dict, answers: dict) -> dict:
    if not isinstance(answers, dict):
        frappe.throw(_("answers must be an object."), frappe.ValidationError)

    normalized = {}
    fields = snapshot.get("fields") or []
    for field in fields:
        key = (field.get("field_key") or "").strip()
        label = (field.get("label") or key).strip()
        field_type = (field.get("field_type") or "Data").strip()
        required = bool(field.get("is_required"))
        options = field.get("options") or []
        raw_value = answers.get(key)

        if field_type == "Section Header":
            continue
        if field_type == "Check":
            value = 1 if _as_bool(raw_value) else 0
            if required and not value:
                frappe.throw(
                    _("Required field is missing: {field_label}.").format(field_label=label),
                    frappe.ValidationError,
                )
        elif field_type == "Likert Scale":
            normalized_likert = _normalize_likert_answer(
                label=label,
                required=required,
                options=options,
                raw_value=raw_value,
            )
            normalized[key] = {
                "label": label,
                "field_type": field_type,
                "value": normalized_likert["value"],
                "likert_columns": normalized_likert["columns"],
                "likert_rows": normalized_likert["rows"],
            }
            continue
        else:
            value = "" if raw_value is None else str(raw_value).strip()
            if required and not value:
                frappe.throw(
                    _("Required field is missing: {field_label}.").format(field_label=label),
                    frappe.ValidationError,
                )
            select_options = [str(option).strip() for option in options if str(option).strip()]
            if field_type == "Select" and value and select_options and value not in select_options:
                frappe.throw(
                    _("Invalid option for {field_label}.").format(field_label=label),
                    frappe.ValidationError,
                )

        normalized[key] = {
            "label": label,
            "field_type": field_type,
            "value": value,
        }

    return normalized


def _normalize_likert_answer(*, label: str, required: bool, options, raw_value) -> dict:
    if not isinstance(options, dict):
        options = {}
    columns = _normalize_keyed_option_list(options.get("columns"))
    rows = _normalize_keyed_option_list(options.get("rows"))
    allowed_columns = {column.get("key") for column in columns if column.get("key")}
    allowed_rows = {row.get("key") for row in rows if row.get("key")}

    if not columns or not rows:
        frappe.throw(_("Likert Scale field {field_label} is not configured correctly.").format(field_label=label))

    if raw_value in (None, ""):
        raw_value = {}
    if not isinstance(raw_value, dict):
        frappe.throw(_("Invalid Likert Scale response for {field_label}.").format(field_label=label))

    normalized_value = {}
    for row in rows:
        row_key = row.get("key")
        selected = _text(raw_value.get(row_key))
        if not selected:
            if required:
                frappe.throw(
                    _("Required field is missing: {field_label}.").format(field_label=label),
                    frappe.ValidationError,
                )
            continue
        if row_key not in allowed_rows or selected not in allowed_columns:
            frappe.throw(_("Invalid Likert Scale response for {field_label}.").format(field_label=label))
        normalized_value[row_key] = selected

    for row_key in raw_value:
        if _text(row_key) not in allowed_rows:
            frappe.throw(_("Invalid Likert Scale response for {field_label}.").format(field_label=label))

    return {
        "value": normalized_value,
        "columns": columns,
        "rows": rows,
    }


def _parse_answers_payload(data: dict) -> dict:
    answers = data.get("answers")
    if answers is None:
        answers = data.get("answers_json")

    if isinstance(answers, str):
        text = answers.strip()
        if not text:
            return {}
        parsed = frappe.parse_json(text)
        if isinstance(parsed, dict):
            return parsed
        frappe.throw(_("answers must be a JSON object."), frappe.ValidationError)
    if isinstance(answers, dict):
        return answers
    if answers is None:
        return {}
    frappe.throw(_("answers must be a JSON object."), frappe.ValidationError)
    return {}


def _sort_datetime_value(value) -> str:
    if not value:
        return ""
    try:
        return get_datetime(value).isoformat()
    except Exception:
        return str(value or "")


def _render_likert_answer_value(*, value, columns, rows) -> str:
    if not isinstance(value, dict):
        return ""

    column_labels = {
        _text(column.get("key")): _text(column.get("label"))
        for column in _normalize_keyed_option_list(columns)
        if _text(column.get("key"))
    }
    lines = []
    for row in _normalize_keyed_option_list(rows):
        row_key = _text(row.get("key"))
        selected_key = _text(value.get(row_key))
        selected_label = column_labels.get(selected_key)
        if selected_label:
            lines.append(
                _("{row_label}: {selected_label}").format(
                    row_label=row.get("label"),
                    selected_label=selected_label,
                )
            )
    return "\n".join(lines)


def _render_recommendation_answer_value(field_type: str, value, *, columns=None, rows=None) -> str:
    normalized_type = (field_type or "Data").strip()
    if normalized_type == "Check":
        return _("Yes") if cint(value) else _("No")
    if normalized_type == "Likert Scale":
        return _render_likert_answer_value(value=value, columns=columns or [], rows=rows or [])
    if value is None:
        return ""
    text = str(value).strip()
    return text


def _likert_metadata_from_field_options(options) -> tuple[list, list]:
    if not isinstance(options, dict):
        return [], []
    return options.get("columns") or [], options.get("rows") or []


def _build_recommendation_answer_rows(snapshot: dict, answers_json: str | None) -> list[dict]:
    parsed_answers = {}
    if answers_json:
        try:
            candidate = frappe.parse_json(answers_json)
            if isinstance(candidate, dict):
                parsed_answers = candidate
        except Exception:
            parsed_answers = {}

    rows: list[dict] = []
    seen_keys: set[str] = set()

    for field in snapshot.get("fields") or []:
        field_key = frappe.scrub((field.get("field_key") or "").strip())[:80]
        if not field_key:
            continue
        snapshot_field_type = (field.get("field_type") or "Data").strip()
        if snapshot_field_type == "Section Header":
            continue

        answer_entry = parsed_answers.get(field_key)
        if isinstance(answer_entry, dict):
            value = answer_entry.get("value")
            label = (answer_entry.get("label") or field.get("label") or field_key).strip()
            field_type = (answer_entry.get("field_type") or snapshot_field_type).strip()
            if field_type == "Likert Scale":
                snapshot_columns, snapshot_rows = _likert_metadata_from_field_options(field.get("options"))
                likert_columns = answer_entry.get("likert_columns") or snapshot_columns
                likert_rows = answer_entry.get("likert_rows") or snapshot_rows
            else:
                likert_columns = []
                likert_rows = []
        else:
            value = answer_entry
            label = (field.get("label") or field_key).strip()
            field_type = snapshot_field_type
            if field_type == "Likert Scale":
                likert_columns, likert_rows = _likert_metadata_from_field_options(field.get("options"))
            else:
                likert_columns = []
                likert_rows = []

        display_value = _render_recommendation_answer_value(
            field_type,
            value,
            columns=likert_columns,
            rows=likert_rows,
        )
        rows.append(
            {
                "field_key": field_key,
                "label": label or field_key,
                "field_type": field_type,
                "value": value,
                "display_value": display_value,
                "has_value": True if field_type == "Check" else bool(display_value),
                "likert_columns": _normalize_keyed_option_list(likert_columns) if field_type == "Likert Scale" else [],
                "likert_rows": _normalize_keyed_option_list(likert_rows) if field_type == "Likert Scale" else [],
            }
        )
        seen_keys.add(field_key)

    for field_key, answer_entry in parsed_answers.items():
        normalized_key = frappe.scrub((field_key or "").strip())[:80]
        if not normalized_key or normalized_key in seen_keys:
            continue

        if isinstance(answer_entry, dict):
            value = answer_entry.get("value")
            label = (answer_entry.get("label") or normalized_key).strip()
            field_type = (answer_entry.get("field_type") or "Data").strip()
            likert_columns = answer_entry.get("likert_columns") or []
            likert_rows = answer_entry.get("likert_rows") or []
        else:
            value = answer_entry
            label = normalized_key
            field_type = "Data"
            likert_columns = []
            likert_rows = []

        display_value = _render_recommendation_answer_value(
            field_type,
            value,
            columns=likert_columns,
            rows=likert_rows,
        )
        rows.append(
            {
                "field_key": normalized_key,
                "label": label or normalized_key,
                "field_type": field_type,
                "value": value,
                "display_value": display_value,
                "has_value": True if field_type == "Check" else bool(display_value),
                "likert_columns": _normalize_keyed_option_list(likert_columns) if field_type == "Likert Scale" else [],
                "likert_rows": _normalize_keyed_option_list(likert_rows) if field_type == "Likert Scale" else [],
            }
        )

    return rows
