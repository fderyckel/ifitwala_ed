// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.listview_settings["Student Referral"] = {
	// Ensure these fields are fetched for indicators without extra queries
	add_fields: ["referral_case", "sla_due"],

	onload(list) {
		const me = frappe.session.user;
		const privileged = frappe.user.has_role(["Counselor", "Academic Admin", "System Manager"]);

		if (privileged) {
			// Global triage queues (counselor/admin/system manager)
			list.page.add_inner_button(__("Needs Triage (All)"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.run();
			});

			list.page.add_inner_button(__("SLA Breached (All)"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.filter_area.add([["Student Referral", "sla_due", "<", "Now"]]);
				list.run();
			});
		} else {
			// Author-focused views (teachers/instructors)
			list.page.add_inner_button(__("My Referrals - Needs Triage"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "owner", "=", me]]);
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.run();
			});

			list.page.add_inner_button(__("My Referrals – SLA Breached"), () => {
				list.filter_area.clear();
				list.filter_area.add([["Student Referral", "owner", "=", me]]);
				list.filter_area.add([["Student Referral", "docstatus", "=", 1]]);
				list.filter_area.add([["Student Referral", "referral_case", "is", "not set"]]);
				list.filter_area.add([["Student Referral", "sla_due", "<", "Now"]]);
				list.run();
			});
		}
	},

	get_indicator(doc) {
		// Submitted + no case => Needs Triage
		if (doc.docstatus === 1 && !doc.referral_case) {
			const overdue =
				!!doc.sla_due &&
				frappe.datetime.get_hour_diff(frappe.datetime.now_datetime(), doc.sla_due) > 0;

			if (overdue) {
				return [
					__("Needs Triage (SLA Breached)"),
					"red",
					"docstatus,=,1|referral_case,is,not set|sla_due,<,Now"
				];
			}
			return [
				__("Needs Triage"),
				"orange",
				"docstatus,=,1|referral_case,is,not set"
			];
		}

		// Case opened (treated/triaged)
		if (doc.referral_case) {
			return [
				__("Case Opened"),
				"green",
				"referral_case,is,set"
			];
		}

		// Drafts
		return [__("Draft"), "blue", "docstatus,=,0"];
	}
};

