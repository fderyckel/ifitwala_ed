# ifitwala_ed/patches/website/p06_backfill_workflow_state_from_status.py

import frappe

VALID_WORKFLOW_STATES = {
    "Draft",
    "In Review",
    "Approved",
    "Published",
}


def _backfill_workflow_state(doctype: str):
    if not frappe.db.has_column(doctype, "workflow_state"):
        return

    rows = frappe.get_all(
        doctype,
        fields=["name", "status", "workflow_state"],
        limit_page_length=0,
    )
    for row in rows:
        current_state = (row.workflow_state or "").strip()
        if current_state in VALID_WORKFLOW_STATES:
            continue

        target_state = "Published" if (row.status or "").strip() == "Published" else "Draft"
        frappe.db.set_value(
            doctype,
            row.name,
            "workflow_state",
            target_state,
            update_modified=False,
        )


def execute():
    _backfill_workflow_state("School Website Page")
    _backfill_workflow_state("Program Website Profile")
