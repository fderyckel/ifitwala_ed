from __future__ import annotations

from importlib import import_module
from typing import Any, Callable, Sequence

_PROFILE_IMAGE_REQUEST_METHODS = {
    "Employee": ("request_employee_image_preview_derivatives", "employee"),
    "Guardian": ("request_guardian_image_preview_derivatives", "guardian"),
    "Student": ("request_student_image_preview_derivatives", "student"),
}


def _load_drive_media_callable(attribute: str) -> Callable[..., dict[str, Any]] | None:
    try:
        media_api = import_module("ifitwala_drive.api.media")
        callable_obj = getattr(media_api, attribute, None)
        if callable(callable_obj):
            return callable_obj
    except Exception:
        pass

    return None


def request_profile_image_preview_derivatives(
    primary_subject_type: str,
    subject_name: str | None,
    *,
    file_id: str | None,
    derivative_roles: Sequence[str] | None,
) -> dict[str, Any] | None:
    resolved_subject_type = str(primary_subject_type or "").strip()
    resolved_subject_name = str(subject_name or "").strip()
    resolved_file_id = str(file_id or "").strip()
    resolved_roles = [str(role or "").strip() for role in (derivative_roles or []) if str(role or "").strip()]
    method_parts = _PROFILE_IMAGE_REQUEST_METHODS.get(resolved_subject_type)
    if not method_parts or not resolved_subject_name or not resolved_file_id or not resolved_roles:
        return None

    method_name, subject_field = method_parts
    callable_obj = _load_drive_media_callable(method_name)
    if not callable(callable_obj):
        return None

    payload = {
        subject_field: resolved_subject_name,
        "file_id": resolved_file_id,
        "derivative_roles": resolved_roles,
    }
    return callable_obj(**payload)
