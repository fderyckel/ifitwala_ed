frappe.ui.form.on("Initial Enrollment Billing Package", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.is_active) {
			frm.add_custom_button(__("Generate Draft Invoices"), async () => {
				const r = await frm.call("generate_draft_invoices");
				const message = r.message || {};
				frappe.msgprint(
					__("Created {0} draft invoices. {1} already existed.", [
						message.created_count || 0,
						message.existing_count || 0,
					])
				);
			});
		}
	},
});
