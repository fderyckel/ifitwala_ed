from __future__ import annotations

import mimetypes
from typing import Any

_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif", "bmp", "svg"}
_VIDEO_EXTENSIONS = {"mp4", "mov", "webm", "m4v", "avi", "mkv"}
_AUDIO_EXTENSIONS = {"mp3", "wav", "ogg", "m4a", "aac", "flac"}
_OFFICE_EXTENSIONS = {
    "doc",
    "docx",
    "ppt",
    "pptx",
    "xls",
    "xlsx",
    "odt",
    "ods",
    "odp",
}
_ARCHIVE_EXTENSIONS = {"zip", "rar", "7z", "tar", "gz", "bz2", "xz"}


def clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def coerce_size_bytes(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def extract_file_extension(*, file_name: Any = None, file_url: Any = None) -> str | None:
    for candidate in (file_name, file_url):
        resolved = clean_text(candidate)
        if not resolved:
            continue
        last_segment = resolved.rsplit("/", 1)[-1]
        if "." not in last_segment:
            continue
        extension = last_segment.rsplit(".", 1)[-1].strip().lower()
        if extension:
            return extension
    return None


def guess_mime_type(*, file_name: Any = None, file_url: Any = None) -> str | None:
    for candidate in (file_name, file_url):
        resolved = clean_text(candidate)
        if not resolved:
            continue
        guessed = mimetypes.guess_type(resolved)[0]
        if guessed:
            return guessed
    return None


def classify_attachment_kind(
    *,
    file_id: Any = None,
    link_url: Any = None,
    mime_type: Any = None,
    extension: Any = None,
) -> str:
    if clean_text(link_url) and not clean_text(file_id):
        return "link"

    resolved_mime = clean_text(mime_type)
    resolved_extension = clean_text(extension)
    if resolved_extension:
        resolved_extension = resolved_extension.lower()

    if resolved_mime:
        if resolved_mime.startswith("image/"):
            return "image"
        if resolved_mime == "application/pdf":
            return "pdf"
        if resolved_mime.startswith("video/"):
            return "video"
        if resolved_mime.startswith("audio/"):
            return "audio"
        if resolved_mime.startswith("text/"):
            return "text"
        if resolved_mime.startswith("application/zip"):
            return "archive"
        if resolved_mime in {
            "application/msword",
            "application/vnd.ms-excel",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/vnd.oasis.opendocument.presentation",
        }:
            return "office"

    if resolved_extension in _IMAGE_EXTENSIONS:
        return "image"
    if resolved_extension == "pdf":
        return "pdf"
    if resolved_extension in _VIDEO_EXTENSIONS:
        return "video"
    if resolved_extension in _AUDIO_EXTENSIONS:
        return "audio"
    if resolved_extension in _OFFICE_EXTENSIONS:
        return "office"
    if resolved_extension in _ARCHIVE_EXTENSIONS:
        return "archive"
    if resolved_extension in {"txt", "md", "csv", "json", "xml"}:
        return "text"
    return "other"


def resolve_preview_mode(
    *,
    kind: str,
    thumbnail_url: Any = None,
    preview_url: Any = None,
    link_url: Any = None,
) -> str:
    if clean_text(link_url) and kind == "link":
        return "external_link"
    if kind == "image":
        if clean_text(thumbnail_url):
            return "thumbnail_image"
        if clean_text(preview_url):
            return "inline_image"
        return "icon_only"
    if kind == "pdf" and clean_text(preview_url):
        return "pdf_embed"
    if kind in {"video", "audio"} and clean_text(preview_url):
        return "media_player"
    return "icon_only"


def build_attachment_preview_item(
    *,
    item_id: Any,
    owner_doctype: Any,
    owner_name: Any,
    file_id: Any = None,
    link_url: Any = None,
    display_name: Any = None,
    description: Any = None,
    mime_type: Any = None,
    extension: Any = None,
    size_bytes: Any = None,
    preview_status: Any = None,
    thumbnail_url: Any = None,
    preview_url: Any = None,
    open_url: Any = None,
    download_url: Any = None,
    width: Any = None,
    height: Any = None,
    page_count: Any = None,
    duration_seconds: Any = None,
    can_preview: bool | None = None,
    can_open: bool | None = None,
    can_download: bool | None = None,
    can_delete: bool | None = None,
    is_latest_version: bool | None = None,
    version_label: Any = None,
    badge: Any = None,
    source_label: Any = None,
    created_at: Any = None,
    created_by_label: Any = None,
) -> dict[str, Any]:
    resolved_file_id = clean_text(file_id)
    resolved_link_url = clean_text(link_url)
    resolved_display_name = clean_text(display_name) or resolved_file_id or resolved_link_url or clean_text(item_id)
    resolved_mime_type = clean_text(mime_type)
    resolved_extension = clean_text(extension)
    kind = classify_attachment_kind(
        file_id=resolved_file_id,
        link_url=resolved_link_url,
        mime_type=resolved_mime_type,
        extension=resolved_extension,
    )
    resolved_thumbnail_url = clean_text(thumbnail_url)
    resolved_preview_url = clean_text(preview_url)
    resolved_open_url = clean_text(open_url)
    resolved_download_url = clean_text(download_url)
    if not resolved_download_url and resolved_file_id:
        resolved_download_url = resolved_open_url

    return {
        "item_id": clean_text(item_id),
        "owner_doctype": clean_text(owner_doctype),
        "owner_name": clean_text(owner_name),
        "file_id": resolved_file_id,
        "link_url": resolved_link_url,
        "display_name": resolved_display_name,
        "description": clean_text(description),
        "mime_type": resolved_mime_type,
        "extension": resolved_extension.lower() if resolved_extension else None,
        "size_bytes": coerce_size_bytes(size_bytes),
        "kind": kind,
        "preview_mode": resolve_preview_mode(
            kind=kind,
            thumbnail_url=resolved_thumbnail_url,
            preview_url=resolved_preview_url,
            link_url=resolved_link_url,
        ),
        "preview_status": clean_text(preview_status),
        "thumbnail_url": resolved_thumbnail_url,
        "preview_url": resolved_preview_url,
        "open_url": resolved_open_url,
        "download_url": resolved_download_url,
        "width": width,
        "height": height,
        "page_count": page_count,
        "duration_seconds": duration_seconds,
        "can_preview": bool(resolved_preview_url) if can_preview is None else bool(can_preview),
        "can_open": bool(resolved_open_url or resolved_link_url) if can_open is None else bool(can_open),
        "can_download": bool(resolved_download_url) if can_download is None else bool(can_download),
        "can_delete": False if can_delete is None else bool(can_delete),
        "is_latest_version": bool(is_latest_version) if is_latest_version is not None else True,
        "version_label": clean_text(version_label),
        "badge": clean_text(badge),
        "source_label": clean_text(source_label),
        "created_at": clean_text(created_at),
        "created_by_label": clean_text(created_by_label),
    }
