# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/image_utils.py

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Sequence
from datetime import timedelta
from urllib.error import URLError
from urllib.request import Request, urlopen

import frappe
from frappe import _
from PIL import Image

from ifitwala_ed.integrations.drive.authority import (
    get_current_drive_file_for_slot,
    get_current_drive_files_for_slots,
    get_drive_file_for_file,
    is_governed_file,
)

PROFILE_IMAGE_VARIANT_SLOTS = (
    "profile_image_thumb",
    "profile_image_card",
    "profile_image_medium",
    "profile_image",
)
PROFILE_IMAGE_VARIANT_PRIORITY = PROFILE_IMAGE_VARIANT_SLOTS
PROFILE_IMAGE_VARIANT_ROLE_MAP = {
    "profile_image_thumb": "thumb",
    "profile_image_card": "card",
    "profile_image_medium": "viewer_preview",
}

EMPLOYEE_VARIANT_SLOTS = PROFILE_IMAGE_VARIANT_SLOTS

EMPLOYEE_VARIANT_PRIORITY = EMPLOYEE_VARIANT_SLOTS
STUDENT_VARIANT_SLOTS = PROFILE_IMAGE_VARIANT_SLOTS
STUDENT_VARIANT_PRIORITY = STUDENT_VARIANT_SLOTS
GUARDIAN_VARIANT_SLOTS = PROFILE_IMAGE_VARIANT_SLOTS
GUARDIAN_VARIANT_PRIORITY = GUARDIAN_VARIANT_SLOTS


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def slugify(text):
    """lowercase, replace non-alphanums with '_', strip extra."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _get_drive_file_row(file_doc, *, statuses=("active", "processing", "blocked")):
    if not file_doc:
        return None

    return get_drive_file_for_file(file_doc.name, statuses=statuses)


def resolve_file_absolute_path(file_url: str | None, is_private: int | None = 0) -> str | None:
    """Resolve a Frappe-managed file_url to a local absolute path when possible."""
    if not file_url:
        return None

    if file_url.startswith("http"):
        return None

    rel_path = file_url.lstrip("/")
    if rel_path.startswith("private/") or rel_path.startswith("public/"):
        return frappe.utils.get_site_path(rel_path)

    base = "private" if is_private else "public"
    return frappe.utils.get_site_path(base, rel_path)


def file_url_exists_on_disk(file_url: str | None, is_private: int | None = 0) -> bool:
    if not file_url:
        return False

    if file_url.startswith("http"):
        return True

    abs_path = resolve_file_absolute_path(file_url, is_private=is_private)
    return bool(abs_path and os.path.exists(abs_path))


def file_url_is_accessible(
    file_url: str | None,
    *,
    file_name: str | None = None,
    is_private: int | None = 0,
) -> bool:
    raw_url = str(file_url or "").strip()
    if file_url_exists_on_disk(raw_url, is_private=is_private):
        return True

    # Public local files should never depend on Drive metadata for access checks.
    # If the file is gone from disk, treat it as inaccessible and let callers fall back.
    if raw_url.startswith("/files/") and not raw_url.startswith("/files/ifitwala_drive/") and not int(is_private or 0):
        return False

    clean_file_name = str(file_name or "").strip()
    if not clean_file_name:
        return False

    drive_file = frappe.db.get_value(
        "Drive File",
        {"file": clean_file_name},
        ["storage_backend", "storage_object_key"],
        as_dict=True,
    )
    if not drive_file or not drive_file.get("storage_object_key"):
        return False

    storage_backend = (drive_file.get("storage_backend") or "").strip()
    if storage_backend and storage_backend != "local":
        return True

    try:
        from ifitwala_drive.services.storage.base import get_storage_backend

        storage = get_storage_backend(storage_backend or None)
    except Exception:
        return False

    absolute_path = getattr(storage, "_absolute_path", None)
    if not callable(absolute_path):
        return False

    candidate = absolute_path(drive_file.get("storage_object_key"))
    return bool(candidate and os.path.exists(candidate))


def _resolve_drive_local_path(file_doc) -> str | None:
    if not file_doc:
        return None

    drive_file = frappe.db.get_value(
        "Drive File",
        {"file": file_doc.name},
        ["storage_backend", "storage_object_key"],
        as_dict=True,
    )
    if not drive_file:
        return None
    if drive_file.get("storage_backend") != "local" or not drive_file.get("storage_object_key"):
        return None

    try:
        from ifitwala_drive.services.storage.base import get_storage_backend

        storage = get_storage_backend(drive_file.get("storage_backend"))
    except Exception:
        return None

    absolute_path = getattr(storage, "_absolute_path", None)
    if not callable(absolute_path):
        return None

    candidate = absolute_path(drive_file.get("storage_object_key"))
    if candidate and os.path.exists(candidate):
        return candidate
    return None


def _resolve_employee_drive_local_path(file_doc) -> str | None:
    return _resolve_drive_local_path(file_doc)


def _download_drive_original(file_doc, *, log_title: str) -> bytes | None:
    if not file_doc:
        return None

    drive_file = frappe.db.get_value(
        "Drive File",
        {"file": file_doc.name},
        ["storage_backend", "storage_object_key"],
        as_dict=True,
    )
    if not drive_file or not drive_file.get("storage_object_key"):
        return None

    try:
        from ifitwala_drive.services.storage.base import get_storage_backend

        storage = get_storage_backend(drive_file.get("storage_backend"))
        expires_on = frappe.utils.now_datetime() + timedelta(minutes=10)
        grant = storage.issue_download_grant(
            object_key=drive_file.get("storage_object_key"),
            file_url=file_doc.file_url,
            expires_on=expires_on,
        )
        download_url = (grant or {}).get("url")
        if not download_url:
            return None
        if download_url.startswith("/"):
            download_url = frappe.utils.get_url(download_url)

        request = Request(download_url, method="GET")
        with urlopen(request, timeout=30) as response:
            return response.read()
    except (ImportError, URLError, OSError):
        return None
    except Exception:
        frappe.log_error(frappe.get_traceback(), log_title)
        return None


def _download_employee_drive_original(file_doc) -> bytes | None:
    return _download_drive_original(file_doc, log_title="Employee Image Download Failed")


def _resolve_governed_original_path(file_doc) -> str | None:
    if not file_doc:
        return None

    candidate = resolve_file_absolute_path(file_doc.file_url, is_private=getattr(file_doc, "is_private", 0))
    if candidate and os.path.exists(candidate):
        return candidate

    return _resolve_drive_local_path(file_doc)


def _resolve_employee_original_path(file_doc) -> str | None:
    return _resolve_governed_original_path(file_doc)


def _is_directly_displayable_file_url(file_url: str | None) -> bool:
    raw_url = str(file_url or "").strip()
    if not raw_url:
        return False
    if raw_url.startswith(("http://", "https://")):
        return True
    return raw_url.startswith("/files/") and not raw_url.startswith("/files/ifitwala_drive/")


def _resolve_governed_display_url(
    primary_subject_type: str,
    subject_name: str | None,
    *,
    file_name: str | None,
    file_url: str | None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    derivative_role: str | None = None,
) -> str | None:
    raw_url = str(file_url or "").strip()
    resolved_drive_file_id = str(drive_file_id or "").strip() or None
    resolved_canonical_ref = str(canonical_ref or "").strip() or None
    resolved_file_name = str(file_name or "").strip() or None
    if not raw_url and not resolved_file_name and not resolved_drive_file_id and not resolved_canonical_ref:
        return None

    explicit_derivative_role = str(derivative_role or "").strip() or None

    if raw_url and not explicit_derivative_role and _is_directly_displayable_file_url(raw_url):
        return raw_url

    resolved_subject = str(subject_name or "").strip()
    if not resolved_subject:
        return None

    if primary_subject_type == "Student":
        from ifitwala_ed.api.file_access import resolve_academic_file_open_url

        resolved_url = resolve_academic_file_open_url(
            file_name=resolved_file_name,
            file_url=raw_url,
            context_doctype="Student",
            context_name=resolved_subject,
            derivative_role=explicit_derivative_role,
        )
        return resolved_url or (
            raw_url if not explicit_derivative_role and _is_directly_displayable_file_url(raw_url) else None
        )

    if primary_subject_type == "Guardian":
        from ifitwala_ed.api.file_access import resolve_guardian_file_open_url

        resolved_url = resolve_guardian_file_open_url(
            file_name=resolved_file_name,
            file_url=raw_url,
            context_doctype="Guardian",
            context_name=resolved_subject,
            derivative_role=explicit_derivative_role,
        )
        return resolved_url or (
            raw_url if not explicit_derivative_role and _is_directly_displayable_file_url(raw_url) else None
        )

    if primary_subject_type == "Employee":
        from ifitwala_ed.api.file_access import resolve_employee_file_open_url

        resolved_url = resolve_employee_file_open_url(
            file_name=resolved_file_name,
            file_url=raw_url,
            drive_file_id=resolved_drive_file_id,
            canonical_ref=resolved_canonical_ref,
            context_doctype="Employee",
            context_name=resolved_subject,
            derivative_role=explicit_derivative_role,
        )
        return resolved_url or (
            raw_url if not explicit_derivative_role and _is_directly_displayable_file_url(raw_url) else None
        )

    return raw_url if not explicit_derivative_role and _is_directly_displayable_file_url(raw_url) else None


def _resolve_original_governed_image_url(
    primary_subject_type: str,
    subject_name: str | None,
    original_url: str | None,
) -> str | None:
    raw_url = str(original_url or "").strip()
    resolved_subject = str(subject_name or "").strip()
    if not raw_url:
        if not resolved_subject:
            return None

    if primary_subject_type and resolved_subject:
        current_file_doc = _get_current_governed_profile_file(
            primary_subject_type=primary_subject_type,
            subject_name=resolved_subject,
        )
        current_file_url = str(getattr(current_file_doc, "file_url", "") or "").strip()
        if current_file_doc and current_file_url:
            drive_file_row = _get_drive_file_row(current_file_doc) or {}
            resolved_current_url = _resolve_governed_display_url(
                primary_subject_type,
                resolved_subject,
                file_name=current_file_doc.name,
                file_url=current_file_url,
                drive_file_id=drive_file_row.get("name"),
                canonical_ref=drive_file_row.get("canonical_ref"),
            )
            if resolved_current_url:
                return resolved_current_url

    file_name = None
    if raw_url and primary_subject_type and resolved_subject:
        file_name = frappe.db.get_value(
            "File",
            {
                "attached_to_doctype": primary_subject_type,
                "attached_to_name": resolved_subject,
                "file_url": raw_url,
            },
            "name",
        )

    return _resolve_governed_display_url(
        primary_subject_type,
        resolved_subject,
        file_name=file_name,
        file_url=raw_url,
    )


def _get_governed_image_variants_map(
    primary_subject_type: str,
    subject_names: Sequence[str] | Iterable[str],
    *,
    slots: Sequence[str],
) -> dict[str, dict[str, str]]:
    names = [str(name or "").strip() for name in (subject_names or [])]
    names = [name for name in names if name]
    if not names:
        return {}

    rows = get_current_drive_files_for_slots(
        primary_subject_type=primary_subject_type,
        primary_subject_ids=names,
        slots=("profile_image",),
        fields=["name", "primary_subject_id", "slot", "file", "current_version", "canonical_ref"],
        statuses=("active",),
    )
    if not rows:
        return {}

    file_names = [row["file"] for row in rows if row.get("file")]
    if not file_names:
        return {}

    files = frappe.get_all(
        "File",
        filters={"name": ("in", file_names)},
        fields=["name", "file_url", "is_private"],
        limit=0,
    )
    file_map = {row["name"]: row for row in files}

    derivative_roles = sorted(
        {PROFILE_IMAGE_VARIANT_ROLE_MAP[slot] for slot in (slots or []) if slot in PROFILE_IMAGE_VARIANT_ROLE_MAP}
    )
    ready_roles_by_drive_file: dict[str, set[str]] = {}
    if derivative_roles:
        drive_file_ids = [str(row.get("name") or "").strip() for row in rows if str(row.get("name") or "").strip()]
        current_versions = [
            str(row.get("current_version") or "").strip()
            for row in rows
            if str(row.get("current_version") or "").strip()
        ]
        if drive_file_ids and current_versions:
            derivative_rows = frappe.get_all(
                "Drive File Derivative",
                filters={
                    "drive_file": ("in", drive_file_ids),
                    "drive_file_version": ("in", current_versions),
                    "derivative_role": ("in", derivative_roles),
                    "status": "ready",
                },
                fields=["drive_file", "derivative_role"],
                limit=0,
            )
            for derivative_row in derivative_rows or []:
                drive_file_id = str(derivative_row.get("drive_file") or "").strip()
                derivative_role = str(derivative_row.get("derivative_role") or "").strip()
                if not drive_file_id or not derivative_role:
                    continue
                ready_roles_by_drive_file.setdefault(drive_file_id, set()).add(derivative_role)

    variants: dict[str, dict[str, str]] = {}
    for row in rows:
        subject_name = row.get("primary_subject_id")
        drive_file_id = str(row.get("name") or "").strip()
        file_name = row.get("file")
        if not (subject_name and file_name):
            continue

        file_row = file_map.get(file_name) or {}
        file_url = (file_row.get("file_url") or "").strip()
        canonical_ref = str(row.get("canonical_ref") or "").strip() or None

        subject_variants = variants.setdefault(subject_name, {})
        if "profile_image" in slots:
            original_display_url = _resolve_governed_display_url(
                primary_subject_type,
                subject_name,
                file_name=file_name,
                file_url=file_url,
                drive_file_id=drive_file_id or None,
                canonical_ref=canonical_ref,
            )
            if original_display_url:
                subject_variants["profile_image"] = original_display_url

        ready_roles = ready_roles_by_drive_file.get(drive_file_id, set())
        for slot in slots:
            derivative_role = PROFILE_IMAGE_VARIANT_ROLE_MAP.get(slot)
            if not derivative_role or derivative_role not in ready_roles:
                continue
            display_url = _resolve_governed_display_url(
                primary_subject_type,
                subject_name,
                file_name=file_name,
                file_url=file_url,
                drive_file_id=drive_file_id or None,
                canonical_ref=canonical_ref,
                derivative_role=derivative_role,
            )
            if display_url:
                subject_variants[slot] = display_url

    return variants


def _get_preferred_governed_image_url(
    primary_subject_type: str,
    subject_name: str | None,
    *,
    original_url: str | None = None,
    slots: Sequence[str],
    fallback_to_original: bool = True,
) -> str | None:
    subject_name = str(subject_name or "").strip()
    if not subject_name:
        if not fallback_to_original:
            return None
        return _resolve_governed_display_url(
            primary_subject_type,
            None,
            file_name=None,
            file_url=original_url,
        )

    variants = _get_governed_image_variants_map(primary_subject_type, [subject_name], slots=slots).get(subject_name, {})
    for slot in slots:
        file_url = variants.get(slot)
        if file_url:
            return file_url

    if not fallback_to_original:
        return None

    return _resolve_original_governed_image_url(primary_subject_type, subject_name, original_url)


def _build_governed_image_variants(
    primary_subject_type: str,
    subject_name: str | None,
    *,
    original_url: str | None = None,
    slots: Sequence[str],
    fallback_to_original: bool = True,
) -> dict[str, str | None]:
    subject_name = str(subject_name or "").strip()
    variants = (
        _get_governed_image_variants_map(primary_subject_type, [subject_name], slots=slots).get(subject_name, {})
        if subject_name
        else {}
    )
    original_fallback = variants.get("profile_image")
    if not original_fallback and fallback_to_original:
        original_fallback = _resolve_original_governed_image_url(
            primary_subject_type,
            subject_name,
            original_url,
        )

    return {
        "original": original_fallback,
        "medium": variants.get("profile_image_medium") or original_fallback,
        "card": variants.get("profile_image_card") or variants.get("profile_image_medium") or original_fallback,
        "thumb": variants.get("profile_image_thumb")
        or variants.get("profile_image_card")
        or variants.get("profile_image_medium")
        or original_fallback,
    }


def _apply_preferred_governed_images(
    rows: list[dict],
    *,
    primary_subject_type: str,
    subject_field: str,
    image_field: str,
    slots: Sequence[str],
    fallback_to_original: bool = True,
) -> list[dict]:
    if not rows:
        return rows

    subject_names = [row.get(subject_field) for row in rows if row.get(subject_field)]
    variants = _get_governed_image_variants_map(primary_subject_type, subject_names, slots=slots)

    for row in rows:
        subject_name = row.get(subject_field)
        if not subject_name:
            continue

        original_url = row.get(image_field)
        preferred_url = None
        for slot in slots:
            preferred_url = variants.get(subject_name, {}).get(slot)
            if preferred_url:
                break

        if preferred_url:
            row[image_field] = preferred_url
        elif fallback_to_original:
            row[image_field] = _resolve_original_governed_image_url(
                primary_subject_type,
                subject_name,
                original_url,
            )
        else:
            row[image_field] = None

    return rows


def get_employee_image_variants_map(
    employee_names: Sequence[str] | Iterable[str],
    *,
    slots: Sequence[str] = EMPLOYEE_VARIANT_SLOTS,
) -> dict[str, dict[str, str]]:
    return _get_governed_image_variants_map("Employee", employee_names, slots=slots)


def get_preferred_employee_image_url(
    employee_name: str | None,
    *,
    original_url: str | None = None,
    slots: Sequence[str] = EMPLOYEE_VARIANT_PRIORITY,
    fallback_to_original: bool = True,
) -> str | None:
    return _get_preferred_governed_image_url(
        "Employee",
        employee_name,
        original_url=original_url,
        slots=slots,
        fallback_to_original=fallback_to_original,
    )


def build_employee_image_variants(
    employee_name: str | None,
    original_url: str | None = None,
    *,
    fallback_to_original: bool = True,
) -> dict[str, str | None]:
    return _build_governed_image_variants(
        "Employee",
        employee_name,
        original_url=original_url,
        slots=EMPLOYEE_VARIANT_SLOTS,
        fallback_to_original=fallback_to_original,
    )


def apply_preferred_employee_images(
    rows: list[dict],
    *,
    employee_field: str = "id",
    image_field: str = "image",
    slots: Sequence[str] = EMPLOYEE_VARIANT_PRIORITY,
    fallback_to_original: bool = True,
) -> list[dict]:
    return _apply_preferred_governed_images(
        rows,
        primary_subject_type="Employee",
        subject_field=employee_field,
        image_field=image_field,
        slots=slots,
        fallback_to_original=fallback_to_original,
    )


def get_student_image_variants_map(
    student_names: Sequence[str] | Iterable[str],
    *,
    slots: Sequence[str] = STUDENT_VARIANT_SLOTS,
) -> dict[str, dict[str, str]]:
    return _get_governed_image_variants_map("Student", student_names, slots=slots)


def get_preferred_student_image_url(
    student_name: str | None,
    *,
    original_url: str | None = None,
    slots: Sequence[str] = STUDENT_VARIANT_PRIORITY,
    fallback_to_original: bool = True,
) -> str | None:
    return _get_preferred_governed_image_url(
        "Student",
        student_name,
        original_url=original_url,
        slots=slots,
        fallback_to_original=fallback_to_original,
    )


def build_student_image_variants(student_name: str | None, original_url: str | None = None) -> dict[str, str | None]:
    return _build_governed_image_variants(
        "Student",
        student_name,
        original_url=original_url,
        slots=STUDENT_VARIANT_SLOTS,
    )


def apply_preferred_student_images(
    rows: list[dict],
    *,
    student_field: str = "student",
    image_field: str = "student_image",
    slots: Sequence[str] = STUDENT_VARIANT_PRIORITY,
    fallback_to_original: bool = True,
) -> list[dict]:
    return _apply_preferred_governed_images(
        rows,
        primary_subject_type="Student",
        subject_field=student_field,
        image_field=image_field,
        slots=slots,
        fallback_to_original=fallback_to_original,
    )


def get_guardian_image_variants_map(
    guardian_names: Sequence[str] | Iterable[str],
    *,
    slots: Sequence[str] = GUARDIAN_VARIANT_SLOTS,
) -> dict[str, dict[str, str]]:
    return _get_governed_image_variants_map("Guardian", guardian_names, slots=slots)


def get_preferred_guardian_image_url(
    guardian_name: str | None,
    *,
    original_url: str | None = None,
    slots: Sequence[str] = GUARDIAN_VARIANT_PRIORITY,
    fallback_to_original: bool = True,
) -> str | None:
    return _get_preferred_governed_image_url(
        "Guardian",
        guardian_name,
        original_url=original_url,
        slots=slots,
        fallback_to_original=fallback_to_original,
    )


def build_guardian_image_variants(guardian_name: str | None, original_url: str | None = None) -> dict[str, str | None]:
    return _build_governed_image_variants(
        "Guardian",
        guardian_name,
        original_url=original_url,
        slots=GUARDIAN_VARIANT_SLOTS,
    )


def apply_preferred_guardian_images(
    rows: list[dict],
    *,
    guardian_field: str = "guardian",
    image_field: str = "guardian_image",
    slots: Sequence[str] = GUARDIAN_VARIANT_PRIORITY,
) -> list[dict]:
    return _apply_preferred_governed_images(
        rows,
        primary_subject_type="Guardian",
        subject_field=guardian_field,
        image_field=image_field,
        slots=slots,
    )


def _read_managed_file_bytes(file_doc, *, log_label: str) -> bytes | None:
    if not file_doc:
        return None

    original_path = _resolve_governed_original_path(file_doc)
    if original_path and os.path.exists(original_path):
        try:
            with open(original_path, "rb") as handle:
                return handle.read()
        except OSError:
            return None

    return _download_drive_original(file_doc, log_title=f"{log_label} Image Download Failed")


def _get_current_governed_profile_file(*, primary_subject_type: str, subject_name: str) -> object | None:
    resolved_subject = str(subject_name or "").strip()
    if not resolved_subject:
        return None

    drive_file = get_current_drive_file_for_slot(
        primary_subject_type=primary_subject_type,
        primary_subject_id=resolved_subject,
        slot="profile_image",
        fields=["file"],
        statuses=("active",),
    )
    file_name = (drive_file or {}).get("file")
    if not file_name:
        return None
    if not frappe.db.exists("File", file_name):
        return None
    return frappe.get_doc("File", file_name)


def _resolve_unique_file_doc_by_url(file_url: str | None) -> object | None:
    raw_url = str(file_url or "").strip()
    if not raw_url:
        return None

    matches = frappe.get_all(
        "File",
        filters={"file_url": raw_url},
        fields=["name"],
        limit=2,
    )
    if len(matches) != 1:
        return None

    return frappe.get_doc("File", matches[0]["name"])


def _sync_guardian_profile_image_field(*, guardian_name: str, file_url: str | None, organization: str | None) -> None:
    resolved_guardian = str(guardian_name or "").strip()
    resolved_url = str(file_url or "").strip()
    resolved_organization = str(organization or "").strip()
    if not resolved_guardian or not resolved_url:
        return

    frappe.db.set_value(
        "Guardian",
        resolved_guardian,
        {
            "guardian_image": resolved_url,
            "organization": resolved_organization or None,
        },
        update_modified=False,
    )


def ensure_guardian_profile_image(
    guardian_name: str | None,
    *,
    original_url: str | None = None,
    source_file_name: str | None = None,
    organization: str | None = None,
    upload_source: str = "API",
) -> str | None:
    resolved_guardian = str(guardian_name or "").strip()
    if not resolved_guardian:
        return None

    guardian_doc = None

    def _load_guardian_doc():
        nonlocal guardian_doc
        if guardian_doc is None:
            guardian_doc = frappe.get_doc("Guardian", resolved_guardian)
            if organization and not (guardian_doc.organization or "").strip():
                guardian_doc.organization = organization
        return guardian_doc

    current_file_doc = _get_current_governed_profile_file(
        primary_subject_type="Guardian",
        subject_name=resolved_guardian,
    )

    if current_file_doc:
        current_drive_file = _get_drive_file_row(current_file_doc)
        resolved_organization = (current_drive_file or {}).get("organization") or organization
        if not str(resolved_organization or "").strip():
            resolved_organization = getattr(_load_guardian_doc(), "organization", None)
        _sync_guardian_profile_image_field(
            guardian_name=resolved_guardian,
            file_url=current_file_doc.file_url,
            organization=resolved_organization,
        )
        return current_file_doc.file_url

    guardian_doc = _load_guardian_doc()

    from ifitwala_drive.api.media import upload_guardian_image

    from ifitwala_ed.integrations.drive.content_uploads import upload_content_via_drive
    from ifitwala_ed.integrations.drive.media import build_guardian_image_contract

    contract = build_guardian_image_contract(guardian_doc)
    contract["upload_source"] = upload_source

    source_file_doc = None
    resolved_source_file_name = str(source_file_name or "").strip()
    if resolved_source_file_name and frappe.db.exists("File", resolved_source_file_name):
        source_file_doc = frappe.get_doc("File", resolved_source_file_name)
    else:
        raw_url = str(original_url or "").strip()
        if raw_url:
            source_file_doc = _resolve_unique_file_doc_by_url(raw_url)
            if not source_file_doc:
                guardian_matches = frappe.get_all(
                    "File",
                    filters={
                        "attached_to_doctype": "Guardian",
                        "attached_to_name": resolved_guardian,
                        "file_url": raw_url,
                    },
                    fields=["name"],
                    limit=2,
                )
                if len(guardian_matches) == 1:
                    source_file_doc = frappe.get_doc("File", guardian_matches[0]["name"])

    if not source_file_doc:
        return None

    content = _read_managed_file_bytes(source_file_doc, log_label="Guardian")
    if not content:
        frappe.log_error(
            frappe.as_json(
                {
                    "error": "guardian_profile_image_source_unreadable",
                    "guardian": resolved_guardian,
                    "source_file": source_file_doc.name,
                    "source_file_url": source_file_doc.file_url,
                },
                indent=2,
            ),
            "Guardian Profile Image Sync Failed",
        )
        return None

    filename = (source_file_doc.file_name or "").strip() or os.path.basename(
        source_file_doc.file_url or "guardian_profile_image"
    )
    _session_response, _finalize_response, current_file_doc = upload_content_via_drive(
        create_session_callable=upload_guardian_image,
        session_payload={
            "guardian": guardian_doc.name,
            "upload_source": upload_source,
        },
        file_name=filename,
        content=content,
    )

    _sync_guardian_profile_image_field(
        guardian_name=resolved_guardian,
        file_url=current_file_doc.file_url,
        organization=contract.get("organization"),
    )
    return current_file_doc.file_url


def resize_and_save(
    doc,
    original_path,
    base_filename,
    doctype_folder,
    size_label,
    width,
    quality=75,
):
    """Create a single WebP variant if it doesn't already exist."""
    slug_base = slugify(base_filename)
    resized_filename = f"{size_label}_{slug_base}.webp"
    resized_rel = f"files/gallery_resized/{doctype_folder}/{resized_filename}"
    resized_path = frappe.utils.get_site_path("public", resized_rel)
    resized_url = f"/{resized_rel}"

    if os.path.exists(resized_path):
        return  # already done

    try:
        with Image.open(original_path) as img:
            if img.width <= width:
                return  # nothing to downscale
            img.thumbnail((width, width))
            os.makedirs(os.path.dirname(resized_path), exist_ok=True)
            img.save(resized_path, "WEBP", optimize=True, quality=quality)
    except Exception as e:
        frappe.log_error(f"Error resizing image: {e}", "File Auto-Resize")
        return

    # ── Register new File row if not present ───────────────────────────────
    try:
        parent_folder = f"Home/gallery_resized/{doctype_folder}"
        if not frappe.db.exists("File", {"file_url": resized_url}):
            # create intermediate folders if missing
            if not frappe.db.exists(
                "File",
                {
                    "file_name": doctype_folder,
                    "is_folder": 1,
                    "folder": "Home/gallery_resized",
                },
            ):
                if not frappe.db.exists("File", {"file_name": "gallery_resized", "is_folder": 1, "folder": "Home"}):
                    frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_name": "gallery_resized",
                            "is_folder": 1,
                            "folder": "Home",
                        }
                    ).insert(ignore_permissions=True)
                frappe.get_doc(
                    {
                        "doctype": "File",
                        "file_name": doctype_folder,
                        "is_folder": 1,
                        "folder": "Home/gallery_resized",
                    }
                ).insert(ignore_permissions=True)

            frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": resized_filename,
                    "file_url": resized_url,
                    "folder": parent_folder,
                    "is_private": 0,
                    "attached_to_doctype": doc.attached_to_doctype,
                    "attached_to_name": doc.attached_to_name,
                    "attached_to_field": doc.attached_to_field,
                }
            ).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error registering resized image: {e}", "File Auto‑Resize")


