# ifitwala_ed/admission/api/portal/profile_images.py

from __future__ import annotations

import base64
import io
import os
import warnings
from urllib.parse import parse_qs, urlparse

import frappe
from frappe import _
from PIL import Image, ImageOps, UnidentifiedImageError

from ifitwala_ed.admission import admissions_portal as admission_api
from ifitwala_ed.admission.api.common.request_payload import _request_form_value
from ifitwala_ed.admission.api.portal.access import _as_text, _ensure_applicant_match, _require_admissions_applicant
from ifitwala_ed.admission.api.portal.enrollment import _read_only_for
from ifitwala_ed.api.file_access import (
    get_drive_file_thumbnail_ready_map,
    resolve_admissions_file_open_url,
    resolve_admissions_file_thumbnail_url,
)
from ifitwala_ed.integrations.drive.authority import get_current_drive_file_for_slot, get_drive_file_for_file

PROFILE_IMAGE_ALLOWED_EXTENSIONS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
}
PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL = "JPG, JPEG, PNG"
PROFILE_IMAGE_MAX_BYTES = 10 * 1024 * 1024
PROFILE_IMAGE_MAX_PIXELS = 25_000_000
_CURRENT_PROFILE_IMAGE_STATUSES = ("active", "processing", "blocked")


def _decode_profile_image_content(content_text: str | None) -> bytes:
    if not content_text:
        frappe.throw(_("Profile image content is required."))
    try:
        content = base64.b64decode(content_text, validate=True)
    except Exception:
        frappe.throw(_("Profile image content must be base64-encoded."))
    if not content:
        frappe.throw(_("Profile image content is empty."))
    return content


def _profile_image_allowed_formats_message() -> str:
    return _(
        "Only {accepted_formats} image files are accepted. Convert HEIC or HEIF photos to JPG before uploading."
    ).format(accepted_formats=PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL)


def _profile_image_invalid_content_message() -> str:
    return _("Uploaded profile image must be a valid {accepted_format} image.").format(
        accepted_format=PROFILE_IMAGE_ALLOWED_ACCEPT_LABEL
    )


def _profile_image_extension_mismatch_message() -> str:
    return _("The selected file extension does not match the uploaded image content. Please upload a JPG or PNG image.")


def _profile_image_size_limit_message() -> str:
    return _("Image is too large. Max file size is {max_size_mb} MB.").format(
        max_size_mb=PROFILE_IMAGE_MAX_BYTES // (1024 * 1024)
    )


def _profile_image_pixel_limit_message() -> str:
    return _("Image is too large. Max image size is {max_megapixels} megapixels.").format(
        max_megapixels=PROFILE_IMAGE_MAX_PIXELS // 1_000_000
    )


def _profile_image_output_filename(prefix: str) -> str:
    return f"{prefix}_{frappe.generate_hash(length=12)}.jpg"


def _profile_image_extension(upload_name: str | None) -> str:
    return os.path.splitext(_as_text(upload_name).strip().lower())[1]


def _sniff_profile_image_format(content: bytes) -> str | None:
    if content.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    return None


def _profile_image_to_rgb(image_obj):
    if image_obj.mode in {"RGBA", "LA"} or (image_obj.mode == "P" and "transparency" in getattr(image_obj, "info", {})):
        rgba_image = image_obj.convert("RGBA")
        background = Image.new("RGB", rgba_image.size, (255, 255, 255))
        background.paste(rgba_image, mask=rgba_image.getchannel("A"))
        return background
    return image_obj.convert("RGB")


