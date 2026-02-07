# ifitwala_ed/www/website.py

import frappe

from ifitwala_ed.website.renderer import build_render_context


def _redirect(to: str):
	frappe.local.flags.redirect_location = to
	raise frappe.Redirect


def get_context(context):
	path = frappe.request.path if hasattr(frappe, "request") else "/"
	normalized_path = (path or "").rstrip("/") or "/"
	form_dict = getattr(frappe, "form_dict", {}) or {}
	cmd = str(form_dict.get("cmd") or "").strip()

	# Defensive normalization for routes that must never fall into school website rendering.
	if normalized_path == "/logout":
		_redirect("/?cmd=web_logout")

	# After web logout, always land on the canonical login page.
	if cmd == "web_logout":
		_redirect("/login")

	preview = str(form_dict.get("preview") or "") == "1"
	context.no_cache = 1
	try:
		context.update(build_render_context(route=path, preview=preview))
	except (frappe.ValidationError, frappe.DoesNotExistError) as exc:
		user = frappe.session.user
		if normalized_path in {"/", "/home"} and (not user or user == "Guest"):
			frappe.log_error(
				title="Website Home Fallback to Login",
				message=f"route={normalized_path}\nerror={exc}",
			)
			_redirect("/login")
		raise
	return context
