// ifitwala_ed/governance/doctype/institutional_policy/institutional_policy.js
// Copyright (c) 2026, François de Ryckel and contributors
// For license information, please see license.txt

frappe.ui.form.on("Institutional Policy", {
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name) return;

		frm.add_custom_button(__("Create Policy Version"), async () => {
			if (!frm.doc.is_active) {
				frappe.msgprint(__("Activate this Institutional Policy before creating a Policy Version."));
				return;
			}

			try {
				const baseVersion = await getBaseVersion(frm.doc.name);
				const newDoc = frappe.model.get_new_doc("Policy Version");

				newDoc.institutional_policy = frm.doc.name;
				newDoc.version_label = suggestNextVersionLabel(
					String(baseVersion?.version_label || "v1").trim() || "v1"
				);
				newDoc.is_active = 0;
				newDoc.approved_by = "";
				newDoc.approved_on = "";
				newDoc.effective_from = "";
				newDoc.effective_to = "";

				if (baseVersion) {
					newDoc.amended_from = baseVersion.name;
					newDoc.policy_text = baseVersion.policy_text || "";
					newDoc.change_summary = "";
				} else {
					newDoc.policy_text = "";
				}

				frappe.set_route("Form", "Policy Version", newDoc.name);
				frappe.show_alert({
					message: baseVersion
						? __("Draft amendment created from the latest version. Update summary/text, then save.")
						: __("Draft first policy version created. Add policy text, then save."),
					indicator: "blue",
				});
			} catch (error) {
				frappe.msgprint({
					title: __("Unable to create Policy Version draft"),
					indicator: "red",
					message: (error && error.message) || __("Please retry or contact support."),
				});
			}
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
		if (Number.isFinite(number)) return `${prefix}${number + 1}`;
	}

	return `${value}-amend-1`;
}

async function getBaseVersion(institutionalPolicy) {
	const activeResponse = await frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Policy Version",
			filters: {
				institutional_policy: institutionalPolicy,
				is_active: 1,
			},
			fields: ["name", "version_label", "policy_text", "is_active"],
			order_by: "modified desc",
			limit_page_length: 1,
		},
	});

	const activeRows = activeResponse?.message || [];
	if (activeRows.length) return activeRows[0];

	const latestResponse = await frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Policy Version",
			filters: {
				institutional_policy: institutionalPolicy,
			},
			fields: ["name", "version_label", "policy_text", "is_active"],
			order_by: "modified desc",
			limit_page_length: 1,
		},
	});
	const latestRows = latestResponse?.message || [];
	return latestRows.length ? latestRows[0] : null;
}
