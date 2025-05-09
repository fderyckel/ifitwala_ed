# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import os
import re
import frappe
from frappe import _  
from PIL import Image

def slugify(text): 
    """lowercase, replace non-alphanums with '_', strip extra.""" 
    return re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_')

def resize_and_save(doc, original_path, base_filename, doctype_folder, size_label, width, quality=75):
    """
    Resize and save an image version as WebP only.
    """
    slug_base = slugify(base_filename) 
    folder_slug = slugify(doctype_folder) 
    resized_filename = f"{size_label}_{slug_base}.webp"
    resized_relative_path = f"files/gallery_resized/{doctype_folder}/{resized_filename}"
    resized_path = frappe.utils.get_site_path("public", resized_relative_path)
    resized_url = f"/{resized_relative_path}"

    if os.path.exists(resized_path):
        return

    try:
        with Image.open(original_path) as img:
            if img.width <= width:
                return  # no need to resize
            img.thumbnail((width, width))
            os.makedirs(os.path.dirname(resized_path), exist_ok=True)
            img.save(resized_path, format="WEBP", optimize=True, quality=quality)
    except Exception as e:
        frappe.log_error(f"Error resizing image: {e}", "File Auto-Resize Error")
        return

    # Register in File only if not already
    try:
        parent_folder = f"Home/gallery_resized/{doctype_folder}"
        if not frappe.db.exists("File", {"file_url": resized_url}):
            if not frappe.db.exists("File", {"file_name": doctype_folder, "is_folder": 1, "folder": "Home/gallery_resized"}):
                if not frappe.db.exists("File", {"file_name": "gallery_resized", "is_folder": 1, "folder": "Home"}):
                    frappe.get_doc({
                        "doctype": "File", "file_name": "gallery_resized",
                        "is_folder": 1, "folder": "Home"
                    }).insert(ignore_permissions=True)
                frappe.get_doc({
                    "doctype": "File", "file_name": doctype_folder,
                    "is_folder": 1, "folder": "Home/gallery_resized"
                }).insert(ignore_permissions=True)

            frappe.get_doc({
                "doctype": "File",
                "file_name": resized_filename,
                "file_url": resized_url,
                "folder": parent_folder,
                "is_private": 0,
                "attached_to_doctype": doc.attached_to_doctype,
                "attached_to_name": doc.attached_to_name,
                "attached_to_field": doc.attached_to_field,
            }).insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error(f"Error registering resized image: {e}", "File Auto-Resize Error")


def handle_file_after_insert(doc, method=None):
    if not (doc.file_url and doc.attached_to_doctype):
        return

    allowed_doctypes = ["Employee", "Student", "School", "Course", "Program", "Blog Post"]
    image_extensions = [".jpg", ".jpeg", ".png"]
    target_widths = {
        "hero": 1800,
        "medium": 960,
        "card": 400,
        "thumb": 160
    }

    if doc.attached_to_doctype not in allowed_doctypes:
        return

    filename = os.path.basename(doc.file_url)
    if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
        return

    if not any(doc.file_url.lower().endswith(ext) for ext in image_extensions):
        return

    original_path = frappe.utils.get_site_path("public", doc.file_url.lstrip("/"))
    base_filename = os.path.splitext(os.path.basename(doc.file_url))[0]
    doctype_folder = slugify(doc.attached_to_doctype)

    os.makedirs(frappe.utils.get_site_path("public", "files", "gallery_resized", doctype_folder),
         exist_ok=True
    )

    for size_label, width in target_widths.items():
        resize_and_save(doc, original_path, base_filename, doctype_folder, size_label, width)


def handle_file_on_update(doc, method=None):
    """Triggered when File is updated — same logic as after_insert."""
    handle_file_after_insert(doc, method)


@frappe.whitelist()
def rebuild_resized_images(doctype):
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("Not permitted."))

    allowed_image_extensions = [".jpg", ".jpeg", ".png"]
    count = 0

    files = frappe.get_all(
        "File",
        fields=["name", "file_url", "attached_to_name", "attached_to_field", "attached_to_doctype"],
        filters={
            "attached_to_doctype": doctype,
            "is_private": 0
        }
    )

    for file in files:
        if not file.file_url or not any(file.file_url.lower().endswith(ext) for ext in allowed_image_extensions):
            continue

        filename = os.path.basename(file.file_url)
        if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
            continue

        original_path = frappe.utils.get_site_path("public", file.file_url.lstrip("/"))
        base_filename = os.path.splitext(filename)[0]
        doctype_folder = file.attached_to_doctype.lower()

        if not os.path.exists(original_path):
            continue

        try:
            for size_label, width in {
                "hero": 1800, "medium": 960, "card": 400, "thumb": 160
            }.items():
                resize_and_save(file, original_path, base_filename, doctype_folder, size_label, width)
            count += 1
        except Exception as e:
            frappe.log_error(f"Error on rebuild {file.name}: {e}", "Admin Resize Error")

    frappe.msgprint(_(f"Processed {count} file(s) attached to {doctype}."))
