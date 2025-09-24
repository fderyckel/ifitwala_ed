// ifitwala_ed/schedule/report/enrollment_gaps_report/enrollment_gaps_report.js

frappe.query_reports["Enrollment Gaps Report"] = {
	filters: [
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
			reqd: 1,
			get_query: () => {
				// Show only user's default school + its descendants
				const root = frappe.query_report.__root_school || null;
				return root
					? {
							query: "ifitwala_ed.utilities.school_tree.get_school_descendants",
							filters: { root }
						}
					: {}; // until root is known, fall back to default picker
			},
			on_change: () => {
				// Clear AY when school changes (no immediate refresh to avoid race)
				const ay = frappe.query_report.get_filter("academic_year");
				if (ay) {
					ay.set_value("");
					ay.refresh();
				}
			}
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
			get_query: () => {
				// Only AY whose school == selected school
				const school = frappe.query_report.get_filter_value("school") || "";
				return {
					query: "ifitwala_ed.schedule.report.enrollment_gaps_report.enrollment_gaps_report.academic_year_link_query",
					filters: { school }
				};
			}
		}
	],

	onload() {
		// Wait until controls are mounted, then set defaults
		frappe.after_ajax(() => {
			const school = frappe.query_report.get_filter("school");
			const ay = frappe.query_report.get_filter("academic_year");

			frappe.call({
				method: "ifitwala_ed.utilities.school_tree.get_user_default_school"
			}).then(r => {
				const user_default = r && r.message ? r.message : null;
				if (!user_default) return;

				frappe.query_report.__root_school = user_default;

				if (school && !school.get_value()) {
					school.set_value(user_default);
					school.refresh(); // rebind School's scoped query
				}
				if (ay) ay.refresh(); // now that School is known, refresh AY's query
			});
		});
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "type") {
			if (data.type === "Missing Program") {
				value = `<span style="color: rgba(220, 53, 69, 0.65); font-weight: bold;">${value}</span>`;
			} else if (data.type === "Missing Student Group") {
				value = `<span style="color: rgba(255, 140, 0, 0.65); font-weight: bold;">${value}</span>`;
			}
		}
		const centerAligned = ["term", "program_offering", "missing"];

		if (centerAligned.includes(column.fieldname)) {
			value = `<div style="text-align: center;">${value}</div>`;
		}
		const leftAligned   = ["type", "student", "student_name", "course"];
		if (leftAligned.includes(column.fieldname)) {
			value = `<div style="text-align: left;">${value}</div>`;
		}
		return value;
	}
};
