// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

let selected_student = null;
let recent_start = 0;
const recent_page_len = 25;
let branchSchools = [];

/*── 0.1 recent log table ─────────────────────────────────────────────────*/
function fetch_recent_logs(page, append = false) {
	const fd = page.fields_dict;
	const safe = name =>
		fd && fd[name] && typeof fd[name].get_value === "function"
			? fd[name].get_value() : null;

	frappe.call({
		method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_recent_logs",
		args: {
			filters: JSON.stringify({
				school: safe("school"),
				academic_year: safe("academic_year"),
				program: safe("program"),
				author: safe("author"),
				from_date: safe("from_date"),
				to_date: safe("to_date"),
			}),
			start: recent_start,
			page_length: recent_page_len,
		},
		callback: (r) => {
			if (!r.message || r.message.error) return;

			const rows = r.message.map(d => `
				<tr>
					<td>${d.date}</td>
					<td>${d.student}</td>
					<td>${d.program}</td>
					<td>${d.log_type}</td>
					<td>${d.content}</td>
					<td>${d.author}</td>
					<td class="text-center">${d.requires_follow_up ? "✓" : "✗"}</td>
				</tr>`).join("");

			const body = document.getElementById("recent-log-table-body");
			if (!append) body.innerHTML = "";
			body.insertAdjacentHTML("beforeend", rows);

			if (r.message.length < recent_page_len) {
				document.getElementById("recent-log-load-more").style.display = "none";
			} else {
				document.getElementById("recent-log-load-more").style.display = "block";
			}
			recent_start += r.message.length;
		}
	});
}

/*── 0.2 dashboard data ───────────────────────────────────────────────────*/
function fetch_dashboard_data(page) {
	const fd = page.fields_dict;
	const safe = (name) =>
		fd && fd[name] && typeof fd[name].get_value === "function"
			? fd[name].get_value() : null;

	const filters = {
		school: safe("school"),
		academic_year: safe("academic_year"),
		program: safe("program"),
		student: selected_student,
		author: safe("author"),
		from_date: safe("from_date"),
		to_date: safe("to_date"),
	};

	frappe.call({
		method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_dashboard_data",
		args: { filters },
		callback: (r) => {
			if (r.message) update_charts(r.message);
		},
	});
}

/*── 0.3 chart render (unchanged) ─────────────────────────────────────────*/
function update_charts(data) {
	if (data.error) {
		console.error("Dashboard error:", data.error);
		frappe.msgprint({ title: __("Dashboard Error"), message: data.error, indicator: "red" });
		return;
	}

	const chartConfigs = [
		{ id: "log-type-count",       dataKey: "logTypeCount",       color: "#007bff" },
		{ id: "logs-by-cohort",       dataKey: "logsByCohort",       color: "#17a2b8" },
		{ id: "logs-by-program",      dataKey: "logsByProgram",      color: "#28a745" },
		{ id: "logs-by-author",       dataKey: "logsByAuthor",       color: "#ffc107" },
		{ id: "next-step-types",      dataKey: "nextStepTypes",      color: "#fd7e14" },
		{ id: "incidents-over-time",  dataKey: "incidentsOverTime",  color: "#dc3545", type: "line" },
	];

	chartConfigs.forEach(cfg => {
		const rows = (data[cfg.dataKey] || []).filter(r => r && r.value != null && !isNaN(Number(r.value)));
		if (!rows.length) { $(`#chart-${cfg.id}`).empty(); return; }

		const values = rows.map(r => Number(r.value));
		const total  = values.reduce((a, b) => a + b, 0);
		const labels = rows.map((r, i) => (cfg.type || "bar") === "line"
			? r.label
			: `${r.label} (${total ? Math.round((values[i] / total) * 1000) / 10 : 0}%)`
		);

		new frappe.Chart(`#chart-${cfg.id}`, {
			data: { labels, datasets: [{ values }] },
			type: cfg.type || "bar",
			height: 300,
			colors: [cfg.color],
		});
	});

	if (Array.isArray(data.studentLogs)) {
		const rows = data.studentLogs.map(l => `
			<tr>
				<td>${l.date}</td>
				<td>${l.log_type}</td>
				<td>${l.content}</td>
				<td>${l.author}</td>
			</tr>`).join("");
		document.getElementById("student-log-table-body").innerHTML = rows;
	}
}


