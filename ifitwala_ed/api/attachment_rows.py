from __future__ import annotations

from typing import Any

from ifitwala_ed.api.attachment_previews import build_attachment_preview_item, clean_text


def build_governed_attachment_row(
    *,
    row_id: Any = None,
    surface: Any,
    item_id: Any,
    owner_doctype: Any,
    owner_name: Any,
    **kwargs,
) -> dict[str, Any]:
    row = build_attachment_preview_item(
        item_id=item_id,
        owner_doctype=owner_doctype,
        owner_name=owner_name,
        **kwargs,
    )
    resolved_id = clean_text(row_id) or clean_text(row.get("item_id"))
    return {
        "id": resolved_id,
        "surface": clean_text(surface),
        **row,
    }
