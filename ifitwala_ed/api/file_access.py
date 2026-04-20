# ifitwala_ed/api/file_access.py

from __future__ import annotations

import hashlib
import mimetypes
import os
from types import SimpleNamespace
from urllib.parse import unquote, urlencode, urlparse

import frappe
from frappe import _

from ifitwala_ed.admission.access import (
    ADMISSIONS_APPLICANT_ROLE,
    ADMISSIONS_FAMILY_ROLE,
    user_can_access_student_applicant,
)
from ifitwala_ed.admission.admission_utils import (
    has_open_applicant_review_access,
    has_scoped_staff_access_to_student_applicant,
    is_admissions_file_staff_user,
)
from ifitwala_ed.api.org_comm_utils import check_audience_match, expand_employee_visibility_context
from ifitwala_ed.curriculum import materials as materials_domain
from ifitwala_ed.integrations.drive.authority import (
    get_current_drive_file_for_attachment,
    get_current_drive_file_for_slot,
    get_drive_file_by_canonical_ref,
    get_drive_file_by_id,
    get_drive_file_for_file,
)
from ifitwala_ed.routing.policy import has_active_employee_profile

ADMISSIONS_ATTACHMENT_DOCTYPES = {
    "Applicant Document Item",
    "Applicant Health Profile",
    "Student Applicant",
    "Student Applicant Guardian",
    "Contact",
}
CONTEXT_STUDENT_APPLICANT = "Student Applicant"
CONTEXT_APPLICANT_INTERVIEW = "Applicant Interview"
CONTEXT_TASK_SUBMISSION = "Task Submission"
CONTEXT_STUDENT_PORTFOLIO_ITEM = "Student Portfolio Item"
CONTEXT_SUPPORTING_MATERIAL = "Supporting Material"
CONTEXT_MATERIAL_PLACEMENT = "Material Placement"
CONTEXT_STUDENT = "Student"
CONTEXT_GUARDIAN = "Guardian"
CONTEXT_EMPLOYEE = "Employee"
CONTEXT_ORG_COMMUNICATION = "Org Communication"
_THUMBNAIL_REDIRECT_CACHE_TTL_SECONDS = 240
EMPLOYEE_PROFILE_IMAGE_PURPOSE = "employee_profile_display"
STUDENT_PROFILE_IMAGE_PURPOSE = "student_profile_display"
GUARDIAN_PROFILE_IMAGE_PURPOSE = "guardian_profile_display"
PROFILE_IMAGE_SLOT = "profile_image"
EMPLOYEE_PROFILE_IMAGE_SLOT = PROFILE_IMAGE_SLOT
CARD_IMAGE_DERIVATIVE_ROLE = "thumb"
CARD_PDF_DERIVATIVE_ROLE = "pdf_card"
PDF_MIME_TYPE = "application/pdf"


def _is_external_url(value: str | None) -> bool:
    raw = (value or "").strip()
    return raw.startswith(("http://", "https://"))


def _is_public_site_file_url(value: str | None) -> bool:
    raw = (value or "").strip()
    return raw.startswith("/files/") and not raw.startswith("/files/ifitwala_drive/")


def _is_raw_private_redirect_target(value: str | None) -> bool:
    raw = (value or "").strip()
    if not raw:
        return False

    path = str(urlparse(raw).path or raw).strip()
    return path.startswith("/private/") or path.startswith("private/")


def _resolve_file_name_from_url(file_url: str | None) -> str | None:
    raw_url = (file_url or "").strip()
    if not raw_url or _is_external_url(raw_url):
        return None
    resolved = frappe.db.get_value("File", {"file_url": raw_url}, "name")
    resolved_name = (resolved or "").strip()
    return resolved_name or None


def _guess_filename_from_url(file_url: str | None) -> str | None:
    raw_url = (file_url or "").strip()
    if not raw_url:
        return None
    path = unquote(str(urlparse(raw_url).path or raw_url).strip())
    filename = os.path.basename(path)
    return filename or None


def _resolve_card_preview_derivative_role_for_mime_type(mime_type: str | None) -> str:
    resolved_mime_type = str(mime_type or "").strip().lower()
    if resolved_mime_type == PDF_MIME_TYPE:
        return CARD_PDF_DERIVATIVE_ROLE
    return CARD_IMAGE_DERIVATIVE_ROLE


def _resolve_card_preview_derivative_role_for_drive_file(drive_file_id: str | None) -> str:
    resolved_drive_file_id = str(drive_file_id or "").strip()
    if not resolved_drive_file_id:
        return CARD_IMAGE_DERIVATIVE_ROLE

    drive_file_row = (
        frappe.db.get_value(
            "Drive File",
            resolved_drive_file_id,
            ["name", "current_version"],
            as_dict=True,
        )
        or {}
    )
    current_version = str((drive_file_row or {}).get("current_version") or "").strip()
    mime_type = frappe.db.get_value("Drive File Version", current_version, "mime_type") if current_version else None
    return _resolve_card_preview_derivative_role_for_mime_type(mime_type)


def _resolve_local_site_file_path(file_url: str | None, *, is_private: int | bool | None = None) -> str | None:
    raw_url = (file_url or "").strip()
    if not raw_url or _is_external_url(raw_url):
        return None

    path = unquote(str(urlparse(raw_url).path or raw_url).strip())
    if not path:
        return None

    rel_path = path.lstrip("/")
    if rel_path.startswith("private/") or rel_path.startswith("public/"):
        abs_path = frappe.utils.get_site_path(rel_path)
    else:
        base = "private" if frappe.utils.cint(is_private) else "public"
        abs_path = frappe.utils.get_site_path(base, rel_path)

    return abs_path if os.path.exists(abs_path) else None


def _respond_with_local_file_content(
    *,
    file_url: str | None,
    filename: str | None = None,
    is_private: int | bool | None = None,
    cache_headers: bool = False,
) -> bool:
    abs_path = _resolve_local_site_file_path(file_url, is_private=is_private)
    if not abs_path:
        return False

    with open(abs_path, "rb") as handle:
        content = handle.read()

    resolved_filename = str(filename or _guess_filename_from_url(file_url) or "document").strip() or "document"
    content_type = mimetypes.guess_type(resolved_filename)[0] or "application/octet-stream"

    if cache_headers:
        _set_thumbnail_cache_headers()

    frappe.local.response["type"] = "download"
    frappe.local.response["filename"] = resolved_filename
    frappe.local.response["filecontent"] = content
    frappe.local.response["display_content_as"] = "inline"
    frappe.local.response["content_type"] = content_type
    return True


def _respond_with_delivery_target(*, target_url: str | None, cache_headers: bool = False) -> bool:
    resolved_target_url = str(target_url or "").strip()
    if not resolved_target_url:
        return False
    if _is_raw_private_redirect_target(resolved_target_url):
        return _respond_with_local_file_content(
            file_url=resolved_target_url,
            is_private=True,
            cache_headers=cache_headers,
        )
    return _respond_with_redirect_target(target_url=resolved_target_url, cache_headers=cache_headers)


