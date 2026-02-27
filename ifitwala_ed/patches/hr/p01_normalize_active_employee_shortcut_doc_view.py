# ifitwala_ed/patches/hr/p01_normalize_active_employee_shortcut_doc_view.py

import frappe


def execute():
    if not frappe.db.table_exists("Workspace Shortcut"):
        return
    if not frappe.db.has_column("Workspace Shortcut", "doc_view"):
        return
    if not frappe.db.has_column("Workspace Shortcut", "link_to"):
        return

    filters = {"link_to": "Employee"}
    if frappe.db.has_column("Workspace Shortcut", "label"):
        filters["label"] = "Active Employee"
    if frappe.db.has_column("Workspace Shortcut", "parenttype"):
        filters["parenttype"] = "Workspace"
    if frappe.db.has_column("Workspace Shortcut", "parent"):
        filters["parent"] = "HR"

    rows = frappe.get_all(
        "Workspace Shortcut",
        filters=filters,
        fields=["name", "doc_view"],
        limit_page_length=0,
    )

    for row in rows:
        if (row.get("doc_view") or "").strip() == "List":
            continue
        frappe.db.set_value("Workspace Shortcut", row["name"], "doc_view", "List", update_modified=False)
