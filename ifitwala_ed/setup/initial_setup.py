# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

import frappe
from frappe import _
# ─────────────────────────────────────────────────────────────────────────────

@frappe.whitelist()
def is_setup_done():
	"""Return True once the bench/site has had initial setup applied.

	We consider setup done if either:
	- Org Setting.ifitwala_initial_setup == 1, OR
	- the root Organization 'All Organizations' exists (installer creates it)
	"""
	flag = 0
	try:
		raw = frappe.db.get_single_value("Org Setting", "ifitwala_initial_setup")
		if raw is not None:
			flag = int(raw)  # raw may be 0/1 or '0'/'1'
	except Exception:
		# If Org Setting or field is missing for any reason, treat as not done
		flag = 0

	# Installer path creates this; if present, do NOT keep prompting.
	has_root_org = bool(frappe.db.exists("Organization", "All Organizations"))

	return (flag == 1) or has_root_org


@frappe.whitelist()
def complete_initial_setup(
	org_name=None, org_abbr=None, school_name=None, school_abbr=None,
	app_logo=None
):
	"""Create root Organization & School and optionally set
	the login-logo in Website Settings."""
	if is_setup_done():
		frappe.throw(_("Initial setup already completed."))

	# Ensure root organization "All Organizations" exists
	root_org = frappe.db.exists("Organization", "All Organizations")
	if not root_org:
		root_org = frappe.get_doc({
			"doctype": "Organization",
			"organization_name": "All Organizations",
			"abbr": "ALL",
			"is_group": 1,
			"parent_organization": "",
			"archived": 0
		}).insert(ignore_permissions=True)
	root_org_name = root_org.name if hasattr(root_org, "name") else root_org

	# ─── Create initial organization and school if provided ─────────────────
	if org_name and org_abbr:
		org = frappe.get_doc({
			"doctype": "Organization",
			"organization_name": org_name.strip(),
			"abbr": org_abbr.strip().upper(),
			"is_group": 1,
			"parent_organization": "All Organizations",
		}).insert(ignore_permissions=True)
	else:
		org = None

	if school_name and school_abbr:
		school = frappe.get_doc({
			"doctype": "School",
			"school_name": school_name.strip(),
			"abbr": school_abbr.strip().upper(),
			"is_group": 1,
			"organization": org.name if org else root_org_name,
		}).insert(ignore_permissions=True)
	else:
		school = None

	if school:
		from ifitwala_ed.website.bootstrap import ensure_default_school_website

		ensure_default_school_website(
			school_name=school.name,
			set_default_organization=True,
		)

	# ─── update Website Settings ─────────────────────────────────────────────
	ws = frappe.get_single("Website Settings")

	file_url = None
	if app_logo:
		if app_logo.startswith("/files/"):
			file_url = app_logo
		else:
			docname = frappe.db.exists("File", app_logo)
			file_url = frappe.db.get_value("File", docname, "file_url") if docname else None

		if not file_url:
			frappe.log_error(_("App logo file not found: {0}. Proceeding without it.").format(app_logo))

	# apply & save once
	if file_url:
		ws.app_logo = file_url
	ws.save(ignore_permissions=True)

	# ─── mark setup done (only after all saves succeeded) ────────────────────
	doc = frappe.get_single("Org Setting")
	doc.ifitwala_initial_setup = 1
	doc.save(ignore_permissions=True)
	# Force commit to ensure the change is persisted
	frappe.db.commit()

	# Return created docs and URLs for immediate UI use
	return {
		"organization": org.name if org else root_org.name,
		"school": school.name if school else None,
		"app_logo": ws.app_logo,
		"message": _("Organization, School and logo created successfully."),
	}
