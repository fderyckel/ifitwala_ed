from __future__ import annotations

from collections.abc import Iterable, Sequence

import frappe

_DEFAULT_DRIVE_FILE_FIELDS = (
    "name",
    "file",
    "status",
    "preview_status",
    "current_version",
    "current_version_no",
    "canonical_ref",
    "display_name",
    "folder",
    "attached_doctype",
    "attached_name",
    "owner_doctype",
    "owner_name",
    "organization",
    "school",
    "primary_subject_type",
    "primary_subject_id",
    "data_class",
    "purpose",
    "retention_policy",
    "slot",
    "storage_backend",
    "storage_object_key",
    "upload_source",
    "content_hash",
    "is_private",
    "modified",
    "creation",
)


def _clean_text(value) -> str:
    return str(value or "").strip()


def _ordered_fields(fields: Sequence[str] | None) -> list[str]:
    resolved = list(fields or _DEFAULT_DRIVE_FILE_FIELDS)
    for fieldname in ("modified", "creation"):
        if fieldname not in resolved:
            resolved.append(fieldname)
    return resolved


def _get_all_rows(
    doctype: str,
    *,
    filters: dict[str, object],
    fields: Sequence[str] | None,
    order_by: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    get_all = getattr(frappe, "get_all", None)
    if not callable(get_all):
        return []

    kwargs = {
        "filters": filters,
        "fields": list(fields or []),
    }
    if order_by:
        kwargs["order_by"] = order_by
    if limit is not None:
        kwargs["limit"] = limit

    try:
        rows = get_all(doctype, **kwargs)
    except TypeError:
        kwargs.pop("order_by", None)
        kwargs.pop("limit", None)
        rows = get_all(doctype, **kwargs)

    return rows or []


def get_drive_file_for_file(
    file_name: str | None,
    *,
    fields: Sequence[str] | None = None,
    statuses: Sequence[str] | None = None,
) -> dict | None:
    resolved_file = _clean_text(file_name)
    if not resolved_file:
        return None

    filters: dict[str, object] = {"file": resolved_file}
    if statuses:
        filters["status"] = ["in", list(statuses)]

    rows = _get_all_rows(
        "Drive File",
        filters=filters,
        fields=_ordered_fields(fields),
        order_by="modified desc, creation desc",
        limit=1,
    )
    return rows[0] if rows else None


def is_governed_file(file_name: str | None) -> bool:
    return bool(get_drive_file_for_file(file_name, fields=("name",), statuses=None))


def get_current_drive_file_for_slot(
    *,
    primary_subject_type: str,
    primary_subject_id: str,
    slot: str,
    fields: Sequence[str] | None = None,
    organization: str | None = None,
    school: str | None = None,
    attached_doctype: str | None = None,
    attached_name: str | None = None,
    statuses: Sequence[str] | None = ("active",),
) -> dict | None:
    rows = get_current_drive_files_for_slots(
        primary_subject_type=primary_subject_type,
        primary_subject_ids=[primary_subject_id],
        slots=[slot],
        fields=fields,
        organization=organization,
        school=school,
        attached_doctype=attached_doctype,
        attached_name=attached_name,
        statuses=statuses,
    )
    return rows[0] if rows else None


def get_current_drive_files_for_slots(
    *,
    primary_subject_type: str,
    primary_subject_ids: Sequence[str] | Iterable[str],
    slots: Sequence[str] | Iterable[str],
    fields: Sequence[str] | None = None,
    organization: str | None = None,
    school: str | None = None,
    attached_doctype: str | None = None,
    attached_name: str | None = None,
    statuses: Sequence[str] | None = ("active",),
) -> list[dict]:
    subject_ids = [_clean_text(value) for value in (primary_subject_ids or [])]
    subject_ids = [value for value in subject_ids if value]
    slot_names = [_clean_text(value) for value in (slots or [])]
    slot_names = [value for value in slot_names if value]
    if not primary_subject_type or not subject_ids or not slot_names:
        return []

    filters: dict[str, object] = {
        "primary_subject_type": _clean_text(primary_subject_type),
        "primary_subject_id": ["in", subject_ids],
        "slot": ["in", slot_names],
    }
    if statuses:
        filters["status"] = ["in", list(statuses)]
    if _clean_text(organization):
        filters["organization"] = _clean_text(organization)
    if _clean_text(school):
        filters["school"] = _clean_text(school)
    if _clean_text(attached_doctype):
        filters["attached_doctype"] = _clean_text(attached_doctype)
    if _clean_text(attached_name):
        filters["attached_name"] = _clean_text(attached_name)

    rows = _get_all_rows(
        "Drive File",
        filters=filters,
        fields=_ordered_fields(fields),
        order_by="modified desc, creation desc",
        limit=0,
    )
    if not rows:
        return []

    current_rows: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (_clean_text(row.get("primary_subject_id")), _clean_text(row.get("slot")))
        if key in seen:
            continue
        seen.add(key)
        current_rows.append(row)
    return current_rows


def supersede_drive_files_for_slots(
    *,
    primary_subject_type: str,
    primary_subject_id: str,
    slots: Sequence[str] | Iterable[str],
) -> list[str]:
    rows = get_current_drive_files_for_slots(
        primary_subject_type=primary_subject_type,
        primary_subject_ids=[primary_subject_id],
        slots=slots,
        fields=("name", "slot"),
    )
    for row in rows:
        frappe.db.set_value(
            "Drive File",
            row["name"],
            "status",
            "superseded",
            update_modified=False,
        )
    return [row["name"] for row in rows if row.get("name")]
