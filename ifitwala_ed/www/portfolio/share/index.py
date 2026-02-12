# ifitwala_ed/www/portfolio/share/index.py

import frappe

from ifitwala_ed.api.student_portfolio import resolve_portfolio_share_context


def get_context(context):
	path = frappe.request.path if hasattr(frappe, "request") else ""
	token = (path.rstrip("/").split("/")[-1] or "").strip()
	viewer_email = (getattr(frappe, "form_dict", {}).get("viewer_email") or "").strip() or None

	context.no_cache = 1
	context.noindex = 1
	context.share_error = ""
	context.share = None

	try:
		context.share = resolve_portfolio_share_context(token=token, viewer_email=viewer_email)
	except Exception:
		context.share_error = "This share link is invalid, expired, or revoked."

	return context
