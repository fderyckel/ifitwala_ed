# ifitwala_ed/patches/admission/p01_seed_inquiry_team_kanban_board.py

import frappe

BOARD_NAME = "Inquiry Team Pipeline"
BOARD_DOCTYPE = "Inquiry"
BOARD_FIELD = "sla_status"

BOARD_CARD_FIELDS = [
    "workflow_state",
    "assigned_to",
    "first_contact_due_on",
    "type_of_inquiry",
    "organization",
    "school",
]

BOARD_FILTERS = [[BOARD_DOCTYPE, "workflow_state", "!=", "Archived"]]

COLUMN_INDICATORS = {
    "🔴 Overdue": "red",
    "🟡 Due Today": "orange",
    "⚪ Upcoming": "blue",
    "✅ On Track": "green",
}


def _kanban_board_supported() -> bool:
    if not frappe.db.exists("DocType", "Kanban Board"):
        return False
    if not frappe.db.table_exists("Kanban Board"):
        return False
    if not frappe.db.has_column("Kanban Board", "reference_doctype"):
        return False
    if not frappe.db.has_column("Kanban Board", "kanban_board_name"):
        return False
    if not frappe.db.has_column("Kanban Board", "field_name"):
        return False
    if not frappe.db.has_column("Kanban Board", "fields"):
        return False
    if not frappe.db.has_column("Kanban Board", "filters"):
        return False
    return True


def _find_or_create_board_name() -> str | None:
    board_name = frappe.db.get_value(
        "Kanban Board",
        {"reference_doctype": BOARD_DOCTYPE, "kanban_board_name": BOARD_NAME},
        "name",
    )
    if board_name:
        return board_name

    quick_kanban_board = frappe.get_attr("frappe.desk.doctype.kanban_board.kanban_board.quick_kanban_board")
    board = quick_kanban_board(BOARD_DOCTYPE, BOARD_NAME, BOARD_FIELD)
    return board.name if board else None


def _apply_board_settings(board_name: str) -> None:
    board = frappe.get_doc("Kanban Board", board_name)
    changed = False
    show_labels_supported = frappe.db.has_column("Kanban Board", "show_labels")
    indicator_supported = frappe.db.table_exists("Kanban Board Column") and frappe.db.has_column(
        "Kanban Board Column", "indicator"
    )

    if (board.field_name or "").strip() != BOARD_FIELD:
        board.field_name = BOARD_FIELD
        changed = True

    current_fields = frappe.parse_json(board.fields) if board.fields else []
    if current_fields != BOARD_CARD_FIELDS:
        board.fields = frappe.as_json(BOARD_CARD_FIELDS)
        changed = True

    current_filters = frappe.parse_json(board.filters) if board.filters else []
    if current_filters != BOARD_FILTERS:
        board.filters = frappe.as_json(BOARD_FILTERS)
        changed = True

    if show_labels_supported and hasattr(board, "show_labels") and int(board.show_labels or 0) != 1:
        board.show_labels = 1
        changed = True

    if indicator_supported:
        for column in board.columns or []:
            target_indicator = COLUMN_INDICATORS.get((column.column_name or "").strip())
            if target_indicator and (column.indicator or "").strip() != target_indicator:
                column.indicator = target_indicator
                changed = True

    if changed:
        board.save(ignore_permissions=True)


def execute():
    if not _kanban_board_supported():
        return

    board_name = _find_or_create_board_name()
    if not board_name:
        return

    _apply_board_settings(board_name)