def _normalize_profile_image_bytes(content: bytes) -> bytes:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as source_image:
                image_format = (_as_text(getattr(source_image, "format", None)).strip() or "").upper()
                if image_format not in {"JPEG", "PNG"}:
                    frappe.throw(_profile_image_invalid_content_message())

                width, height = source_image.size or (0, 0)
                if width <= 0 or height <= 0:
                    frappe.throw(_profile_image_invalid_content_message())
                if width * height > PROFILE_IMAGE_MAX_PIXELS:
                    frappe.throw(_profile_image_pixel_limit_message())

                source_image.load()
                normalized_image = ImageOps.exif_transpose(source_image)
                normalized_rgb = _profile_image_to_rgb(normalized_image)
                output_buffer = io.BytesIO()
                normalized_rgb.save(output_buffer, format="JPEG", optimize=True, quality=85)
                normalized_bytes = output_buffer.getvalue()
                if not normalized_bytes:
                    frappe.throw(_profile_image_invalid_content_message())
                return normalized_bytes
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        frappe.throw(_profile_image_pixel_limit_message())
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        frappe.throw(_profile_image_invalid_content_message())


def _prepare_profile_image_upload(
    *, upload_name: str | None, content: bytes, filename_prefix: str
) -> tuple[str, bytes]:
    extension = _profile_image_extension(upload_name)
    if extension not in PROFILE_IMAGE_ALLOWED_EXTENSIONS:
        frappe.throw(_profile_image_allowed_formats_message())

    if len(content) > PROFILE_IMAGE_MAX_BYTES:
        frappe.throw(_profile_image_size_limit_message())

    sniffed_format = _sniff_profile_image_format(content)
    if not sniffed_format:
        frappe.throw(_profile_image_invalid_content_message())

    expected_format = PROFILE_IMAGE_ALLOWED_EXTENSIONS.get(extension)
    if sniffed_format != expected_format:
        frappe.throw(_profile_image_extension_mismatch_message())

    normalized_bytes = _normalize_profile_image_bytes(content)
    return _profile_image_output_filename(filename_prefix), normalized_bytes


def _guardian_profile_image_slot(guardian_row_name: str) -> str:
    return f"guardian_profile_image__{frappe.scrub((guardian_row_name or '').strip())[:80]}"


def _resolve_applicant_profile_image_drive_file(*, applicant_name: str) -> dict | None:
    return get_current_drive_file_for_slot(
        primary_subject_type="Student Applicant",
        primary_subject_id=applicant_name,
        slot="profile_image",
        attached_doctype="Student Applicant",
        attached_name=applicant_name,
        fields=["name", "file", "canonical_ref"],
        statuses=_CURRENT_PROFILE_IMAGE_STATUSES,
    )


def _resolve_guardian_image_drive_file(*, applicant_name: str, guardian_row_name: str | None) -> dict | None:
    resolved_guardian_row_name = _as_text(guardian_row_name).strip()
    if not resolved_guardian_row_name:
        return None
    return get_current_drive_file_for_slot(
        primary_subject_type="Student Applicant",
        primary_subject_id=applicant_name,
        slot=_guardian_profile_image_slot(resolved_guardian_row_name),
        attached_doctype="Student Applicant Guardian",
        attached_name=resolved_guardian_row_name,
        fields=["name", "file", "canonical_ref"],
        statuses=_CURRENT_PROFILE_IMAGE_STATUSES,
    )


def _file_is_scoped_to_applicant(*, file_row: dict, applicant_name: str) -> bool:
    file_name = _as_text(file_row.get("name")).strip()
    if file_name:
        drive_file = get_drive_file_for_file(
            file_name,
            fields=["primary_subject_type", "primary_subject_id"],
            statuses=("active", "processing", "blocked"),
        )
        if drive_file and (
            _as_text(drive_file.get("primary_subject_type")).strip() == "Student Applicant"
            and _as_text(drive_file.get("primary_subject_id")).strip() == applicant_name
        ):
            return True

    return (
        _as_text(file_row.get("attached_to_doctype")).strip() == "Student Applicant"
        and _as_text(file_row.get("attached_to_name")).strip() == applicant_name
    )


