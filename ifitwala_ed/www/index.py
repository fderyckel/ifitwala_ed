# ifitwala_ed/www/index.py

import frappe

from ifitwala_ed.website.renderer import build_render_context


def get_context(context):
	path = frappe.request.path if hasattr(frappe, "request") else "/"
	preview = str(getattr(frappe, "form_dict", {}).get("preview") or "") == "1"
	context.no_cache = 1
	context.update(build_render_context(route=path, preview=preview))
	return context
