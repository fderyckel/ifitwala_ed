// ifitwala_ed/schedule/report/enrollment_gaps_report/enrollment_gaps_report.js


frappe.query_reports["Enrollment Gaps Report"] = {
	filters: [
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School",
			reqd: 1,
			// We scope the school choices to the user's default school subtree.
			get_query: () => {
				const root = frappe.query_report.__root_school || null;
				return root
					? {
							query: "ifitwala_ed.utilities.school_tree.get_school_descendants",
							filters: { root }
						}
					: {}; // empty until we fetch default
			},
			on_change: () => {
				// When school changes, clear AY and re-run with a fresh AY query
				const ay_filter = frappe.query_report.get_filter("academic_year");
				ay_filter.set_value("");
				ay_filter.refresh();
				frappe.query_report.refresh(); // optional; keeps UI in sync
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
			},
			depends_on: "eval:!!doc.school"
		}
	],

	onload() {
		// 1) Fetch and set default school
		frappe.call({
			method: "ifitwala_ed.utilities.school_tree.get_user_default_school"
		}).then(r => {
			const user_default = r && r.message ? r.message : null;
			if (!user_default) return;
			frappe.query_report.__root_school = user_default;

			// Set default school if empty
			const school_filter = frappe.query_report.get_filter("school");
			if (!school_filter.get_value()) {
				school_filter.set_value(user_default);
			}

			// Force the School filter to use the descendant-scoped query now that we know the root
			school_filter.refresh();

			// Also refresh AY’s query (it depends on School)
			const ay_filter = frappe.query_report.get_filter("academic_year");
			ay_filter.refresh();
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

