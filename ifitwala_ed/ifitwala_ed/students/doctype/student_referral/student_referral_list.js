// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Student Referral"] = {
	// add the manager mirror so non-privileged users can see case-open state
	add_fields: ["referral_case", "assigned_case_manager", "sla_due"],

	onload(list) {
		const me = frappe.session.user;
		// Policy: System Manager is NOT privileged here
		const privileged = frappe.user.has_role(["Counselor"]);

		if (privileged) {
			// Needs Triage (All)
			list.page.add_inner_button(__("Needs Triage (All)"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				// case not open yet
				list.filter_area.add([["Student Referral", "assigned_case_manager", "is", "not set"]]);
				list.run();
			}).removeClass("btn-default").addClass("btn-warning");

			// SLA Breached (All)
			const breachAllBtn = list.page.add_inner_button(__("SLA Breached (All)"), () => {
				const now = frappe.datetime.now_datetime();
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "assigned_case_manager", "is", "not set"]]);
				list.filter_area.add([["Student Referral", "sla_due", "<", now]]);
				list.run();
			});
			breachAllBtn.removeClass("btn-default").addClass("btn-danger");
		} else {
			// Author-focused views for teachers/instructors
			list.page.add_inner_button(__("My Referrals – Needs Triage"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "owner", "=", me]]);
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "assigned_case_manager", "is", "not set"]]);
				list.run();
			}).removeClass("btn-default").addClass("btn-warning");

			list.page.add_inner_button(__("My Referrals – SLA Breached"), () => {
				const now = frappe.datetime.now_datetime();
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "owner", "=", me]]);
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "assigned_case_manager", "is", "not set"]]);
				list.filter_area.add([["Student Referral", "sla_due", "<", now]]);
				list.run();
			}).removeClass("btn-default").addClass("btn-danger");
		}
	},

	get_indicator(doc) {
		// treat case as opened if either the link is present (privileged)
		// OR a case manager has been mirrored (works for everyone)
		const has_case = !!doc.referral_case || !!doc.assigned_case_manager;

		// Submitted + no case => Needs Triage
		if (doc.docstatus === 1 && !has_case) {
			const overdue = !!doc.sla_due &&
				frappe.datetime.get_hour_diff(frappe.datetime.now_datetime(), doc.sla_due) > 0;

			if (overdue) {
				const now = frappe.datetime.now_datetime();
				return [
					__("Needs Triage (SLA Breached)"),
					"red",
					// use assigned_case_manager to make the filter useful for non-privileged users
					`docstatus,=,1|assigned_case_manager,is,not set|sla_due,<,${now}`
				];
			}
			return [__("Needs Triage"), "orange", "docstatus,=,1|assigned_case_manager,is,not set"];
		}

		// Case opened (use the manager mirror for the filter)
		if (has_case) {
			return [__("Case Opened"), "green", "assigned_case_manager,is,set|docstatus,=,1"];
		}

		// Drafts (BLUE)
		return [__("Draft"), "blue", "docstatus,=,0"];
	}
};
