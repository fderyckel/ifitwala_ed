from __future__ import annotations

import frappe

CACHE_TTL_SECONDS = 3600
_STUDENT_PORTAL_IDENTITY_CACHE_VERSION = "v4"


def student_portal_identity_cache_key(user: str) -> str:
    return f"student_portal:identity:{_STUDENT_PORTAL_IDENTITY_CACHE_VERSION}:{user}"


def invalidate_student_portal_identity_cache(
    *,
    student: str | None = None,
    user: str | None = None,
    users: list[str] | None = None,
) -> None:
    resolved_users = {
        str(candidate or "").strip() for candidate in [user, *(users or [])] if str(candidate or "").strip()
    }
    resolved_student = str(student or "").strip()
    if resolved_student:
        student_email = str(frappe.db.get_value("Student", resolved_student, "student_email") or "").strip()
        if student_email:
            resolved_users.add(student_email)

    if not resolved_users:
        return

    cache = frappe.cache()
    for current_user in sorted(resolved_users):
        cache.delete_value(student_portal_identity_cache_key(current_user))
