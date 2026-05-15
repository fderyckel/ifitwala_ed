// ifitwala_ed/hr/doctype/leave_allocation/leave_allocation.js

cur_frm.add_fetch("employee", "employee_full_name", "employee_full_name");

frappe.ui.form.on("Leave Allocation", {
	onload(frm) {
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry"];
		if (!frm.doc.from_date) frm.set_value("from_date", frappe.datetime.get_today());
		frm.set_query("leave_type", () => ({ filters: { is_lwp: 0 } }));
	},

	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.expired) {
			const today = moment(frappe.datetime.get_today());
			const valid_expiry = today.isBetween(frm.doc.from_date, frm.doc.to_date);
			if (valid_expiry) {
				frm.add_custom_button(__("Expire Allocation"), () => {
					frappe.confirm(__("Are you sure you want to expire this allocation?"), () => {
						frm.trigger("expire_allocation");
					});
				}, __("Actions"));
			}
		}
		frm.trigger("toggle_retry_button");
	},

	expire_allocation(frm) {
		frappe.call({
			method: "ifitwala_ed.hr.doctype.leave_ledger_entry.leave_ledger_entry.expire_allocation",
			args: {
				allocation: frm.doc,
				expiry_date: frappe.datetime.get_today(),
			},
			freeze: true,
			callback(r) {
				if (!r.exc) frappe.msgprint(__("Allocation Expired"));
				frm.refresh();
			},
		});
	},

	employee(frm) {
		frm.trigger("calculate_total_leaves_allocated");
	},

	leave_type(frm) {
		frm.trigger("leave_policy");
		frm.trigger("calculate_total_leaves_allocated");
	},

	carry_forward(frm) {
		frm.trigger("calculate_total_leaves_allocated");
	},

	unused_leaves(frm) {
		frm.set_value("total_leaves_allocated", flt(frm.doc.unused_leaves) + flt(frm.doc.new_leaves_allocated));
	},

	new_leaves_allocated(frm) {
		frm.set_value("total_leaves_allocated", flt(frm.doc.unused_leaves) + flt(frm.doc.new_leaves_allocated));
	},

	leave_policy(frm) {
		if (!(frm.doc.leave_policy && frm.doc.leave_type)) return;
		frappe.db.get_value(
			"Leave Policy Detail",
			{ parent: frm.doc.leave_policy, leave_type: frm.doc.leave_type },
			"annual_allocation",
			(r) => {
				if (r && !r.exc) frm.set_value("new_leaves_allocated", flt(r.annual_allocation));
			},
			"Leave Policy",
		);
	},

	toggle_retry_button(frm) {
		const earned_leave_schedule = frm.doc.earned_leave_schedule || [];
		const toggle_button =
			earned_leave_schedule.some((row) => row.attempted && row.failed) && frm.perm[0]?.write;
		frm.toggle_display("retry_failed_allocations", toggle_button);
	},

	retry_failed_allocations(frm) {
		const failed_allocations = (frm.doc.earned_leave_schedule || []).filter(
			(row) => row.attempted && row.failed,
		);
		frappe.call({
			method: "retry_failed_allocations",
			doc: frm.doc,
			args: { failed_allocations },
			freeze: true,
			freeze_message: __("Retrying allocations"),
			callback() {
				frappe.show_alert({ message: __("Retry Successful"), indicator: "green" });
				frm.reload_doc();
			},
		});
	},

	calculate_total_leaves_allocated(frm) {
		if (cint(frm.doc.carry_forward) !== 1 || !(frm.doc.leave_type && frm.doc.employee)) return;
		frappe.call({
			method: "set_total_leaves_allocated",
			doc: frm.doc,
			freeze: true,
			callback() {
				frm.refresh_field("new_leaves_allocated");
				frm.refresh_field("unused_leaves");
				frm.refresh_field("total_leaves_allocated");
			},
		});
	},
});
