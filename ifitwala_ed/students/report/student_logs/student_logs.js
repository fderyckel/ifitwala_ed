// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Ifitwala Ed - Student Log + Follow-ups (Report JS)

/* global frappe */

frappe.query_reports["Student Log + Follow-ups"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30),
			reqd: 1
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1
		},
		{
			fieldname: "student",
			label: __("Student"),
			fieldtype: "Link",
			options: "Student"
		},
		{
			fieldname: "program",
			label: __("Program"),
			fieldtype: "Link",
			options: "Program"
		},
		{
			fieldname: "school",
			label: __("School"),
			fieldtype: "Link",
			options: "School"
		},
		{
			fieldname: "academic_year",
			label: __("Academic Year"),
			fieldtype: "Link",
			options: "Academic Year"
		},
		{
			fieldname: "log_type",
			label: __("Log Type"),
			fieldtype: "Link",
			options: "Student Log Type"
		},
		{
			fieldname: "follow_up_status",
			label: __("Follow-up Status"),
			fieldtype: "Select",
			options: ["", "Open", "In Progress", "Closed"]
		},
		{
			fieldname: "requires_follow_up",
			label: __("Requires Follow-up"),
			fieldtype: "Check"
		},
		{
			fieldname: "author",
			label: __("Author (Log)"),
			fieldtype: "Link",
			options: "User"
		},
		{
			fieldname: "fu_author",
			label: __("Author (Follow-up)"),
			fieldtype: "Link",
			options: "User"
		},
		// NEW: view mode toggle (client-only)
		{
			fieldname: "view_mode",
			label: __("View"),
			fieldtype: "Select",
			options: ["Compact", "Full"],
			default: "Compact"
		}
	],

	onload(report) {
		inject_compact_css_once();
		// re-render when switching view mode
		report.page.wrapper.on("change", 'select[data-fieldname="view_mode"]', () => {
			frappe.query_report.refresh();
		});
	},

	after_datatable_render(report) {
		apply_view_mode_class(report);
		shorten_header_labels(report);
	},

	formatter(value, row, column, data, default_formatter) {
		let val = default_formatter(value, row, column, data);
		const mode = (frappe.query_report.get_filter_value("view_mode") || "Compact").trim();

		// status badge
		if (column.fieldname === "follow_up_status" && value) {
			let color = "secondary";
			if (value === "In Progress") color = "primary";
			if (value === "Closed") color = "dark";
			return `<span class="badge bg-${color}">${value}</span>`;
		}

		// visibility icons
		if (column.fieldname === "visibility" && value) {
			return `<span style="font-size:1.1em;opacity:.9">${value}</span>`;
		}

		// grouped view helpers
		const followupFields = new Set(["follow_up_id","fu_date","fu_author","follow_up_snippet"]);

		// Child rows: hide non-follow-up columns to reduce noise
		if (data && data.indent === 1 && !followupFields.has(column.fieldname)) {
			return "";
		}

		// Snippet cells → ellipsis + native tooltip
		if (column.fieldname === "log_snippet" || column.fieldname === "follow_up_snippet") {
			if (!value) return val;
			const safe = frappe.utils.escape_html(value);
			const wide = column.fieldname === "follow_up_snippet" ? " wide" : "";
			return `<span class="report-cell-ellipsis${wide}" title="${safe}">${safe}</span>`;
		}

		// Compact mode: visually de-emphasize secondary columns
		if (mode === "Compact") {
			const dim = new Set(["program", "school", "academic_year", "author_name", "visibility", "log_time"]);
			if (dim.has(column.fieldname) && val) {
				val = `<span class="text-dim">${val}</span>`;
			}
		}

		// Group header emphasis (bold a few key fields)
		if (data && data.is_group && ["log_id","student_name","log_date","log_type"].includes(column.fieldname) && val) {
			val = `<strong>${val}</strong>`;
		}

		return val;
	}, 
};

// ---- helpers (client-only) ----

function inject_compact_css_once() {
	const id = "slfu-compact-css";
	if (document.getElementById(id)) return;

	const style = document.createElement("style");
	style.id = id;
	style.textContent = `
		/* ellipsis utility for long cells (no extra bundles, tiny CSS) */
		.report-cell-ellipsis{
			display:inline-block;
			max-width:260px;
			white-space:nowrap;
			overflow:hidden;
			text-overflow:ellipsis;
			vertical-align:bottom;
		}
		.report-cell-ellipsis.wide{ max-width:340px; }

		/* subtle de-emphasis */
		.text-dim{ opacity:.8; }

		/* compact vertical rhythm */
		.compact .dt-scrollable .dt-cell__content{ line-height:1.15; }
		.compact .dt-header .dt-cell__content{ line-height:1.15; }
	`;
	document.head.appendChild(style);
}

function apply_view_mode_class(report) {
	const mode = (frappe.query_report.get_filter_value("view_mode") || "Compact").trim();
	const wrap = report?.page?.wrapper?.get(0);
	if (!wrap) return;
	wrap.classList.toggle("compact", mode === "Compact");
}

/* Relabel a few headers on the fly (client-only; zero server changes) */
function shorten_header_labels(report) {
	const map = {
		"Follow-ups": "FU #",
		"Last Follow-up On": "Last FU",
		"Follow-up Snippet": "FU Snippet"
	};
	const hdr = report?.datatable?.header?.wrapper || report?.datatable?.wrapper;
	if (!hdr) return;

	hdr.querySelectorAll(".dt-header .dt-cell__content").forEach(el => {
		const t = (el.textContent || "").trim();
		if (map[t]) el.textContent = map[t];
	});
}
