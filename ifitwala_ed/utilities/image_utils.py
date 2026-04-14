# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/image_utils.py

import io
import os
import re
from collections.abc import Iterable, Sequence
from datetime import timedelta
from urllib.error import URLError
from urllib.request import Request, urlopen

import frappe
from frappe import _
from PIL import Image

PROFILE_IMAGE_VARIANT_SLOTS = (
    "profile_image_thumb",
    "profile_image_card",
    "profile_image_medium",
    "profile_image",
)
PROFILE_IMAGE_VARIANT_PRIORITY = PROFILE_IMAGE_VARIANT_SLOTS
PROFILE_IMAGE_VARIANT_SIZES = {"thumb": 160, "card": 400, "medium": 960}

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


def _get_file_classification(file_doc):
    if not file_doc:
        return None

    name = frappe.db.get_value("File Classification", {"file": file_doc.name}, "name")
    if not name:
        return None

    return frappe.get_doc("File Classification", name)


def _get_secondary_subjects(fc_doc):
    if not fc_doc:
        return []

    return [
        {
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "role": row.role,
        }
        for row in (fc_doc.secondary_subjects or [])
    ]


def _render_resized_bytes(original_path, width, quality=75):
    try:
        with Image.open(original_path) as img:
            if img.width <= width:
                return None
            img.thumbnail((width, width))
            buffer = io.BytesIO()
            img.save(buffer, "WEBP", optimize=True, quality=quality)
            return buffer.getvalue()
    except Exception as e:
        frappe.log_error(f"Error resizing image bytes: {e}", "File Auto-Resize")
        return None


def _render_resized_content(original_content: bytes, width, quality=75):
    if not original_content:
        return None

    try:
        with Image.open(io.BytesIO(original_content)) as img:
            if img.width <= width:
                return None
            img.thumbnail((width, width))
            buffer = io.BytesIO()
            img.save(buffer, "WEBP", optimize=True, quality=quality)
            return buffer.getvalue()
    except Exception as e:
        frappe.log_error(f"Error resizing image content: {e}", "File Auto-Resize")
        return None


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


def _build_governed_derivative_classification(fc_doc, slot_suffix, source_file):
    return {
        "primary_subject_type": fc_doc.primary_subject_type,
        "primary_subject_id": fc_doc.primary_subject_id,
        "data_class": fc_doc.data_class,
        "purpose": fc_doc.purpose,
        "retention_policy": fc_doc.retention_policy,
        "slot": f"{fc_doc.slot}_{slot_suffix}",
        "organization": fc_doc.organization,
        "school": fc_doc.school,
        "upload_source": fc_doc.upload_source or "Desk",
        "source_file": source_file,
    }


def _build_employee_derivative_classification(fc_doc, slot_suffix, source_file):
    return _build_governed_derivative_classification(fc_doc, slot_suffix, source_file)


def _governed_derivative_exists(source_file, slot_base, slot_suffix):
    slot = f"{slot_base}_{slot_suffix}"
    return frappe.db.exists(
        "File Classification",
        {"source_file": source_file, "slot": slot},
    )


def _employee_derivative_exists(source_file, slot_base, slot_suffix):
    return _governed_derivative_exists(source_file, slot_base, slot_suffix)


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


def _resolve_governed_display_url(
    primary_subject_type: str,
    subject_name: str | None,
    *,
    file_name: str | None,
    file_url: str | None,
) -> str | None:
    raw_url = str(file_url or "").strip()
    if not raw_url:
        return None

    if raw_url.startswith("/files/") and not raw_url.startswith("/files/ifitwala_drive/"):
        return raw_url

    resolved_subject = str(subject_name or "").strip()
    if not resolved_subject:
        return raw_url

    if primary_subject_type == "Student":
        from ifitwala_ed.api.file_access import resolve_academic_file_open_url

        return (
            resolve_academic_file_open_url(
                file_name=file_name,
                file_url=raw_url,
                context_doctype="Student",
                context_name=resolved_subject,
            )
            or raw_url
        )

    if primary_subject_type == "Guardian":
        from ifitwala_ed.api.file_access import resolve_guardian_file_open_url

        return (
            resolve_guardian_file_open_url(
                file_name=file_name,
                file_url=raw_url,
                context_doctype="Guardian",
                context_name=resolved_subject,
            )
            or raw_url
        )

    if primary_subject_type == "Employee":
        from ifitwala_ed.api.file_access import resolve_employee_file_open_url

        return (
            resolve_employee_file_open_url(
                file_name=file_name,
                file_url=raw_url,
                context_doctype="Employee",
                context_name=resolved_subject,
            )
            or raw_url
        )

    return raw_url


