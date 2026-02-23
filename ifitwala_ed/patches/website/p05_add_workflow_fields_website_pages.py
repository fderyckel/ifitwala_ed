# ifitwala_ed/patches/website/p05_add_workflow_fields_website_pages.py

import frappe


def execute():
    frappe.reload_doc("school_site", "doctype", "school_website_page")
    frappe.reload_doc("school_site", "doctype", "program_website_profile")
