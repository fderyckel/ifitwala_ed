# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/portal/index.py

import os
import json
import frappe
from frappe import _

APP = "ifitwala_ed"
DIST_DIR = os.path.join(frappe.get_app_path(APP), "public", "dist")
MANIFEST_PATH = os.path.join(DIST_DIR, ".vite", "manifest.json")
PUBLIC_BASE = f"/assets/{APP}/dist/"

def _load_manifest():
	if not os.path.exists(MANIFEST_PATH):
		return {}
	with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
		return json.load(f)

def _collect_assets(manifest: dict):
	"""
	Return (entry_js, css_files, preload_js_files) from the Vite manifest.
	We try common keys in order: 'index.html', 'src/main.ts', 'src/main.js'.
	If nothing is found, fall back to predictable paths so the page still loads.
	"""
	candidates = ["index.html", "src/main.ts", "src/main.js"]
	entry = None
	for key in candidates:
		if key in manifest:
			entry = manifest[key]
			break
	# If no candidate key, try first isEntry=true
	if not entry:
		for _, v in manifest.items():
			if isinstance(v, dict) and v.get("isEntry"):
				entry = v
				break

	if not entry:
		# Fallback (non-hashed) to keep page usable even if manifest is missing
		return (f"{PUBLIC_BASE}main.js", [], [])

	def _url(rel_path: str) -> str:
		# manifest 'file' & 'css' are relative to outDir; prefix with PUBLIC_BASE
		return f"{PUBLIC_BASE}{rel_path}"

	js_entry = _url(entry["file"])
	css_files = [_url(p) for p in entry.get("css", [])]

	# Recursively collect imported JS chunk files for <link rel="modulepreload">
	preload = []
	seen = set()
	def walk_imports(chunk):
		for imp in chunk.get("imports", []) or []:
			if imp in seen:
				continue
			seen.add(imp)
			sub = manifest.get(imp)
			if sub and "file" in sub:
				preload.append(_url(sub["file"]))
				walk_imports(sub)

	walk_imports(entry)
	return (js_entry, css_files, preload)

def get_context(context):
	# Auth gate: only logged-in users
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/portal"
		raise frappe.Redirect

	# Role gate: only users with 'Student' role
	if "Student" not in frappe.get_roles():
		frappe.local.flags.redirect_location = "/login?redirect-to=/portal"
		raise frappe.Redirect

	manifest = _load_manifest()
	js_entry, css_files, preload_files = _collect_assets(manifest)

	# Pass resolved URLs to the Jinja template
	context.vite_js = js_entry
	context.vite_css = css_files
	context.vite_preload = preload_files
	return context
