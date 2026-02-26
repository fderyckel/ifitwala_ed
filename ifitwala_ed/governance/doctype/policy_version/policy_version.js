// ifitwala_ed/governance/doctype/policy_version/policy_version.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Policy Version", {
	setup(frm) {
		frm.set_query("approved_by", () => ({
			query: "ifitwala_ed.governance.doctype.policy_version.policy_version.approved_by_user_query",
			filters: {
				institutional_policy: frm.doc.institutional_policy || "",
			},
		}));
		frm.set_query("amended_from", () => ({
			filters: {
				institutional_policy: frm.doc.institutional_policy || "",
				name: ["!=", frm.doc.name || ""],
			},
		}));
	},
});
