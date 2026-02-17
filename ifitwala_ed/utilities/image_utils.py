# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/utilities/image_utils.py

import io
import os
import re

import frappe
from frappe import _
from PIL import Image


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────
def slugify(text):
    """lowercase, replace non‑alphanums with '_', strip extra."""
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _get_file_classification(file_doc):
    if not file_doc:
        return None

    name = frappe.db.get_value("File Classification", {"file": file_doc.name}, "name")
    if not name:
        return None

    return frappe.get_doc("File Classification", name)


def _get_secondary_subjects(fc_doc):
    if not fc_doc:
        return []

    return [
        {
            "subject_type": row.subject_type,
            "subject_id": row.subject_id,
            "role": row.role,
        }
        for row in (fc_doc.secondary_subjects or [])
    ]


def _render_resized_bytes(original_path, width, quality=75):
    try:
        with Image.open(original_path) as img:
            if img.width <= width:
                return None
            img.thumbnail((width, width))
            buffer = io.BytesIO()
            img.save(buffer, "WEBP", optimize=True, quality=quality)
            return buffer.getvalue()
    except Exception as e:
        frappe.log_error(f"Error resizing image bytes: {e}", "File Auto‑Resize")
        return None


def _build_employee_derivative_classification(fc_doc, slot_suffix, source_file):
    return {
        "primary_subject_type": fc_doc.primary_subject_type,
        "primary_subject_id": fc_doc.primary_subject_id,
        "data_class": fc_doc.data_class,
        "purpose": fc_doc.purpose,
        "retention_policy": fc_doc.retention_policy,
        "slot": f"{fc_doc.slot}_{slot_suffix}",
        "organization": fc_doc.organization,
        "school": fc_doc.school,
        "upload_source": fc_doc.upload_source or "Desk",
        "source_file": source_file,
    }


def _employee_derivative_exists(source_file, slot_base, slot_suffix):
    slot = f"{slot_base}_{slot_suffix}"
    return frappe.db.exists(
        "File Classification",
        {"source_file": source_file, "slot": slot},
    )


def _generate_employee_derivatives(file_doc):
    if not file_doc or file_doc.attached_to_doctype != "Employee":
        return

    if file_doc.attached_to_field and file_doc.attached_to_field != "employee_image":
        return

    filename = os.path.basename(file_doc.file_url or file_doc.file_name or "")
    if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
        return

    fc_doc = _get_file_classification(file_doc)
    if not fc_doc or fc_doc.slot != "profile_image":
        return

    if not file_doc.file_url or file_doc.file_url.startswith("http"):
        return

    original_path = frappe.utils.get_site_path("public", file_doc.file_url.lstrip("/"))
    if not os.path.exists(original_path):
        frappe.log_error(
            f"Employee image missing on disk: {original_path}",
            "Employee Image Resize",
        )
        return

    base_filename = os.path.splitext(filename)[0]
    slug_base = slugify(base_filename)
    if not slug_base:
        return

    from ifitwala_ed.utilities import file_dispatcher

    sizes = {"thumb": 160, "card": 400, "medium": 960}
    secondary_subjects = _get_secondary_subjects(fc_doc)

    for size_label, width in sizes.items():
        if _employee_derivative_exists(file_doc.name, fc_doc.slot, size_label):
            continue

        content = _render_resized_bytes(original_path, width)
        if not content:
            continue

        classification = _build_employee_derivative_classification(
            fc_doc,
            size_label,
            file_doc.name,
        )

        file_dispatcher.create_and_classify_file(
            file_kwargs={
                "attached_to_doctype": file_doc.attached_to_doctype,
                "attached_to_name": file_doc.attached_to_name,
                "attached_to_field": file_doc.attached_to_field,
                "file_name": f"{size_label}_{slug_base}.webp",
                "content": content,
                "is_private": int(file_doc.is_private or 0),
            },
            classification=classification,
            secondary_subjects=secondary_subjects,
        )


def resize_and_save(
    doc,
    original_path,
    base_filename,
    doctype_folder,
    size_label,
    width,
    quality=75,
):
    """Create a single WebP variant if it doesn’t already exist."""
    slug_base = slugify(base_filename)
    resized_filename = f"{size_label}_{slug_base}.webp"
    resized_rel = f"files/gallery_resized/{doctype_folder}/{resized_filename}"
    resized_path = frappe.utils.get_site_path("public", resized_rel)
    resized_url = f"/{resized_rel}"

    if os.path.exists(resized_path):
        return  # already done

    try:
        with Image.open(original_path) as img:
            if img.width <= width:
                return  # nothing to downscale
            img.thumbnail((width, width))
            os.makedirs(os.path.dirname(resized_path), exist_ok=True)
            img.save(resized_path, "WEBP", optimize=True, quality=quality)
    except Exception as e:
        frappe.log_error(f"Error resizing image: {e}", "File Auto‑Resize")
        return

    # ── Register new File row if not present ───────────────────────────────
    try:
        parent_folder = f"Home/gallery_resized/{doctype_folder}"
        if not frappe.db.exists("File", {"file_url": resized_url}):
            # create intermediate folders if missing
            if not frappe.db.exists(
                "File",
                {
                    "file_name": doctype_folder,
                    "is_folder": 1,
                    "folder": "Home/gallery_resized",
                },
            ):
                if not frappe.db.exists("File", {"file_name": "gallery_resized", "is_folder": 1, "folder": "Home"}):
                    frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_name": "gallery_resized",
                            "is_folder": 1,
                            "folder": "Home",
                        }
                    ).insert(ignore_permissions=True)
                frappe.get_doc(
                    {
                        "doctype": "File",
                        "file_name": doctype_folder,
                        "is_folder": 1,
                        "folder": "Home/gallery_resized",
                    }
                ).insert(ignore_permissions=True)

            frappe.get_doc(
                {
                    "doctype": "File",
                    "file_name": resized_filename,
                    "file_url": resized_url,
                    "folder": parent_folder,
                    "is_private": 0,
                    "attached_to_doctype": doc.attached_to_doctype,
                    "attached_to_name": doc.attached_to_name,
                    "attached_to_field": doc.attached_to_field,
                }
            ).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Error registering resized image: {e}", "File Auto‑Resize")


