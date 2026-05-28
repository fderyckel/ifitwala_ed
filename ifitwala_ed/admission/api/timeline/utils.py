from __future__ import annotations

from datetime import date, datetime
from typing import Any
from urllib.parse import quote

from frappe.utils import cint, get_datetime, strip_html

from ifitwala_ed.admission.admissions_crm_domain import clean
from ifitwala_ed.admission.api.timeline.constants import DEFAULT_LIMIT, MAX_LIMIT


def _bounded_limit(value: int | str | None) -> int:
    limit = cint(value) or DEFAULT_LIMIT
    return min(max(limit, 1), MAX_LIMIT)


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _as_bool(value: Any) -> bool:
    return bool(cint(value))


def _preview(value: str | None, *, length: int = 180) -> str | None:
    text = " ".join(strip_html(value or "").split()).strip()
    if not text:
        return None
    if len(text) <= length:
        return text
    return f"{text[:length].rstrip()}..."


def _subtitle(parts: list[str | None]) -> str | None:
    cleaned = [clean(part) for part in parts if clean(part)]
    return " • ".join(cleaned) if cleaned else None


def _desk_url(doctype: str, name: str | None) -> str | None:
    docname = clean(name)
    if not docname:
        return None
    doctype_slug = doctype.strip().lower().replace(" ", "-")
    return f"/desk/{doctype_slug}/{quote(docname, safe='')}"


def _to_sort_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return get_datetime(value)
    except Exception:
        return None


def _item(
    *,
    kind: str,
    source_doctype: str,
    source_name: str,
    occurred_at: Any,
    title: str,
    summary: str | None = None,
    actor: str | None = None,
    visibility: str = "staff",
    context_labels: dict | None = None,
    open_url: str | None = None,
    actions: list[dict] | None = None,
) -> dict:
    occurred_text = _as_text(occurred_at)
    return {
        "id": f"{source_doctype.lower().replace(' ', '_')}:{source_name}:{kind}",
        "kind": kind,
        "source_doctype": source_doctype,
        "source_name": source_name,
        "occurred_at": occurred_text,
        "title": title,
        "summary": summary,
        "actor": clean(actor),
        "visibility": visibility,
        "context_labels": context_labels or {},
        "open_url": open_url,
        "actions": actions or [],
        "_sort_at": _to_sort_datetime(occurred_at),
    }


def _strip_internal_fields(items: list[dict]) -> list[dict]:
    for item in items:
        item.pop("_sort_at", None)
    return items


def _query_in_condition(field_sql: str, key: str, values: list[str], conditions: list[str], params: dict) -> None:
    cleaned = sorted({clean(value) for value in values if clean(value)})
    if not cleaned:
        conditions.append("1=0")
        return
    conditions.append(f"{field_sql} IN %({key})s")
    params[key] = tuple(cleaned)


def _any_link_condition(
    *,
    alias: str,
    context: dict,
    fields: dict[str, str],
    params: dict,
) -> str:
    parts: list[str] = []
    conversation_names = context.get("conversation_names") or []
    inquiry_names = context.get("inquiry_names") or []
    applicant_names = context.get("applicant_names") or []

    if fields.get("conversation") and conversation_names:
        key = f"{alias}_conversation_names"
        parts.append(f"{fields['conversation']} IN %({key})s")
        params[key] = tuple(sorted({clean(value) for value in conversation_names if clean(value)}))
    if fields.get("inquiry") and inquiry_names:
        key = f"{alias}_inquiry_names"
        parts.append(f"{fields['inquiry']} IN %({key})s")
        params[key] = tuple(sorted({clean(value) for value in inquiry_names if clean(value)}))
    if fields.get("student_applicant") and applicant_names:
        key = f"{alias}_applicant_names"
        parts.append(f"{fields['student_applicant']} IN %({key})s")
        params[key] = tuple(sorted({clean(value) for value in applicant_names if clean(value)}))

    return "(" + " OR ".join(parts) + ")" if parts else "1=0"
