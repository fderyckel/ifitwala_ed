# ifitwala_ed/patches/website/p13_consolidate_public_intake_to_inquiry.py

import frappe

INQUIRY_ROUTE = "/apply/inquiry"


def _remove_registration_of_interest_web_form():
    if not frappe.db.exists("Web Form", "registration-of-interest"):
        return
    frappe.delete_doc(
        "Web Form",
        "registration-of-interest",
        force=1,
        ignore_permissions=True,
    )


def _normalize_website_top_bar_contact_link():
    ws = frappe.get_single("Website Settings")
    rows = list(ws.top_bar_items or [])
    if not rows:
        ws.append("top_bar_items", {"label": "Contact Us", "url": INQUIRY_ROUTE})
        ws.save(ignore_permissions=True)
        return

    kept_rows = []
    changed = False
    has_contact_us = False

    for row in rows:
        label = (row.label or "").strip()
        url = (row.url or "").strip()
        label_lc = label.lower()
        url_lc = url.lower()

        is_roi_row = (
            "registration of interest" in label_lc
            or "registration-of-interest" in label_lc
            or "registration-of-interest" in url_lc
        )
        if is_roi_row:
            changed = True
            continue

        if label_lc == "contact us":
            has_contact_us = True
            if url != INQUIRY_ROUTE:
                row.url = INQUIRY_ROUTE
                changed = True

        kept_rows.append(
            {
                "label": row.label,
                "url": row.url,
                "parent_label": row.parent_label,
                "right": row.right,
            }
        )

    if not has_contact_us:
        kept_rows.append({"label": "Contact Us", "url": INQUIRY_ROUTE})
        changed = True

    if not changed:
        return

    ws.set("top_bar_items", [])
    for row in kept_rows:
        ws.append("top_bar_items", row)
    ws.save(ignore_permissions=True)


def execute():
    _remove_registration_of_interest_web_form()
    _normalize_website_top_bar_contact_link()