# ────────────────────────────────────────────────────────────────────────────
# Core hooks
# ────────────────────────────────────────────────────────────────────────────
def handle_file_after_insert(doc, method=None):
    """Hook: create WebP variants after a File is inserted."""
    # Governed Employee images should only be processed once classified.
    if doc.attached_to_doctype == "Employee":
        if not frappe.db.exists("File Classification", {"file": doc.name}):
            return
        _generate_employee_derivatives(doc)
        return

    # Defer Student images until after rename_student_image() puts them
    # into /files/student/ with secure suffix.
    if doc.attached_to_doctype == "Student" and not doc.file_url.startswith("/files/student/"):
        return

    if not (doc.file_url and doc.attached_to_doctype):
        return

    allowed_doctypes = ["Employee", "Student", "School", "Course", "Program", "Blog Post"]
    if doc.attached_to_doctype not in allowed_doctypes:
        return

    # Ignore already‑generated variants
    filename = os.path.basename(doc.file_url)
    if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
        return

    # Process only images we care about
    if not any(doc.file_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
        return

    original_path = frappe.utils.get_site_path("public", doc.file_url.lstrip("/"))
    base_filename = os.path.splitext(filename)[0]
    doctype_folder = slugify(doc.attached_to_doctype)

    # ── Student path: centralised single call ───────────────────────────────
    if doc.attached_to_doctype == "Student":
        process_single_file(doc)
        return

    # ── All other doctypes: direct resize loop ─────────────────────────────
    for size_label, width in {"hero": 1800, "medium": 960, "card": 400, "thumb": 160}.items():
        resize_and_save(doc, original_path, base_filename, doctype_folder, size_label, width)


def handle_file_on_update(doc, method=None):
    """Hook: same logic for updates (but Student may still be mid‑rename)."""
    handle_file_after_insert(doc, method)


# ────────────────────────────────────────────────────────────────────────────
# Governed dispatcher entry point
# ────────────────────────────────────────────────────────────────────────────
def handle_governed_file_after_classification(file_doc):
    """Run derivative generation after governance is established."""
    if not file_doc:
        return
    if file_doc.attached_to_doctype != "Employee":
        return
    _generate_employee_derivatives(file_doc)


# ────────────────────────────────────────────────────────────────────────────
# Rebuild utility (unchanged API)
# ────────────────────────────────────────────────────────────────────────────
@frappe.whitelist()
def rebuild_resized_images(doctype):
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("Not permitted."))

    count = 0
    for file in frappe.get_all(
        "File",
        fields=["name", "file_url", "attached_to_doctype"],
        filters={"attached_to_doctype": doctype, "is_private": 0},
    ):
        if not file.file_url or not any(file.file_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
            continue
        if os.path.basename(file.file_url).startswith(("hero_", "medium_", "card_", "thumb_")):
            continue

        original_path = frappe.utils.get_site_path("public", file.file_url.lstrip("/"))
        if not os.path.exists(original_path):
            continue

        base_filename = os.path.splitext(os.path.basename(file.file_url))[0]
        doctype_folder = slugify(file.attached_to_doctype)
        try:
            for size_label, width in {"hero": 1800, "medium": 960, "card": 400, "thumb": 160}.items():
                resize_and_save(file, original_path, base_filename, doctype_folder, size_label, width)
            count += 1
        except Exception as e:
            frappe.log_error(f"Error on rebuild {file.name}: {e}", "Admin Resize Error")

    frappe.msgprint(_(f"Processed {count} file(s) attached to {doctype}."))


# ────────────────────────────────────────────────────────────────────────────
# Central entry point (used by Student.rename_student_image)
# ────────────────────────────────────────────────────────────────────────────
def process_single_file(file_doc):
    """Create all four WebP sizes for a File (idempotent)."""
    if not file_doc.file_url:
        return

    # skip generated variants & non‑images
    filename = os.path.basename(file_doc.file_url)
    if filename.startswith(("hero_", "medium_", "card_", "thumb_")):
        return
    if not any(file_doc.file_url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png")):
        return

    original_path = frappe.utils.get_site_path("public", file_doc.file_url.lstrip("/"))
    base_filename = os.path.splitext(filename)[0]
    doctype_folder = slugify(file_doc.attached_to_doctype)

    for size_label, width in {"hero": 1800, "medium": 960, "card": 400, "thumb": 160}.items():
        resize_and_save(file_doc, original_path, base_filename, doctype_folder, size_label, width)