frappe.pages["student-log-dashboard"].on_page_load = function (wrapper) {
	frappe.require("/assets/ifitwala_ed/css/dashboard_cards.css");

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Student Log Dashboard",
		single_column: true,
	});

	const user_default_school = frappe.defaults.get_user_default("school");

	/*── 2. FILTER FIELDS ───────────────────────────────────────────*/
	const school_field = page.add_field({
		fieldname: "school",
		label: __("School"),
		fieldtype: "Link",
		options: "School",
		default: user_default_school,
		change: async () => {
			loadBranchSchools();
			program_field.set_value("");
			selected_student = null;
			studentInput.value = "";
			recent_start = 0;
			fetch_recent_logs(page);
			fetch_dashboard_data(page);
		},
	});
	school_field.set_value(user_default_school);

	async function loadBranchSchools() {
		const root = school_field.get_value();
		if (!root) { branchSchools = []; return; }
		branchSchools = [root];
		try {
			const { message: lr } = await frappe.db.get_value('School', root, ['lft','rgt']);
			if (!lr) return;
			const rows = await frappe.db.get_list('School', {
				fields: ['name'],
				filters: [['lft','>=', lr.lft], ['rgt','<=', lr.rgt]],
				limit: 1000,
			});
			branchSchools = rows.map(r => r.name);
		} catch (e) { console.error('Failed to load branch schools', e); }
	}
	loadBranchSchools();

	const program_field = page.add_field({
		fieldname: "program",
		label: __("Program"),
		fieldtype: "Link",
		options: "Program",
		get_query: () => {
			const sch = school_field.get_value();
			if (sch && branchSchools.length) return { filters: { school: ["in", branchSchools] } };
			if (sch) return { filters: { school: sch } };
			return {};
		},
		change: () => {
			selected_student = null;
			studentInput.value = "";
			recent_start = 0;
			fetch_recent_logs(page);
			fetch_dashboard_data(page);
		},
	});

	const academic_year_field = page.add_field({
		fieldname: "academic_year",
		label: __("Academic Year"),
		fieldtype: "Link",
		options: "Academic Year",
		change: () => {
			recent_start = 0;
			fetch_recent_logs(page);
			fetch_dashboard_data(page);
		}
	});

	const author_field = page.add_field({
		fieldname: "author",
		label: __("Author"),
		fieldtype: "Link",
		options: "Employee",
		change: () => { recent_start = 0; fetch_recent_logs(page); fetch_dashboard_data(page); },
	});

	// ★ NEW: From / To Date filters
	const from_date_field = page.add_field({
		fieldname: "from_date",
		label: __("From Date"),
		fieldtype: "Date",
		change: () => { recent_start = 0; fetch_recent_logs(page); fetch_dashboard_data(page); },
	});
	const to_date_field = page.add_field({
		fieldname: "to_date",
		label: __("To Date"),
		fieldtype: "Date",
		change: () => { recent_start = 0; fetch_recent_logs(page); fetch_dashboard_data(page); },
	});

	/*── 3. MAIN CONTENT HTML ───────────────────────────────────────────────*/
	$(wrapper).append(`
		<div class="dashboard-overlay" id="dashboard-overlay"></div>

		<div class="dashboard-content container">

			${createDashboardCard("incidents-over-time", "Incidents Over Time")}
			${recentLogsCard()}
			${createDashboardCard("log-type-count",  "Log Type Count")}
			${createDashboardCard("logs-by-cohort",  "Logs by Cohort")}
			${createDashboardCard("logs-by-program", "Logs by Program")}
			${createDashboardCard("logs-by-author",  "Logs by Author")}
			${createDashboardCard("next-step-types", "Next Step Types")}

			${studentLogDetailCard()}

		</div>
	`);

	function createDashboardCard(id, title) {
		return `
			<div class="dashboard-card" id="${id}">
				<div class="card-title">${title}</div>
				<div id="chart-${id}"></div>
			</div>`;
	}

	function recentLogsCard() {
		return `
			<div class="dashboard-card" id="recent-log-card">
				<div class="card-title">Recent Student Logs</div>

				<div class="student-log-table-wrapper">
					<table class="table table-bordered table-hover">
						<thead class="table-light">
							<tr>
								<th>Date</th><th>Student</th><th>Program</th><th>Log Type</th>
								<th>Log</th><th>Author</th><th>⧈</th>
							</tr>
						</thead>
						<tbody id="recent-log-table-body"></tbody>
					</table>
				</div>

				<div class="load-more-wrapper">
					<button class="btn btn-link w-100" id="recent-log-load-more">
						Load more…
					</button>
				</div>
			</div>`;
	}

	function studentLogDetailCard() {
		return `
			<div class="dashboard-card" id="student-log-detail">
				<div class="card-title">Student Log Detail</div>

				<div class="student-log-filter mb-2">
					<label class="form-label" for="student-select">Student</label>
					<input class="form-control" type="text" id="student-select"
						   placeholder="Start typing…" autocomplete="off">
					<div id="student-dropdown" class="student-dropdown"></div>
				</div>

				<div class="student-log-table-wrapper">
					<table class="table table-bordered table-hover student-log-table">
						<thead class="table-light">
							<tr>
								<th>Date</th><th>Log Type</th>
								<th>Log Content</th><th>Author</th>
							</tr>
						</thead>
						<tbody id="student-log-table-body"></tbody>
					</table>
				</div>
			</div>`;
	}

	document.getElementById("recent-log-load-more")
		.addEventListener("click", () => fetch_recent_logs(page, true));

	/*── 5. STUDENT FILTER LOGIC (unchanged) ───────────────────────────────*/
	const studentInput = document.getElementById("student-select");
	const dropdownEl   = document.getElementById("student-dropdown");

	studentInput.addEventListener("input", () => {
		const query = studentInput.value.trim();
		if (!query) return hideStudentSuggestions();

		const filters = {
			school: page.fields_dict.school.get_value(),
			program: page.fields_dict.program.get_value(),
			academic_year: page.fields_dict.academic_year.get_value(),
		};

		frappe.call({
			method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_distinct_students",
			args: { filters: JSON.stringify(filters), search_text: query },
			callback: (r) => {
				if (r.message && !r.message.error) {
					const suggestions = r.message.map(s => `
						<div class="student-suggestion"
							 data-id="${s.student}"
							 data-name="${s.student_full_name}">
							${s.student_full_name} (${s.student})
						</div>`).join("");
					showStudentSuggestions(suggestions);
				}
			},
		});
	});

	studentInput.addEventListener("keydown", (e) => {
		if (e.key === "Enter") {
			e.preventDefault();
			e.stopPropagation();
			const first = dropdownEl.querySelector(".student-suggestion");
			if (first) first.click();
		}
	});

	dropdownEl.addEventListener("click", (e) => {
		e.stopPropagation();
		const target = e.target.closest(".student-suggestion");
		if (!target) return;
		selected_student   = target.dataset.id;
		studentInput.value = target.dataset.name;
		hideStudentSuggestions();
		fetch_dashboard_data(page);
	});

	document.addEventListener("click", (e) => {
		if (e.target !== studentInput && !dropdownEl.contains(e.target)) {
			hideStudentSuggestions();
		}
	});

	function showStudentSuggestions(html) {
		dropdownEl.innerHTML = html;
		dropdownEl.style.display = "block";
	}
	function hideStudentSuggestions() {
		dropdownEl.innerHTML = "";
		dropdownEl.style.display = "none";
	}

	/*── 6. ZOOM UX (unchanged) ───────────────────────────────────────────*/
	function toggleZoom(card) {
		const overlay = document.getElementById("dashboard-overlay");
		if (card.classList.contains("zoomed")) {
			card.classList.remove("zoomed");
			overlay.classList.remove("active");
		} else {
			document.querySelectorAll(".dashboard-card.zoomed").forEach(c => {
				if (c !== card) c.classList.remove("zoomed");
			});
			card.classList.add("zoomed");
			overlay.classList.add("active");
		}
	}
	document.querySelectorAll(".dashboard-card").forEach(card => {
		card.addEventListener("click", (e) => {
			if (card.id === "student-log-detail" &&
				e.target.closest(".student-log-filter, .student-dropdown")) {
				e.stopPropagation();
				return;
			}
			toggleZoom(card);
		});
	});
	document.getElementById("dashboard-overlay").addEventListener("click", () => {
		document.querySelectorAll(".dashboard-card.zoomed").forEach(c => c.classList.remove("zoomed"));
		document.getElementById("dashboard-overlay").classList.remove("active");
	});

	/*── 7. INITIAL LOAD ───────────────────────────────────────────────────*/
	fetch_recent_logs(page);
	fetch_dashboard_data(page);
};


