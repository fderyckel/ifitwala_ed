from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Letter Head") or not frappe.db.table_exists("Print Settings"):
        return

    from ifitwala_ed.printing.letter_head.sync import (
        ensure_print_settings_with_letterhead,
        sync_default_school_letter_head,
    )

    sync_default_school_letter_head()
    ensure_print_settings_with_letterhead()
