# ifitwala_ed/request_hooks.py

from __future__ import annotations


def apply_default_security_headers(response):
    if response is None:
        return response

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response
