# ifitwala_ed/patches/website/p09_seed_theme_profiles_k12_college.py

import frappe

from ifitwala_ed.school_site.doctype.website_theme_profile.website_theme_profile import (
	ensure_theme_profile_presets,
)


def execute():
	frappe.reload_doc("school_site", "doctype", "website_theme_profile")
	ensure_theme_profile_presets()
