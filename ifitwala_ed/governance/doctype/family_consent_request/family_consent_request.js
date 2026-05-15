frappe.ui.form.on("Family Consent Request", {
	setup(frm) {
		frm.set_query("school", () => ({
			filters: {
				organization: frm.doc.organization || "",
			},
		}));
	},
	refresh(frm) {
		if (frm.is_new() || !frm.doc.name || frm.doc.status !== "Draft") return;

		frm.add_custom_button(__("Publish Request"), async () => {
			const response = await frappe.call({
				method: "ifitwala_ed.api.family_consent_staff.publish_family_consent_request",
				args: {
					family_consent_request: frm.doc.name,
				},
			});

			const payload = response?.message || {};
			if (!payload.ok) return;

			frappe.show_alert({
				message:
					payload.status === "already_published"
						? __("Request was already published.")
						: __("Request published."),
				indicator: payload.status === "already_published" ? "orange" : "green",
			});
			await frm.reload_doc();
		});
	},
});
