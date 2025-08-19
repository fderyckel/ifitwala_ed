// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

frappe.pages["inquiry-dashboard"].on_page_load = function (wrapper) {
	// load shared card styles
	frappe.require("/assets/ifitwala_ed/css/dashboard_cards.css");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Inquiry Dashboard"),
		single_column: true
	});

	// NEW: chart handles to prevent overlay & ReferenceError
	let chartMonthly, chartAssignees, chartTypes, chartPipeline, chartWeekly;
	let weeklyRanges = [];


	// NEW: ensure flt exists locally (fallback to Number)
	const flt = (v) => {
		try {
			if (frappe.utils && typeof frappe.utils.flt === "function") {
				return frappe.utils.flt(v);
			}
		} catch (e) {}
		const n = parseFloat(v);
		return isNaN(n) ? 0 : n;
	};

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
		options: "", // will be populated dynamically
		change: () => refresh_all()
	});

	fd.assigned_to = page.add_field({
		fieldname: "assigned_to",
		label: __("Assignee"),
		fieldtype: "Link",
		options: "User",
		change: () => refresh_all()
	});

	// Attach server-side link queries (AFTER add_field calls)
	fd.academic_year.get_query = () => ({
		query: "ifitwala_ed.admission.page.inquiry_dashboard.inquiry_dashboard.academic_year_link_query"
	});

	fd.assigned_to.get_query = () => ({
		query: "ifitwala_ed.admission.page.inquiry_dashboard.inquiry_dashboard.admission_user_link_query"
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

	// Populate Type options dynamically from server
	(function populate_types() {
		frappe.call({
			method: "ifitwala_ed.admission.page.inquiry_dashboard.inquiry_dashboard.get_inquiry_types",
			callback: (r) => {
				const types = r.message || [];
				const opts = ["", ...types]; // keep blank as "All"
				fd.type_of_inquiry.df.options = opts.join("\n");
				fd.type_of_inquiry.refresh();
			}
		});
	})();	

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

				<div class="kpi-number-card">
					<div class="kpi-label">${__("Due Today")}</div>
					<div class="kpi-value text-warning" id="kpi-due-today">–</div>
					<div class="kpi-sub">${__("First contact due today")}</div>
				</div>

				<div class="kpi-number-card">
					<div class="kpi-label">${__("Upcoming")}</div>
					<div class="kpi-value" id="kpi-upcoming">–</div>
					<div class="kpi-sub"><span id="kpi-upcoming-horizon">–</span></div>
				</div>

				<div class="kpi-number-card">
					<div class="kpi-label">${__("SLA % (30d)")}</div>
					<div class="kpi-value" id="kpi-sla-30">–</div>
					<div class="kpi-sub">${__("Contacted within deadline")}</div>
				</div>

			</div>

			<div class="dashboard-card" id="card-pipeline">
				<div class="card-title">${__("Pipeline by Workflow State")}</div>
				<div id="chart-pipeline"></div>
			</div>

			<div class="dashboard-card" id="card-weekly">
				<div class="card-title">${__("Weekly Inquiry Volume")}</div>
				<div id="chart-weekly"></div>
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


	// ── Drilldown helpers
	function list_base_filters() {
		const from_date = fd.from_date.get_value();
		const to_date = fd.to_date.get_value();
		const filters = {
			"submitted_at": ["between", [
				`${from_date} 00:00:00`,
				`${to_date} 23:59:59`
			]]
		};
		const type = fd.type_of_inquiry.get_value();
		if (type) filters["type_of_inquiry"] = type;

		const assignee = fd.assigned_to.get_value();
		if (assignee) filters["assigned_to"] = assignee;

		return filters;
	}

	function open_inquiry_list(extra = {}) {
		const filters = Object.assign({}, list_base_filters(), extra);
		frappe.route_options = filters;
		frappe.set_route("List", "Inquiry", "List");
	}

	// Make KPI cards clickable
	$(".kpi-number-card").css("cursor", "pointer");

	// Total (all in window)
	$("#kpi-total").closest(".kpi-number-card").on("click", () => {
		open_inquiry_list({});
	});

	// Avg hrs to 1st contact → contacted
	$("#kpi-avg-first-30").closest(".kpi-number-card").on("click", () => {
		open_inquiry_list({
			"first_contacted_at": ["is", "set"]
		});
	});

	// Avg hrs from assign → assigned & contacted
	$("#kpi-avg-assign-30").closest(".kpi-number-card").on("click", () => {
		open_inquiry_list({
			"assigned_to": ["is", "set"],
			"first_contacted_at": ["is", "set"]
		});
	});

	// Overdue (1st contact) → due date passed & not contacted
	$("#kpi-overdue").closest(".kpi-number-card").on("click", () => {
		open_inquiry_list({
			"first_contacted_at": ["is", "not set"],
			"first_contact_due_on": ["<", frappe.datetime.get_today()]
		});
	});

	// Due Today → due today & not contacted
	$("#kpi-due-today").closest(".kpi-number-card").on("click", () => {
		open_inquiry_list({
			"first_contacted_at": ["is", "not set"],
			"first_contact_due_on": ["between", [
				frappe.datetime.get_today(), frappe.datetime.get_today()
			]]
		});
	});

	// Upcoming → due within horizon & not contacted
	$("#kpi-upcoming").closest(".kpi-number-card").on("click", () => {
		const horizonText = $("#kpi-upcoming-horizon").data("horizonTo");
		const to = (horizonText || frappe.datetime.get_today());
		open_inquiry_list({
			"first_contacted_at": ["is", "not set"],
			"first_contact_due_on": ["between", [
				frappe.datetime.add_days(frappe.datetime.get_today(), 1), to
			]]
		});
	});



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

		$("#kpi-due-today").text(flt(data.counts.due_today).toLocaleString());
		$("#kpi-upcoming").text(flt(data.counts.upcoming).toLocaleString());
		$("#kpi-sla-30").text(`${flt(data.sla.pct_30d).toFixed(1)}%`);

		const labels = data.monthly_avg_series.labels || [];
		const firstVals = data.monthly_avg_series.first_contact || [];
		const assignVals = data.monthly_avg_series.from_assign || [];
		const h = data.config?.upcoming_horizon_days || 7;
		const horizonTo = frappe.datetime.add_days(frappe.datetime.get_today(), h);

		$("#kpi-upcoming-horizon")
			.text(__("Next {0} days (until {1})", [h, horizonTo]))
			.data("horizonTo", horizonTo);

		if (labels.length) {
			const monthlyData = {
				labels,
				datasets: [
					{ name: __("First Contact"), values: firstVals },
					{ name: __("From Assign"), values: assignVals }
				]
			};
			if (chartMonthly) {
				chartMonthly.update(monthlyData);
			} else {
				chartMonthly = new frappe.Chart("#chart-monthly", {
					type: "line",
					data: monthlyData,
					height: 320
				});
			}
		} else {
			$("#chart-monthly").empty();
			chartMonthly = null;
		}

		const assignees = data.assignee_distribution || [];
		if (assignees.length) {
			const adata = {
				labels: assignees.map(r => r.label),
				datasets: [{ values: assignees.map(r => r.value) }]
			};
			if (chartAssignees) {
				chartAssignees.update(adata);
			} else {
				chartAssignees = new frappe.Chart("#chart-assignees", {
					type: "bar",
					data: adata,
					height: 300
				});
			}
		} else {
			$("#chart-assignees").empty();
			chartAssignees = null;
		}

		const types = data.type_distribution || [];
		if (types.length) {
			const tdata = {
				labels: types.map(r => r.label),
				datasets: [{ values: types.map(r => r.value) }]
			};
			if (chartTypes) {
				chartTypes.update(tdata);
			} else {
				chartTypes = new frappe.Chart("#chart-types", {
					type: "percentage",
					data: tdata,
					height: 280
				});
			}
		} else {
			$("#chart-types").empty();
			chartTypes = null;
		}

		// Pipeline chart
		const pipeline = data.pipeline_by_state || [];
		if (pipeline.length) {
			const pdata = {
				labels: pipeline.map(r => r.label),
				datasets: [{ values: pipeline.map(r => r.value) }]
			};
			if (chartPipeline) {
				chartPipeline.update(pdata);
			} else {
				chartPipeline = new frappe.Chart("#chart-pipeline", {
					type: "bar",
					data: pdata,
					height: 300
				});
				chartPipeline.parent.addEventListener("data-select", (e) => {
					const lbl = e?.detail?.label;
					if (lbl) open_inquiry_list({ "workflow_state": lbl });
				});
			}
		} else {
			$("#chart-pipeline").empty();
			chartPipeline = null;
		}

		// Weekly volume
		const weekly = data.weekly_volume_series || {};
		const wlabels = weekly.labels || [];
		const wvalues = weekly.values || [];
		weeklyRanges = weekly.ranges || [];
		if (wlabels.length) {
			const wdata = { labels: wlabels, datasets: [{ values: wvalues }] };
			if (chartWeekly) {
				chartWeekly.update(wdata);
			} else {
				chartWeekly = new frappe.Chart("#chart-weekly", {
					type: "line",
					data: wdata,
					height: 300
				});
				chartWeekly.parent.addEventListener("data-select", (e) => {
					const i = e?.detail?.index ?? -1;
					const r = weeklyRanges[i];
					if (r?.from && r?.to) {
						open_inquiry_list({
							"submitted_at": ["between", [r.from, r.to]]
						});
					}
				});
			}
		} else {
			$("#chart-weekly").empty();
			chartWeekly = null;
		}		
	}

	// initial defaults: last 90d until AY picked
	fd.to_date.set_value(frappe.datetime.obj_to_str(new Date()));
	fd.from_date.set_value(frappe.datetime.add_days(fd.to_date.get_value(), -90));

	refresh_all();
};
