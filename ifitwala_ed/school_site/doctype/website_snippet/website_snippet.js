// ifitwala_ed/school_site/doctype/website_snippet/website_snippet.js

// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

function applyScopeUI(frm) {
	const scope = String(frm.doc.scope_type || "Global").trim() || "Global";
	const isGlobal = scope === "Global";
	const isOrganization = scope === "Organization";
	const isSchool = scope === "School";

	frm.set_df_property("organization", "reqd", isOrganization ? 1 : 0);
	frm.set_df_property("school", "reqd", isSchool ? 1 : 0);
	frm.set_df_property("organization", "hidden", isGlobal || isSchool ? 1 : 0);
	frm.set_df_property("school", "hidden", isGlobal || isOrganization ? 1 : 0);
}

frappe.ui.form.on("Website Snippet", {
	refresh(frm) {
		applyScopeUI(frm);
	},

	scope_type(frm) {
		applyScopeUI(frm);
	}
});
