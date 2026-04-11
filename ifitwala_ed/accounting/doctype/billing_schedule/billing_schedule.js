frappe.ui.form.on("Billing Schedule", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status !== "Cancelled") {
			frm.add_custom_button(__("Generate Draft Invoice"), async () => {
				const r = await frappe.call(
					"ifitwala_ed.accounting.doctype.billing_schedule.billing_schedule.generate_draft_invoice",
					{ billing_schedule: frm.doc.name }
				);
				if (r.message?.sales_invoice) {
					frappe.set_route("Form", "Sales Invoice", r.message.sales_invoice);
				}
			});
		}
	},
});
