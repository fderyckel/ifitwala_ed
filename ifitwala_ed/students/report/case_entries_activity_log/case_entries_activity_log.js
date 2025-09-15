// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// ifitwala_ed/students/report/case_entries_activity_log/case_entries_activity_log.js

/* global frappe */

frappe.query_reports["Case Entries Activity Log"] = {
	// ---------- top filter bar ----------
	filters: [
		{ fieldname: "from_date",     label: __("From Date"),     fieldtype: "Date" },
		{ fieldname: "to_date",       label: __("To Date"),       fieldtype: "Date" },
		{ fieldname: "student",       label: __("Student"),       fieldtype: "Link",  options: "Student" },
		{ fieldname: "referral",      label: __("Referral"),      fieldtype: "Link",  options: "Student Referral" },
		{ fieldname: "school",        label: __("School"),        fieldtype: "Link",  options: "School" },
		{ fieldname: "program",       label: __("Program"),       fieldtype: "Link",  options: "Program" },
		{ fieldname: "academic_year", label: __("Academic Year"), fieldtype: "Link",  options: "Academic Year" },
		{ fieldname: "case_manager",  label: __("Case Manager"),  fieldtype: "Link",  options: "User" },
		{ fieldname: "assignee",      label: __("Entry Assignee"),fieldtype: "Link",  options: "User" },
		{ fieldname: "entry_type",    label: __("Entry Type"),    fieldtype: "Select",
			options: "\nMeeting\nCounseling Session\nAcademic Support\nCheck-in\nFamily Contact\nExternal Referral\nSafety Plan\nReview\nOther" },
		{ fieldname: "entry_status",  label: __("Entry Status"),  fieldtype: "Select",
			options: "\nOpen\nIn Progress\nDone\nCancelled" },
		{ fieldname: "case_severity", label: __("Case Severity"), fieldtype: "Select",
			options: "\nLow\nModerate\nHigh\nCritical" },
		{ fieldname: "case_status",   label: __("Case Status"),   fieldtype: "Select",
			options: "\nOpen\nIn Progress\nOn Hold\nEscalated\nClosed" },
		// The only toggle we keep
		{ fieldname: "time_bucket",   label: __("Time Bucket"),   fieldtype: "Select",
			options: "Week\nMonth", default: "Week",
			on_change: () => frappe.query_report.refresh()
		}
	],

	// ---------- header Print button ----------
	onload(report) {
		const page = report.page;
		ensure_print_button(page);
	},

	// ---------- no custom footer UI; just keep the button after reruns ----------
	after_datatable_render(datatable) {
		const page = (frappe.query_report && frappe.query_report.page) || null;
		if (page) {
			ensure_print_button(page);
		}
		// Intentionally no DOM work here (no extra charts/boxes)
	},
};


// ---------- helpers (print) ----------
function ensure_print_button(page) {
	const BTN_KEY = "cea-print-btn";

	// Avoid duplicates
	if (page.inner_toolbar && page.inner_toolbar.find(`button[data-key="${BTN_KEY}"]`).length) {
		return;
	}

	// Blue button (Bootstrap 4)
	const $btn = page.add_inner_button(__("Print"), () => handle_report_print(), null);
	if ($btn) {
		$btn.attr("data-key", BTN_KEY);
		$btn.removeClass("btn-default").addClass("btn-info");
	}
}

function handle_report_print() {
	const qr = frappe.query_report;
	if (!qr || typeof qr.print_report !== "function") {
		frappe.msgprint(__("Print is not available on this report."));
		return;
	}

	// Open the standard Print Settings dialog and pass the settings to print_report
	frappe.ui.get_print_settings(
		false, // with_letterhead handled in dialog
		(print_settings) => {
			try {
				print_settings = print_settings || {};
				if (!print_settings.orientation) {
					print_settings.orientation = "Landscape";
				}
				qr.print_report(print_settings);
			} catch (e) {
				console.error(e);
				frappe.msgprint(__("Print failed. Please try the ⋮ menu or check permissions."));
			}
		},
		qr.report_doc && qr.report_doc.letter_head,
		qr.get_visible_columns ? qr.get_visible_columns() : null
	);
}
