# ifitwala_ed/www/website.py

import frappe

from ifitwala_ed.api.users import _resolve_login_redirect_path
from ifitwala_ed.website.renderer import build_render_context


def _redirect(to: str):
	frappe.local.flags.redirect_location = to
	raise frappe.Redirect


def get_context(context):
	path = frappe.request.path if hasattr(frappe, "request") else "/"
	normalized_path = (path or "").rstrip("/") or "/"

	# Defensive normalization for routes that must never fall into school website rendering.
	if normalized_path == "/logout":
		_redirect("/?cmd=web_logout")

	if normalized_path == "/app":
		user = frappe.session.user
		if not user or user == "Guest":
			_redirect("/login?redirect-to=/portal")
		roles = set(frappe.get_roles(user))
		_redirect(_resolve_login_redirect_path(user, roles))

	preview = str(getattr(frappe, "form_dict", {}).get("preview") or "") == "1"
	context.no_cache = 1
	context.update(build_render_context(route=path, preview=preview))
	return context
