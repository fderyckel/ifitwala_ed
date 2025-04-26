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
