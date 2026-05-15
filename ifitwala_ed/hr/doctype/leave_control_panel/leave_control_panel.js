// ifitwala_ed/hr/doctype/leave_control_panel/leave_control_panel.js

frappe.ui.form.on("Leave Control Panel", {
	setup(frm) {
		frm.trigger("set_query");
		frm.trigger("set_leave_details");
	},

	refresh(frm) {
		frm.disable_save();
		frm.trigger("get_employees");
		frm.trigger("set_primary_action");
	},

	organization(frm) {
		if (frm.doc.organization) {
			frm.set_query("department", () => ({
				filters: { organization: frm.doc.organization },
			}));
		}
		frm.trigger("get_employees");
	},

	employment_type(frm) {
		frm.trigger("get_employees");
	},

	department(frm) {
		frm.trigger("get_employees");
	},

	designation(frm) {
		frm.trigger("get_employees");
	},

	dates_based_on(frm) {
		frm.trigger("reset_leave_details");
		frm.trigger("get_employees");
	},

	from_date(frm) {
		frm.trigger("get_employees");
	},

	to_date(frm) {
		frm.trigger("get_employees");
	},

	leave_period(frm) {
		frm.trigger("get_employees");
	},

	allocate_based_on_leave_policy(frm) {
		frm.trigger("get_employees");
	},

	leave_type(frm) {
		frm.trigger("get_employees");
	},

	leave_policy(frm) {
		frm.trigger("get_employees");
	},

	reset_leave_details(frm) {
		if (frm.doc.dates_based_on === "Leave Period") {
			frm.add_fetch("leave_period", "from_date", "from_date");
			frm.add_fetch("leave_period", "to_date", "to_date");
		}
	},

	set_leave_details(frm) {
		frm.call("get_latest_leave_period").then((r) => {
			frm.set_value({
				dates_based_on: "Leave Period",
				from_date: frappe.datetime.get_today(),
				to_date: null,
				leave_period: r.message,
				carry_forward: 1,
				allocate_based_on_leave_policy: 1,
				leave_type: null,
				no_of_days: 0,
				leave_policy: null,
				organization: frappe.defaults.get_default("organization"),
			});
		});
	},

	get_employees(frm) {
		frm.call({
			method: "get_employees",
			args: {
				advanced_filters: frm.advanced_filters || [],
			},
			doc: frm.doc,
		}).then((r) => {
			frm._employees = r.message || [];
			frm.page.set_indicator(__("Employees: {0}", [frm._employees.length]), "blue");
		});
	},

	set_query(frm) {
		frm.set_query("leave_policy", () => ({
			filters: { docstatus: 1 },
		}));
		frm.set_query("leave_period", () => ({
			filters: { is_active: 1 },
		}));
	},

	set_primary_action(frm) {
		frm.page.set_primary_action(__("Allocate Leave"), () => {
			frm.trigger("allocate_leave");
		});
	},

	allocate_leave(frm) {
		const selected = (frm._employees || []).map((row) => row.name);
		if (!selected.length) {
			frappe.msgprint(__("No employees match the selected filters."));
			return;
		}

		frappe.confirm(
			__("Allocate leaves to {0} employee(s)?", [selected.length]),
			() => frm.events.bulk_allocate_leave(frm, selected),
		);
	},

	bulk_allocate_leave(frm, employees) {
		frm.call({
			method: "allocate_leave",
			doc: frm.doc,
			args: {
				employees: employees,
			},
			freeze: true,
			freeze_message: __("Allocating Leave"),
		}).then(() => {
			frm.refresh();
		});
	},
});