def _build_file_action_params(
    *,
    file_name: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> dict[str, str]:
    params: dict[str, str] = {}
    resolved_file = (file_name or "").strip()
    resolved_drive_file_id = (drive_file_id or "").strip()
    resolved_canonical_ref = (canonical_ref or "").strip()
    if resolved_file:
        params["file"] = resolved_file
    if resolved_drive_file_id:
        params["drive_file_id"] = resolved_drive_file_id
    elif resolved_canonical_ref:
        params["canonical_ref"] = resolved_canonical_ref
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    return params


def build_admissions_file_open_url(
    *,
    file_name: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str:
    params = _build_file_action_params(
        file_name=file_name,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    if not params:
        return ""
    return f"/api/method/ifitwala_ed.api.file_access.download_admissions_file?{urlencode(params)}"


def build_admissions_file_preview_url(
    *,
    file_name: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str:
    params = _build_file_action_params(
        file_name=file_name,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    if not params:
        return ""
    return f"/api/method/ifitwala_ed.api.file_access.preview_admissions_file?{urlencode(params)}"


def build_admissions_file_thumbnail_url(
    *,
    file_name: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str:
    params = _build_file_action_params(
        file_name=file_name,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    if not params:
        return ""
    return f"/api/method/ifitwala_ed.api.file_access.thumbnail_admissions_file?{urlencode(params)}"


def resolve_admissions_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if _is_external_url(raw_url):
        return raw_url

    resolved_name = (file_name or "").strip()
    resolved_drive_file_id = (drive_file_id or "").strip()
    resolved_canonical_ref = (canonical_ref or "").strip()
    if not (resolved_name or resolved_drive_file_id or resolved_canonical_ref):
        return raw_url if _is_public_site_file_url(raw_url) else None

    open_url = build_admissions_file_open_url(
        file_name=resolved_name,
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    return open_url or raw_url or None


def resolve_admissions_file_preview_url(
    *,
    file_name: str | None,
    file_url: str | None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    preview_ready: bool | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if _is_external_url(raw_url):
        return raw_url

    resolved_name = (file_name or "").strip()
    resolved_drive_file_id = (drive_file_id or "").strip()
    resolved_canonical_ref = (canonical_ref or "").strip()
    if not (resolved_name or resolved_drive_file_id or resolved_canonical_ref):
        return raw_url if _is_public_site_file_url(raw_url) else None

    if preview_ready is False:
        return None

    preview_url = build_admissions_file_preview_url(
        file_name=resolved_name,
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    return preview_url or None


def resolve_admissions_file_thumbnail_url(
    *,
    file_name: str | None,
    file_url: str | None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    thumbnail_ready: bool | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if _is_external_url(raw_url):
        return None

    resolved_name = (file_name or "").strip()
    resolved_drive_file_id = (drive_file_id or "").strip()
    resolved_canonical_ref = (canonical_ref or "").strip()
    if not (resolved_name or resolved_drive_file_id or resolved_canonical_ref):
        return None
    if thumbnail_ready is False:
        return None

    thumbnail_url = build_admissions_file_thumbnail_url(
        file_name=resolved_name,
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    return thumbnail_url or None


def build_academic_file_open_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
    derivative_role: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    if (share_token or "").strip():
        params["share_token"] = share_token.strip()
    if (viewer_email or "").strip():
        params["viewer_email"] = viewer_email.strip()
    if (derivative_role or "").strip():
        params["derivative_role"] = derivative_role.strip()
    return f"/api/method/ifitwala_ed.api.file_access.download_academic_file?{urlencode(params)}"


def build_academic_file_preview_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    if (share_token or "").strip():
        params["share_token"] = share_token.strip()
    if (viewer_email or "").strip():
        params["viewer_email"] = viewer_email.strip()
    return f"/api/method/ifitwala_ed.api.file_access.preview_academic_file?{urlencode(params)}"


def build_academic_file_thumbnail_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    if (share_token or "").strip():
        params["share_token"] = share_token.strip()
    if (viewer_email or "").strip():
        params["viewer_email"] = viewer_email.strip()
    return f"/api/method/ifitwala_ed.api.file_access.thumbnail_academic_file?{urlencode(params)}"


def get_academic_file_thumbnail_ready_map(file_names: list[str] | tuple[str, ...] | set[str]) -> dict[str, bool]:
    cleaned = sorted({str(file_name or "").strip() for file_name in (file_names or []) if str(file_name or "").strip()})
    if not cleaned:
        return {}

    rows = (
        frappe.db.sql(
            """
        SELECT
            df.file,
            df.preview_status,
            df.current_version,
            dfd.name AS derivative_name
        FROM `tabDrive File` df
        LEFT JOIN `tabDrive File Version` dfv
          ON dfv.name = df.current_version
        LEFT JOIN `tabDrive File Derivative` dfd
          ON dfd.drive_file = df.name
         AND dfd.drive_file_version = df.current_version
         AND dfd.derivative_role = CASE
             WHEN COALESCE(dfv.mime_type, '') = 'application/pdf' THEN 'pdf_card'
             ELSE 'thumb'
         END
         AND dfd.status = 'ready'
        WHERE df.file IN %(file_names)s
        """,
            {"file_names": tuple(cleaned)},
            as_dict=True,
        )
        or []
    )

    ready_map = {file_name: False for file_name in cleaned}
    for row in rows:
        file_name = str((row or {}).get("file") or "").strip()
        if not file_name or file_name not in ready_map:
            continue
        ready_map[file_name] = ready_map[file_name] or bool(
            str((row or {}).get("preview_status") or "").strip() == "ready"
            and str((row or {}).get("current_version") or "").strip()
            and str((row or {}).get("derivative_name") or "").strip()
        )

    return ready_map


def get_drive_file_thumbnail_ready_map(
    drive_file_ids: list[str] | tuple[str, ...] | set[str],
) -> dict[str, bool]:
    cleaned = sorted(
        {
            str(drive_file_id or "").strip()
            for drive_file_id in (drive_file_ids or [])
            if str(drive_file_id or "").strip()
        }
    )
    if not cleaned:
        return {}

    rows = (
        frappe.db.sql(
            """
        SELECT
            df.name,
            df.preview_status,
            df.current_version,
            dfd.name AS derivative_name
        FROM `tabDrive File` df
        LEFT JOIN `tabDrive File Version` dfv
          ON dfv.name = df.current_version
        LEFT JOIN `tabDrive File Derivative` dfd
          ON dfd.drive_file = df.name
         AND dfd.drive_file_version = df.current_version
         AND dfd.derivative_role = CASE
             WHEN COALESCE(dfv.mime_type, '') = 'application/pdf' THEN 'pdf_card'
             ELSE 'thumb'
         END
         AND dfd.status = 'ready'
        WHERE df.name IN %(drive_file_ids)s
        """,
            {"drive_file_ids": tuple(cleaned)},
            as_dict=True,
        )
        or []
    )

    ready_map = {drive_file_id: False for drive_file_id in cleaned}
    for row in rows:
        drive_file_id = str((row or {}).get("name") or "").strip()
        if not drive_file_id or drive_file_id not in ready_map:
            continue
        ready_map[drive_file_id] = ready_map[drive_file_id] or bool(
            str((row or {}).get("preview_status") or "").strip() == "ready"
            and str((row or {}).get("current_version") or "").strip()
            and str((row or {}).get("derivative_name") or "").strip()
        )
    return ready_map


def resolve_academic_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
    derivative_role: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if _is_external_url(raw_url):
        return raw_url

    resolved_name = (file_name or "").strip()
    if not resolved_name:
        return raw_url if _is_public_site_file_url(raw_url) else None

    open_url = build_academic_file_open_url(
        file_name=resolved_name,
        context_doctype=context_doctype,
        context_name=context_name,
        share_token=share_token,
        viewer_email=viewer_email,
        derivative_role=derivative_role,
    )
    return open_url or raw_url or None


def resolve_academic_file_preview_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    resolved_name = (file_name or "").strip()
    if resolved_name:
        preview_url = build_academic_file_preview_url(
            file_name=resolved_name,
            context_doctype=context_doctype,
            context_name=context_name,
            share_token=share_token,
            viewer_email=viewer_email,
        )
        return preview_url or None

    if _is_external_url(raw_url) or _is_public_site_file_url(raw_url):
        return raw_url or None
    return None


def resolve_academic_file_thumbnail_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
    thumbnail_ready: bool | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    resolved_name = (file_name or "").strip()
    if resolved_name:
        resolved_thumbnail_ready = (
            thumbnail_ready
            if thumbnail_ready is not None
            else get_academic_file_thumbnail_ready_map([resolved_name]).get(resolved_name, False)
        )
        if not resolved_thumbnail_ready:
            return None
        thumbnail_url = build_academic_file_thumbnail_url(
            file_name=resolved_name,
            context_doctype=context_doctype,
            context_name=context_name,
            share_token=share_token,
            viewer_email=viewer_email,
        )
        return thumbnail_url or None

    if _is_external_url(raw_url) or _is_public_site_file_url(raw_url):
        return raw_url or None
    return None


def build_guardian_file_open_url(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    derivative_role: str | None = None,
) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""

    params = {"file": resolved_file}
    if (context_doctype or "").strip():
        params["context_doctype"] = context_doctype.strip()
    if (context_name or "").strip():
        params["context_name"] = context_name.strip()
    if (derivative_role or "").strip():
        params["derivative_role"] = derivative_role.strip()
    return f"/api/method/ifitwala_ed.api.file_access.download_guardian_file?{urlencode(params)}"


def resolve_guardian_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    derivative_role: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if _is_external_url(raw_url):
        return raw_url

    resolved_name = (file_name or "").strip() or _resolve_file_name_from_url(raw_url) or ""
    if not resolved_name:
        return raw_url if _is_public_site_file_url(raw_url) else None

    open_url = build_guardian_file_open_url(
        file_name=resolved_name,
        context_doctype=context_doctype,
        context_name=context_name,
        derivative_role=derivative_role,
    )
    return open_url or raw_url or None


def build_employee_file_open_url(
    *,
    file_name: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    derivative_role: str | None = None,
) -> str:
    params = _build_file_action_params(
        file_name=file_name,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    if not params:
        return ""

    if (derivative_role or "").strip():
        params["derivative_role"] = derivative_role.strip()
    return f"/api/method/ifitwala_ed.api.file_access.download_employee_file?{urlencode(params)}"


def resolve_employee_file_open_url(
    *,
    file_name: str | None,
    file_url: str | None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    derivative_role: str | None = None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if _is_external_url(raw_url):
        return raw_url

    resolved_name = (file_name or "").strip()
    resolved_drive_file_id = (drive_file_id or "").strip()
    resolved_canonical_ref = (canonical_ref or "").strip()
    if not resolved_name and not resolved_drive_file_id and not resolved_canonical_ref:
        resolved_name = _resolve_file_name_from_url(raw_url) or ""
    if not (resolved_name or resolved_drive_file_id or resolved_canonical_ref):
        return raw_url if _is_public_site_file_url(raw_url) else None

    open_url = build_employee_file_open_url(
        file_name=resolved_name,
        drive_file_id=resolved_drive_file_id,
        canonical_ref=resolved_canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
        derivative_role=derivative_role,
    )
    return open_url or raw_url or None


def build_org_communication_attachment_open_url(
    *,
    org_communication: str,
    row_name: str,
) -> str:
    resolved_org_communication = (org_communication or "").strip()
    resolved_row_name = (row_name or "").strip()
    if not resolved_org_communication or not resolved_row_name:
        return ""

    return "/api/method/ifitwala_ed.api.file_access.open_org_communication_attachment?" + urlencode(
        {"org_communication": resolved_org_communication, "row_name": resolved_row_name}
    )


def build_org_communication_attachment_preview_url(
    *,
    org_communication: str,
    row_name: str,
) -> str:
    resolved_org_communication = (org_communication or "").strip()
    resolved_row_name = (row_name or "").strip()
    if not resolved_org_communication or not resolved_row_name:
        return ""

    return "/api/method/ifitwala_ed.api.file_access.preview_org_communication_attachment?" + urlencode(
        {"org_communication": resolved_org_communication, "row_name": resolved_row_name}
    )


def build_org_communication_attachment_thumbnail_url(
    *,
    org_communication: str,
    row_name: str,
) -> str:
    resolved_org_communication = (org_communication or "").strip()
    resolved_row_name = (row_name or "").strip()
    if not resolved_org_communication or not resolved_row_name:
        return ""

    return "/api/method/ifitwala_ed.api.file_access.thumbnail_org_communication_attachment?" + urlencode(
        {"org_communication": resolved_org_communication, "row_name": resolved_row_name}
    )


def build_public_website_media_url(*, file_name: str) -> str:
    resolved_file = (file_name or "").strip()
    if not resolved_file:
        return ""
    return "/api/method/ifitwala_ed.api.file_access.open_public_website_media?" + urlencode({"file": resolved_file})


def resolve_public_website_media_url(
    *,
    file_name: str | None,
    file_url: str | None,
) -> str | None:
    raw_url = (file_url or "").strip()
    if raw_url.startswith(("http://", "https://")):
        return raw_url
    if raw_url.startswith("/files/") and not raw_url.startswith("/files/ifitwala_drive/"):
        return raw_url

    resolved_name = (file_name or "").strip()
    if not resolved_name:
        if raw_url.startswith("/private/") or raw_url.startswith("/files/ifitwala_drive/"):
            return None
        return raw_url or None

    open_url = build_public_website_media_url(file_name=resolved_name)
    return open_url or raw_url or None


def _require_authenticated_user() -> str:
    user = (frappe.session.user or "").strip()
    if not user or user == "Guest":
        frappe.throw(_("You need to sign in to access this file."), frappe.PermissionError)
    return user


def _is_adminish(user: str) -> bool:
    return user == "Administrator" or ("System Manager" in frappe.get_roles(user))


def _resolve_file_row(file_name: str) -> dict:
    row = frappe.db.get_value(
        "File",
        file_name,
        [
            "name",
            "file_url",
            "file_name",
            "is_private",
            "attached_to_doctype",
            "attached_to_name",
            "attached_to_field",
        ],
        as_dict=True,
    )
    if not row:
        frappe.throw(_("File not found."), frappe.DoesNotExistError)
    if (row.get("attached_to_doctype") or "").strip() not in ADMISSIONS_ATTACHMENT_DOCTYPES:
        frappe.throw(_("Not permitted for this file."), frappe.PermissionError)
    return row


def _resolve_any_file_row(file_name: str) -> dict:
    row = _get_any_file_row(file_name)
    if not row:
        frappe.throw(_("File not found."), frappe.DoesNotExistError)
    return row


def _get_any_file_row(file_name: str | None) -> dict | None:
    resolved_file_name = (file_name or "").strip()
    if not resolved_file_name:
        return None

    return frappe.db.get_value(
        "File",
        resolved_file_name,
        [
            "name",
            "file_url",
            "file_name",
            "is_private",
            "attached_to_doctype",
            "attached_to_name",
            "attached_to_field",
        ],
        as_dict=True,
    )


def _resolve_public_website_media_row(file_name: str) -> dict:
    file_row = _resolve_any_file_row(file_name)
    drive_file = get_drive_file_for_file(
        file_name,
        fields=["name", "organization", "school", "primary_subject_type", "purpose"],
        statuses=("active",),
    )
    if not drive_file:
        frappe.throw(_("This file is not published for public website use."), frappe.PermissionError)
    if (drive_file.get("primary_subject_type") or "").strip() != "Organization":
        frappe.throw(_("This file is not published for public website use."), frappe.PermissionError)
    if (drive_file.get("purpose") or "").strip() != "organization_public_media":
        frappe.throw(_("This file is not published for public website use."), frappe.PermissionError)
    file_row.update(
        {
            "drive_file_id": drive_file.get("name"),
            "organization": (drive_file.get("organization") or "").strip(),
            "school": (drive_file.get("school") or "").strip(),
        }
    )
    return file_row


def _load_drive_access_callable(attribute: str):
    try:
        from ifitwala_drive.api import access as drive_api
    except ImportError as exc:
        frappe.throw(_("Ifitwala Drive is required for governed file access: {0}").format(exc))

    callable_obj = getattr(drive_api, attribute, None)
    if callable(callable_obj):
        return callable_obj

    frappe.throw(_("Ifitwala Drive access method is unavailable: {0}").format(attribute))


def _load_drive_communications_callable(attribute: str):
    try:
        from ifitwala_drive.api import communications as drive_api
    except ImportError:
        return None

    callable_obj = getattr(drive_api, attribute, None)
    if callable(callable_obj):
        return callable_obj
    return None


def _load_drive_materials_callable(attribute: str):
    try:
        from ifitwala_drive.api import materials as drive_api
    except ImportError:
        return None

    callable_obj = getattr(drive_api, attribute, None)
    if callable(callable_obj):
        return callable_obj
    return None


def _load_drive_media_callable(attribute: str):
    try:
        from ifitwala_drive.api import media as drive_api
    except ImportError:
        return None

    callable_obj = getattr(drive_api, attribute, None)
    if callable(callable_obj):
        return callable_obj
    return None


def _ensure_response_headers() -> dict:
    if not hasattr(frappe, "local") or frappe.local is None:
        frappe.local = SimpleNamespace()
    if not hasattr(frappe.local, "response") or frappe.local.response is None:
        frappe.local.response = {}

    headers = frappe.local.response.get("headers")
    if not isinstance(headers, dict):
        headers = {}
        frappe.local.response["headers"] = headers
    return headers


def _set_thumbnail_cache_headers() -> None:
    headers = _ensure_response_headers()
    headers["Cache-Control"] = f"private, max-age={_THUMBNAIL_REDIRECT_CACHE_TTL_SECONDS}, must-revalidate"


def _get_shared_cache():
    cache_factory = getattr(frappe, "cache", None)
    if not callable(cache_factory):
        return None
    try:
        return cache_factory()
    except Exception:
        return None


def _thumbnail_redirect_cache_key(
    *,
    drive_file_id: str,
    current_version: str | None,
    derivative_role: str,
    surface_parts: list[str | None],
) -> str | None:
    resolved_drive_file_id = str(drive_file_id or "").strip()
    resolved_version = str(current_version or "").strip()
    if not resolved_drive_file_id or not resolved_version:
        return None

    raw_scope = "|".join(str(part or "").strip() or "-" for part in surface_parts)
    scope_hash = hashlib.sha256(raw_scope.encode("utf-8")).hexdigest()[:24]
    return f"ifitwala_ed:preview_thumbnail:{resolved_drive_file_id}:{resolved_version}:{derivative_role}:{scope_hash}"


def _resolve_drive_file_delivery_row(
    file_name: str | None = None,
    *,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
) -> dict | None:
    fields = [
        "name",
        "file",
        "canonical_ref",
        "preview_status",
        "current_version",
        "owner_doctype",
        "owner_name",
        "primary_subject_type",
        "primary_subject_id",
        "attached_doctype",
        "attached_name",
        "purpose",
        "slot",
    ]
    if (drive_file_id or "").strip():
        return get_drive_file_by_id(
            drive_file_id,
            fields=fields,
            statuses=("active", "processing", "blocked"),
        )
    if (canonical_ref or "").strip():
        return get_drive_file_by_canonical_ref(
            canonical_ref,
            fields=fields,
            statuses=("active", "processing", "blocked"),
        )
    resolved_file_name = (file_name or "").strip()
    if not resolved_file_name:
        return None
    drive_file = frappe.db.get_value(
        "Drive File",
        {"file": resolved_file_name},
        fields,
        as_dict=True,
    )
    if not drive_file or not drive_file.get("name"):
        return None
    return drive_file


def _require_org_communication_attachment_context(org_communication: str, row_name: str):
    resolved_org_communication = (org_communication or "").strip()
    resolved_row_name = (row_name or "").strip()
    if not resolved_org_communication:
        frappe.throw(_("Org Communication is required."), frappe.ValidationError)
    if not resolved_row_name:
        frappe.throw(_("Attachment row name is required."), frappe.ValidationError)

    user = _require_authenticated_user()
    roles = frappe.get_roles(user)
    employee = frappe.db.get_value(
        "Employee",
        {"user_id": user},
        ["name", "school", "organization"],
        as_dict=True,
    )
    employee = expand_employee_visibility_context(employee, roles)
    if not check_audience_match(resolved_org_communication, user, roles, employee, allow_owner=True):
        frappe.throw(_("You do not have permission to access this communication attachment."), frappe.PermissionError)

    doc = frappe.get_doc("Org Communication", resolved_org_communication)
    target_row = None
    for row in doc.get("attachments") or []:
        if str(getattr(row, "name", "") or "").strip() == resolved_row_name:
            target_row = row
            break
    if not target_row:
        frappe.throw(_("Attachment row was not found."), frappe.DoesNotExistError)

    return doc, target_row


def _resolve_org_communication_drive_file(org_communication: str, row_name: str) -> tuple[str, str | None]:
    row_slot = f"communication_attachment__{row_name}"
    drive_file = frappe.db.get_value(
        "Drive Binding",
        {
            "binding_doctype": "Org Communication",
            "binding_name": org_communication,
            "binding_role": "communication_attachment",
            "slot": row_slot,
            "status": "active",
        },
        ["drive_file", "file"],
        as_dict=True,
    )
    if drive_file and drive_file.get("drive_file"):
        return drive_file.get("drive_file"), (drive_file.get("file") or "").strip() or None

    drive_file = frappe.db.get_value(
        "Drive File",
        {
            "owner_doctype": "Org Communication",
            "owner_name": org_communication,
            "slot": row_slot,
            "status": "active",
        },
        ["name", "file"],
        as_dict=True,
    )
    if drive_file and drive_file.get("name"):
        return drive_file.get("name"), (drive_file.get("file") or "").strip() or None

    frappe.throw(_("Governed attachment file was not found."), frappe.DoesNotExistError)


def _resolve_current_material_drive_file(material: str | None) -> dict | None:
    resolved_material = str(material or "").strip()
    if not resolved_material:
        return None

    return get_current_drive_file_for_attachment(
        attached_doctype=CONTEXT_SUPPORTING_MATERIAL,
        attached_name=resolved_material,
        fields=[
            "name",
            "file",
            "canonical_ref",
            "preview_status",
            "current_version",
            "owner_doctype",
            "owner_name",
            "primary_subject_type",
            "primary_subject_id",
            "attached_doctype",
            "attached_name",
            "purpose",
            "slot",
        ],
        statuses=("active", "processing", "blocked"),
    )


def _resolve_drive_file_grant_target_url(
    *,
    drive_file_id: str,
    file_id: str,
    prefer_preview: bool = False,
    derivative_role: str | None = None,
    strict_derivative: bool = False,
) -> str | None:
    target_url = ""
    explicit_derivative_role = (derivative_role or "").strip()
    if prefer_preview and explicit_derivative_role:
        try:
            grant = _load_drive_access_callable("issue_preview_grant")(
                drive_file_id=drive_file_id,
                derivative_role=explicit_derivative_role,
            )
            target_url = str((grant or {}).get("url") or "").strip()
        except Exception:
            target_url = ""
        if strict_derivative:
            return target_url or None

    if not target_url:
        grant_method = "issue_download_grant"
        if prefer_preview:
            preview_status = frappe.db.get_value("Drive File", drive_file_id, "preview_status")
            if preview_status == "ready":
                grant_method = "issue_preview_grant"
        grant = _load_drive_access_callable(grant_method)(drive_file_id=drive_file_id)
        target_url = str((grant or {}).get("url") or "").strip()

    return target_url or None


def _resolve_cached_thumbnail_target_url(
    *,
    drive_file_id: str,
    file_id: str,
    surface_parts: list[str | None],
    derivative_role: str | None = None,
    strict_derivative: bool = False,
    target_resolver=None,
) -> str | None:
    drive_file_row = (
        frappe.db.get_value(
            "Drive File",
            drive_file_id,
            ["name", "current_version"],
            as_dict=True,
        )
        or {}
    )
    resolved_derivative_role = (derivative_role or "").strip() or _resolve_card_preview_derivative_role_for_drive_file(
        drive_file_row.get("name") or drive_file_id
    )
    cache_key = _thumbnail_redirect_cache_key(
        drive_file_id=str(drive_file_row.get("name") or drive_file_id),
        current_version=drive_file_row.get("current_version"),
        derivative_role=resolved_derivative_role,
        surface_parts=surface_parts,
    )
    shared_cache = _get_shared_cache()
    if cache_key and shared_cache is not None:
        cached_url = str(shared_cache.get_value(cache_key) or "").strip()
        if cached_url and not _is_raw_private_redirect_target(cached_url):
            return cached_url

    if callable(target_resolver):
        target_url = target_resolver()
    else:
        target_url = _resolve_drive_file_grant_target_url(
            drive_file_id=drive_file_id,
            file_id=file_id,
            prefer_preview=True,
            derivative_role=resolved_derivative_role,
            strict_derivative=strict_derivative,
        )
    if cache_key and shared_cache is not None and target_url:
        shared_cache.set_value(
            cache_key,
            target_url,
            expires_in_sec=_THUMBNAIL_REDIRECT_CACHE_TTL_SECONDS,
        )
    return target_url


def _request_org_communication_attachment_grant(
    *,
    method_name: str,
    org_communication: str,
    row_name: str,
    drive_file_id: str,
    derivative_role: str | None = None,
):
    grant_callable = _load_drive_communications_callable(method_name)
    if callable(grant_callable):
        payload = {
            "org_communication": str(org_communication or "").strip(),
            "row_name": str(row_name or "").strip(),
        }
        explicit_derivative_role = (derivative_role or "").strip()
        if explicit_derivative_role:
            payload["derivative_role"] = explicit_derivative_role
        return grant_callable(**payload)

    generic_method = "issue_preview_grant" if "preview" in method_name else "issue_download_grant"
    payload = {"drive_file_id": drive_file_id}
    explicit_derivative_role = (derivative_role or "").strip()
    if generic_method == "issue_preview_grant" and explicit_derivative_role:
        payload["derivative_role"] = explicit_derivative_role
    return _load_drive_access_callable(generic_method)(**payload)


def _request_supporting_material_grant(
    *,
    method_name: str,
    material: str,
    placement: str | None,
    drive_file_id: str,
    derivative_role: str | None = None,
):
    grant_callable = _load_drive_materials_callable(method_name)
    if callable(grant_callable):
        payload = {"material": str(material or "").strip()}
        resolved_placement = str(placement or "").strip()
        explicit_derivative_role = (derivative_role or "").strip()
        if resolved_placement:
            payload["placement"] = resolved_placement
        if explicit_derivative_role:
            payload["derivative_role"] = explicit_derivative_role
        return grant_callable(**payload)

    generic_method = "issue_preview_grant" if "preview" in method_name else "issue_download_grant"
    payload = {"drive_file_id": drive_file_id}
    explicit_derivative_role = (derivative_role or "").strip()
    if generic_method == "issue_preview_grant" and explicit_derivative_role:
        payload["derivative_role"] = explicit_derivative_role
    return _load_drive_access_callable(generic_method)(**payload)


def _request_employee_image_grant(
    *,
    method_name: str,
    employee: str,
    file_id: str,
    drive_file_id: str,
    derivative_role: str | None = None,
):
    grant_callable = _load_drive_media_callable(method_name)
    if callable(grant_callable):
        payload = {
            "employee": str(employee or "").strip(),
            "file_id": str(file_id or "").strip(),
        }
        explicit_derivative_role = (derivative_role or "").strip()
        if explicit_derivative_role:
            payload["derivative_role"] = explicit_derivative_role
        return grant_callable(**payload)

    generic_method = "issue_preview_grant" if "preview" in method_name else "issue_download_grant"
    payload = {"drive_file_id": drive_file_id}
    explicit_derivative_role = (derivative_role or "").strip()
    if generic_method == "issue_preview_grant" and explicit_derivative_role:
        payload["derivative_role"] = explicit_derivative_role
    return _load_drive_access_callable(generic_method)(**payload)


def _request_student_image_grant(
    *,
    method_name: str,
    student: str,
    file_id: str,
    drive_file_id: str,
    derivative_role: str | None = None,
):
    grant_callable = _load_drive_media_callable(method_name)
    if callable(grant_callable):
        payload = {
            "student": str(student or "").strip(),
            "file_id": str(file_id or "").strip(),
        }
        explicit_derivative_role = (derivative_role or "").strip()
        if explicit_derivative_role:
            payload["derivative_role"] = explicit_derivative_role
        return grant_callable(**payload)

    generic_method = "issue_preview_grant" if "preview" in method_name else "issue_download_grant"
    payload = {"drive_file_id": drive_file_id}
    explicit_derivative_role = (derivative_role or "").strip()
    if generic_method == "issue_preview_grant" and explicit_derivative_role:
        payload["derivative_role"] = explicit_derivative_role
    return _load_drive_access_callable(generic_method)(**payload)


def _request_guardian_image_grant(
    *,
    method_name: str,
    guardian: str,
    file_id: str,
    drive_file_id: str,
    derivative_role: str | None = None,
):
    grant_callable = _load_drive_media_callable(method_name)
    if callable(grant_callable):
        payload = {
            "guardian": str(guardian or "").strip(),
            "file_id": str(file_id or "").strip(),
        }
        explicit_derivative_role = (derivative_role or "").strip()
        if explicit_derivative_role:
            payload["derivative_role"] = explicit_derivative_role
        return grant_callable(**payload)

    generic_method = "issue_preview_grant" if "preview" in method_name else "issue_download_grant"
    payload = {"drive_file_id": drive_file_id}
    explicit_derivative_role = (derivative_role or "").strip()
    if generic_method == "issue_preview_grant" and explicit_derivative_role:
        payload["derivative_role"] = explicit_derivative_role
    return _load_drive_access_callable(generic_method)(**payload)


def _resolve_supporting_material_grant_target_url(
    *,
    material: str,
    placement: str | None,
    drive_file_id: str,
    file_id: str,
    prefer_preview: bool = False,
    derivative_role: str | None = None,
    strict_derivative: bool = False,
) -> str | None:
    target_url = ""
    explicit_derivative_role = (derivative_role or "").strip()
    resolved_material = str(material or "").strip()
    resolved_placement = str(placement or "").strip() or None

    if prefer_preview and explicit_derivative_role:
        try:
            grant = _request_supporting_material_grant(
                method_name="issue_supporting_material_preview_grant",
                material=resolved_material,
                placement=resolved_placement,
                drive_file_id=drive_file_id,
                derivative_role=explicit_derivative_role,
            )
            target_url = str((grant or {}).get("url") or "").strip()
        except Exception:
            target_url = ""
        if strict_derivative:
            return target_url or None

    if not target_url:
        grant_method = "issue_supporting_material_download_grant"
        if prefer_preview:
            preview_status = frappe.db.get_value("Drive File", drive_file_id, "preview_status")
            if preview_status == "ready":
                grant_method = "issue_supporting_material_preview_grant"
        grant = _request_supporting_material_grant(
            method_name=grant_method,
            material=resolved_material,
            placement=resolved_placement,
            drive_file_id=drive_file_id,
        )
        target_url = str((grant or {}).get("url") or "").strip()

    return target_url or None


def _resolve_employee_image_grant_target_url(
    *,
    employee: str,
    file_id: str,
    drive_file_id: str,
    prefer_preview: bool = False,
    derivative_role: str | None = None,
    strict_derivative: bool = False,
) -> str | None:
    target_url = ""
    explicit_derivative_role = (derivative_role or "").strip()
    resolved_employee = str(employee or "").strip()
    resolved_file_id = str(file_id or "").strip()

    if prefer_preview and explicit_derivative_role:
        try:
            if resolved_file_id:
                grant = _request_employee_image_grant(
                    method_name="issue_employee_image_preview_grant",
                    employee=resolved_employee,
                    file_id=resolved_file_id,
                    drive_file_id=drive_file_id,
                    derivative_role=explicit_derivative_role,
                )
                target_url = str((grant or {}).get("url") or "").strip()
            else:
                target_url = _resolve_drive_preview_grant_url(
                    drive_file_id=drive_file_id,
                    derivative_role=explicit_derivative_role,
                )
        except Exception:
            target_url = ""
        if strict_derivative:
            return target_url or None

    if not target_url:
        if resolved_file_id:
            grant_method = "issue_employee_image_download_grant"
            if prefer_preview:
                preview_status = frappe.db.get_value("Drive File", drive_file_id, "preview_status")
                if preview_status == "ready":
                    grant_method = "issue_employee_image_preview_grant"
            grant = _request_employee_image_grant(
                method_name=grant_method,
                employee=resolved_employee,
                file_id=resolved_file_id,
                drive_file_id=drive_file_id,
            )
            target_url = str((grant or {}).get("url") or "").strip()
        else:
            target_url = (
                _resolve_drive_preview_grant_url(drive_file_id=drive_file_id)
                if prefer_preview
                else _resolve_drive_download_grant_url(drive_file_id=drive_file_id)
            )

    return target_url or None


def _resolve_student_image_grant_target_url(
    *,
    student: str,
    file_id: str,
    drive_file_id: str,
    prefer_preview: bool = False,
    derivative_role: str | None = None,
    strict_derivative: bool = False,
) -> str | None:
    target_url = ""
    explicit_derivative_role = (derivative_role or "").strip()
    resolved_student = str(student or "").strip()
    resolved_file_id = str(file_id or "").strip()

    if prefer_preview and explicit_derivative_role:
        try:
            if resolved_file_id:
                grant = _request_student_image_grant(
                    method_name="issue_student_image_preview_grant",
                    student=resolved_student,
                    file_id=resolved_file_id,
                    drive_file_id=drive_file_id,
                    derivative_role=explicit_derivative_role,
                )
                target_url = str((grant or {}).get("url") or "").strip()
            else:
                target_url = _resolve_drive_preview_grant_url(
                    drive_file_id=drive_file_id,
                    derivative_role=explicit_derivative_role,
                )
        except Exception:
            target_url = ""
        if strict_derivative:
            return target_url or None

    if not target_url:
        if resolved_file_id:
            grant_method = "issue_student_image_download_grant"
            if prefer_preview:
                preview_status = frappe.db.get_value("Drive File", drive_file_id, "preview_status")
                if preview_status == "ready":
                    grant_method = "issue_student_image_preview_grant"
            grant = _request_student_image_grant(
                method_name=grant_method,
                student=resolved_student,
                file_id=resolved_file_id,
                drive_file_id=drive_file_id,
            )
            target_url = str((grant or {}).get("url") or "").strip()
        else:
            target_url = (
                _resolve_drive_preview_grant_url(drive_file_id=drive_file_id)
                if prefer_preview
                else _resolve_drive_download_grant_url(drive_file_id=drive_file_id)
            )

    return target_url or None


def _resolve_guardian_image_grant_target_url(
    *,
    guardian: str,
    file_id: str,
    drive_file_id: str,
    prefer_preview: bool = False,
    derivative_role: str | None = None,
    strict_derivative: bool = False,
) -> str | None:
    target_url = ""
    explicit_derivative_role = (derivative_role or "").strip()
    resolved_guardian = str(guardian or "").strip()
    resolved_file_id = str(file_id or "").strip()

    if prefer_preview and explicit_derivative_role:
        try:
            if resolved_file_id:
                grant = _request_guardian_image_grant(
                    method_name="issue_guardian_image_preview_grant",
                    guardian=resolved_guardian,
                    file_id=resolved_file_id,
                    drive_file_id=drive_file_id,
                    derivative_role=explicit_derivative_role,
                )
                target_url = str((grant or {}).get("url") or "").strip()
            else:
                target_url = _resolve_drive_preview_grant_url(
                    drive_file_id=drive_file_id,
                    derivative_role=explicit_derivative_role,
                )
        except Exception:
            target_url = ""
        if strict_derivative:
            return target_url or None

    if not target_url:
        if resolved_file_id:
            grant_method = "issue_guardian_image_download_grant"
            if prefer_preview:
                preview_status = frappe.db.get_value("Drive File", drive_file_id, "preview_status")
                if preview_status == "ready":
                    grant_method = "issue_guardian_image_preview_grant"
            grant = _request_guardian_image_grant(
                method_name=grant_method,
                guardian=resolved_guardian,
                file_id=resolved_file_id,
                drive_file_id=drive_file_id,
            )
            target_url = str((grant or {}).get("url") or "").strip()
        else:
            target_url = (
                _resolve_drive_preview_grant_url(drive_file_id=drive_file_id)
                if prefer_preview
                else _resolve_drive_download_grant_url(drive_file_id=drive_file_id)
            )

    return target_url or None


def _resolve_org_communication_attachment_grant_target_url(
    *,
    org_communication: str,
    row_name: str,
    drive_file_id: str,
    file_id: str,
    prefer_preview: bool = False,
    derivative_role: str | None = None,
    strict_derivative: bool = False,
) -> str | None:
    target_url = ""
    explicit_derivative_role = (derivative_role or "").strip()
    resolved_org_communication = str(org_communication or "").strip()
    resolved_row_name = str(row_name or "").strip()

    if prefer_preview and explicit_derivative_role:
        try:
            grant = _request_org_communication_attachment_grant(
                method_name="issue_org_communication_attachment_preview_grant",
                org_communication=resolved_org_communication,
                row_name=resolved_row_name,
                drive_file_id=drive_file_id,
                derivative_role=explicit_derivative_role,
            )
            target_url = str((grant or {}).get("url") or "").strip()
        except Exception:
            target_url = ""
        if strict_derivative:
            return target_url or None

    if not target_url:
        grant_method = "issue_org_communication_attachment_download_grant"
        if prefer_preview:
            preview_status = frappe.db.get_value("Drive File", drive_file_id, "preview_status")
            if preview_status == "ready":
                grant_method = "issue_org_communication_attachment_preview_grant"
        grant = _request_org_communication_attachment_grant(
            method_name=grant_method,
            org_communication=resolved_org_communication,
            row_name=resolved_row_name,
            drive_file_id=drive_file_id,
        )
        target_url = str((grant or {}).get("url") or "").strip()

    return target_url or None


def _resolve_guardian_from_file(file_row: dict) -> str:
    file_name = (file_row.get("name") or "").strip()
    if file_name:
        drive_file = get_drive_file_for_file(
            file_name,
            fields=["primary_subject_type", "primary_subject_id"],
            statuses=("active", "processing", "blocked"),
        )
        if drive_file and (drive_file.get("primary_subject_type") or "").strip() == CONTEXT_GUARDIAN:
            resolved = (drive_file.get("primary_subject_id") or "").strip()
            if resolved:
                return resolved

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if attached_to_doctype == CONTEXT_GUARDIAN and attached_to_name:
        return attached_to_name

    frappe.throw(_("File is missing guardian ownership context."), frappe.ValidationError)


def _resolve_guardian_from_drive_file(drive_file_row: dict) -> str:
    if (drive_file_row.get("primary_subject_type") or "").strip() == CONTEXT_GUARDIAN:
        resolved = (drive_file_row.get("primary_subject_id") or "").strip()
        if resolved:
            return resolved

    attached_doctype = (drive_file_row.get("attached_doctype") or "").strip()
    attached_name = (drive_file_row.get("attached_name") or "").strip()
    if attached_doctype == CONTEXT_GUARDIAN and attached_name:
        return attached_name

    frappe.throw(_("Drive File is missing guardian ownership context."), frappe.ValidationError)


def _resolve_employee_from_file(file_row: dict) -> str:
    file_name = (file_row.get("name") or "").strip()
    if file_name:
        drive_file = get_drive_file_for_file(
            file_name,
            fields=["primary_subject_type", "primary_subject_id"],
            statuses=("active", "processing", "blocked"),
        )
        if drive_file and (drive_file.get("primary_subject_type") or "").strip() == CONTEXT_EMPLOYEE:
            resolved = (drive_file.get("primary_subject_id") or "").strip()
            if resolved:
                return resolved

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if attached_to_doctype == CONTEXT_EMPLOYEE and attached_to_name:
        return attached_to_name

    frappe.throw(_("File is missing employee ownership context."), frappe.ValidationError)


def _resolve_student_from_drive_file(drive_file_row: dict) -> tuple[str, str | None]:
    if (drive_file_row.get("primary_subject_type") or "").strip() == CONTEXT_STUDENT:
        resolved = (drive_file_row.get("primary_subject_id") or "").strip()
        if resolved:
            return resolved, (drive_file_row.get("school") or "").strip() or None

    attached_doctype = (drive_file_row.get("attached_doctype") or "").strip()
    attached_name = (drive_file_row.get("attached_name") or "").strip()
    if attached_doctype == CONTEXT_STUDENT and attached_name:
        school = frappe.db.get_value("Student", attached_name, "anchor_school")
        return attached_name, school

    frappe.throw(_("Drive File is missing student ownership context."), frappe.ValidationError)


def _resolve_employee_from_drive_file(drive_file_row: dict) -> str:
    if (drive_file_row.get("primary_subject_type") or "").strip() == CONTEXT_EMPLOYEE:
        resolved = (drive_file_row.get("primary_subject_id") or "").strip()
        if resolved:
            return resolved

    attached_doctype = (drive_file_row.get("attached_doctype") or "").strip()
    attached_name = (drive_file_row.get("attached_name") or "").strip()
    if attached_doctype == CONTEXT_EMPLOYEE and attached_name:
        return attached_name

    frappe.throw(_("Drive File is missing employee ownership context."), frappe.ValidationError)


def _resolve_student_profile_image_access(
    *,
    user: str,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    strict: bool = False,
) -> dict | None:
    file_row = _resolve_any_file_row(file_name)
    file_student, school = _resolve_student_context_for_file(file_row)
    if not file_student:
        if strict:
            frappe.throw(_("Student image access requires academic ownership context."), frappe.PermissionError)
        return None

    _assert_internal_academic_context(
        file_row=file_row,
        context_doctype=context_doctype,
        context_name=context_name,
        student=file_student,
    )
    _assert_internal_student_access(user=user, student=file_student, school=school)

    drive_file = get_drive_file_for_file(
        file_name,
        fields=[
            "name",
            "owner_doctype",
            "owner_name",
            "primary_subject_type",
            "primary_subject_id",
            "purpose",
            "slot",
            "school",
        ],
        statuses=("active", "processing", "blocked"),
    )
    if not drive_file:
        if strict:
            frappe.throw(_("Student image access requires an active governed profile image."), frappe.PermissionError)
        return None

    if (
        str(drive_file.get("purpose") or "").strip() != STUDENT_PROFILE_IMAGE_PURPOSE
        or str(drive_file.get("slot") or "").strip() != PROFILE_IMAGE_SLOT
    ):
        if strict:
            frappe.throw(_("Student image access is limited to governed profile images."), frappe.PermissionError)
        return None

    if (
        str(drive_file.get("owner_doctype") or "").strip() != CONTEXT_STUDENT
        or str(drive_file.get("owner_name") or "").strip() != file_student
        or str(drive_file.get("primary_subject_type") or "").strip() != CONTEXT_STUDENT
        or str(drive_file.get("primary_subject_id") or "").strip() != file_student
    ):
        frappe.throw(_("Student image ownership is invalid."), frappe.PermissionError)

    return {
        "file_row": file_row,
        "file_student": file_student,
        "school": school,
        "drive_file_id": str(drive_file.get("name") or "").strip(),
    }


def _resolve_student_profile_image_access_from_drive_file(
    *,
    user: str,
    drive_file_row: dict | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    strict: bool = False,
) -> dict | None:
    resolved_drive_file = drive_file_row or {}
    resolved_drive_file_id = str(resolved_drive_file.get("name") or "").strip()
    if not resolved_drive_file_id:
        if strict:
            frappe.throw(_("Student image access requires an active governed profile image."), frappe.PermissionError)
        return None

    file_student, school = _resolve_student_from_drive_file(resolved_drive_file)
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if resolved_context:
        if resolved_context != CONTEXT_STUDENT:
            frappe.throw(_("Unsupported student image context."), frappe.ValidationError)
        if not resolved_name:
            frappe.throw(_("Context Name is required for Student image access."), frappe.ValidationError)
        if resolved_name != file_student:
            frappe.throw(_("File does not belong to this Student context."), frappe.PermissionError)

    _assert_internal_student_access(user=user, student=file_student, school=school)

    if (
        str(resolved_drive_file.get("purpose") or "").strip() != STUDENT_PROFILE_IMAGE_PURPOSE
        or str(resolved_drive_file.get("slot") or "").strip() != PROFILE_IMAGE_SLOT
    ):
        if strict:
            frappe.throw(_("Student image access is limited to governed profile images."), frappe.PermissionError)
        return None

    if (
        str(resolved_drive_file.get("owner_doctype") or "").strip() != CONTEXT_STUDENT
        or str(resolved_drive_file.get("owner_name") or "").strip() != file_student
        or str(resolved_drive_file.get("primary_subject_type") or "").strip() != CONTEXT_STUDENT
        or str(resolved_drive_file.get("primary_subject_id") or "").strip() != file_student
    ):
        frappe.throw(_("Student image ownership is invalid."), frappe.PermissionError)

    return {
        "file_row": _get_any_file_row(str(resolved_drive_file.get("file") or "").strip()),
        "file_student": file_student,
        "school": school,
        "drive_file_id": resolved_drive_file_id,
    }


def _resolve_guardian_profile_image_access(
    *,
    user: str,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    strict: bool = False,
) -> dict | None:
    file_row = _resolve_any_file_row(file_name)
    file_guardian = _resolve_guardian_from_file(file_row)
    _assert_guardian_file_access(
        user=user,
        file_guardian=file_guardian,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    drive_file = get_drive_file_for_file(
        file_name,
        fields=[
            "name",
            "owner_doctype",
            "owner_name",
            "primary_subject_type",
            "primary_subject_id",
            "purpose",
            "slot",
        ],
        statuses=("active", "processing", "blocked"),
    )
    if not drive_file:
        if strict:
            frappe.throw(_("Guardian image access requires an active governed profile image."), frappe.PermissionError)
        return None

    if (
        str(drive_file.get("purpose") or "").strip() != GUARDIAN_PROFILE_IMAGE_PURPOSE
        or str(drive_file.get("slot") or "").strip() != PROFILE_IMAGE_SLOT
    ):
        if strict:
            frappe.throw(_("Guardian image access is limited to governed profile images."), frappe.PermissionError)
        return None

    if (
        str(drive_file.get("owner_doctype") or "").strip() != CONTEXT_GUARDIAN
        or str(drive_file.get("owner_name") or "").strip() != file_guardian
        or str(drive_file.get("primary_subject_type") or "").strip() != CONTEXT_GUARDIAN
        or str(drive_file.get("primary_subject_id") or "").strip() != file_guardian
    ):
        frappe.throw(_("Guardian image ownership is invalid."), frappe.PermissionError)

    return {
        "file_row": file_row,
        "file_guardian": file_guardian,
        "drive_file_id": str(drive_file.get("name") or "").strip(),
    }


def _resolve_guardian_profile_image_access_from_drive_file(
    *,
    user: str,
    drive_file_row: dict | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    strict: bool = False,
) -> dict | None:
    resolved_drive_file = drive_file_row or {}
    resolved_drive_file_id = str(resolved_drive_file.get("name") or "").strip()
    if not resolved_drive_file_id:
        if strict:
            frappe.throw(_("Guardian image access requires an active governed profile image."), frappe.PermissionError)
        return None

    file_guardian = _resolve_guardian_from_drive_file(resolved_drive_file)
    _assert_guardian_file_access(
        user=user,
        file_guardian=file_guardian,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    if (
        str(resolved_drive_file.get("purpose") or "").strip() != GUARDIAN_PROFILE_IMAGE_PURPOSE
        or str(resolved_drive_file.get("slot") or "").strip() != PROFILE_IMAGE_SLOT
    ):
        if strict:
            frappe.throw(_("Guardian image access is limited to governed profile images."), frappe.PermissionError)
        return None

    if (
        str(resolved_drive_file.get("owner_doctype") or "").strip() != CONTEXT_GUARDIAN
        or str(resolved_drive_file.get("owner_name") or "").strip() != file_guardian
        or str(resolved_drive_file.get("primary_subject_type") or "").strip() != CONTEXT_GUARDIAN
        or str(resolved_drive_file.get("primary_subject_id") or "").strip() != file_guardian
    ):
        frappe.throw(_("Guardian image ownership is invalid."), frappe.PermissionError)

    return {
        "file_row": _get_any_file_row(str(resolved_drive_file.get("file") or "").strip()),
        "file_guardian": file_guardian,
        "drive_file_id": resolved_drive_file_id,
    }


def _resolve_employee_profile_image_access(
    *,
    user: str,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    strict: bool = False,
) -> dict | None:
    file_row = _resolve_any_file_row(file_name)
    file_employee = _resolve_employee_from_file(file_row)
    _assert_employee_file_access(
        user=user,
        file_employee=file_employee,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    drive_file = get_drive_file_for_file(
        file_name,
        fields=[
            "name",
            "owner_doctype",
            "owner_name",
            "primary_subject_type",
            "primary_subject_id",
            "purpose",
            "slot",
        ],
        statuses=("active", "processing", "blocked"),
    )
    if not drive_file:
        if strict:
            frappe.throw(_("Employee image access requires an active governed profile image."), frappe.PermissionError)
        return None

    if (
        str(drive_file.get("purpose") or "").strip() != EMPLOYEE_PROFILE_IMAGE_PURPOSE
        or str(drive_file.get("slot") or "").strip() != EMPLOYEE_PROFILE_IMAGE_SLOT
    ):
        if strict:
            frappe.throw(_("Employee image access is limited to governed profile images."), frappe.PermissionError)
        return None

    if (
        str(drive_file.get("owner_doctype") or "").strip() != CONTEXT_EMPLOYEE
        or str(drive_file.get("owner_name") or "").strip() != file_employee
        or str(drive_file.get("primary_subject_type") or "").strip() != CONTEXT_EMPLOYEE
        or str(drive_file.get("primary_subject_id") or "").strip() != file_employee
    ):
        frappe.throw(_("Employee image ownership is invalid."), frappe.PermissionError)

    return {
        "file_row": file_row,
        "file_employee": file_employee,
        "drive_file_id": str(drive_file.get("name") or "").strip(),
    }


def _resolve_employee_profile_image_access_from_drive_file(
    *,
    user: str,
    drive_file_row: dict | None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    strict: bool = False,
) -> dict | None:
    resolved_drive_file = drive_file_row or {}
    resolved_drive_file_id = str(resolved_drive_file.get("name") or "").strip()
    if not resolved_drive_file_id:
        if strict:
            frappe.throw(_("Employee image access requires an active governed profile image."), frappe.PermissionError)
        return None

    file_employee = _resolve_employee_from_drive_file(resolved_drive_file)
    _assert_employee_file_access(
        user=user,
        file_employee=file_employee,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    if (
        str(resolved_drive_file.get("purpose") or "").strip() != EMPLOYEE_PROFILE_IMAGE_PURPOSE
        or str(resolved_drive_file.get("slot") or "").strip() != EMPLOYEE_PROFILE_IMAGE_SLOT
    ):
        if strict:
            frappe.throw(_("Employee image access is limited to governed profile images."), frappe.PermissionError)
        return None

    if (
        str(resolved_drive_file.get("owner_doctype") or "").strip() != CONTEXT_EMPLOYEE
        or str(resolved_drive_file.get("owner_name") or "").strip() != file_employee
        or str(resolved_drive_file.get("primary_subject_type") or "").strip() != CONTEXT_EMPLOYEE
        or str(resolved_drive_file.get("primary_subject_id") or "").strip() != file_employee
    ):
        frappe.throw(_("Employee image ownership is invalid."), frappe.PermissionError)

    return {
        "file_row": _get_any_file_row(str(resolved_drive_file.get("file") or "").strip()),
        "file_employee": file_employee,
        "drive_file_id": resolved_drive_file_id,
    }


def _resolve_current_employee_profile_drive_file(employee: str | None) -> dict | None:
    resolved_employee = str(employee or "").strip()
    if not resolved_employee:
        return None

    return get_current_drive_file_for_slot(
        primary_subject_type=CONTEXT_EMPLOYEE,
        primary_subject_id=resolved_employee,
        slot=EMPLOYEE_PROFILE_IMAGE_SLOT,
        fields=[
            "name",
            "file",
            "canonical_ref",
            "owner_doctype",
            "owner_name",
            "attached_doctype",
            "attached_name",
            "primary_subject_type",
            "primary_subject_id",
            "purpose",
            "slot",
        ],
        statuses=("active", "processing", "blocked"),
    )


def _resolve_current_student_profile_drive_file(student: str | None) -> dict | None:
    resolved_student = str(student or "").strip()
    if not resolved_student:
        return None

    return get_current_drive_file_for_slot(
        primary_subject_type=CONTEXT_STUDENT,
        primary_subject_id=resolved_student,
        slot=PROFILE_IMAGE_SLOT,
        fields=[
            "name",
            "file",
            "canonical_ref",
            "owner_doctype",
            "owner_name",
            "attached_doctype",
            "attached_name",
            "primary_subject_type",
            "primary_subject_id",
            "purpose",
            "slot",
            "school",
        ],
        statuses=("active", "processing", "blocked"),
    )


def _resolve_current_guardian_profile_drive_file(guardian: str | None) -> dict | None:
    resolved_guardian = str(guardian or "").strip()
    if not resolved_guardian:
        return None

    return get_current_drive_file_for_slot(
        primary_subject_type=CONTEXT_GUARDIAN,
        primary_subject_id=resolved_guardian,
        slot=PROFILE_IMAGE_SLOT,
        fields=[
            "name",
            "file",
            "canonical_ref",
            "owner_doctype",
            "owner_name",
            "attached_doctype",
            "attached_name",
            "primary_subject_type",
            "primary_subject_id",
            "purpose",
            "slot",
        ],
        statuses=("active", "processing", "blocked"),
    )


def _assert_employee_file_access(
    *, user: str, file_employee: str, context_doctype: str | None, context_name: str | None
) -> None:
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if resolved_context:
        if resolved_context != CONTEXT_EMPLOYEE:
            frappe.throw(_("Unsupported employee file context."), frappe.ValidationError)
        if not resolved_name:
            frappe.throw(_("Context Name is required for Employee access."), frappe.ValidationError)
        if resolved_name != file_employee:
            frappe.throw(_("File does not belong to this Employee context."), frappe.PermissionError)

    if _is_adminish(user):
        return

    if not frappe.db.exists("Employee", file_employee):
        frappe.throw(_("Employee not found."), frappe.DoesNotExistError)

    if has_active_employee_profile(user=user, roles=set(frappe.get_roles(user))):
        return

    frappe.throw(_("You do not have permission to access this employee file."), frappe.PermissionError)


def _assert_employee_owner_doc_read(file_employee: str) -> None:
    if not frappe.db.exists("Employee", file_employee):
        frappe.throw(_("Employee not found."), frappe.DoesNotExistError)

    employee_doc = frappe.get_doc("Employee", file_employee)
    if hasattr(employee_doc, "check_permission"):
        employee_doc.check_permission("read")


def _assert_guardian_file_access(
    *, user: str, file_guardian: str, context_doctype: str | None, context_name: str | None
):
    linked_guardian = (frappe.db.get_value("Guardian", {"user": user}, "name") or "").strip()
    if not linked_guardian:
        frappe.throw(_("This account is not linked to a Guardian record."), frappe.PermissionError)

    if linked_guardian != file_guardian:
        frappe.throw(_("You do not have permission to access this guardian file."), frappe.PermissionError)

    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if not resolved_context:
        return

    if resolved_context != CONTEXT_GUARDIAN:
        frappe.throw(_("Unsupported guardian file context."), frappe.ValidationError)

    if not resolved_name:
        frappe.throw(_("Context Name is required for Guardian access."), frappe.ValidationError)

    if resolved_name != file_guardian:
        frappe.throw(_("File does not belong to this Guardian context."), frappe.PermissionError)


def _resolve_student_applicant_from_file(file_row: dict) -> str:
    file_name = (file_row.get("name") or "").strip()
    if file_name:
        drive_file = get_drive_file_for_file(
            file_name,
            fields=["primary_subject_type", "primary_subject_id"],
            statuses=("active", "processing", "blocked"),
        )
        if drive_file and (drive_file.get("primary_subject_type") or "").strip() == "Student Applicant":
            resolved = (drive_file.get("primary_subject_id") or "").strip()
            if resolved:
                return resolved

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if not attached_to_name:
        frappe.throw(_("File attachment context is incomplete."), frappe.ValidationError)

    if attached_to_doctype == "Applicant Document Item":
        applicant_document = frappe.db.get_value("Applicant Document Item", attached_to_name, "applicant_document")
        student_applicant = (
            frappe.db.get_value("Applicant Document", applicant_document, "student_applicant")
            if applicant_document
            else None
        )
    elif attached_to_doctype == "Applicant Health Profile":
        student_applicant = frappe.db.get_value("Applicant Health Profile", attached_to_name, "student_applicant")
    elif attached_to_doctype == "Student Applicant Guardian":
        student_applicant = frappe.db.get_value(
            "Student Applicant Guardian",
            attached_to_name,
            "parent",
        )
    elif attached_to_doctype == "Student Applicant":
        student_applicant = attached_to_name
    else:
        student_applicant = None

    resolved = (student_applicant or "").strip()
    if not resolved:
        frappe.throw(_("File is missing admissions ownership context."), frappe.ValidationError)
    return resolved


def _resolve_student_applicant_from_drive_file(drive_file_row: dict) -> str:
    if (drive_file_row.get("primary_subject_type") or "").strip() == "Student Applicant":
        resolved = (drive_file_row.get("primary_subject_id") or "").strip()
        if resolved:
            return resolved

    attached_doctype = (drive_file_row.get("attached_doctype") or "").strip()
    attached_name = (drive_file_row.get("attached_name") or "").strip()
    if not attached_name:
        frappe.throw(_("Drive File is missing admissions ownership context."), frappe.ValidationError)

    if attached_doctype == "Applicant Document Item":
        applicant_document = frappe.db.get_value("Applicant Document Item", attached_name, "applicant_document")
        student_applicant = (
            frappe.db.get_value("Applicant Document", applicant_document, "student_applicant")
            if applicant_document
            else None
        )
    elif attached_doctype == "Applicant Health Profile":
        student_applicant = frappe.db.get_value("Applicant Health Profile", attached_name, "student_applicant")
    elif attached_doctype == "Student Applicant Guardian":
        student_applicant = frappe.db.get_value("Student Applicant Guardian", attached_name, "parent")
    elif attached_doctype == "Student Applicant":
        student_applicant = attached_name
    else:
        student_applicant = None

    resolved = (student_applicant or "").strip()
    if not resolved:
        frappe.throw(_("Drive File is missing admissions ownership context."), frappe.ValidationError)
    return resolved


def _resolve_authorized_admissions_file_target(
    *,
    user: str,
    file_name: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
) -> tuple[dict | None, dict | None]:
    resolved_drive_file = _resolve_drive_file_delivery_row(
        file_name,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
    )
    if resolved_drive_file and resolved_drive_file.get("name"):
        file_student_applicant = _resolve_student_applicant_from_drive_file(resolved_drive_file)
        _assert_context_permission(
            user=user,
            file_student_applicant=file_student_applicant,
            context_doctype=context_doctype,
            context_name=context_name,
        )
        resolved_file_name = (resolved_drive_file.get("file") or "").strip()
        file_row = _resolve_any_file_row(resolved_file_name) if resolved_file_name else None
        return file_row, resolved_drive_file

    resolved_file_name = (file_name or "").strip()
    if not resolved_file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_file_row(resolved_file_name)
    file_student_applicant = _resolve_student_applicant_from_file(file_row)
    _assert_context_permission(
        user=user,
        file_student_applicant=file_student_applicant,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    return file_row, _resolve_drive_file_delivery_row(resolved_file_name)


def _is_student_applicant_self_user(*, student_applicant: str, user: str) -> bool:
    return user_can_access_student_applicant(user=user, student_applicant=student_applicant)


def _assert_can_access_student_applicant(*, user: str, student_applicant: str) -> None:
    if is_admissions_file_staff_user(user):
        if has_scoped_staff_access_to_student_applicant(user=user, student_applicant=student_applicant):
            return
        frappe.throw(_("You do not have permission to access this applicant file."), frappe.PermissionError)

    roles = set(frappe.get_roles(user))
    if roles & {ADMISSIONS_APPLICANT_ROLE, ADMISSIONS_FAMILY_ROLE} and _is_student_applicant_self_user(
        student_applicant=student_applicant,
        user=user,
    ):
        return

    if has_open_applicant_review_access(user=user, student_applicant=student_applicant):
        return

    frappe.throw(_("You do not have permission to access this applicant file."), frappe.PermissionError)


def _is_interviewer_on_interview(*, user: str, interview_name: str) -> bool:
    return bool(
        frappe.db.exists(
            "Applicant Interviewer",
            {
                "parent": interview_name,
                "parenttype": "Applicant Interview",
                "parentfield": "interviewers",
                "interviewer": user,
            },
        )
    )


def _assert_context_permission(
    *,
    user: str,
    file_student_applicant: str,
    context_doctype: str | None,
    context_name: str | None,
) -> None:
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()

    if not resolved_context:
        _assert_can_access_student_applicant(user=user, student_applicant=file_student_applicant)
        return

    if resolved_context == CONTEXT_STUDENT_APPLICANT:
        if not resolved_name:
            frappe.throw(_("Context Name is required for Student Applicant access."), frappe.ValidationError)
        if resolved_name != file_student_applicant:
            frappe.throw(_("File does not belong to this Student Applicant."), frappe.PermissionError)
        _assert_can_access_student_applicant(user=user, student_applicant=file_student_applicant)
        return

    if resolved_context == CONTEXT_APPLICANT_INTERVIEW:
        if not resolved_name:
            frappe.throw(_("Context Name is required for Applicant Interview access."), frappe.ValidationError)

        interview_applicant = (
            frappe.db.get_value("Applicant Interview", resolved_name, "student_applicant") or ""
        ).strip()
        if not interview_applicant:
            frappe.throw(_("Applicant Interview not found."), frappe.DoesNotExistError)
        if interview_applicant != file_student_applicant:
            frappe.throw(_("File does not belong to this Applicant Interview context."), frappe.PermissionError)

        if is_admissions_file_staff_user(user) and has_scoped_staff_access_to_student_applicant(
            user=user, student_applicant=file_student_applicant
        ):
            return
        if has_open_applicant_review_access(user=user, student_applicant=file_student_applicant):
            return
        if _is_interviewer_on_interview(user=user, interview_name=resolved_name):
            return

        frappe.throw(_("You do not have permission to access this interview file."), frappe.PermissionError)
        return

    frappe.throw(_("Unsupported file access context."), frappe.ValidationError)


def _respond_with_redirect_target(*, target_url: str | None, cache_headers: bool = False) -> bool:
    resolved_target_url = str(target_url or "").strip()
    if resolved_target_url and not _is_raw_private_redirect_target(resolved_target_url):
        if cache_headers:
            _set_thumbnail_cache_headers()
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = resolved_target_url
        return True
    return False


def _resolve_drive_download_grant_url(
    file_name: str | None = None,
    *,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
) -> str | None:
    drive_file = _resolve_drive_file_delivery_row(
        file_name,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
    )
    if not drive_file:
        return None

    try:
        grant = _load_drive_access_callable("issue_download_grant")(drive_file_id=drive_file.get("name"))
    except Exception:
        return None

    target_url = str((grant or {}).get("url") or "").strip()
    return target_url or None


def _resolve_drive_preview_grant_url(
    file_name: str | None = None,
    *,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    derivative_role: str | None = None,
) -> str | None:
    drive_file = _resolve_drive_file_delivery_row(
        file_name,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
    )
    if not drive_file or not drive_file.get("name"):
        return None

    try:
        explicit_derivative_role = (derivative_role or "").strip()
        if explicit_derivative_role:
            grant = _load_drive_access_callable("issue_preview_grant")(
                drive_file_id=drive_file.get("name"),
                derivative_role=explicit_derivative_role,
            )
        else:
            grant_method = (
                "issue_preview_grant"
                if (drive_file.get("preview_status") or "").strip() == "ready"
                else "issue_download_grant"
            )
            grant = _load_drive_access_callable(grant_method)(drive_file_id=drive_file.get("name"))
    except Exception:
        return None

    target_url = str((grant or {}).get("url") or "").strip()
    return target_url or None


def _resolve_public_website_media_grant_url(file_name: str) -> str | None:
    return _resolve_drive_preview_grant_url(file_name)


def _assert_public_website_media_visible(file_row: dict) -> None:
    from ifitwala_ed.website.public_brand import (
        get_descendant_organization_names,
        resolve_public_brand_organization,
    )

    organization = (file_row.get("organization") or "").strip()
    if not organization:
        frappe.throw(_("Public website media is missing organization context."), frappe.PermissionError)

    public_brand_organization = resolve_public_brand_organization()
    visible_organizations = set(get_descendant_organization_names(public_brand_organization))
    if organization not in visible_organizations:
        frappe.throw(_("This media is not visible on the public website."), frappe.PermissionError)

    school = (file_row.get("school") or "").strip()
    if not school:
        return

    school_row = frappe.db.get_value(
        "School",
        school,
        ["organization", "is_published", "website_slug"],
        as_dict=True,
    )
    if not school_row:
        frappe.throw(_("School not found for this media."), frappe.DoesNotExistError)
    if (school_row.get("organization") or "").strip() != organization:
        frappe.throw(_("School media organization scope is invalid."), frappe.PermissionError)
    if not frappe.utils.cint(school_row.get("is_published")):
        frappe.throw(_("This school media is not published."), frappe.PermissionError)
    if not (school_row.get("website_slug") or "").strip():
        frappe.throw(_("This school media is missing a website route."), frappe.PermissionError)


def _resolve_student_context_for_file(file_row: dict) -> tuple[str | None, str | None]:
    file_name = (file_row.get("name") or "").strip()
    if not file_name:
        return None, None

    drive_file = get_drive_file_for_file(
        file_name,
        fields=["primary_subject_type", "primary_subject_id", "school"],
        statuses=("active", "processing", "blocked"),
    )
    if drive_file and (drive_file.get("primary_subject_type") or "").strip() == "Student":
        return (
            (drive_file.get("primary_subject_id") or "").strip() or None,
            (drive_file.get("school") or "").strip() or None,
        )

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if not attached_to_name:
        return None, None

    if attached_to_doctype == CONTEXT_TASK_SUBMISSION:
        row = frappe.db.get_value(
            "Task Submission",
            attached_to_name,
            ["student", "school"],
            as_dict=True,
        )
        if row:
            return (row.get("student") or None, row.get("school") or None)
    elif attached_to_doctype == CONTEXT_STUDENT:
        school = frappe.db.get_value("Student", attached_to_name, "anchor_school")
        return attached_to_name, school
    elif attached_to_doctype == "Student Reflection Entry":
        row = frappe.db.get_value(
            "Student Reflection Entry",
            attached_to_name,
            ["student", "school"],
            as_dict=True,
        )
        if row:
            return (row.get("student") or None, row.get("school") or None)
    elif attached_to_doctype == CONTEXT_STUDENT_PORTFOLIO_ITEM:
        portfolio = frappe.db.get_value("Student Portfolio Item", attached_to_name, "parent")
        if portfolio:
            row = frappe.db.get_value("Student Portfolio", portfolio, ["student", "school"], as_dict=True)
            if row:
                return (row.get("student") or None, row.get("school") or None)

    return None, None


def _resolve_supporting_material_context_for_file(file_row: dict) -> tuple[str | None, str | None]:
    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    if attached_to_doctype != CONTEXT_SUPPORTING_MATERIAL or not attached_to_name:
        return None, None

    course = frappe.db.get_value(CONTEXT_SUPPORTING_MATERIAL, attached_to_name, "course")
    return attached_to_name, (course or None)


def _assert_internal_student_access(*, user: str, student: str, school: str | None = None) -> None:
    from ifitwala_ed.api import student_portfolio as student_portfolio_api

    scope = student_portfolio_api._resolve_actor_scope(  # pylint: disable=protected-access
        requested_students=[student],
        school_filter=(school or "").strip() or None,
    )
    if scope.get("students") or scope.get("all_students"):
        return
    frappe.throw(_("You do not have permission to access this file."), frappe.PermissionError)


def _assert_internal_academic_context(
    *,
    file_row: dict,
    context_doctype: str | None,
    context_name: str | None,
    student: str | None,
) -> None:
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if not resolved_context:
        return
    if not resolved_name:
        frappe.throw(_("Context Name is required."), frappe.ValidationError)

    attached_to_doctype = (file_row.get("attached_to_doctype") or "").strip()
    attached_to_name = (file_row.get("attached_to_name") or "").strip()
    file_name = (file_row.get("name") or "").strip()

    if resolved_context == CONTEXT_TASK_SUBMISSION:
        if attached_to_doctype != CONTEXT_TASK_SUBMISSION or attached_to_name != resolved_name:
            frappe.throw(_("File does not belong to this submission."), frappe.PermissionError)
        return

    if resolved_context == CONTEXT_STUDENT:
        if not student or student != resolved_name:
            frappe.throw(_("File does not belong to this student."), frappe.PermissionError)
        return

    if resolved_context == CONTEXT_STUDENT_PORTFOLIO_ITEM:
        row = frappe.db.get_value(
            "Student Portfolio Item",
            resolved_name,
            ["name", "artefact_file"],
            as_dict=True,
        )
        if not row:
            frappe.throw(_("Portfolio item not found."), frappe.DoesNotExistError)
        if (row.get("artefact_file") or "").strip() != file_name:
            frappe.throw(_("File does not belong to this portfolio item."), frappe.PermissionError)
        return

    frappe.throw(_("Unsupported academic file context."), frappe.ValidationError)


def _assert_internal_material_context(
    *,
    file_row: dict,
    context_doctype: str | None,
    context_name: str | None,
    material: str,
) -> str | None:
    resolved_context = (context_doctype or "").strip()
    resolved_name = (context_name or "").strip()
    if not resolved_context:
        return None
    if not resolved_name:
        frappe.throw(_("Context Name is required."), frappe.ValidationError)
    if resolved_context == CONTEXT_SUPPORTING_MATERIAL:
        if resolved_name != material:
            frappe.throw(_("File does not belong to this material."), frappe.PermissionError)
        return None
    if resolved_context == CONTEXT_MATERIAL_PLACEMENT:
        placement = frappe.db.get_value(
            "Material Placement",
            resolved_name,
            ["name", "supporting_material"],
            as_dict=True,
        )
        if not placement:
            frappe.throw(_("Material placement not found."), frappe.DoesNotExistError)
        if (placement.get("supporting_material") or "").strip() != material:
            frappe.throw(_("File does not belong to this material placement."), frappe.PermissionError)
        return resolved_name
    frappe.throw(_("Unsupported academic file context."), frappe.ValidationError)


def _assert_portfolio_share_file_access(*, file_name: str, share_token: str, viewer_email: str | None = None) -> None:
    from ifitwala_ed.api import student_portfolio as student_portfolio_api

    context = student_portfolio_api.resolve_portfolio_share_context(token=share_token, viewer_email=viewer_email)
    share_link = context.get("share_link") or {}
    if not bool(share_link.get("allow_download")):
        frappe.throw(_("Downloads are disabled for this share link."), frappe.PermissionError)

    allowed_files = {
        (row.get("artefact_file") or "").strip()
        for row in ((context.get("portfolio") or {}).get("items") or [])
        if (row.get("artefact_file") or "").strip()
    }
    if file_name not in allowed_files:
        frappe.throw(_("This file is not available in the shared portfolio scope."), frappe.PermissionError)


@frappe.whitelist()
def download_admissions_file(
    file: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    user = _require_authenticated_user()
    file_row, drive_file = _resolve_authorized_admissions_file_target(
        user=user,
        file_name=(file or "").strip() or None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    file_url = str((file_row or {}).get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    target_url = _resolve_drive_download_grant_url(
        (file_row or {}).get("name"),
        drive_file_id=(drive_file or {}).get("name") or drive_file_id,
        canonical_ref=canonical_ref,
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)


@frappe.whitelist()
def preview_admissions_file(
    file: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    user = _require_authenticated_user()
    file_row, drive_file = _resolve_authorized_admissions_file_target(
        user=user,
        file_name=(file or "").strip() or None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )

    target_url = _resolve_drive_preview_grant_url(
        (file_row or {}).get("name"),
        drive_file_id=(drive_file or {}).get("name") or drive_file_id,
        canonical_ref=canonical_ref,
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    file_url = str((file_row or {}).get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    target_url = _resolve_drive_download_grant_url(
        (file_row or {}).get("name"),
        drive_file_id=(drive_file or {}).get("name") or drive_file_id,
        canonical_ref=canonical_ref,
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)


@frappe.whitelist()
def thumbnail_admissions_file(
    file: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
):
    user = _require_authenticated_user()
    file_row, drive_file = _resolve_authorized_admissions_file_target(
        user=user,
        file_name=(file or "").strip() or None,
        drive_file_id=drive_file_id,
        canonical_ref=canonical_ref,
        context_doctype=context_doctype,
        context_name=context_name,
    )
    resolved_drive_file = drive_file or {}
    resolved_drive_file_id = str(resolved_drive_file.get("name") or drive_file_id or "").strip()
    if not resolved_drive_file_id:
        frappe.throw(_("Drive file is required."), frappe.DoesNotExistError)
    derivative_role = _resolve_card_preview_derivative_role_for_drive_file(resolved_drive_file_id)

    target_url = _resolve_cached_thumbnail_target_url(
        drive_file_id=resolved_drive_file_id,
        file_id=str((file_row or {}).get("name") or resolved_drive_file.get("file") or resolved_drive_file_id).strip(),
        surface_parts=[
            "admissions",
            context_doctype,
            context_name,
            resolved_drive_file_id,
        ],
        derivative_role=derivative_role,
        strict_derivative=True,
    )
    if target_url:
        if _respond_with_delivery_target(target_url=target_url, cache_headers=True):
            return

    frappe.throw(_("Could not resolve the attachment thumbnail."), frappe.DoesNotExistError)


@frappe.whitelist()
def open_org_communication_attachment(
    org_communication: str | None = None,
    row_name: str | None = None,
):
    resolved_org_communication = str(org_communication or "").strip()
    resolved_row_name = str(row_name or "").strip()
    doc, target_row = _require_org_communication_attachment_context(
        resolved_org_communication,
        resolved_row_name,
    )

    external_url = str(getattr(target_row, "external_url", "") or "").strip()
    if external_url:
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = external_url
        return

    file_url = str(getattr(target_row, "file", "") or "").strip()
    if not file_url:
        frappe.throw(_("Attachment file is missing."), frappe.DoesNotExistError)

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    drive_file_id, file_id = _resolve_org_communication_drive_file(doc.name, resolved_row_name)
    target_url = _resolve_org_communication_attachment_grant_target_url(
        org_communication=doc.name,
        row_name=resolved_row_name,
        drive_file_id=drive_file_id,
        file_id=file_id,
        prefer_preview=False,
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    frappe.throw(_("Could not resolve the attachment."), frappe.DoesNotExistError)


@frappe.whitelist()
def preview_org_communication_attachment(
    org_communication: str | None = None,
    row_name: str | None = None,
):
    resolved_org_communication = str(org_communication or "").strip()
    resolved_row_name = str(row_name or "").strip()
    doc, target_row = _require_org_communication_attachment_context(
        resolved_org_communication,
        resolved_row_name,
    )

    if str(getattr(target_row, "external_url", "") or "").strip():
        frappe.throw(_("External links do not support governed preview."), frappe.ValidationError)

    file_url = str(getattr(target_row, "file", "") or "").strip()
    if not file_url:
        frappe.throw(_("Attachment file is missing."), frappe.DoesNotExistError)

    drive_file_id, file_id = _resolve_org_communication_drive_file(doc.name, resolved_row_name)
    target_url = _resolve_org_communication_attachment_grant_target_url(
        org_communication=doc.name,
        row_name=resolved_row_name,
        drive_file_id=drive_file_id,
        file_id=file_id,
        prefer_preview=True,
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    frappe.throw(_("Could not resolve the attachment preview."), frappe.DoesNotExistError)


@frappe.whitelist()
def thumbnail_org_communication_attachment(
    org_communication: str | None = None,
    row_name: str | None = None,
):
    resolved_org_communication = str(org_communication or "").strip()
    resolved_row_name = str(row_name or "").strip()
    doc, target_row = _require_org_communication_attachment_context(
        resolved_org_communication,
        resolved_row_name,
    )

    if str(getattr(target_row, "external_url", "") or "").strip():
        frappe.throw(_("External links do not support governed thumbnails."), frappe.ValidationError)

    file_url = str(getattr(target_row, "file", "") or "").strip()
    if not file_url:
        frappe.throw(_("Attachment file is missing."), frappe.DoesNotExistError)

    drive_file_id, file_id = _resolve_org_communication_drive_file(doc.name, resolved_row_name)
    derivative_role = _resolve_card_preview_derivative_role_for_drive_file(drive_file_id)
    target_url = _resolve_cached_thumbnail_target_url(
        drive_file_id=drive_file_id,
        file_id=file_id,
        surface_parts=["org_communication", doc.name, resolved_row_name],
        derivative_role=derivative_role,
        strict_derivative=True,
        target_resolver=lambda: _resolve_org_communication_attachment_grant_target_url(
            org_communication=doc.name,
            row_name=resolved_row_name,
            drive_file_id=drive_file_id,
            file_id=file_id,
            prefer_preview=True,
            derivative_role=derivative_role,
            strict_derivative=True,
        ),
    )
    if target_url:
        if _respond_with_delivery_target(target_url=target_url, cache_headers=True):
            return

    frappe.throw(_("Could not resolve the attachment thumbnail."), frappe.DoesNotExistError)


@frappe.whitelist(allow_guest=True)
def open_public_website_media(file: str | None = None):
    file_name = (file or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_public_website_media_row(file_name)
    _assert_public_website_media_visible(file_row)

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    target_url = _resolve_public_website_media_grant_url(file_name)
    if _respond_with_delivery_target(target_url=target_url):
        return

    frappe.throw(_("Could not resolve a public website media URL."), frappe.DoesNotExistError)


@frappe.whitelist(allow_guest=True)
def download_academic_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
    derivative_role: str | None = None,
):
    file_name = (file or "").strip()
    explicit_derivative_role = (derivative_role or "").strip()
    resolved_context_doctype = (context_doctype or "").strip()
    resolved_context_name = (context_name or "").strip()
    user = None
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_authorized_academic_file(
        file_name=file_name,
        context_doctype=context_doctype,
        context_name=context_name,
        share_token=share_token,
        viewer_email=viewer_email,
    )
    student_image_context = None
    if not (share_token or "").strip():
        user = _require_authenticated_user()
        try:
            student_image_context = _resolve_student_profile_image_access(
                user=user,
                file_name=file_name,
                context_doctype=context_doctype,
                context_name=context_name,
                strict=False,
            )
        except frappe.DoesNotExistError:
            student_image_context = None

        if (
            not student_image_context
            and resolved_context_doctype == CONTEXT_STUDENT
            and resolved_context_name
            and str((file_row or {}).get("attached_to_doctype") or "").strip() == CONTEXT_STUDENT
            and str((file_row or {}).get("attached_to_name") or "").strip() == resolved_context_name
            and str((file_row or {}).get("attached_to_field") or "").strip() == "student_image"
        ):
            drive_file_row = _resolve_current_student_profile_drive_file(resolved_context_name)
            student_image_context = _resolve_student_profile_image_access_from_drive_file(
                user=user,
                drive_file_row=drive_file_row,
                context_doctype=context_doctype,
                context_name=context_name,
                strict=False,
            )

    if student_image_context:
        file_row = student_image_context.get("file_row") or file_row
    material, _material_course = _resolve_supporting_material_context_for_file(file_row)
    placement_name = (
        _assert_internal_material_context(
            file_row=file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            material=material,
        )
        if material
        else None
    )
    material_drive_file = _resolve_current_material_drive_file(material) if material else None
    student = student_image_context.get("file_student") if student_image_context else None
    resolved_drive_file_id = student_image_context.get("drive_file_id") if student_image_context else ""

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    if explicit_derivative_role:
        target_url = (
            _resolve_student_image_grant_target_url(
                student=student,
                file_id=str((file_row or {}).get("name") or file_name).strip(),
                drive_file_id=resolved_drive_file_id,
                prefer_preview=True,
                derivative_role=explicit_derivative_role,
                strict_derivative=True,
            )
            if student_image_context
            else _resolve_supporting_material_grant_target_url(
                material=material,
                placement=placement_name,
                drive_file_id=str((material_drive_file or {}).get("name") or "").strip(),
                file_id=str((material_drive_file or {}).get("file") or file_name).strip(),
                prefer_preview=True,
                derivative_role=explicit_derivative_role,
            )
            if material and material_drive_file and material_drive_file.get("name")
            else _resolve_drive_preview_grant_url(file_name, derivative_role=explicit_derivative_role)
        )
        if _respond_with_delivery_target(target_url=target_url):
            return
        if student_image_context:
            frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    target_url = (
        _resolve_student_image_grant_target_url(
            student=student,
            file_id=str((file_row or {}).get("name") or file_name).strip(),
            drive_file_id=resolved_drive_file_id,
        )
        if student_image_context
        else _resolve_supporting_material_grant_target_url(
            material=material,
            placement=placement_name,
            drive_file_id=str((material_drive_file or {}).get("name") or "").strip(),
            file_id=str((material_drive_file or {}).get("file") or file_name).strip(),
        )
        if material and material_drive_file and material_drive_file.get("name")
        else _resolve_drive_download_grant_url(file_name)
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    if (
        student_image_context
        and _is_raw_private_redirect_target(file_url)
        and _respond_with_local_file_content(
            file_url=file_url,
            filename=(file_row or {}).get("file_name"),
            is_private=(file_row or {}).get("is_private"),
        )
    ):
        return

    frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)


def _resolve_authorized_academic_file(
    *,
    file_name: str,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
):
    token = (share_token or "").strip() or None
    if token:
        _assert_portfolio_share_file_access(
            file_name=file_name,
            share_token=token,
            viewer_email=(viewer_email or "").strip() or None,
        )
        return _resolve_any_file_row(file_name)

    file_row = _resolve_any_file_row(file_name)
    user = _require_authenticated_user()
    material, material_course = _resolve_supporting_material_context_for_file(file_row)
    if material:
        if not material_course:
            frappe.throw(_("Material file is missing course context."), frappe.ValidationError)
        placement_name = _assert_internal_material_context(
            file_row=file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            material=material,
        )
        if placement_name:
            placement_row = frappe.db.get_value(
                "Material Placement",
                placement_name,
                ["anchor_doctype", "anchor_name"],
                as_dict=True,
            )
            if not placement_row:
                frappe.throw(_("Material placement not found."), frappe.DoesNotExistError)
            if not materials_domain.user_can_read_material_anchor(
                user,
                placement_row.get("anchor_doctype"),
                placement_row.get("anchor_name"),
            ):
                frappe.throw(_("You do not have permission to access this file."), frappe.PermissionError)
        elif not materials_domain.user_can_read_supporting_material(user, material, course=material_course):
            frappe.throw(_("You do not have permission to access this file."), frappe.PermissionError)
        return file_row

    student, school = _resolve_student_context_for_file(file_row)
    if not student:
        frappe.throw(_("File is missing academic ownership context."), frappe.ValidationError)
    _assert_internal_academic_context(
        file_row=file_row,
        context_doctype=context_doctype,
        context_name=context_name,
        student=student,
    )
    _assert_internal_student_access(user=user, student=student, school=school)
    return file_row


@frappe.whitelist(allow_guest=True)
def preview_academic_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
):
    file_name = (file or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_authorized_academic_file(
        file_name=file_name,
        context_doctype=context_doctype,
        context_name=context_name,
        share_token=share_token,
        viewer_email=viewer_email,
    )
    material, _material_course = _resolve_supporting_material_context_for_file(file_row)
    placement_name = (
        _assert_internal_material_context(
            file_row=file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            material=material,
        )
        if material
        else None
    )
    material_drive_file = _resolve_current_material_drive_file(material) if material else None

    target_url = (
        _resolve_supporting_material_grant_target_url(
            material=material,
            placement=placement_name,
            drive_file_id=str((material_drive_file or {}).get("name") or "").strip(),
            file_id=str((material_drive_file or {}).get("file") or file_name).strip(),
            prefer_preview=True,
        )
        if material and material_drive_file and material_drive_file.get("name")
        else _resolve_drive_preview_grant_url(file_name)
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    target_url = (
        _resolve_supporting_material_grant_target_url(
            material=material,
            placement=placement_name,
            drive_file_id=str((material_drive_file or {}).get("name") or "").strip(),
            file_id=str((material_drive_file or {}).get("file") or file_name).strip(),
        )
        if material and material_drive_file and material_drive_file.get("name")
        else _resolve_drive_download_grant_url(file_name)
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)


@frappe.whitelist(allow_guest=True)
def thumbnail_academic_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    share_token: str | None = None,
    viewer_email: str | None = None,
):
    file_name = (file or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_authorized_academic_file(
        file_name=file_name,
        context_doctype=context_doctype,
        context_name=context_name,
        share_token=share_token,
        viewer_email=viewer_email,
    )
    material, _material_course = _resolve_supporting_material_context_for_file(file_row)
    placement_name = (
        _assert_internal_material_context(
            file_row=file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            material=material,
        )
        if material
        else None
    )

    drive_file = (
        _resolve_current_material_drive_file(material) if material else _resolve_drive_file_delivery_row(file_name)
    )
    if drive_file and drive_file.get("name"):
        derivative_role = _resolve_card_preview_derivative_role_for_drive_file(drive_file.get("name"))
        target_url = _resolve_cached_thumbnail_target_url(
            drive_file_id=drive_file.get("name"),
            file_id=str((drive_file or {}).get("file") or file_name).strip(),
            surface_parts=[
                "academic",
                context_doctype,
                context_name,
                share_token,
                viewer_email,
                file_name,
            ],
            derivative_role=derivative_role,
            strict_derivative=True,
            target_resolver=(
                (
                    lambda: _resolve_supporting_material_grant_target_url(
                        material=material,
                        placement=placement_name,
                        drive_file_id=drive_file.get("name"),
                        file_id=str((drive_file or {}).get("file") or file_name).strip(),
                        prefer_preview=True,
                        derivative_role=derivative_role,
                        strict_derivative=True,
                    )
                )
                if material
                else None
            ),
        )
        if target_url:
            if _respond_with_delivery_target(target_url=target_url, cache_headers=True):
                return

    frappe.throw(_("Could not resolve the attachment thumbnail."), frappe.DoesNotExistError)


@frappe.whitelist()
def download_guardian_file(
    file: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    derivative_role: str | None = None,
):
    user = _require_authenticated_user()
    file_name = (file or "").strip()
    explicit_derivative_role = (derivative_role or "").strip()
    resolved_context_doctype = (context_doctype or "").strip()
    resolved_context_name = (context_name or "").strip()
    if not file_name:
        frappe.throw(_("File is required."), frappe.ValidationError)

    file_row = _resolve_any_file_row(file_name)
    guardian_image_context = None
    try:
        guardian_image_context = _resolve_guardian_profile_image_access(
            user=user,
            file_name=file_name,
            context_doctype=context_doctype,
            context_name=context_name,
            strict=False,
        )
    except frappe.DoesNotExistError:
        guardian_image_context = None

    if (
        not guardian_image_context
        and resolved_context_doctype == CONTEXT_GUARDIAN
        and resolved_context_name
        and str((file_row or {}).get("attached_to_doctype") or "").strip() == CONTEXT_GUARDIAN
        and str((file_row or {}).get("attached_to_name") or "").strip() == resolved_context_name
        and str((file_row or {}).get("attached_to_field") or "").strip() == "guardian_image"
    ):
        drive_file_row = _resolve_current_guardian_profile_drive_file(resolved_context_name)
        guardian_image_context = _resolve_guardian_profile_image_access_from_drive_file(
            user=user,
            drive_file_row=drive_file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            strict=False,
        )

    if guardian_image_context:
        file_row = guardian_image_context.get("file_row") or file_row
        file_guardian = guardian_image_context["file_guardian"]
        resolved_drive_file_id = guardian_image_context["drive_file_id"]
    else:
        file_guardian = _resolve_guardian_from_file(file_row)
        _assert_guardian_file_access(
            user=user,
            file_guardian=file_guardian,
            context_doctype=context_doctype,
            context_name=context_name,
        )
        resolved_drive_file_id = ""

    file_url = (file_row.get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    if explicit_derivative_role:
        target_url = (
            _resolve_guardian_image_grant_target_url(
                guardian=file_guardian,
                file_id=str((file_row or {}).get("name") or file_name).strip(),
                drive_file_id=resolved_drive_file_id,
                prefer_preview=True,
                derivative_role=explicit_derivative_role,
                strict_derivative=True,
            )
            if guardian_image_context
            else _resolve_drive_preview_grant_url(file_name, derivative_role=explicit_derivative_role)
        )
        if _respond_with_delivery_target(target_url=target_url):
            return
        if guardian_image_context:
            frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    target_url = (
        _resolve_guardian_image_grant_target_url(
            guardian=file_guardian,
            file_id=str((file_row or {}).get("name") or file_name).strip(),
            drive_file_id=resolved_drive_file_id,
        )
        if guardian_image_context
        else _resolve_drive_download_grant_url(file_name)
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    if (
        guardian_image_context
        and _is_raw_private_redirect_target(file_url)
        and _respond_with_local_file_content(
            file_url=file_url,
            filename=(file_row or {}).get("file_name"),
            is_private=(file_row or {}).get("is_private"),
        )
    ):
        return

    frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)


@frappe.whitelist()
def download_employee_file(
    file: str | None = None,
    drive_file_id: str | None = None,
    canonical_ref: str | None = None,
    context_doctype: str | None = None,
    context_name: str | None = None,
    derivative_role: str | None = None,
):
    user = _require_authenticated_user()
    file_name = (file or "").strip()
    resolved_drive_file_id = (drive_file_id or "").strip()
    resolved_canonical_ref = (canonical_ref or "").strip()
    resolved_context_doctype = (context_doctype or "").strip()
    resolved_context_name = (context_name or "").strip()

    employee_image_context = None
    if resolved_drive_file_id or resolved_canonical_ref:
        drive_file_row = _resolve_drive_file_delivery_row(
            file_name or None,
            drive_file_id=resolved_drive_file_id or None,
            canonical_ref=resolved_canonical_ref or None,
        )
        employee_image_context = _resolve_employee_profile_image_access_from_drive_file(
            user=user,
            drive_file_row=drive_file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            strict=False,
        )
    elif file_name:
        try:
            employee_image_context = _resolve_employee_profile_image_access(
                user=user,
                file_name=file_name,
                context_doctype=context_doctype,
                context_name=context_name,
                strict=False,
            )
        except frappe.DoesNotExistError:
            employee_image_context = None

    if not employee_image_context and resolved_context_doctype == CONTEXT_EMPLOYEE and resolved_context_name:
        drive_file_row = _resolve_current_employee_profile_drive_file(resolved_context_name)
        employee_image_context = _resolve_employee_profile_image_access_from_drive_file(
            user=user,
            drive_file_row=drive_file_row,
            context_doctype=context_doctype,
            context_name=context_name,
            strict=False,
        )

    if employee_image_context:
        file_row = employee_image_context.get("file_row") or {}
        file_employee = employee_image_context["file_employee"]
        resolved_drive_file_id = employee_image_context["drive_file_id"]
    else:
        if not file_name:
            frappe.throw(_("File is required."), frappe.ValidationError)
        file_row = _resolve_any_file_row(file_name)
        file_employee = _resolve_employee_from_file(file_row)
        _assert_employee_file_access(
            user=user,
            file_employee=file_employee,
            context_doctype=context_doctype,
            context_name=context_name,
        )
        _assert_employee_owner_doc_read(file_employee)

    file_url = str((file_row or {}).get("file_url") or "").strip()
    if file_url.startswith(("http://", "https://")):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    if (derivative_role or "").strip():
        target_url = (
            _resolve_employee_image_grant_target_url(
                employee=file_employee,
                file_id=str((file_row or {}).get("name") or file_name or "").strip(),
                drive_file_id=resolved_drive_file_id,
                prefer_preview=True,
                derivative_role=derivative_role,
            )
            if employee_image_context
            else _resolve_drive_preview_grant_url(
                file_name or None,
                drive_file_id=resolved_drive_file_id or None,
                canonical_ref=resolved_canonical_ref or None,
                derivative_role=derivative_role,
            )
        )
        if _respond_with_delivery_target(target_url=target_url):
            return

    if _is_public_site_file_url(file_url):
        frappe.local.response["type"] = "redirect"
        frappe.local.response["location"] = file_url
        return

    target_url = (
        _resolve_employee_image_grant_target_url(
            employee=file_employee,
            file_id=str((file_row or {}).get("name") or file_name or "").strip(),
            drive_file_id=resolved_drive_file_id,
        )
        if employee_image_context
        else _resolve_drive_download_grant_url(
            file_name or None,
            drive_file_id=resolved_drive_file_id or None,
            canonical_ref=resolved_canonical_ref or None,
        )
    )
    if _respond_with_delivery_target(target_url=target_url):
        return

    if (
        employee_image_context
        and _is_raw_private_redirect_target(file_url)
        and _respond_with_local_file_content(
            file_url=file_url,
            filename=(file_row or {}).get("file_name"),
            is_private=(file_row or {}).get("is_private"),
        )
    ):
        return

    frappe.throw(_("Could not resolve the file content."), frappe.DoesNotExistError)
