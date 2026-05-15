// ifitwala_ed/hr/doctype/leave_encashment/leave_encashment.js

frappe.ui.form.on("Leave Encashment", {
	onload(frm) {
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry"];
	},

	setup(frm) {
		frm.set_query("leave_type", () => ({ filters: { allow_encashment: 1 } }));
		frm.set_query("leave_period", () => ({ filters: { is_active: 1 } }));
	},

	refresh(frm) {
		if (
			frm.doc.docstatus === 1 &&
			frm.doc.pay_via_payment_entry == 1 &&
			frm.doc.status !== "Paid"
		) {
			frm.add_custom_button(__("Payment"), () => frm.events.make_payment_entry(frm), __("Create"));
		}
	},

	employee(frm) {
		if (!(frm.doc.employee && frm.doc.leave_type)) return;
		frm.trigger("get_leave_details_for_encashment");
	},

	leave_type(frm) {
		frm.trigger("get_leave_details_for_encashment");
	},

	encashment_date(frm) {
		frm.trigger("get_leave_details_for_encashment");
	},

	get_leave_details_for_encashment(frm) {
		frm.set_value("actual_encashable_days", 0);
		frm.set_value("encashment_days", 0);
		if (frm.doc.docstatus !== 0 || !(frm.doc.employee && frm.doc.leave_type)) return;
		frappe.call({
			method: "get_leave_details_for_encashment",
			doc: frm.doc,
			callback() {
				frm.refresh_fields();
			},
		});
	},

	make_payment_entry(frm) {
		frappe.msgprint(
			__("Leave Encashment payment entry automation is not enabled in this phase."),
		);
	},
});
