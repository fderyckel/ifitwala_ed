# ifitwala_ed/schedule/api/calendar/quick_create/dto.py

from __future__ import annotations

import json
from datetime import date, datetime
from hashlib import sha1
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import format_datetime, get_datetime, get_time, getdate

from ifitwala_ed.schedule.api.calendar.core import _coerce_time
from ifitwala_ed.schedule.api.calendar.quick_create.constants import QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS


def _split_select_options(raw: str | None) -> list[str]:
    options = []
    seen = set()
    for line in (raw or "").splitlines():
        value = (line or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        options.append(value)
    return options


def _safe_text(value: object | None) -> str:
    return str(value or "").strip()


def _desk_route_slug(doctype: str) -> str:
    return frappe.scrub(doctype).replace("_", "-")


def _doc_url(doctype: str, name: str) -> str:
    slug = _desk_route_slug(doctype)
    return f"/desk/{slug}/{quote(_safe_text(name), safe='')}"


def _parse_user_list(value: object | None) -> list[str]:
    if value is None:
        return []

    raw = value
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                raw = frappe.parse_json(text)
            except Exception:
                raw = [part.strip() for part in text.split(",")]
        else:
            raw = [part.strip() for part in text.split(",")]

    users: list[str] = []
    seen = set()

    if not isinstance(raw, list):
        raw = [raw]

    for item in raw:
        if isinstance(item, dict):
            candidate = item.get("participant") or item.get("user") or item.get("value")
        else:
            candidate = item
        user_id = _safe_text(candidate)
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        users.append(user_id)

    return users


def _parse_attendee_list(value: object | None) -> list[dict]:
    if value is None:
        return []

    raw = value
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            raw = frappe.parse_json(text)
        except Exception:
            raw = [{"user": part.strip()} for part in text.split(",")]

    if not isinstance(raw, list):
        raw = [raw]

    attendees: list[dict] = []
    seen = set()
    for item in raw:
        if isinstance(item, dict):
            user_id = _safe_text(item.get("user") or item.get("participant") or item.get("value"))
            kind = _safe_text(item.get("kind")).lower()
            label = _safe_text(item.get("label"))
        else:
            user_id = _safe_text(item)
            kind = ""
            label = ""
        if not user_id or user_id in seen:
            continue
        seen.add(user_id)
        attendees.append({"user": user_id, "kind": kind, "label": label})
    return attendees


def _normalize_attendee_kinds(value: object | None) -> list[str]:
    raw = value
    if raw is None:
        return ["employee", "student", "guardian"]
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return ["employee", "student", "guardian"]
        if text.startswith("["):
            try:
                raw = frappe.parse_json(text)
            except Exception:
                raw = [part.strip() for part in text.split(",")]
        else:
            raw = [part.strip() for part in text.split(",")]
    if not isinstance(raw, list):
        raw = [raw]
    kinds: list[str] = []
    seen = set()
    for item in raw:
        kind = _safe_text(item).lower()
        if kind not in {"employee", "student", "guardian"} or kind in seen:
            continue
        seen.add(kind)
        kinds.append(kind)
    return kinds or ["employee", "student", "guardian"]


def _json_cache_key(prefix: str, payload: dict) -> str:
    digest = sha1(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _idempotency_key(doctype: str, user: str, client_request_id: str) -> str:
    return f"ifitwala_ed:event_quick_create:{doctype}:{user}:{client_request_id}"


def _run_idempotent_create(
    *,
    doctype: str,
    user: str,
    client_request_id: str,
    create_fn,
) -> dict:
    cache = frappe.cache()
    cache_key = _idempotency_key(doctype, user, client_request_id)

    existing = cache.get_value(cache_key)
    if existing:
        parsed = frappe.parse_json(existing)
        if isinstance(parsed, dict):
            return {**parsed, "status": "already_processed", "idempotent": True}

    lock_key = f"ifitwala_ed:lock:event_quick_create:{doctype}:{user}:{client_request_id}"
    with cache.lock(lock_key, timeout=15):
        existing = cache.get_value(cache_key)
        if existing:
            parsed = frappe.parse_json(existing)
            if isinstance(parsed, dict):
                return {**parsed, "status": "already_processed", "idempotent": True}

        result = create_fn()
        cache.set_value(cache_key, frappe.as_json(result), expires_in_sec=QUICK_CREATE_IDEMPOTENCY_TTL_SECONDS)
        return result


def _target_payload(*, doctype: str, name: str, label: str) -> dict:
    return {
        "target_doctype": doctype,
        "target_name": name,
        "target_url": _doc_url(doctype, name),
        "target_label": label,
    }


def _coerce_minutes(value: object | None, *, default: int, minimum: int, maximum: int, label: str) -> int:
    try:
        minutes = int(value or default)
    except Exception:
        frappe.throw(_("{label} must be a whole number.").format(label=label))
    if minutes < minimum or minutes > maximum:
        frappe.throw(
            _("{label} must be between {minimum} and {maximum}.").format(
                label=label,
                minimum=minimum,
                maximum=maximum,
            )
        )
    return minutes


def _coerce_date_required(value: object | None, label: str) -> date:
    try:
        parsed = getdate(value)
    except Exception:
        parsed = None
    if not parsed:
        frappe.throw(_("{label} is required.").format(label=label))
    return parsed


def _coerce_time_required(value: object | None, label: str):
    parsed = _coerce_time(value)
    if not parsed:
        try:
            parsed = get_time(value)
        except Exception:
            parsed = None
    if not parsed:
        frappe.throw(_("{label} is required.").format(label=label))
    return parsed


def _coerce_flag(value: object | None) -> bool:
    if isinstance(value, bool):
        return value
    text = _safe_text(value).lower()
    if text in {"", "0", "false", "no"}:
        return False
    if text in {"1", "true", "yes"}:
        return True
    return bool(value)


def _combine_date_and_time_local(day: date, time_value) -> datetime:
    return get_datetime(f"{day.isoformat()} {time_value}")


def _format_slot_label(start_dt: datetime, end_dt: datetime) -> str:
    return f"{format_datetime(start_dt, 'EEE d MMM yyyy HH:mm')} - {format_datetime(end_dt, 'HH:mm')}"


def _current_user_label(user: str) -> str:
    return frappe.db.get_value("User", user, "full_name") or user
