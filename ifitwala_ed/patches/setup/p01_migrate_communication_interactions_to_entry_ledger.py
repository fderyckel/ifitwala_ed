# ifitwala_ed/patches/setup/p01_migrate_communication_interactions_to_entry_ledger.py

from __future__ import annotations

import frappe

LEGACY_DOCTYPE = "Communication Interaction"
LEGACY_TABLE = "tabCommunication Interaction"
ENTRY_DOCTYPE = "Communication Interaction Entry"
ENTRY_TABLE = "tabCommunication Interaction Entry"
ENTRY_LINK_FIELD = "communication_interaction"
LEGACY_REQUIRED_COLUMNS = (
    "name",
    "creation",
    "modified",
    "modified_by",
    "owner",
    "org_communication",
    "user",
    "audience_type",
    "surface",
    "intent_type",
    "reaction_code",
    "note",
    "visibility",
    "is_teacher_reply",
    "is_pinned",
    "is_resolved",
)

ENTRY_REQUIRED_COLUMNS = (
    "name",
    "creation",
    "modified",
    "modified_by",
    "owner",
    "org_communication",
    "user",
    "audience_type",
    "surface",
    "intent_type",
    "reaction_code",
    "note",
    "visibility",
    "is_teacher_reply",
    "is_pinned",
    "is_resolved",
)


def _table_has_columns(table_name: str, columns: tuple[str, ...]) -> bool:
    if not frappe.db.table_exists(table_name):
        return False
    return all(frappe.db.has_column(table_name, column) for column in columns)


def _as_text(value) -> str:
    return str(value or "").strip()


def _as_int(value) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _legacy_row_has_payload(row: dict) -> bool:
    return bool(_as_text(row.get("intent_type")) or _as_text(row.get("reaction_code")) or _as_text(row.get("note")))


def _fetch_legacy_rows() -> list[dict]:
    return frappe.db.sql(
        f"""
        SELECT
            `name`,
            `creation`,
            `modified`,
            `modified_by`,
            `owner`,
            `org_communication`,
            `user`,
            `audience_type`,
            `surface`,
            `intent_type`,
            `reaction_code`,
            `note`,
            `visibility`,
            `is_teacher_reply`,
            `is_pinned`,
            `is_resolved`
        FROM `{LEGACY_TABLE}`
        ORDER BY `creation` ASC, `modified` ASC, `name` ASC
        """,
        as_dict=True,
    )


def _entry_exists_for_legacy_row(row: dict, *, entry_has_link_column: bool) -> bool:
    if entry_has_link_column:
        existing_by_link = frappe.db.get_value(
            ENTRY_DOCTYPE,
            {ENTRY_LINK_FIELD: _as_text(row.get("name"))},
            "name",
        )
        if existing_by_link:
            return True

    existing_rows = frappe.db.sql(
        f"""
        SELECT `name`
        FROM `{ENTRY_TABLE}`
        WHERE `org_communication` = %(org_communication)s
          AND `user` = %(user)s
          AND COALESCE(`audience_type`, '') = %(audience_type)s
          AND COALESCE(`surface`, '') = %(surface)s
          AND COALESCE(`intent_type`, '') = %(intent_type)s
          AND COALESCE(`reaction_code`, '') = %(reaction_code)s
          AND COALESCE(`note`, '') = %(note)s
          AND COALESCE(`visibility`, '') = %(visibility)s
          AND COALESCE(`is_teacher_reply`, 0) = %(is_teacher_reply)s
          AND COALESCE(`is_pinned`, 0) = %(is_pinned)s
          AND COALESCE(`is_resolved`, 0) = %(is_resolved)s
        LIMIT 1
        """,
        {
            "org_communication": _as_text(row.get("org_communication")),
            "user": _as_text(row.get("user")),
            "audience_type": _as_text(row.get("audience_type")),
            "surface": _as_text(row.get("surface")),
            "intent_type": _as_text(row.get("intent_type")),
            "reaction_code": _as_text(row.get("reaction_code")),
            "note": _as_text(row.get("note")),
            "visibility": _as_text(row.get("visibility")),
            "is_teacher_reply": _as_int(row.get("is_teacher_reply")),
            "is_pinned": _as_int(row.get("is_pinned")),
            "is_resolved": _as_int(row.get("is_resolved")),
        },
        as_dict=True,
    )
    return bool(existing_rows)


