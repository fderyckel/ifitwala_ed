# ifitwala_ed/patches/website/p11_namespace_school_routes_and_public_forms.py

import frappe

from ifitwala_ed.website.utils import normalize_route


WEB_FORM_ROUTE_MAP = {
	"inquiry": "apply/inquiry",
	"registration-of-interest": "apply/registration-of-interest",
}


def _reload_web_form_docs():
	for module, dt, docname in (
		("admission", "web_form", "inquiry"),
		("admission", "web_form", "registration_of_interest"),
	):
		try:
			frappe.reload_doc(module, dt, docname)
		except Exception:
			# Some sites may already have synced metadata.
			pass


def _sync_public_web_form_routes():
	for web_form_name, web_form_route in WEB_FORM_ROUTE_MAP.items():
		if not frappe.db.exists("Web Form", web_form_name):
			continue

		frappe.db.set_value(
			"Web Form",
			web_form_name,
			{
				"anonymous": 1,
				"login_required": 0,
				"published": 1,
				"apply_document_permissions": 0,
				"route": web_form_route,
			},
			update_modified=False,
		)


def _target_full_route(*, school_slug: str, route: str) -> str:
	relative = (route or "").strip()
	if relative == "/":
		return normalize_route(f"/schools/{school_slug}")
	return normalize_route(f"/schools/{school_slug}/{relative}")


def _sync_school_website_page_routes():
	pages = frappe.get_all(
		"School Website Page",
		fields=["name", "school", "route", "full_route"],
	)
	if not pages:
		return

	school_rows = frappe.get_all(
		"School",
		fields=["name", "website_slug"],
	)
	school_slug_map = {row.name: (row.website_slug or "").strip() for row in school_rows}

	for page in pages:
		school_slug = school_slug_map.get(page.school)
		if not school_slug:
			continue
		next_full_route = _target_full_route(school_slug=school_slug, route=page.route)
		if page.full_route == next_full_route:
			continue

		frappe.db.set_value(
			"School Website Page",
			page.name,
			"full_route",
			next_full_route,
			update_modified=False,
		)


def _sync_school_admissions_cta_defaults():
	schools = frappe.get_all("School", fields=["name", "admissions_inquiry_route"])
	for school in schools:
		current = (school.admissions_inquiry_route or "").strip()
		if current and current != "/inquiry":
			continue
		frappe.db.set_value(
			"School",
			school.name,
			"admissions_inquiry_route",
			"/apply/inquiry",
			update_modified=False,
		)


def execute():
	_reload_web_form_docs()
	_sync_public_web_form_routes()
	_sync_school_website_page_routes()
	_sync_school_admissions_cta_defaults()
