# ifitwala_ed/admission/api/crm/idempotency.py

from __future__ import annotations

import frappe

from ifitwala_ed.admission.admissions_crm_domain import clean

IDEMPOTENCY_TTL_SECONDS = 60 * 10


def _cache():
    return frappe.cache()


def _cache_key(*parts: str) -> str:
    cleaned = [str(part or "").strip() for part in parts if str(part or "").strip()]
    return "ifitwala_ed:admissions_crm:" + ":".join(cleaned)


def _lock_key(*parts: str) -> str:
    return _cache_key("lock", *parts)


def _idempotency_key(*parts: str) -> str:
    return _cache_key("idempotency", *parts)


def _run_idempotent(*, user: str, action: str, target: str, client_request_id: str | None, fn):
    request_id = clean(client_request_id)
    cache = _cache()
    cache_key = None
    if request_id:
        cache_key = _idempotency_key(action, user, target, request_id)
        cached = cache.get_value(cache_key)
        if cached:
            return cached

    with cache.lock(_lock_key(action, user, target), timeout=10):
        if cache_key:
            cached = cache.get_value(cache_key)
            if cached:
                return cached

        response = fn()
        if cache_key:
            cache.set_value(cache_key, response, expires_in_sec=IDEMPOTENCY_TTL_SECONDS)
        return response
