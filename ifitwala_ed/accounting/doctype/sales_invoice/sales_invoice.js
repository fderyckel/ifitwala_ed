frappe.ui.form.on("Sales Invoice", {
	refresh(frm) {
		if (frm.doc.docstatus === 1) {
			if (!frm.doc.adjustment_type) {
				frm.add_custom_button(__("Create Payment Request"), async () => {
					const r = await frappe.call(
						"ifitwala_ed.accounting.doctype.payment_request.payment_request.create_from_sales_invoice",
						{ sales_invoice: frm.doc.name }
					);
					if (r.message) {
						frappe.set_route("Form", "Payment Request", r.message);
					}
				}, __("Collections"));

				frm.add_custom_button(__("Make Credit Note"), async () => {
					const r = await frappe.call(
						"ifitwala_ed.accounting.doctype.sales_invoice.sales_invoice.make_credit_note",
						{ source_invoice: frm.doc.name }
					);
					if (r.message) {
						frappe.set_route("Form", "Sales Invoice", r.message);
					}
				}, __("Adjustments"));

				frm.add_custom_button(__("Make Debit Note"), async () => {
					const r = await frappe.call(
						"ifitwala_ed.accounting.doctype.sales_invoice.sales_invoice.make_debit_note",
						{ source_invoice: frm.doc.name }
					);
					if (r.message) {
						frappe.set_route("Form", "Sales Invoice", r.message);
					}
				}, __("Adjustments"));
			}
		}
	},
});
