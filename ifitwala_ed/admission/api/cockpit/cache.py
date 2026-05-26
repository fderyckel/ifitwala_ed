# ifitwala_ed/admission/api/cockpit/cache.py

from __future__ import annotations

import hashlib
import json

import frappe

COCKPIT_CACHE_TTL_SECONDS = 120
COCKPIT_CACHE_PREFIX = "admissions:cockpit:v2:"


def invalidate_admissions_cockpit_cache() -> None:
    cache = frappe.cache()
    get_keys = getattr(cache, "get_keys", None)
    if not callable(get_keys):
        return

    for key in get_keys(f"{COCKPIT_CACHE_PREFIX}*"):
        cache.delete_value(key)


def _cache_key_for_payload(payload: dict) -> str:
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"{COCKPIT_CACHE_PREFIX}{digest}"
