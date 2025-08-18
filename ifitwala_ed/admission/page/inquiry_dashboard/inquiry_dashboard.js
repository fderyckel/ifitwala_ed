// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages["inquiry-dashboard"].on_page_load = function (wrapper) {
	// load shared card styles
	frappe.require("/assets/ifitwala_ed/css/dashboard_cards.css");
	frappe.require("/assets/ifitwala_ed/css/inquiry_numbers.css");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Inquiry Dashboard"),
		single_column: true
	});

	/*──────────── 1) FILTERS ─────────────────────────────────────────────*/
	const fd = {};

	fd.academic_year = page.add_field({
		fieldname: "academic_year",
		label: __("Academic Year"),
		fieldtype: "Link",
		options: "Academic Year",
		change: () => sync_dates_from_ay()
	});

	fd.from_date = page.add_field({
		fieldname: "from_date",
		label: __("From Date"),
		fieldtype: "Date",
		change: () => refresh_all()
	});

	fd.to_date = page.add_field({
		fieldname: "to_date",
		label: __("To Date"),
		fieldtype: "Date",
		change: () => refresh_all()
	});

	fd.type_of_inquiry = page.add_field({
		fieldname: "type_of_inquiry",
		label: __("Type"),
		fieldtype: "Select",
		options: ["", "General", "Admissions", "Financial Aid", "Other"].join("\n"),
		change: () => refresh_all()
	});

	fd.assigned_to = page.add_field({
		fieldname: "assigned_to",
		label: __("Assignee"),
		fieldtype: "Link",
		options: "User",
		change: () => refresh_all()
	});

	function sync_dates_from_ay() {
		const ay = fd.academic_year.get_value();
		if (!ay) return refresh_all();
		// fetch AY bounds (server-side for correctness)
		frappe.db.get_value("Academic Year", ay, ["year_start_date", "year_end_date"])
			.then(({ message }) => {
				if (message) {
					fd.from_date.set_value(message.year_start_date);
					fd.to_date.set_value(message.year_end_date);
				}
				refresh_all();
			});
	}

	/*──────────── 2) PAGE BODY ───────────────────────────────────────────*/
	$(wrapper).append(`
		<div class="dashboard-content container">
			<div class="d-flex flex-wrap gap-3 w-100">
				<div class="kpi-number-card">
					<div class="kpi-label">${__("Total Inquiries")}</div>
					<div class="kpi-value" id="kpi-total">–</div>
					<div class="kpi-sub" id="kpi-contacted">– ${__("contacted")}</div>
				</div>
				<div class="kpi-number-card">
					<div class="kpi-label">${__("Avg hrs to 1st contact")}</div>
					<div class="kpi-value" id="kpi-avg-first-30">–</div>
					<div class="kpi-sub">${__("Last 30 days")} • <span id="kpi-avg-first-all">–</span> ${__("overall")}</div>
				</div>
				<div class="kpi-number-card">
					<div class="kpi-label">${__("Avg hrs from assign")}</div>
					<div class="kpi-value" id="kpi-avg-assign-30">–</div>
					<div class="kpi-sub">${__("Last 30 days")} • <span id="kpi-avg-assign-all">–</span> ${__("overall")}</div>
				</div>
				<div class="kpi-number-card">
					<div class="kpi-label">${__("Overdue (1st contact)")}</div>
					<div class="kpi-value text-danger" id="kpi-overdue">–</div>
					<div class="kpi-sub">${__("Needs attention")}</div>
				</div>
			</div>

			<div class="dashboard-card" id="card-monthly">
				<div class="card-title">${__("Monthly Avg Response Time (hrs)")}</div>
				<div id="chart-monthly"></div>
			</div>

			<div class="dashboard-card" id="card-assignees">
				<div class="card-title">${__("Assignments by User")}</div>
				<div id="chart-assignees"></div>
			</div>

			<div class="dashboard-card" id="card-types">
				<div class="card-title">${__("Inquiry Types")}</div>
				<div id="chart-types"></div>
			</div>
		</div>
	`);

	/*──────────── 3) LOAD DATA ───────────────────────────────────────────*/
	function current_filters() {
		return {
			academic_year: fd.academic_year.get_value(),
			from_date: fd.from_date.get_value(),
			to_date: fd.to_date.get_value(),
			type_of_inquiry: fd.type_of_inquiry.get_value(),
			assigned_to: fd.assigned_to.get_value()
		};
	}

	function refresh_all() {
		frappe.call({
			method: "ifitwala_ed.admission.page.inquiry_dashboard.inquiry_dashboard.get_dashboard_data",
			args: { filters: current_filters() },
			callback: (r) => r.message && render(r.message)
		});
	}

	function render(data) {
		// numbers
		$("#kpi-total").text(flt(data.counts.total).toLocaleString());
		$("#kpi-contacted").text(`${flt(data.counts.contacted).toLocaleString()} ${__("contacted")}`);
		$("#kpi-overdue").text(flt(data.counts.overdue_first_contact).toLocaleString());

		$("#kpi-avg-first-30").text(flt(data.averages.last30d.first_contact_hours).toFixed(1));
		$("#kpi-avg-first-all").text(flt(data.averages.overall.first_contact_hours).toFixed(1));
		$("#kpi-avg-assign-30").text(flt(data.averages.last30d.from_assign_hours).toFixed(1));
		$("#kpi-avg-assign-all").text(flt(data.averages.overall.from_assign_hours).toFixed(1));

		// monthly dual-series line
		const labels = data.monthly_avg_series.labels || [];
		const firstVals = data.monthly_avg_series.first_contact || [];
		const assignVals = data.monthly_avg_series.from_assign || [];

		if (labels.length) {
			new frappe.Chart("#chart-monthly", {
				type: "line",
				data: {
					labels,
					datasets: [
						{ name: __("First Contact"), values: firstVals },
						{ name: __("From Assign"), values: assignVals }
					]
				},
				height: 320
			});
		} else {
			$("#chart-monthly").empty();
		}

		// bar: assignees
		const assignees = data.assignee_distribution || [];
		if (assignees.length) {
			new frappe.Chart("#chart-assignees", {
				type: "bar",
				data: {
					labels: assignees.map(r => r.label),
					datasets: [{ values: assignees.map(r => r.value) }]
				},
				height: 300
			});
		} else {
			$("#chart-assignees").empty();
		}

		// pie: types
		const types = data.type_distribution || [];
		if (types.length) {
			new frappe.Chart("#chart-types", {
				type: "percentage",
				data: {
					labels: types.map(r => r.label),
					datasets: [{ values: types.map(r => r.value) }]
				},
				height: 280
			});
		} else {
			$("#chart-types").empty();
		}
	}

	// initial defaults: last 90d until AY picked
	fd.to_date.set_value(frappe.datetime.obj_to_str(new Date()));
	fd.from_date.set_value(frappe.datetime.add_days(fd.to_date.get_value(), -90));

	refresh_all();
};
