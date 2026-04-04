# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe


def execute():
    if not frappe.db.table_exists("Print Format"):
        return

    from ifitwala_ed.students.print_format.sync import sync_student_profile_print_format

    sync_student_profile_print_format()
