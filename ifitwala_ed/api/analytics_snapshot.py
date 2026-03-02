# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/api/analytics_snapshot.py

from __future__ import annotations

import base64
import html
import re
from typing import Any

import frappe
from frappe.utils import get_system_timezone

MAX_IMAGE_BYTES = 12 * 1024 * 1024
DATA_URL_PREFIX = "data:image/png;base64,"
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _parse_payload(payload: Any | None) -> dict:
    if isinstance(payload, str):
        try:
            payload = frappe.parse_json(payload) or {}
        except Exception:
            payload = {}
    return payload or {}


def _to_text(value: Any) -> str:
    return str(value or "").strip()


def _sanitize_filename(value: str) -> str:
    cleaned = SAFE_FILENAME_RE.sub("-", value or "").strip("-.")
    if not cleaned:
        cleaned = "analytics-snapshot"
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned


def _coerce_filters(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, dict):
            continue
        key = _to_text(row.get("key") or row.get("label"))
        val = _to_text(row.get("value"))
        if not key:
            continue
        rows.append({"key": key, "value": val or "All"})
    return rows


def _decode_snapshot_data_url(data_url: str) -> bytes:
    if not data_url or not data_url.startswith(DATA_URL_PREFIX):
        frappe.throw("Snapshot image payload is missing or invalid.")

    raw = data_url[len(DATA_URL_PREFIX) :]
    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except Exception:
        frappe.throw("Snapshot image payload is malformed.")

    if not image_bytes:
        frappe.throw("Snapshot image payload is empty.")

    if len(image_bytes) > MAX_IMAGE_BYTES:
        frappe.throw("Snapshot image payload is too large. Please reduce the visible dashboard area and retry.")

    return image_bytes


def _render_pdf_html(
    *,
    title: str,
    captured_at: str,
    timezone: str,
    filters: list[dict[str, str]],
    image_data_url: str,
) -> str:
    escaped_title = html.escape(title)
    escaped_captured = html.escape(captured_at or "Unknown")
    escaped_timezone = html.escape(timezone or "UTC")

    filter_rows = ""
    if filters:
        for row in filters:
            filter_rows += (
                f"<tr><td class='k'>{html.escape(row['key'])}</td><td class='v'>{html.escape(row['value'])}</td></tr>"
            )
    else:
        filter_rows = "<tr><td class='k'>Filters</td><td class='v'>No filters applied</td></tr>"

    return f"""
    <html>
      <head>
        <meta charset="utf-8">
        <style>
          body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
            color: #0f172a;
            margin: 0;
            padding: 14px 16px;
          }}
          .header {{
            border: 1px solid #dbe4ef;
            border-radius: 10px;
            padding: 10px 12px;
            margin-bottom: 10px;
            background: #f8fafc;
          }}
          .title {{
            font-size: 18px;
            font-weight: 700;
            margin: 0 0 6px;
          }}
          .meta {{
            font-size: 12px;
            color: #334155;
            margin: 0;
          }}
          .filters {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
            font-size: 11px;
          }}
          .filters td {{
            border: 1px solid #dbe4ef;
            padding: 5px 7px;
            vertical-align: top;
          }}
          .filters td.k {{
            width: 28%;
            font-weight: 600;
            background: #f8fafc;
          }}
          .snapshot {{
            margin-top: 10px;
          }}
          .snapshot img {{
            width: 100%;
            height: auto;
            border: 1px solid #dbe4ef;
            border-radius: 8px;
          }}
        </style>
      </head>
      <body>
        <section class="header">
          <h1 class="title">{escaped_title}</h1>
          <p class="meta">Snapshot captured: {escaped_captured} ({escaped_timezone})</p>
          <table class="filters">{filter_rows}</table>
        </section>
        <section class="snapshot">
          <img src="{image_data_url}" alt="Dashboard snapshot" />
        </section>
      </body>
    </html>
    """


@frappe.whitelist()
def export_dashboard_pdf(payload: Any | None = None):
    user = frappe.session.user
    if not user or user == "Guest":
        frappe.throw("You need to sign in to export analytics snapshots.", frappe.PermissionError)

    params = _parse_payload(payload)

    title = _to_text(params.get("title")) or "Analytics Snapshot"
    file_name = _sanitize_filename(_to_text(params.get("file_name")) or "analytics-snapshot.pdf")
    captured_at = _to_text(params.get("captured_at")) or "Unknown"
    timezone = _to_text(params.get("timezone")) or (get_system_timezone() or "UTC")
    filters = _coerce_filters(params.get("filters"))
    image_data_url = _to_text(params.get("image_data_url"))

    image_bytes = _decode_snapshot_data_url(image_data_url)
    normalized_image_data_url = DATA_URL_PREFIX + base64.b64encode(image_bytes).decode("utf-8")

    from frappe.utils.pdf import get_pdf

    html_doc = _render_pdf_html(
        title=title,
        captured_at=captured_at,
        timezone=timezone,
        filters=filters,
        image_data_url=normalized_image_data_url,
    )
    pdf_bytes = get_pdf(html_doc)

    return {
        "file_name": file_name,
        "content_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
    }
