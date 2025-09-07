// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Student Referral"] = {
	add_fields: ["referral_case", "sla_due"],

	onload(list) {
		const me = frappe.session.user;
		const privileged = frappe.user.has_role(["Counselor", "Academic Admin", "System Manager"]);

		if (privileged) {
			// Needs Triage (All)
			list.page.add_inner_button(__("Needs Triage (All)"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.run();
			}).removeClass("btn-default").addClass("btn-warning"); // orange

			// SLA Breached (All) – use actual timestamp, make button red
			const breachAllBtn = list.page.add_inner_button(__("SLA Breached (All)"), () => {
				const now = frappe.datetime.now_datetime(); // "YYYY-MM-DD HH:mm:ss"
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.filter_area.add([["Student Referral", "sla_due", "<", now]]);
				list.run();
			});
			breachAllBtn.removeClass("btn-default").addClass("btn-danger"); // red
		} else {
			// Author-focused views for teachers/instructors
			list.page.add_inner_button(__("My Referrals – Needs Triage"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "owner", "=", me]]);
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.run();
			}).removeClass("btn-default").addClass("btn-warning");

			list.page.add_inner_button(__("My Referrals – SLA Breached"), () => {
				const now = frappe.datetime.now_datetime();
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "owner", "=", me]]);
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.filter_area.add([["Student Referral", "sla_due", "<", now]]);
				list.run();
			}).removeClass("btn-default").addClass("btn-danger");
		}
	},

	get_indicator(doc) {
		// Submitted + no case => Needs Triage
		if (doc.docstatus === 1 && !doc.referral_case) {
			const overdue = !!doc.sla_due &&
				frappe.datetime.get_hour_diff(frappe.datetime.now_datetime(), doc.sla_due) > 0;

			if (overdue) {
				// Build a concrete filter string with current timestamp
				const now = frappe.datetime.now_datetime();
				return [
					__("Needs Triage (SLA Breached)"),
					"red",
					`docstatus,=,1|referral_case,is,not set|sla_due,<,${now}`
				];
			}
			return [__("Needs Triage"), "orange", "docstatus,=,1|referral_case,is,not set"];
		}

		// Case opened
		if (doc.referral_case) {
			return [__("Case Opened"), "green", "referral_case,is,set"];
		}

		// Drafts (BLUE)
		return [__("Draft"), "blue", "docstatus,=,0"];
	}
};