def _insert_entry_row(row: dict, *, entry_has_link_column: bool) -> None:
    insert_columns = [
        "name",
        "creation",
        "modified",
        "modified_by",
        "owner",
        "docstatus",
        "idx",
    ]
    insert_placeholders = [
        "%(name)s",
        "%(creation)s",
        "%(modified)s",
        "%(modified_by)s",
        "%(owner)s",
        "0",
        "0",
    ]

    if entry_has_link_column:
        insert_columns.append(ENTRY_LINK_FIELD)
        insert_placeholders.append(f"%({ENTRY_LINK_FIELD})s")

    insert_columns.extend(
        [
            "org_communication",
            "user",
            "audience_type",
            "surface",
            "intent_type",
            "reaction_code",
            "note",
            "visibility",
            "is_teacher_reply",
            "is_pinned",
            "is_resolved",
        ]
    )
    insert_placeholders.extend(
        [
            "%(org_communication)s",
            "%(user)s",
            "%(audience_type)s",
            "%(surface)s",
            "%(intent_type)s",
            "%(reaction_code)s",
            "%(note)s",
            "%(visibility)s",
            "%(is_teacher_reply)s",
            "%(is_pinned)s",
            "%(is_resolved)s",
        ]
    )

    values = {
        "name": frappe.generate_hash(length=10),
        "creation": row.get("creation"),
        "modified": row.get("modified") or row.get("creation"),
        "modified_by": _as_text(row.get("modified_by")) or _as_text(row.get("owner")) or "Administrator",
        "owner": _as_text(row.get("owner")) or _as_text(row.get("modified_by")) or "Administrator",
        ENTRY_LINK_FIELD: _as_text(row.get("name")) or None,
        "org_communication": _as_text(row.get("org_communication")),
        "user": _as_text(row.get("user")),
        "audience_type": _as_text(row.get("audience_type")) or None,
        "surface": _as_text(row.get("surface")) or None,
        "intent_type": _as_text(row.get("intent_type")) or None,
        "reaction_code": _as_text(row.get("reaction_code")) or None,
        "note": _as_text(row.get("note")) or None,
        "visibility": _as_text(row.get("visibility")) or None,
        "is_teacher_reply": _as_int(row.get("is_teacher_reply")),
        "is_pinned": _as_int(row.get("is_pinned")),
        "is_resolved": _as_int(row.get("is_resolved")),
    }

    column_sql = ", ".join(f"`{column}`" for column in insert_columns)
    placeholder_sql = ", ".join(insert_placeholders)
    frappe.db.sql(
        f"""
        INSERT INTO `{ENTRY_TABLE}` ({column_sql})
        VALUES ({placeholder_sql})
        """,
        values,
    )


def _backfill_legacy_rows() -> dict[str, int]:
    summary = {
        "processed": 0,
        "inserted": 0,
        "skipped": 0,
        "failed": 0,
    }

    if not _table_has_columns(LEGACY_DOCTYPE, LEGACY_REQUIRED_COLUMNS):
        return summary
    if not _table_has_columns(ENTRY_DOCTYPE, ENTRY_REQUIRED_COLUMNS):
        return summary

    entry_has_link_column = frappe.db.has_column(ENTRY_DOCTYPE, ENTRY_LINK_FIELD)
    for row in _fetch_legacy_rows():
        summary["processed"] += 1

        if not _as_text(row.get("org_communication")) or not _as_text(row.get("user")):
            summary["skipped"] += 1
            continue
        if not _legacy_row_has_payload(row):
            summary["skipped"] += 1
            continue
        if _entry_exists_for_legacy_row(row, entry_has_link_column=entry_has_link_column):
            summary["skipped"] += 1
            continue

        try:
            _insert_entry_row(row, entry_has_link_column=entry_has_link_column)
            summary["inserted"] += 1
        except Exception:
            summary["failed"] += 1
            frappe.log_error(
                title="Communication Interaction migration row failed",
                message=frappe.as_json(
                    {
                        "legacy_name": _as_text(row.get("name")),
                        "org_communication": _as_text(row.get("org_communication")),
                        "user": _as_text(row.get("user")),
                    }
                ),
            )

    return summary


def execute():
    summary = _backfill_legacy_rows()

    frappe.log_error(
        title="Communication Interaction migration summary",
        message=frappe.as_json(
            {
                **summary,
            }
        ),
    )
