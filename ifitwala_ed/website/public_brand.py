from __future__ import annotations

import frappe
from frappe import _

from ifitwala_ed.api.file_access import resolve_public_website_media_url

VIRTUAL_ROOT = "All Organizations"
WEBSITE_FALLBACK_LOGO = "/assets/ifitwala_ed/favicon.svg"


def resolve_public_brand_organization() -> frappe._dict | None:
    org = frappe.db.get_value(
        "Organization",
        {
            "archived": 0,
            "name": ["!=", VIRTUAL_ROOT],
            "parent_organization": ["in", [VIRTUAL_ROOT, "", None]],
        },
        [
            "name",
            "organization_name",
            "organization_logo",
            "organization_logo_file",
            "default_website_school",
            "lft",
            "rgt",
        ],
        as_dict=True,
        order_by="lft asc",
    )
    if org:
        return org

    org = frappe.db.get_value(
        "Organization",
        {"archived": 0, "name": ["!=", VIRTUAL_ROOT]},
        [
            "name",
            "organization_name",
            "organization_logo",
            "organization_logo_file",
            "default_website_school",
            "lft",
            "rgt",
        ],
        as_dict=True,
        order_by="lft asc",
    )
    if org:
        return org

    return frappe.db.get_value(
        "Organization",
        {"name": VIRTUAL_ROOT},
        [
            "name",
            "organization_name",
            "organization_logo",
            "organization_logo_file",
            "default_website_school",
            "lft",
            "rgt",
        ],
        as_dict=True,
    )


def get_descendant_organization_names(organization) -> list[str]:
    if not organization:
        return []

    lft = organization.get("lft")
    rgt = organization.get("rgt")
    if lft is None or rgt is None:
        return [organization.get("name")] if organization.get("name") else []

    return frappe.get_all(
        "Organization",
        filters={"lft": [">=", lft], "rgt": ["<=", rgt], "archived": 0},
        pluck="name",
        order_by="lft asc",
    )


def get_public_brand_identity() -> dict:
    organization = resolve_public_brand_organization() or {}
    organization_name = (organization.get("organization_name") or organization.get("name") or "").strip()
    organization_logo = (organization.get("organization_logo") or "").strip() or None
    organization_logo_file = (organization.get("organization_logo_file") or "").strip() or None
    site_app_name = (frappe.get_website_settings("app_name") or frappe.get_system_settings("app_name") or "").strip()
    site_app_logo = (frappe.get_website_settings("app_logo") or "").strip()

    if organization_name == VIRTUAL_ROOT:
        organization_name = ""

    brand_name = organization_name or site_app_name or _("Ifitwala Ed")
    brand_logo = (
        resolve_public_website_media_url(
            file_name=organization_logo_file,
            file_url=organization_logo,
        )
        or (site_app_logo if site_app_logo.startswith(("/files/", "http://", "https://")) else None)
        or WEBSITE_FALLBACK_LOGO
    )

    return {
        "organization": organization,
        "organization_name": organization_name or brand_name,
        "organization_logo": organization_logo,
        "organization_logo_file": organization_logo_file,
        "brand_name": brand_name,
        "brand_logo": brand_logo,
    }


def sync_public_brand_website_settings() -> dict:
    brand = get_public_brand_identity()
    organization = brand.get("organization") or {}
    organization_name = (organization.get("organization_name") or organization.get("name") or "").strip()
    organization_logo = (organization.get("organization_logo") or "").strip()
    if organization_name == VIRTUAL_ROOT:
        organization_name = ""

    ws = frappe.get_single("Website Settings")
    changed = False

    if organization_name and ws.app_name != organization_name:
        ws.app_name = organization_name
        changed = True

    if organization_logo and ws.app_logo != organization_logo:
        ws.app_logo = organization_logo
        changed = True

    if ws.meta.has_field("home_page") and ws.home_page != "index":
        ws.home_page = "index"
        changed = True

    if changed:
        ws.save(ignore_permissions=True)

    return {
        "updated": changed,
        "app_name": ws.app_name,
        "app_logo": ws.app_logo,
        "home_page": ws.home_page if ws.meta.has_field("home_page") else None,
    }
