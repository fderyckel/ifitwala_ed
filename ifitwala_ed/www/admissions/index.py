# ifitwala_ed/www/admissions/index.py

import os
import json
from urllib.parse import quote
import frappe

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


def _load_manifest() -> dict:
	for path in MANIFEST_PATHS:
		if not os.path.exists(path):
			continue
		with open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	return {}


def _collect_assets(manifest: dict) -> tuple[str, list[str], list[str]]:
	entry = None
	for key in ADMISSIONS_ENTRY_KEYS:
		if key in manifest:
			entry = manifest[key]
			break
	if not entry:
		for _, v in manifest.items():
			if isinstance(v, dict) and v.get("isEntry"):
				entry = v
				break
	if not entry:
		return (f"{PUBLIC_BASE}main.js", [], [])

	def _url(p: str) -> str:
		return f"{PUBLIC_BASE}{p}"

	js_entry = _url(entry["file"])
	css_files = [_url(p) for p in entry.get("css", [])]

	preload = []
	seen = set()

	def walk(chunk: dict):
		for imp in (chunk.get("imports") or []):
			if imp in seen:
				continue
			seen.add(imp)
			sub = manifest.get(imp)
			if sub and "file" in sub:
				preload.append(_url(sub["file"]))
				walk(sub)

	if isinstance(entry, dict):
		walk(entry)
	return (js_entry, css_files, preload)


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

	manifest = _load_manifest()
	js_entry, css_files, preload_files = _collect_assets(manifest)

	context.vite_js = js_entry
	context.vite_css = css_files
	context.vite_preload = preload_files
	return context
