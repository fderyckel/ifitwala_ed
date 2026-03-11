frappe.ui.form.on("Payment Reconciliation", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Load Open Invoices"), async () => {
				await frappe.call(
					"ifitwala_ed.accounting.doctype.payment_reconciliation.payment_reconciliation.load_open_invoices",
					{ name: frm.doc.name }
				);
				await frm.reload_doc();
			});
		}
	},
});