def _resolve_original_governed_image_url(
    primary_subject_type: str,
    subject_name: str | None,
    original_url: str | None,
) -> str | None:
    raw_url = str(original_url or "").strip()
    resolved_subject = str(subject_name or "").strip()
    if not raw_url:
        return None

    file_name = None
    if primary_subject_type and resolved_subject:
        file_name = frappe.db.get_value(
            "File",
            {
                "attached_to_doctype": primary_subject_type,
                "attached_to_name": resolved_subject,
                "file_url": raw_url,
            },
            "name",
        )

    if not file_url_is_accessible(raw_url, file_name=file_name):
        return None

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

    rows = frappe.get_all(
        "File Classification",
        filters={
            "primary_subject_type": primary_subject_type,
            "primary_subject_id": ("in", names),
            "slot": ("in", list(slots)),
            "is_current_version": 1,
        },
        fields=["primary_subject_id", "slot", "file"],
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
    )
    file_map = {row["name"]: row for row in files}

    variants: dict[str, dict[str, str]] = {}
    for row in rows:
        subject_name = row.get("primary_subject_id")
        slot = row.get("slot")
        file_name = row.get("file")
        if not (subject_name and slot and file_name):
            continue

        file_row = file_map.get(file_name)
        if not file_row:
            continue

        file_url = (file_row.get("file_url") or "").strip()
        if not file_url:
            continue
        if not file_url_is_accessible(
            file_url,
            file_name=file_name,
            is_private=file_row.get("is_private"),
        ):
            continue

        display_url = _resolve_governed_display_url(
            primary_subject_type,
            subject_name,
            file_name=file_name,
            file_url=file_url,
        )
        if not display_url:
            continue

        variants.setdefault(subject_name, {})[slot] = display_url

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
        return original_url if file_url_exists_on_disk(original_url) else None

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
) -> str | None:
    return _get_preferred_governed_image_url(
        "Student",
        student_name,
        original_url=original_url,
        slots=slots,
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
) -> list[dict]:
    return _apply_preferred_governed_images(
        rows,
        primary_subject_type="Student",
        subject_field=student_field,
        image_field=image_field,
        slots=slots,
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
) -> str | None:
    return _get_preferred_governed_image_url(
        "Guardian",
        guardian_name,
        original_url=original_url,
        slots=slots,
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


def _generate_governed_profile_derivatives(file_doc, *, doctype: str, fieldname: str, log_label: str):
    if not file_doc or file_doc.attached_to_doctype != doctype:
        return

    if file_doc.attached_to_field and file_doc.attached_to_field != fieldname:
        return

    filename = os.path.basename(file_doc.file_url or file_doc.file_name or "")
    if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
        return

    fc_doc = _get_file_classification(file_doc)
    if not fc_doc or fc_doc.slot != "profile_image":
        return

    if not file_doc.file_url:
        return

    original_path = _resolve_governed_original_path(file_doc)
    original_content = None
    if not original_path or not os.path.exists(original_path):
        original_content = _download_drive_original(file_doc, log_title=f"{log_label} Image Download Failed")
    if (not original_path or not os.path.exists(original_path)) and not original_content:
        frappe.log_error(
            f"{log_label} image missing on disk for file {file_doc.name}: {file_doc.file_url}",
            f"{log_label} Image Resize",
        )
        return

    base_filename = os.path.splitext(filename)[0]
    slug_base = slugify(base_filename)
    if not slug_base:
        return

    from ifitwala_ed.utilities import file_dispatcher

    secondary_subjects = _get_secondary_subjects(fc_doc)

    for size_label, width in PROFILE_IMAGE_VARIANT_SIZES.items():
        if _governed_derivative_exists(file_doc.name, fc_doc.slot, size_label):
            continue

        if original_path and os.path.exists(original_path):
            content = _render_resized_bytes(original_path, width)
        else:
            content = _render_resized_content(original_content or b"", width)
        if not content:
            continue

        classification = _build_governed_derivative_classification(
            fc_doc,
            size_label,
            file_doc.name,
        )

        file_dispatcher.create_and_classify_file(
            file_kwargs={
                "attached_to_doctype": file_doc.attached_to_doctype,
                "attached_to_name": file_doc.attached_to_name,
                "attached_to_field": file_doc.attached_to_field,
                "file_name": f"{size_label}_{slug_base}.webp",
                "content": content,
                "is_private": int(file_doc.is_private or 0),
            },
            classification=classification,
            secondary_subjects=secondary_subjects,
        )


def _generate_employee_derivatives(file_doc):
    _generate_governed_profile_derivatives(
        file_doc,
        doctype="Employee",
        fieldname="employee_image",
        log_label="Employee",
    )


def _generate_student_derivatives(file_doc):
    _generate_governed_profile_derivatives(
        file_doc,
        doctype="Student",
        fieldname="student_image",
        log_label="Student",
    )


def _generate_guardian_derivatives(file_doc):
    _generate_governed_profile_derivatives(
        file_doc,
        doctype="Guardian",
        fieldname="guardian_image",
        log_label="Guardian",
    )


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
    # Governed Employee images should only be processed once classified.
    if doc.attached_to_doctype == "Employee":
        if not frappe.db.exists("File Classification", {"file": doc.name}):
            return
        _generate_employee_derivatives(doc)
        return

    if doc.attached_to_doctype == "Student":
        if frappe.db.exists("File Classification", {"file": doc.name}):
            _generate_student_derivatives(doc)
            return

        # Defer legacy Student images until after rename_student_image()
        # puts them into /files/student/ with secure suffix.
        if not doc.file_url or not doc.file_url.startswith("/files/student/"):
            return

    if doc.attached_to_doctype == "Guardian":
        if not frappe.db.exists("File Classification", {"file": doc.name}):
            return
        _generate_guardian_derivatives(doc)
        return

    if not (doc.file_url and doc.attached_to_doctype):
        return

    allowed_doctypes = ["Employee", "Student", "School", "Course", "Program", "Blog Post"]
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
# Governed dispatcher entry point
# ────────────────────────────────────────────────────────────────────────────
def handle_governed_file_after_classification(file_doc):
    """Run derivative generation after governance is established."""
    if not file_doc:
        return
    if file_doc.attached_to_doctype == "Employee":
        _generate_employee_derivatives(file_doc)
        return
    if file_doc.attached_to_doctype == "Student":
        _generate_student_derivatives(file_doc)
        return
    if file_doc.attached_to_doctype == "Guardian":
        _generate_guardian_derivatives(file_doc)


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