# ────────────────────────────────────────────────────────────────────────────
# Core hooks
# ────────────────────────────────────────────────────────────────────────────
def handle_file_after_insert(doc, method=None):
    """Hook: create WebP variants after a File is inserted."""
    if doc.attached_to_doctype == "Employee":
        return

    if doc.attached_to_doctype == "Student":
        if is_governed_file(doc.name):
            return

        # Defer legacy Student images until after rename_student_image()
        # puts them into /files/student/ with secure suffix.
        if not doc.file_url or not doc.file_url.startswith("/files/student/"):
            return

    if doc.attached_to_doctype == "Guardian":
        return

    if not (doc.file_url and doc.attached_to_doctype):
        return

    allowed_doctypes = ["Student", "School", "Course", "Program", "Blog Post"]
    if doc.attached_to_doctype not in allowed_doctypes:
        return

    # Ignore already‑generated variants
    filename = os.path.basename(doc.file_url)
    if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
        return

    # Process only images we care about
    if not any(doc.file_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
        return

    original_path = frappe.utils.get_site_path("public", doc.file_url.lstrip("/"))
    base_filename = os.path.splitext(filename)[0]
    doctype_folder = slugify(doc.attached_to_doctype)

    # ── Student path: centralised single call ───────────────────────────────
    if doc.attached_to_doctype == "Student":
        process_single_file(doc)
        return

    # ── All other doctypes: direct resize loop ─────────────────────────────
    for size_label, width in {"hero": 1800, "medium": 960, "card": 400, "thumb": 160}.items():
        resize_and_save(doc, original_path, base_filename, doctype_folder, size_label, width)


def handle_file_on_update(doc, method=None):
    """Hook: same logic for updates (but Student may still be mid‑rename)."""
    handle_file_after_insert(doc, method)


# ────────────────────────────────────────────────────────────────────────────
# Rebuild utility (unchanged API)
# ────────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def rebuild_resized_images(doctype):
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("Not permitted."))

    count = 0
    for file in frappe.get_all(
        "File",
        fields=["name", "file_url", "attached_to_doctype"],
        filters={"attached_to_doctype": doctype, "is_private": 0},
    ):
        if not file.file_url or not any(file.file_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
            continue
        if os.path.basename(file.file_url).startswith(("hero_", "medium_", "card_", "thumb_")):
            continue

        original_path = frappe.utils.get_site_path("public", file.file_url.lstrip("/"))
        if not os.path.exists(original_path):
            continue

        base_filename = os.path.splitext(os.path.basename(file.file_url))[0]
        doctype_folder = slugify(file.attached_to_doctype)
        try:
            for size_label, width in {"hero": 1800, "medium": 960, "card": 400, "thumb": 160}.items():
                resize_and_save(file, original_path, base_filename, doctype_folder, size_label, width)
            count += 1
        except Exception as e:
            frappe.log_error(f"Error on rebuild {file.name}: {e}", "Admin Resize Error")

    frappe.msgprint(_(f"Processed {count} file(s) attached to {doctype}."))


# ────────────────────────────────────────────────────────────────────────────
# Central entry point (used by Student.rename_student_image)
# ────────────────────────────────────────────────────────────────────────────
def process_single_file(file_doc):
    """Create all four WebP sizes for a File (idempotent)."""
    if not file_doc.file_url:
        return

    # skip generated variants & non‑images
    filename = os.path.basename(file_doc.file_url)
    if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
        return
    if not any(file_doc.file_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
        return

    original_path = frappe.utils.get_site_path("public", file_doc.file_url.lstrip("/"))
    base_filename = os.path.splitext(filename)[0]
    doctype_folder = slugify(file_doc.attached_to_doctype)

    for size_label, width in {"hero": 1800, "medium": 960, "card": 400, "thumb": 160}.items():
        resize_and_save(file_doc, original_path, base_filename, doctype_folder, size_label, width)
