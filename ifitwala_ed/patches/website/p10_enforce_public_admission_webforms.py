# ifitwala_ed/patches/website/p10_enforce_public_admission_webforms.py

import frappe


def _make_public_web_form(name: str):
    if not frappe.db.exists("Web Form", name):
        return

    frappe.db.set_value(
        "Web Form",
        name,
        {
            "anonymous": 1,
            "login_required": 0,
            "published": 1,
            "apply_document_permissions": 0,
        },
        update_modified=False,
    )


def execute():
    # Ensure standard JSON definitions are loaded, then enforce live-site access flags.
    for module, dt, docname in (("admission", "web_form", "inquiry"),):
        try:
            frappe.reload_doc(module, dt, docname)
        except Exception:
            # Some sites may already have synced metadata; proceed with DB enforcement.
            pass

    _make_public_web_form("inquiry")
