frappe.ui.form.on("Payment Request", {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.status === "Draft") {
			frm.add_custom_button(__("Mark Sent"), async () => {
				await frappe.call(
					"ifitwala_ed.accounting.doctype.payment_request.payment_request.mark_sent",
					{ name: frm.doc.name }
				);
				await frm.reload_doc();
			});
		}
	},
});
