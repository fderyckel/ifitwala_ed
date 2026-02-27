# ifitwala_ed/patches/governance/p02_policy_acknowledgement_add_unique_evidence_index.py

import frappe

INDEX_NAME = "uniq_policy_ack_evidence"
TABLE_NAME = "Policy Acknowledgement"
REQUIRED_COLUMNS = (
    "policy_version",
    "acknowledged_by",
    "context_doctype",
    "context_name",
)


def _has_required_schema() -> bool:
    if not frappe.db.table_exists(TABLE_NAME):
        return False
    for column in REQUIRED_COLUMNS:
        if not frappe.db.has_column(TABLE_NAME, column):
            return False
    return True


def _index_exists() -> bool:
    rows = frappe.db.sql(
        """
        SHOW INDEX FROM `tabPolicy Acknowledgement`
        WHERE Key_name = %(index_name)s
        """,
        {"index_name": INDEX_NAME},
        as_dict=True,
    )
    return bool(rows)


def execute():
    if not _has_required_schema():
        return
    if _index_exists():
        return

    duplicates = frappe.db.sql(
        """
        SELECT
            policy_version,
            acknowledged_by,
            context_doctype,
            context_name,
            COUNT(*) AS duplicate_count
        FROM `tabPolicy Acknowledgement`
        GROUP BY policy_version, acknowledged_by, context_doctype, context_name
        HAVING COUNT(*) > 1
        LIMIT 20
        """,
        as_dict=True,
    )
    if duplicates:
        frappe.log_error(
            title="Policy acknowledgement unique index skipped",
            message=frappe.as_json(
                {
                    "table": TABLE_NAME,
                    "index_name": INDEX_NAME,
                    "reason": "duplicate evidence rows detected",
                    "duplicates": duplicates,
                }
            ),
        )
        return

    frappe.db.sql(
        f"""
        ALTER TABLE `tabPolicy Acknowledgement`
        ADD UNIQUE INDEX `{INDEX_NAME}` (
            `policy_version`,
            `acknowledged_by`,
            `context_doctype`,
            `context_name`
        )
        """
    )
