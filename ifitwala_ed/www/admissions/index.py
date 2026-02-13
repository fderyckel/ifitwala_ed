# ifitwala_ed/www/admissions/index.py

import os
import json
from urllib.parse import quote
import frappe

from ifitwala_ed.website.vite_utils import get_vite_assets

APP = "ifitwala_ed"
VITE_DIR = os.path.join(frappe.get_app_path(APP), "public", "vite")
MANIFEST_PATHS = [
	os.path.join(VITE_DIR, "manifest.json"),
	os.path.join(VITE_DIR, ".vite", "manifest.json"),
]
PUBLIC_BASE = f"/assets/{APP}/vite/"

ADMISSIONS_ROLE = "Admissions Applicant"
ADMISSIONS_ENTRY_KEYS = [
	"src/admissions/main.ts",
	"src/admissions/main.js",
	"index.html",
]


def _load_assets():
	return get_vite_assets(
		app_name=APP,
		manifest_paths=MANIFEST_PATHS,
		public_base=PUBLIC_BASE,
		entry_keys=ADMISSIONS_ENTRY_KEYS
	)


def _redirect(to: str):
	frappe.local.flags.redirect_location = to
	raise frappe.Redirect


def _login_redirect_path(path: str) -> str:
	return f"/login?redirect-to={path}"


def _redirect_to_login(path: str, *, clear_session: bool = False):
	login_path = _login_redirect_path(path)
	if clear_session:
		encoded_login_path = quote(login_path, safe="")
		_redirect(f"/logout?redirect-to={encoded_login_path}")
	_redirect(login_path)


def get_context(context):
	user = frappe.session.user
	path = frappe.request.path if hasattr(frappe, "request") else "/admissions"

	if not user or user == "Guest":
		_redirect_to_login(path)

	roles = set(frappe.get_roles(user))
	if ADMISSIONS_ROLE not in roles:
		_redirect_to_login(path, clear_session=True)

	applicant = frappe.db.get_value(
		"Student Applicant",
		{"applicant_user": user},
		"name",
	)
	if not applicant:
		_redirect_to_login(path, clear_session=True)

	context.title = "Admissions Portal"
	context.applicant = applicant
	context.csrf_token = frappe.sessions.get_csrf_token()

	js_entry, css_files, preload_files = _load_assets()

	context.vite_js = js_entry
	context.vite_css = css_files
	context.vite_preload = preload_files
	return context
