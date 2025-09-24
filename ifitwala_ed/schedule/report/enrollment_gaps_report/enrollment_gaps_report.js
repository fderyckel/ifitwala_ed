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
				// Limit choices to user's default school subtree once we know the root
				const root = frappe.query_report.__root_school || null;
				return root
					? {
							query: "ifitwala_ed.utilities.school_tree.get_school_descendants",
							filters: { root }
						}
					: {}; // before root is known, fall back to default query
			},
			on_change: () => {
				// Clear AY when school changes (if AY filter is mounted)
				const ay_filter = frappe.query_report.get_filter("academic_year");
				if (ay_filter) {
					ay_filter.set_value("");
					ay_filter.refresh();
				}
				// optional: trigger a refresh if both filters are set
				frappe.query_report.refresh();
			}
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year",
			reqd: 1,
			get_query: () => {
				const school = frappe.query_report.get_filter_value("school");
				return {
					query: "ifitwala_ed.schedule.report.enrollment_gaps_report.enrollment_gaps_report.academic_year_link_query",
					filters: { school }
				};
			}
			// IMPORTANT: no depends_on here; keep the filter mounted always
		}
	],

	onload() {
		// Ensure filters exist before manipulating them
		const school_filter = frappe.query_report.get_filter("school");
		const ay_filter = frappe.query_report.get_filter("academic_year");

		// Fetch default school, then set it if empty
		frappe.call({
			method: "ifitwala_ed.utilities.school_tree.get_user_default_school"
		}).then(r => {
			const user_default = r && r.message ? r.message : null;
			if (!user_default) return;

			// cache root for schooling subtree queries
			frappe.query_report.__root_school = user_default;

			// Set default school only if user hasn't chosen one yet
			if (school_filter && !school_filter.get_value()) {
				school_filter.set_value(user_default);
				// refresh school filter so its get_query picks up the new root
				school_filter.refresh();
			}

			// Now that school is known, refresh AY filter’s query safely
			if (ay_filter) {
				ay_filter.refresh();
			}
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
		const centerAligned = ["term", "program", "missing"];
		if (centerAligned.includes(column.fieldname)) {
			value = `<div style="text-align: center;">${value}</div>`;
		}
		const leftAligned = ["type", "student", "student_name", "course"];
		if (leftAligned.includes(column.fieldname)) {
			value = `<div style="text-align: left;">${value}</div>`;
		}
		return value;
	}
};

