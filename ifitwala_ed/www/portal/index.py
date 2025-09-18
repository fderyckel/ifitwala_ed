# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/portal/index.py

import os
import json
import frappe

APP = "ifitwala_ed"
DIST_DIR = os.path.join(frappe.get_app_path(APP), "public", "dist")
MANIFEST_PATH = os.path.join(DIST_DIR, ".vite", "manifest.json")
PUBLIC_BASE = f"/assets/{APP}/dist/"

def _load_manifest() -> dict:
	if not os.path.exists(MANIFEST_PATH):
		return {}
	with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
		return json.load(f)

def _collect_assets(manifest: dict) -> tuple[str, list[str], list[str]]:
	candidates = ["index.html", "src/main.ts", "src/main.js"]
	entry = None
	for key in candidates:
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

def get_context(context):
	user = frappe.session.user
	if not user or user == "Guest":
		_redirect("/login?redirect-to=/portal")

	# Explicit role check for this user
	if "Student" not in set(frappe.get_roles(user)):
		_redirect("/login?redirect-to=/portal")

	manifest = _load_manifest()
	js_entry, css_files, preload_files = _collect_assets(manifest)

	context.vite_js = js_entry
	context.vite_css = css_files
	context.vite_preload = preload_files
	return context
