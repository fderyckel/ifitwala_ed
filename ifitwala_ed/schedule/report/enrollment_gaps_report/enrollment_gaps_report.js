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
				// Limit choices to the user's default school subtree, once we know it
				const root = frappe.query_report.__root_school || null;
				return root
					? {
							query: "ifitwala_ed.utilities.school_tree.get_school_descendants",
							filters: { root }
						}
					: {};
			},
			on_change: () => {
				// Changing school invalidates the AY scope; clear it
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
				// AY options are constrained to the selected school's ancestor chain
				const school = frappe.query_report.get_filter_value("school") || "";
				return {
					query: "ifitwala_ed.schedule.report.enrollment_gaps_report.enrollment_gaps_report.academic_year_link_query",
					filters: { school }
				};
			}
		}
	],

	onload() {
		// Prefill School with the user's default, then refresh AY query
		frappe.after_ajax(() => {
			const school = frappe.query_report.get_filter("school");
			const ay = frappe.query_report.get_filter("academic_year");

			frappe.call({
				method: "ifitwala_ed.utilities.school_tree.get_user_default_school"
			}).then(r => {
				const user_default = (r && r.message) || null;
				if (!user_default) return;

				frappe.query_report.__root_school = user_default;

				if (school && !school.get_value()) {
					school.set_value(user_default);
					school.refresh();
				}
				if (ay) ay.refresh();
			});
		});
	},

	formatter(value, row, column, data, default_formatter) {
		// Keep native formatter behavior first
		value = default_formatter(value, row, column, data);

		// Emphasis on "Type" based on server labels
		if (column.fieldname === "type" && data) {
			if (data.type === "Missing Program Enrollment") {
				value = `<span style="color: rgba(220,53,69,.8); font-weight: 600;">${value}</span>`;
			} else if (data.type === "Missing Student Group") {
				value = `<span style="color: rgba(255,140,0,.9); font-weight: 600;">${value}</span>`;
			}
		}

		// Light emphasis on the Missing column
		if (column.fieldname === "missing") {
			value = `<span style="font-weight: 600;">${value}</span>`;
		}

		// Alignments to improve scanability
		const centerAligned = new Set(["program_offering", "term", "missing"]);
		const leftAligned = new Set(["type", "student", "student_name", "course"]);

		if (centerAligned.has(column.fieldname)) {
			value = `<div style="text-align:center;">${value}</div>`;
		} else if (leftAligned.has(column.fieldname)) {
			value = `<div style="text-align:left;">${value}</div>`;
		}

		return value;
	}
};
