# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import os
import frappe
from PIL import Image

def resize_image(source_file_url, width=1600, quality=80):
    """
    Resize an image to a given max width while preserving aspect ratio and quality.
    Save resized version in /public/files/gallery_resized/.
    Return the URL of the resized image.

    Args:
        source_file_url (str): the original file URL (e.g., '/files/school_image.jpg')
        width (int): target max width in pixels (default 1600)
        quality (int): JPEG/PNG compression quality (default 80)

    Returns:
        str: the public URL of the resized image
    """

    if not source_file_url:
        return None

    # Paths and filenames
    original_path = frappe.utils.get_site_path("public", source_file_url.lstrip("/"))
    filename, ext = os.path.splitext(os.path.basename(source_file_url))
    ext = ext.lower().lstrip(".")

    # Define resized folder
    resized_folder = frappe.utils.get_site_path("public", "files", "gallery_resized")
    os.makedirs(resized_folder, exist_ok=True)

    # Define resized filename
    resized_filename = f"{filename}__w{width}_q{quality}.{ext if ext in ['png', 'jpg', 'jpeg'] else 'jpg'}"
    resized_path = os.path.join(resized_folder, resized_filename)
    resized_url = f"/files/gallery_resized/{resized_filename}"

    # If already exists, return directly
    if os.path.exists(resized_path):
        return resized_url

    # Perform resizing
    try:
        with Image.open(original_path) as img:
            original_format = img.format  # 'JPEG', 'PNG', etc.

            # SAFETY CHECK: do not upscale images smaller than target width
            if img.width <= width:
                return source_file_url  # Return original image if already smaller or equal

            img.thumbnail((width, width))  # Resize proportionally (width max)

            if original_format == "PNG":
                img.save(resized_path, format="PNG", optimize=True)
            else:
                img = img.convert("RGB")  # Remove alpha if JPEG
                img.save(resized_path, format="JPEG", quality=quality, optimize=True)

    except Exception as e:
        frappe.log_error(f"Error resizing image {source_file_url}: {e}", "Resize Image Error")
        return source_file_url

    return resized_url


def resize_and_save(original_path, target_folder, base_filename, width, quality=80, preserve_format="JPEG"):
    """Resize and save image version to a specific width."""
    resized_filename = f"{base_filename}__w{width}_q{quality}.jpg"
    resized_path = os.path.join(target_folder, resized_filename)

    if os.path.exists(resized_path):
        return

    try:
        with Image.open(original_path) as img:
            if img.width <= width:
                return  # No need to resize
            img.thumbnail((width, width))
            if preserve_format == "PNG":
                img.save(resized_path, format="PNG", optimize=True)
            else:
                img = img.convert("RGB")  # Remove alpha if saving JPEG
                img.save(resized_path, format="JPEG", optimize=True, quality=quality)
    except Exception as e:
        frappe.log_error(f"Error resizing image: {e}", "File Auto-Resize Error")

def handle_file_after_insert(doc, method=None):
    frappe.logger().info(f"[AutoResize] New File Inserted: {doc.name} attached to {doc.attached_to_doctype} ({doc.attached_to_name})")
    """Triggered after a File is inserted — resize images if applicable."""
    allowed_doctypes = ["Employee", "School"]
    target_widths = [1600, 300, 140]
    quality = 80
    resized_folder = frappe.utils.get_site_path("public", "files", "gallery_resized")

    if (doc.file_url 
        and doc.file_url.startswith("/files/") 
        and doc.attached_to_doctype in allowed_doctypes):

        file_ext = os.path.splitext(doc.file_url)[1].lower()

        if file_ext in [".jpg", ".jpeg", ".png"]:
            original_path = frappe.utils.get_site_path("public", doc.file_url.lstrip("/"))
            os.makedirs(resized_folder, exist_ok=True)
            base_filename = os.path.splitext(os.path.basename(doc.file_url))[0]

            try:
                with Image.open(original_path) as img:
                    original_format = img.format
            except Exception as e:
                frappe.log_error(f"Error reading uploaded image: {e}", "File Auto-Resize Error")
                original_format = "JPEG"

            for width in target_widths:
                resize_and_save(original_path, resized_folder, base_filename, width=width, quality=quality, preserve_format=original_format)
