// ifitwala_ed/hr/doctype/leave_application/leave_application.js

frappe.ui.form.on("Leave Application", {
	setup(frm) {
		frm.set_query("leave_approver", () => ({
			filters: { enabled: 1 },
		}));
	},

	onload(frm) {
		frm.ignore_doctypes_on_cancel_all = ["Leave Ledger Entry", "Employee Attendance"];
		if (!frm.doc.posting_date) {
			frm.set_value("posting_date", frappe.datetime.get_today());
		}
		if (!frm.doc.employee) {
			frappe.call("ifitwala_ed.hr.leave_api.get_current_employee_info").then((r) => {
				if (r.message?.name) {
					frm.set_value("employee", r.message.name);
				}
			});
		}
	},

	refresh(frm) {
		if (frm.is_new()) {
			frm.trigger("calculate_total_days");
		}
	},

	validate(frm) {
		if (frm.doc.from_date === frm.doc.to_date && cint(frm.doc.half_day)) {
			frm.doc.half_day_date = frm.doc.from_date;
		} else if (!cint(frm.doc.half_day)) {
			frm.doc.half_day_date = "";
		}
		frm.toggle_reqd("half_day_date", cint(frm.doc.half_day));
	},

	employee(frm) {
		frm.trigger("set_leave_approver");
		frm.trigger("get_leave_balance");
		frm.trigger("calculate_total_days");
	},

	leave_type(frm) {
		frm.trigger("get_leave_balance");
		frm.trigger("calculate_total_days");
	},

	half_day(frm) {
		if (!frm.doc.half_day) {
			frm.set_value("half_day_date", "");
		}
		frm.trigger("calculate_total_days");
	},

	from_date(frm) {
		frm.trigger("calculate_total_days");
	},

	to_date(frm) {
		frm.trigger("calculate_total_days");
	},

	half_day_date(frm) {
		frm.trigger("calculate_total_days");
	},

	leave_approver(frm) {
		if (frm.doc.leave_approver) {
			frm.set_value("leave_approver_name", frappe.user.full_name(frm.doc.leave_approver));
		}
	},

	set_leave_approver(frm) {
		if (!frm.doc.employee) return;
		frappe.call({
			method: "ifitwala_ed.hr.doctype.leave_application.leave_application.get_leave_approver",
			args: { employee: frm.doc.employee },
			callback: (r) => {
				if (r.message) frm.set_value("leave_approver", r.message);
			},
		});
	},

	get_leave_balance(frm) {
		if (!(frm.doc.employee && frm.doc.leave_type && frm.doc.from_date && frm.doc.to_date)) return;
		frappe.call({
			method: "ifitwala_ed.hr.doctype.leave_application.leave_application.get_leave_balance_on",
			args: {
				employee: frm.doc.employee,
				date: frm.doc.from_date,
				to_date: frm.doc.to_date,
				leave_type: frm.doc.leave_type,
				consider_all_leaves_in_the_allocation_period: 1,
			},
			callback: (r) => {
				if (!r.exc) frm.set_value("leave_balance", r.message || 0);
			},
		});
	},

	calculate_total_days(frm) {
		if (!(frm.doc.from_date && frm.doc.to_date && frm.doc.employee && frm.doc.leave_type)) return;
		frappe.call({
			method: "ifitwala_ed.hr.doctype.leave_application.leave_application.get_number_of_leave_days",
			args: {
				employee: frm.doc.employee,
				leave_type: frm.doc.leave_type,
				from_date: frm.doc.from_date,
				to_date: frm.doc.to_date,
				half_day: frm.doc.half_day,
				half_day_date: frm.doc.half_day_date,
			},
			callback: (r) => {
				if (r?.message !== undefined) {
					frm.set_value("total_leave_days", r.message);
					frm.trigger("get_leave_balance");
				}
			},
		});
	},
});