def _resolve_guardian_image_file(
    *,
    applicant_name: str,
    guardian_row_name: str | None = None,
    guardian_image: str | None,
) -> dict | None:
    image_value = _as_text(guardian_image).strip()
    if not image_value:
        return None

    drive_file = _resolve_guardian_image_drive_file(
        applicant_name=applicant_name,
        guardian_row_name=guardian_row_name,
    )
    file_name = _as_text((drive_file or {}).get("file")).strip()
    if file_name:
        row = frappe.db.get_value(
            "File",
            file_name,
            ["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        if row and _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    file_name = ""
    if "download_admissions_file" in image_value:
        parsed = urlparse(image_value)
        file_name = _as_text((parse_qs(parsed.query).get("file") or [""])[0]).strip()
    if file_name:
        row = frappe.db.get_value(
            "File",
            file_name,
            ["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        if row and _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    file_rows = frappe.get_all(
        "File",
        filters={"file_url": image_value},
        fields=["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
        order_by="creation desc",
        limit=5,
    )
    for row in file_rows:
        if _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    return None


def _resolve_profile_image_drive_file_from_file_row(file_row: dict | None) -> dict | None:
    file_name = _as_text((file_row or {}).get("name")).strip()
    if not file_name:
        return None
    return get_drive_file_for_file(
        file_name,
        fields=["name", "file", "canonical_ref"],
        statuses=_CURRENT_PROFILE_IMAGE_STATUSES,
    )


def _resolve_applicant_profile_image_file(*, applicant_name: str, applicant_image: str | None) -> dict | None:
    image_value = _as_text(applicant_image).strip()
    if not image_value:
        return None

    drive_file = _resolve_applicant_profile_image_drive_file(applicant_name=applicant_name)
    file_name = _as_text((drive_file or {}).get("file")).strip()
    if file_name:
        row = frappe.db.get_value(
            "File",
            file_name,
            ["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        if row and _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    file_name = ""
    if "download_admissions_file" in image_value:
        parsed = urlparse(image_value)
        file_name = _as_text((parse_qs(parsed.query).get("file") or [""])[0]).strip()
    if file_name:
        row = frappe.db.get_value(
            "File",
            file_name,
            ["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
            as_dict=True,
        )
        if row and _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    file_rows = frappe.get_all(
        "File",
        filters={"file_url": image_value},
        fields=["name", "file_url", "attached_to_doctype", "attached_to_name", "attached_to_field"],
        order_by="creation desc",
        limit=5,
    )
    for row in file_rows:
        if _file_is_scoped_to_applicant(file_row=row, applicant_name=applicant_name):
            return row

    return None


def _resolve_applicant_profile_image_authority(
    *,
    applicant_name: str,
    applicant_image: str | None,
) -> tuple[dict, dict | None]:
    drive_file = _resolve_applicant_profile_image_drive_file(applicant_name=applicant_name) or {}
    file_row = _resolve_applicant_profile_image_file(
        applicant_name=applicant_name,
        applicant_image=applicant_image,
    )
    if not drive_file.get("name"):
        drive_file = _resolve_profile_image_drive_file_from_file_row(file_row) or drive_file
    return drive_file, file_row


def _resolve_guardian_image_authority(
    *,
    applicant_name: str,
    guardian_row_name: str | None,
    guardian_image: str | None,
) -> tuple[dict, dict | None]:
    drive_file = (
        _resolve_guardian_image_drive_file(
            applicant_name=applicant_name,
            guardian_row_name=guardian_row_name,
        )
        or {}
    )
    file_row = _resolve_guardian_image_file(
        applicant_name=applicant_name,
        guardian_row_name=guardian_row_name,
        guardian_image=guardian_image,
    )
    if not drive_file.get("name"):
        drive_file = _resolve_profile_image_drive_file_from_file_row(file_row) or drive_file
    return drive_file, file_row


def _collect_guardian_image_authority_map(applicant) -> dict[str, tuple[dict, dict | None]]:
    authority_map: dict[str, tuple[dict, dict | None]] = {}
    applicant_name = _as_text(applicant.get("name")).strip()
    for row in applicant.get("guardians") or []:
        guardian_row_name = _as_text(row.get("name")).strip()
        if not guardian_row_name:
            continue
        authority_map[guardian_row_name] = _resolve_guardian_image_authority(
            applicant_name=applicant_name,
            guardian_row_name=guardian_row_name,
            guardian_image=row.get("guardian_image"),
        )
    return authority_map


def _build_admissions_profile_image_urls(
    *,
    applicant_name: str,
    original_image: str | None,
    drive_file: dict | None,
    file_row: dict | None,
    guardian_row_name: str | None = None,
    thumbnail_ready: bool | None = None,
) -> dict[str, str]:
    del guardian_row_name
    resolved_drive_file = drive_file or {}
    resolved_file_row = file_row or {}
    file_name = _as_text(resolved_file_row.get("name") or resolved_drive_file.get("file")).strip() or None
    drive_file_id = _as_text(resolved_drive_file.get("name")).strip() or None
    canonical_ref = _as_text(resolved_drive_file.get("canonical_ref")).strip() or None
    fallback_file_url = (
        None if (file_name or drive_file_id or canonical_ref) else _as_text(original_image).strip() or None
    )

    open_url = (
        resolve_admissions_file_open_url(
            file_name=file_name,
            file_url=fallback_file_url,
            drive_file_id=drive_file_id,
            canonical_ref=canonical_ref,
            context_doctype="Student Applicant",
            context_name=applicant_name,
        )
        or ""
    )

    image_url = ""
    if drive_file_id or canonical_ref:
        image_url = (
            resolve_admissions_file_thumbnail_url(
                file_name=file_name,
                file_url=None,
                drive_file_id=drive_file_id,
                canonical_ref=canonical_ref,
                context_doctype="Student Applicant",
                context_name=applicant_name,
                thumbnail_ready=thumbnail_ready,
            )
            or ""
        )

    return {"image_url": image_url, "open_url": open_url}


def _applicant_image_open_url(*, applicant_name: str, applicant_image: str | None) -> str:
    drive_file, file_row = _resolve_applicant_profile_image_authority(
        applicant_name=applicant_name,
        applicant_image=applicant_image,
    )
    return _build_admissions_profile_image_urls(
        applicant_name=applicant_name,
        original_image=applicant_image,
        drive_file=drive_file,
        file_row=file_row,
    )["open_url"]


def _guardian_image_open_url(
    *,
    applicant_name: str,
    guardian_row_name: str | None = None,
    guardian_image: str | None,
) -> str:
    drive_file, file_row = _resolve_guardian_image_authority(
        applicant_name=applicant_name,
        guardian_row_name=guardian_row_name,
        guardian_image=guardian_image,
    )
    return _build_admissions_profile_image_urls(
        applicant_name=applicant_name,
        original_image=guardian_image,
        drive_file=drive_file,
        file_row=file_row,
    )["open_url"]


def upload_applicant_profile_image_impl(
    *,
    student_applicant: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    student_applicant = _request_form_value("student_applicant", student_applicant)
    file_name = _request_form_value("file_name", file_name)
    content = _request_form_value("content", content)
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    is_read_only, reason = _read_only_for(_as_text(row.get("application_status")).strip())
    if is_read_only:
        frappe.throw(reason or _("This application is read-only."), frappe.PermissionError)

    applicant_name = _as_text(row.get("name")).strip()
    if not applicant_name:
        frappe.throw(_("Applicant context is missing."))

    upload_name = _as_text(file_name).strip()
    if not upload_name:
        frappe.throw(_("file_name is required."))

    upload_content = _decode_profile_image_content(_as_text(content))
    normalized_file_name, normalized_content = _prepare_profile_image_upload(
        upload_name=upload_name,
        content=upload_content,
        filename_prefix="applicant_profile_image",
    )

    applicant = frappe.get_doc("Student Applicant", applicant_name)
    if not applicant.get("organization") or not applicant.get("school"):
        frappe.throw(_("Organization and School are required for governed admissions uploads."))

    upload_result = admission_api.upload_applicant_profile_image(
        student_applicant=applicant.name,
        file_name=normalized_file_name,
        content=normalized_content,
        upload_source="SPA",
    )
    drive_file_id = _as_text(upload_result.get("drive_file_id")).strip()
    thumbnail_ready_map = get_drive_file_thumbnail_ready_map([drive_file_id]) if drive_file_id else {}
    image_urls = _build_admissions_profile_image_urls(
        applicant_name=applicant.name,
        original_image=None,
        drive_file={
            "name": drive_file_id,
            "file": upload_result.get("file"),
            "canonical_ref": upload_result.get("canonical_ref"),
        },
        file_row=None,
        thumbnail_ready=thumbnail_ready_map.get(drive_file_id),
    )

    return {
        "ok": True,
        "file": upload_result.get("file"),
        "image_url": image_urls["image_url"],
        "open_url": image_urls["open_url"],
        "file_name": normalized_file_name,
        "file_size": len(normalized_content),
        "drive_file_id": upload_result.get("drive_file_id"),
        "canonical_ref": upload_result.get("canonical_ref"),
    }


def upload_applicant_guardian_image_impl(
    *,
    student_applicant: str | None = None,
    guardian_row_name: str | None = None,
    file_name: str | None = None,
    content: str | None = None,
):
    student_applicant = _request_form_value("student_applicant", student_applicant)
    file_name = _request_form_value("file_name", file_name)
    content = _request_form_value("content", content)
    user = _require_admissions_applicant()
    row = _ensure_applicant_match(student_applicant, user)

    is_read_only, reason = _read_only_for(_as_text(row.get("application_status")).strip())
    if is_read_only:
        frappe.throw(reason or _("This application is read-only."), frappe.PermissionError)

    applicant_name = _as_text(row.get("name")).strip()
    if not applicant_name:
        frappe.throw(_("Applicant context is missing."))
    guardian_row_name = _as_text(_request_form_value("guardian_row_name", guardian_row_name)).strip()
    if not guardian_row_name:
        frappe.throw(_("guardian_row_name is required."))

    upload_name = _as_text(file_name).strip()
    if not upload_name:
        frappe.throw(_("file_name is required."))

    upload_content = _decode_profile_image_content(_as_text(content))
    normalized_file_name, normalized_content = _prepare_profile_image_upload(
        upload_name=upload_name,
        content=upload_content,
        filename_prefix="guardian_profile_image",
    )

    applicant = frappe.get_doc("Student Applicant", applicant_name)
    if not applicant.get("organization") or not applicant.get("school"):
        frappe.throw(_("Organization and School are required for governed admissions uploads."))

    upload_result = admission_api.upload_applicant_guardian_image(
        student_applicant=applicant.name,
        guardian_row_name=guardian_row_name,
        file_name=normalized_file_name,
        content=normalized_content,
        upload_source="SPA",
    )
    drive_file_id = _as_text(upload_result.get("drive_file_id")).strip()
    thumbnail_ready_map = get_drive_file_thumbnail_ready_map([drive_file_id]) if drive_file_id else {}
    image_urls = _build_admissions_profile_image_urls(
        applicant_name=applicant.name,
        original_image=None,
        drive_file={
            "name": drive_file_id,
            "file": upload_result.get("file"),
            "canonical_ref": upload_result.get("canonical_ref"),
        },
        file_row=None,
        thumbnail_ready=thumbnail_ready_map.get(drive_file_id),
    )

    return {
        "ok": True,
        "file": upload_result.get("file"),
        "image_url": image_urls["image_url"],
        "open_url": image_urls["open_url"],
        "file_name": normalized_file_name,
        "file_size": len(normalized_content),
        "drive_file_id": upload_result.get("drive_file_id"),
        "canonical_ref": upload_result.get("canonical_ref"),
    }
