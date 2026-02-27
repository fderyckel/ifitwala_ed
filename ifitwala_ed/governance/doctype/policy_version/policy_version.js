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
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name || !frm.doc.institutional_policy) return;

		frm.add_custom_button(__("Create Amendment"), () => {
			const currentLabel = String(frm.doc.version_label || "").trim();
			const suggestion = suggestNextVersionLabel(currentLabel || "v1");
			const newDoc = frappe.model.get_new_doc("Policy Version");

			newDoc.institutional_policy = frm.doc.institutional_policy;
			newDoc.version_label = suggestion;
			newDoc.amended_from = frm.doc.name;
			newDoc.change_summary = "";
			newDoc.policy_text = frm.doc.policy_text || "";
			newDoc.is_active = 0;
			newDoc.approved_by = "";
			newDoc.approved_on = "";
			newDoc.effective_from = "";
			newDoc.effective_to = "";

			frappe.set_route("Form", "Policy Version", newDoc.name);
			frappe.show_alert({
				message: __("Draft amendment created. Update summary/text, then save and activate."),
				indicator: "blue",
			});
		});
	},
});

function suggestNextVersionLabel(label) {
	const value = String(label || "").trim();
	if (!value) return "v1";

	const match = value.match(/^(.*?)(\d+)$/);
	if (match) {
		const prefix = match[1] || "";
		const number = Number.parseInt(match[2], 10);
		if (Number.isFinite(number)) {
			return `${prefix}${number + 1}`;
		}
	}

	return `${value}-amend-1`;
}
