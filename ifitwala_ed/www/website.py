# ifitwala_ed/www/website.py

import frappe

from ifitwala_ed.website.renderer import build_render_context


def get_context(context):
	path = frappe.request.path if hasattr(frappe, "request") else "/"
	context.no_cache = 1
	context.update(build_render_context(route=path))
	return context
