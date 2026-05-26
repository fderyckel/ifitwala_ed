# ifitwala_ed/admission/api/common/request_payload.py

from __future__ import annotations

import frappe


def _has_bound_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _parse_request_payload(value) -> dict | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            value = value.decode()
        except Exception:
            return None
    if isinstance(value, str):
        try:
            value = frappe.parse_json(value)
        except Exception:
            return None
        if isinstance(value, dict):
            return value
    return None


def _request_json_payload() -> dict:
    request = getattr(frappe, "request", None)
    if not request:
        return {}

    get_json = getattr(request, "get_json", None)
    if callable(get_json):
        try:
            payload = get_json(silent=True)
        except TypeError:
            try:
                payload = get_json()
            except Exception:
                payload = None
        except Exception:
            payload = None
        parsed_payload = _parse_request_payload(payload)
        if isinstance(parsed_payload, dict):
            return parsed_payload

    parsed_payload = _parse_request_payload(getattr(request, "data", None))
    if isinstance(parsed_payload, dict):
        return parsed_payload
    return {}


def _request_form_value(key: str, current_value=None):
    if _has_bound_value(current_value):
        return current_value

    form_dict = getattr(frappe, "form_dict", None)
    if form_dict and hasattr(form_dict, "get"):
        value = form_dict.get(key)
        if _has_bound_value(value):
            return value

        args = _parse_request_payload(form_dict.get("args"))
        if isinstance(args, dict):
            value = args.get(key)
            if _has_bound_value(value):
                return value

    request_payload = _request_json_payload()
    value = request_payload.get(key)
    if _has_bound_value(value):
        return value

    args = _parse_request_payload(request_payload.get("args"))
    if isinstance(args, dict):
        value = args.get(key)
        if _has_bound_value(value):
            return value

    return current_value


def _as_check(value) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    normalized = str(value or "").strip().lower()
    return 1 if normalized in {"1", "true", "yes", "on"} else 0


def _as_bool(value) -> bool:
    return bool(_as_check(value))
