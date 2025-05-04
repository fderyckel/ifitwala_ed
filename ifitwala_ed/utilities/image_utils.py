# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import os
import frappe
from frappe import _  
from PIL import Image

def resize_and_save(doc, original_path, base_filename, doctype_folder, size_label, width, quality=80, preserve_format="JPEG"):
    """
    Resize and save an image version to a specific width.
    This function is currently used by handle_file_after_insert, but also reserved
    for future batch resizing, admin utilities, or migration scripts.
    """

    resized_filename = f"{size_label}_{base_filename}.jpg"
    resized_relative_path = f"files/gallery_resized/{doctype_folder}/{resized_filename}"
    resized_path = frappe.utils.get_site_path("public", resized_relative_path)
    resized_url = f"/{resized_relative_path}"

    # Skip if resized file already exists
    if os.path.exists(resized_path):
        return

    try:
        with Image.open(original_path) as img:
            if img.width <= width:
                return  # No need to resize
            img.thumbnail((width, width))
            if preserve_format == "PNG":
                os.makedirs(os.path.dirname(resized_path), exist_ok=True)
                img.save(resized_path, format="PNG", optimize=True)
            else:
                img = img.convert("RGB")  # Remove alpha if saving JPEG
                os.makedirs(os.path.dirname(resized_path), exist_ok=True)
                img.save(resized_path, format="JPEG", optimize=True, quality=quality)
    except Exception as e:
        frappe.log_error(f"Error resizing image: {e}", "File Auto-Resize Error")
        return

    # Register the resized file into Frappe File Doctype
    try:
        # Ensure parent folder exists (gallery_resized/{doctype})
        parent_folder_name = f"gallery_resized/{doctype_folder}"

        if not frappe.db.exists("File", {"file_name": doctype_folder, "is_folder": 1, "folder": "Home/gallery_resized"}):
            if not frappe.db.exists("File", {"file_name": "gallery_resized", "is_folder": 1, "folder": "Home"}):
                frappe.get_doc({
                    "doctype": "File",
                    "file_name": "gallery_resized",
                    "is_folder": 1,
                    "folder": "Home",
                }).insert(ignore_permissions=True)

            frappe.get_doc({
                "doctype": "File",
                "file_name": doctype_folder,
                "is_folder": 1,
                "folder": "Home/gallery_resized",
            }).insert(ignore_permissions=True)

        # Check if resized File already registered
        if not frappe.db.exists("File", {"file_url": resized_url}):
            frappe.get_doc({
                "doctype": "File",
                "file_name": resized_filename,
                "file_url": resized_url,
                "folder": f"Home/gallery_resized/{doctype_folder}",
                "is_private": 0,  # Public
                "attached_to_doctype": doc.attached_to_doctype,
                "attached_to_name": doc.attached_to_name,
                "attached_to_field": doc.attached_to_field,
            }).insert(ignore_permissions=True)

    except Exception as e:
        frappe.log_error( 
            title="File Auto-Resize Error", 
            message=f"Error resizing image {doc.name}: {e}"
        )

def handle_file_after_insert(doc, method=None):
    """Triggered after a File is inserted — resize images if applicable."""
    if not (doc.file_url and doc.attached_to_doctype):
        return

    allowed_doctypes = ["Employee", "School", "Course", "Program", "Blog Post"]  # extend if needed
    image_extensions = [".jpg", ".jpeg", ".png"]
    target_widths = {
        "small": 300,
        "medium": 800,
        "large": 1200,
    }
    quality = 80

    if doc.attached_to_doctype not in allowed_doctypes:
        return
    
    # Skip if file is already a Frappe-generated small_ or medium_ thumbnail
    filename = os.path.basename(doc.file_url)
    if filename.startswith(("large_", "medium_", "small_")):
        return


    if not any(doc.file_url.lower().endswith(ext) for ext in image_extensions):
        return

    original_path = frappe.utils.get_site_path("public", doc.file_url.lstrip("/"))
    base_filename = os.path.splitext(os.path.basename(doc.file_url))[0]
    doctype_folder = doc.attached_to_doctype.lower()

    # Ensure main folder exists
    gallery_base_folder = frappe.utils.get_site_path("public", "files", "gallery_resized", doctype_folder)
    os.makedirs(gallery_base_folder, exist_ok=True)

    try:
        with Image.open(original_path) as img:
            original_format = img.format
    except Exception as e:
        frappe.log_error(f"Error reading uploaded image: {e}", "File Auto-Resize Error")
        return

    for size_label, width in target_widths.items():
        resize_and_save(doc, original_path, base_filename, doctype_folder, size_label, width, quality=quality, preserve_format=original_format)

def handle_file_on_update(doc, method=None):
    """Triggered when File is updated — same logic as after_insert."""
    handle_file_after_insert(doc, method)


@frappe.whitelist()
def rebuild_resized_images(doctype):
    """
    Admin utility: Rebuild resized versions of images attached to a given DocType (e.g., Employee, School, Program).
    """
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("Not permitted."))

    allowed_image_extensions = [".jpg", ".jpeg", ".png"]
    count = 0

    # Fetch all File records attached to the specified doctype
    files = frappe.get_all(
        "File",
        fields=["name", "file_url", "attached_to_name", "attached_to_field", "attached_to_doctype"],
        filters={
            "attached_to_doctype": doctype,
            "is_private": 0  # only public files
        }
    )

    for file in files:
        if not file.file_url or not any(file.file_url.lower().endswith(ext) for ext in allowed_image_extensions):
            continue

        filename = os.path.basename(file.file_url)
        if filename.startswith(("large_", "medium_", "small_")):
            continue  # 🛡️ Skip already resized files

        original_path = frappe.utils.get_site_path("public", file.file_url.lstrip("/"))
        base_filename = os.path.splitext(os.path.basename(file.file_url))[0]
        doctype_folder = file.attached_to_doctype.lower()

        if not os.path.exists(original_path):
            continue  # skip missing files

        try:
            with Image.open(original_path) as img:
                original_format = img.format
        except Exception as e:
            frappe.log_error(f"Error opening file {file.name}: {e}", "Admin Resize Error")
            continue

        # Small, Medium, Large
        target_widths = {
            "large": 1200,
            "medium": 800,
            "small": 300
        }

        for size_label, width in target_widths.items():
            resize_and_save(file, original_path, base_filename, doctype_folder, size_label, width, quality=80, preserve_format=original_format)

        count += 1

    frappe.msgprint(_(f"Processed {count} file(s) attached to {doctype}."))


def convert_gallery_to_webp(delete_jpgs=False):
    base_folder = frappe.utils.get_site_path("public", "files", "gallery_resized")
    count_converted = 0
    count_skipped = 0

    for root, dirs, files in os.walk(base_folder):
        for fname in files:
            if not fname.lower().endswith(".jpg"):
                continue

            jpg_path = os.path.join(root, fname)
            webp_path = os.path.splitext(jpg_path)[0] + ".webp"

            if os.path.exists(webp_path):
                count_skipped += 1
                continue

            try:
                with Image.open(jpg_path) as img:
                    img.save(webp_path, format="WEBP", optimize=True, quality=75)
                count_converted += 1

                if delete_jpgs:
                    os.remove(jpg_path)
            except Exception as e:
                frappe.log_error(f"Failed to convert {jpg_path}: {e}", "Gallery WebP Migration")

    frappe.msgprint(f"✅ Converted {count_converted} JPG files to WebP. Skipped {count_skipped} existing.")
