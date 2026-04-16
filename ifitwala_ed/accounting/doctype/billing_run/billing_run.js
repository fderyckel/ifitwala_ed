frappe.ui.form.on("Billing Run", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Draft") {
			frm.add_custom_button(__("Generate Draft Invoices"), async () => {
				const r = await frappe.call(
					"ifitwala_ed.accounting.doctype.billing_run.billing_run.generate_draft_invoices",
					{ billing_run: frm.doc.name }
				);
				const message = r.message || {};
				frappe.msgprint(
					__(
						"Created {0} draft invoices covering {1} billing rows.",
						[message.invoice_count || 0, message.billing_row_count || 0]
					)
				);
				await frm.reload_doc();
			});
		}
	},
});
