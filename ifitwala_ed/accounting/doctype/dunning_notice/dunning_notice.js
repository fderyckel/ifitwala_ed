frappe.ui.form.on("Dunning Notice", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Load Overdue Invoices"), async () => {
				await frappe.call(
					"ifitwala_ed.accounting.doctype.dunning_notice.dunning_notice.load_overdue_items",
					{ name: frm.doc.name }
				);
				await frm.reload_doc();
			});

			if ((frm.doc.items || []).length) {
				frm.add_custom_button(__("Create Payment Requests"), async () => {
					await frappe.call(
						"ifitwala_ed.accounting.doctype.dunning_notice.dunning_notice.create_payment_requests",
						{ name: frm.doc.name }
					);
					await frm.reload_doc();
				});
			}

			if (frm.doc.status === "Draft") {
				frm.add_custom_button(__("Mark Sent"), async () => {
					await frappe.call(
						"ifitwala_ed.accounting.doctype.dunning_notice.dunning_notice.mark_sent",
						{ name: frm.doc.name }
					);
					await frm.reload_doc();
				});
			}
		}
	},
});
