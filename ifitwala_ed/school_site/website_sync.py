# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# =============================
# ENQUEUED ENTRY POINT
# =============================

def enqueue_sync(doc, method=None):
    """Enqueue hook for any doc update that needs website sync."""
    if isinstance(doc, dict):  # might come from hooks.py
        doc = frappe.get_doc(doc)

    frappe.enqueue(
        "ifitwala_ed.school_site.website_sync.route_sync",
        doc=doc.as_dict(),
        queue="long"
    )

# =============================
# ROUTING LOGIC
# =============================

def route_sync(doc: dict):
    """Main dispatcher for background syncs."""
    doctype = doc.get("doctype")

    if doctype == "School":
        sync_school(frappe.get_doc(doc))
    elif doctype == "Program":
        sync_program(frappe.get_doc(doc))
    elif doctype == "Course":
        sync_course(frappe.get_doc(doc))
    else:
        frappe.logger().debug(f"[Website Sync] Ignored Doctype: {doctype}")

# =============================
# SCHOOL SYNC
# =============================

def sync_school(school):
    """Sync all website artifacts related to a School."""
    _validate_languages(school)

    langs = [
        row.language_code
        for row in school.site_languages or []
        if row.publish
    ]

    for lang in langs:
        _ensure_navbar(school, lang)
        _ensure_landing_page(school, lang)


def _validate_languages(school):
    published = [l for l in school.site_languages if l.publish]
    if len(published) > 3:
        frappe.throw(_("A campus may publish at most 3 languages."))
    if not any(row.is_default for row in published):
        frappe.throw(_("At least one website language must be marked as default."))

def _ensure_navbar(school, lang):
    # Placeholder – this will create or update a Website Navbar doc
    print(f"[Website Sync] Sync navbar for {school.website_slug} ({lang})")

def _ensure_landing_page(school, lang):
    # Placeholder – this will create or update Web Page for /<slug>/<lang>
    print(f"[Website Sync] Sync landing page for {school.website_slug} ({lang})")


# =============================
# PROGRAM SYNC (to be fleshed)
# =============================

def sync_program(program):
    school = frappe.get_doc("School", program.school)
    langs = [
        row.language_code
        for row in school.site_languages or []
        if row.publish
    ]

    for lang in langs:
        _ensure_program_page(program, school, lang)
        _ensure_program_navlink(program, school, lang)

def _ensure_program_page(program, school, lang):
    print(f"[Website Sync] Create/update program page {program.website_slug} in {lang} for {school.website_slug}")

def _ensure_program_navlink(program, school, lang):
    print(f"[Website Sync] Ensure navlink exists for program {program.website_slug} in navbar of {school.website_slug} ({lang})")


# =============================
# COURSE SYNC (future)
# =============================

def sync_course(course):
    # Similar logic to program sync
    pass


# =============================
# NAVBAR SYNC
# =============================

def _ensure_navbar(school, lang):
    """Create or update a Website Navbar for this campus-language combo."""
    navbar_name = f"{school.website_slug}-{lang}-navbar"
    label = f"{school.school_name} ({lang.upper()})"

    existing = frappe.db.exists("Website Navbar", navbar_name)
    if not existing:
        navbar = frappe.new_doc("Website Navbar")
        navbar.name = navbar_name
        navbar.title = label
        navbar.is_standard = 0
        navbar.items = [
            {
                "item_label": _("Home"),
                "item_type": "Route",
                "route": f"/{school.website_slug}/{lang}"
            },
            {
                "item_label": _("Programs"),
                "item_type": "Group",
                "parent_label": "",
                "child_items": []
            }
        ]
        navbar.insert(ignore_permissions=True)
        print(f"[Website Sync] Created navbar: {navbar_name}")
    else:
        # Future: update logic (if structure changes)
        print(f"[Website Sync] Navbar exists: {navbar_name}")
