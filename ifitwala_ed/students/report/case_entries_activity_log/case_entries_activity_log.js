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
		// Optional: initial chart bucket (the in-chart toggle can override this)
		{ fieldname: "time_bucket",   label: __("Time Bucket"),   fieldtype: "Select",
			options: "Week\nMonth", default: "Week" }
	],


	// ---------- header Print button ----------
	onload(report) {
		const page = report.page;
		ensure_print_button(page);
	},

	// ---------- extra charts with a Weekly/Monthly toggle ----------
	after_datatable_render(datatable) {
		// In v15 the hook receives the datatable instance; use the global query_report object.
		const page = (frappe.query_report && frappe.query_report.page) || null;
		if (!page || !page.main) return;

		ensure_print_button(page);

		const msg = (frappe.query_report && frappe.query_report.message) || {};

		const charts = {
			week: msg.chart_over_time_week || null,
			month: msg.chart_over_time_month || null,
			by_school: msg.chart_by_school || null,
			by_program: msg.chart_by_program || null,
			by_manager: msg.chart_by_manager || null
		};

		// Create/refresh wrapper (idempotent)
		let $area = page.main.find(".cea-extra-charts");
		if (!$area.length) {
			$area = $(`
				<div class="cea-extra-charts" style="margin-top: 1rem;">
					<div class="row gy-4">
						<!-- Time -->
						<div class="col-12 col-lg-6">
							<div class="d-flex align-items-center justify-content-between">
								<h5 class="mb-2">${__("Entries Over Time")}</h5>
								<div>
									<select class="form-select form-select-sm cea-bucket" style="width:auto;display:inline-block">
										<option value="week">${__("Weekly")}</option>
										<option value="month">${__("Monthly")}</option>
									</select>
								</div>
							</div>
							<div class="cea-chart cea-time"></div>
						</div>

						<!-- School / Program -->
						<div class="col-12 col-lg-6">
							<div class="d-flex align-items-center justify-content-between">
								<h5 class="mb-2">${__("Entries by School / Program")}</h5>
								<div>
									<select class="form-select form-select-sm cea-dim" style="width:auto;display:inline-block">
										<option value="school">${__("School")}</option>
										<option value="program">${__("Program")}</option>
									</select>
								</div>
							</div>
							<div class="cea-chart cea-dim-chart"></div>
						</div>

						<!-- By Case Manager -->
						<div class="col-12">
							<h5 class="mb-2">${__("Entries per Case Manager")}</h5>
							<div class="cea-chart cea-manager"></div>
						</div>
					</div>
				</div>
			`).appendTo(page.main);
		} else {
			// Clear chart containers on every re-render to avoid stacking canvases
			$area.find(".cea-chart").empty();
		}

		// Elements
		const $timeEl = $area.find(".cea-time")[0];
		const $dimEl = $area.find(".cea-dim-chart")[0];
		const $mgrEl = $area.find(".cea-manager")[0];
		const $bucket = $area.find(".cea-bucket");
		const $dimSel = $area.find(".cea-dim");

		function render_chart(el, spec) {
			if (!el) return;
			el.innerHTML = "";
			if (!spec || !spec.data || !Array.isArray(spec.data.labels) || !spec.data.labels.length) {
				el.innerHTML = `<div class="text-muted small">${__("No data")}</div>`;
				return;
			}
			new frappe.Chart(el, spec); // { data:{labels,datasets}, type:'line'|'bar' }
		}

		function current_time_spec(bucket) {
			const key = (bucket || "week").toLowerCase();
			return key === "month" ? (charts.month || charts.week) : (charts.week || charts.month);
		}

		function render_dim(which) {
			render_chart($dimEl, (which || "school") === "program" ? charts.by_program : charts.by_school);
		}

		// Initial selections (respect filter)
		const initBucket = (frappe.query_report.get_filter_value("time_bucket") || "Week").toLowerCase();
		$bucket.val(initBucket);
		render_chart($timeEl, current_time_spec(initBucket));
		render_dim($dimSel.val() || "school");
		render_chart($mgrEl, charts.by_manager);

		// Wire toggles (namespaced to avoid duplicates)
		$bucket.off("change.cea").on("change.cea", () => {
			render_chart($timeEl, current_time_spec($bucket.val()));
		});
		$dimSel.off("change.cea").on("change.cea", () => {
			render_dim($dimSel.val());
		});
	},
};


