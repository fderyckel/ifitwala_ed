# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _


# ----------------------------------------------------------------------
def enqueue_sync(doc, method=None):
    """Hook entry: always background-queue for safety."""
    if isinstance(doc, dict):
        doc = frappe.get_doc(doc)
    frappe.enqueue(
        "ifitwala_ed.school_site.website_sync.sync_school",
        school_name=doc.name,
        queue="long"
    )

# ----------------------------------------------------------------------
def sync_school(school_name):
    school = frappe.get_doc("School", school_name)

    # sanity: must have slug + at least one published language
    if not school.website_slug:
        frappe.throw(_("School {0} needs website_slug").format(school.school_name))

    langs = [row.language_code
             for row in school.site_languages or []
             if row.publish]
    if not langs:
        frappe.throw(_("No published languages for {0}").format(school.school_name))

    for lang in langs:
        _ensure_school_page(school, lang)

# ----------------------------------------------------------------------
def _ensure_school_page(school, lang):
    """Create or update Web Page at /<slug>/<lang>."""
    route = f"/{school.website_slug}/{lang}"
    page_name = f"{school.website_slug}-{lang}-landing"

    ctx = {
        "school": school.name,
        "lang": lang
    }

    if frappe.db.exists("Web Page", {"name": page_name}):
        page = frappe.get_doc("Web Page", page_name)
        page.route = route          # in case slug changed
        page.meta_json = frappe.as_json(ctx)
        page.published = 1
        page.save(ignore_permissions=True)
        print(f"🔄 updated {route}")
    else:
        page = frappe.new_doc("Web Page")
        page.name        = page_name
        page.title       = school.school_name
        page.route       = route
        page.published   = 1
        page.module      = "School Site"
        page.content_type= "Page Builder"
        page.full_width  = 1
        page.page_blocks = []       # empty builder canvas for editors
        page.template    = ""       # default built-in template
        page.meta_json   = frappe.as_json(ctx)
        page.insert(ignore_permissions=True)
        print(f"✅ created {route}")

    # optional: clear route cache so the page appears immediately
    frappe.website.clear_sitemap_cache()
