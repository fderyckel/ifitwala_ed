# Copyright (c) 2026, François de Ryckel and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe

from ifitwala_ed.schedule.doctype.instructor.instructor import sync_instructor_logs


def execute():
    if not frappe.db.table_exists("Instructor") or not frappe.db.table_exists("Student Group Instructor"):
        return

    sync_instructor_logs(frappe.get_all("Instructor", pluck="name"))
