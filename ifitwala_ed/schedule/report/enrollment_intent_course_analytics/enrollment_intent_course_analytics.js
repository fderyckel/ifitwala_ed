// Copyright (c) 2026, Francois de Ryckel and contributors
// For license information, please see license.txt

async function refreshSchoolScope(report) {
	const school = report.get_filter_value("school") || "";
	if (!school) {
		frappe.query_report.__school_scope = [];
		return;
	}

	const response = await frappe.call({
		method: "ifitwala_ed.utilities.school_tree.get_descendant_schools",
		args: { user_school: school }
	});

	frappe.query_report.__school_scope = response.message || [school];
	const programOfferingFilter = report.get_filter("program_offering");
	if (programOfferingFilter) {
		programOfferingFilter.refresh();
	}
}

function getIndicatorColor(value, mapping, fallback = "gray") {
	return mapping[String(value || "").trim()] || fallback;
}

frappe.query_reports["Enrollment Intent Course Analytics"] = {
	filters: [
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
			reqd: 1,
			get_query() {
				return {
					filters: {
						name: ["in", frappe.query_report.__allowed_schools || []]
					}
				};
			},
			async on_change() {
				const report = frappe.query_report;
				const programOffering = report.get_filter("program_offering");
				if (programOffering) {
					programOffering.set_value("");
				}
				await refreshSchoolScope(report);
			}
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
			get_query() {
				const school = frappe.query_report.get_filter_value("school") || "";
				return {
					query: "ifitwala_ed.schedule.report.enrollment_gaps_report.enrollment_gaps_report.academic_year_link_query",
					filters: { school }
				};
			}
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program",
			on_change() {
				const programOffering = frappe.query_report.get_filter("program_offering");
				if (programOffering) {
					programOffering.set_value("");
				}
			}
		},
		{
			fieldname: "program_offering",
			label: __("Program Offering"),
			fieldtype: "Link",
			options: "Program Offering",
			get_query() {
				const filters = {};
				const program = frappe.query_report.get_filter_value("program");
				const schoolScope = frappe.query_report.__school_scope || [];
				if (program) {
					filters.program = program;
				}
				if (schoolScope.length) {
					filters.school = ["in", schoolScope];
				}
				return { filters };
			}
		},
		{
			fieldname: "selection_window",
			label: __("Selection Window"),
			fieldtype: "Link",
			options: "Program Offering Selection Window",
			get_query() {
				const filters = {};
				const schoolScope = frappe.query_report.__school_scope || [];
				const academicYear = frappe.query_report.get_filter_value("academic_year");
				const programOffering = frappe.query_report.get_filter_value("program_offering");
				if (schoolScope.length) {
					filters.school = ["in", schoolScope];
				}
				if (academicYear) {
					filters.academic_year = academicYear;
				}
				if (programOffering) {
					filters.program_offering = programOffering;
				}
				return { filters };
			}
		},
		{
			fieldname: "request_status",
			label: __("Request Status"),
			fieldtype: "Select",
			options: __("\nDraft\nSubmitted\nUnder Review\nApproved\nRejected\nCancelled")
		},
		{
			fieldname: "validation_status",
			label: __("Validation"),
			fieldtype: "Select",
			options: __("\nNot Validated\nValid\nInvalid")
		},
		{
			fieldname: "enrollment_intent",
			label: __("Enrollment Intent"),
			fieldtype: "Select",
			options: __("\nIntends to Enroll\nDoes Not Intend to Enroll\nUndecided\nNo Response\nNot Collected"),
			default: "Intends to Enroll"
		},
		{
			fieldname: "latest_request_only",
			label: __("Latest Request Only"),
			fieldtype: "Check",
			default: 1
		}
	],

	async onload(report) {
		report.page.set_title(__("Enrollment Intent Course Analytics"));
		const response = await frappe.call({
			method: "ifitwala_ed.school_settings.school_settings_utils.get_user_allowed_schools"
		});
		const allowedSchools = response.message || [];
		frappe.query_report.__allowed_schools = allowedSchools;

		if (!allowedSchools.length) {
			frappe.msgprint(__("You do not have a default school assigned. Please contact your administrator."));
			return;
		}

		const schoolFilter = report.get_filter("school");
		if (schoolFilter && !schoolFilter.get_value()) {
			schoolFilter.set_value(allowedSchools[0]);
		}
		if (schoolFilter) {
			schoolFilter.df.read_only = allowedSchools.length === 1 ? 1 : 0;
			schoolFilter.refresh();
		}

		await refreshSchoolScope(report);
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "intent_students" && data) {
			const color = getIndicatorColor(
				data.intent_students > 0 ? "has-demand" : "none",
				{ "has-demand": "green", none: "gray" }
			);
			return `<span class="indicator-pill ${color}">${frappe.utils.escape_html(String(data.intent_students || 0))}</span>`;
		}
		if (column.fieldtype === "Int" && value !== undefined && value !== null && value !== "") {
			return `<div class="text-end">${value}</div>`;
		}
		return value;
	}
};
