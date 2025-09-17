# Copyright (c) 2025, François de Ryckel and contributors
# For license information, please see license.txt

# ifitwala_ed/www/portal/index.py

import frappe

def get_context(context):
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/portal"
		raise frappe.Redirect
	# no server-rendered content; SPA mounts on #app
	return context
