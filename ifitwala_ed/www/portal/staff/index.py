import frappe

from .index import _load_manifest, _collect_assets

ALLOWED_ROLES = {"Instructor", "Academic Assistant", "Academic Admin", "System Manager", "Administrator"}


def _redirect(target: str) -> None:
	frappe.local.flags.redirect_location = target
	raise frappe.Redirect


def _has_access(user: str) -> bool:
	if not user or user == "Guest":
		return False

	if user == "Administrator":
		return True

	user_roles = set(frappe.get_roles(user))
	return bool(user_roles & ALLOWED_ROLES)


def get_context(context):
	user = frappe.session.user
	if not _has_access(user):
		_redirect(f"/login?redirect-to=/portal/staff")

	manifest = _load_manifest()
	js_entry, css_files, preload_files = _collect_assets(manifest)

	context.vite_js = js_entry
	context.vite_css = css_files
	context.vite_preload = preload_files
	return context

