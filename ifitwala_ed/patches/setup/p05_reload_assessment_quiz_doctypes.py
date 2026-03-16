# ifitwala_ed/patches/setup/p05_reload_assessment_quiz_doctypes.py

from __future__ import annotations

import frappe


def execute():
    # Defensive re-sync for sites where Quiz child tables were pruned as orphaned.
    frappe.reload_doc("assessment", "doctype", "quiz_question_option")
    frappe.reload_doc("assessment", "doctype", "quiz_question")