// ---------- helpers (print) ----------
function ensure_print_button(page) {
	const BTN_KEY = "cea-print-btn";

	// Avoid duplicates
	if (page.inner_toolbar && page.inner_toolbar.find(`button[data-key="${BTN_KEY}"]`).length) {
		return;
	}

	// Add a plain blue Print button (Bootstrap 4 → btn-info)
	const $btn = page.add_inner_button(__("Print"), () => handle_report_print(), null);
	if ($btn) {
		$btn.attr("data-key", BTN_KEY);
		$btn.removeClass("btn-default").addClass("btn-info");
	}
}

async function handle_report_print() {
	try {
		const report_name = "Case Entries Activity Log";
		const filters = (frappe.query_report && frappe.query_report.get_values)
			? frappe.query_report.get_values()
			: {};

		const r = await frappe.call({
			method: "frappe.desk.query_report.export_query",
			args: {
				report_name,
				file_format_type: "PDF",
				filters
			}
		});

		const url = r && r.message && r.message.file_url;
		if (url) {
			window.open(url, "_blank");
		} else {
			frappe.msgprint(__("Could not generate the PDF file for this report."));
		}
	} catch (e) {
		frappe.msgprint(__("Print failed. Please try the ⋮ menu or check permissions."));
	}
}

// ---------- helpers (client-side aggregates) ----------
function parse_rows(rows) {
	const out = {
		byWeek: {},
		byMonth: {},
		bySchool: {},
		byProgram: {},
		byManager: {}
	};

	rows.forEach(r => {
		const dateStr = (r.entry_date || r.entry_datetime || "").toString();
		if (dateStr) {
			const d = frappe.datetime.str_to_obj(dateStr);
			if (d) {
				const weekStart = new Date(d);
				weekStart.setDate(d.getDate() - ((d.getDay() + 6) % 7)); // Monday
				const wlabel = frappe.format(weekStart, "Date", { format: "d MMM yyyy" });
				out.byWeek[wlabel] = (out.byWeek[wlabel] || 0) + 1;

				const mStart = new Date(d.getFullYear(), d.getMonth(), 1);
				const mlabel = frappe.format(mStart, "Date", { format: "MMM yyyy" });
				out.byMonth[mlabel] = (out.byMonth[mlabel] || 0) + 1;
			}
		}

		const school = (r.school || "").trim() || __("—");
		out.bySchool[school] = (out.bySchool[school] || 0) + 1;

		const program = (r.program || "").trim() || __("—");
		out.byProgram[program] = (out.byProgram[program] || 0) + 1;

		const mgr = (r.case_manager_name || "").trim() || __("— Unassigned —");
		out.byManager[mgr] = (out.byManager[mgr] || 0) + 1;
	});

	return out;
}

function render_time(el, parsed, bucket) {
	const src = bucket === "month" ? parsed.byMonth : parsed.byWeek;
	const labels = Object.keys(src).sort((a, b) => new Date(a) - new Date(b));
	const values = labels.map(l => src[l]);

	el.innerHTML = "";
	new frappe.Chart(el, {
		data: { labels, datasets: [{ name: __("Entries"), values }] },
		type: "line",
		height: 240
	});
}

function render_dim(el, parsed, dim) {
	const src = dim === "program" ? parsed.byProgram : parsed.bySchool;
	const labels = Object.keys(src).sort();
	const values = labels.map(l => src[l]);

	el.innerHTML = "";
	new frappe.Chart(el, {
		data: { labels, datasets: [{ name: __("Entries"), values }] },
		type: "bar",
		height: 240
	});
}

function render_manager(el, parsed) {
	const entries = Object.entries(parsed.byManager).sort((a, b) => b[1] - a[1]).slice(0, 12);
	const labels = entries.map(x => x[0]);
	const values = entries.map(x => x[1]);

	el.innerHTML = "";
	new frappe.Chart(el, {
		data: { labels, datasets: [{ name: __("Entries"), values }] },
		type: "bar",
		height: 260
	});
}
