# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _

# --------------------------------------------------------------------
# ENTRY: enqueue from hooks
# --------------------------------------------------------------------
def enqueue_sync(doc, method=None):
    if isinstance(doc, dict):
        doc = frappe.get_doc(doc)
    frappe.enqueue("ifitwala_ed.school_site.website_sync.route_sync",
                   doc=doc.as_dict(), queue="long")

def route_sync(doc: dict):
    doctype = doc.get("doctype")
    if doctype == "School":
        sync_school(frappe.get_doc(doc))
    elif doctype == "Program":
        if doc.get("is_published"):
            sync_program(frappe.get_doc(doc))
        else:
            remove_program_from_site(frappe.get_doc(doc))
    # ignore Course/etc. for now

# --------------------------------------------------------------------
# SCHOOL SYNC
# --------------------------------------------------------------------
def sync_school(school):
    _validate_languages(school)

    langs = [row.language_code for row in school.site_languages if row.publish]

    for lang in langs:
        nav = _ensure_navbar_settings(school, lang)
        page = _ensure_landing_page(school, lang, nav.name)
        print(f"[OK] {school.name}: {lang} → {nav.name} / {page.route}")

def _validate_languages(school):
    published = [l for l in school.site_languages if l.publish]
    if len(published) > 3:
        frappe.throw(_("A campus may publish at most 3 languages."))
    if not any(r.is_default for r in published):
        frappe.throw(_("Mark one default site language."))

# --------------------------------------------------------------------
# NAVBAR SETTINGS + ITEMS
# --------------------------------------------------------------------
def _ensure_navbar_settings(school, lang):
    settings_name = f"{school.website_slug}-{lang}-navbar"
    if frappe.db.exists("Navbar Settings", settings_name):
        return frappe.get_doc("Navbar Settings", settings_name)

    nav = frappe.new_doc("Navbar Settings")
    nav.name  = settings_name
    nav.app   = "website"
    nav.label = f"{school.school_name} {lang.upper()}"

    # HOME link
    nav.append("items", {
        "item_label": _("Home"),
        "item_type": "Route",
        "route": f"/{school.website_slug}/{lang}"
    })
    # empty Programs group; filled on first program sync
    nav.append("items", {
        "item_label": _("Programs"),
        "item_type": "Group"
    })
    nav.insert(ignore_permissions=True)
    return nav

# --------------------------------------------------------------------
# LANDING PAGE
# --------------------------------------------------------------------
def _ensure_landing_page(school, lang, navbar_name):
    route = f"/{school.website_slug}/{lang}"
    existing = frappe.db.get_value("Web Page", {"route": route})
    ctx = {
        "school_name": school.name,
        "navbar_settings": navbar_name
    }

    if not existing:
        page = frappe.new_doc("Web Page")
        page.route       = route
        page.title       = school.school_name
        page.published   = 0            # Draft first
        page.template    = "ifitwala_ed/school_site/templates/pages/school_landing.html"
        page.meta_json   = frappe.as_json(ctx)
        page.insert(ignore_permissions=True)
    else:
        page = frappe.get_doc("Web Page", existing)
        page.meta_json = frappe.as_json(ctx)
        page.save(ignore_permissions=True)

    return page

# --------------------------------------------------------------------
# PROGRAM SYNC
# --------------------------------------------------------------------
def sync_program(program):
    school = frappe.get_doc("School", program.school)
    navs   = {row.language_code: row
              for row in school.site_languages if row.publish}

    for lang in navs:
        _ensure_program_nav_item(program, school, lang)

def _ensure_program_nav_item(program, school, lang):
    settings_name = f"{school.website_slug}-{lang}-navbar"
    nav = frappe.get_doc("Navbar Settings", settings_name)

    # find Programs group
    group = next((i for i in nav.items if i.item_label == "Programs"), None)
    if not group:
        return

    # does link exist?
    exists = [i for i in nav.items
              if i.parent_label == "Programs" and i.route.endswith(program.website_slug)]
    if exists:
        return

    nav.append("items", {
        "item_label": program.program_name,
        "item_type": "Route",
        "route": f"/{school.website_slug}/{lang}/programs/{program.website_slug}",
        "parent_label": "Programs"
    })
    nav.save(ignore_permissions=True)

def remove_program_from_site(program):
    # Remove from all navbars; leave Web Page cleanup for later
    for nav in frappe.get_all("Navbar Settings", pluck="name"):
        doc = frappe.get_doc("Navbar Settings", nav)
        changed = False
        doc.items = [i for i in doc.items
                     if not (i.parent_label == "Programs"
                             and i.route and i.route.endswith(program.website_slug))]
        if changed:
            doc.save(ignore_permissions=True)
