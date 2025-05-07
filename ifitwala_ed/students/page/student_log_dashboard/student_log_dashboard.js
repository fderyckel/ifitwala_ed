/*************************************************************************
 *  Student Log Dashboard – Ifitwala_Ed
 *  Version: 2025‑05‑07  (fully patched)                                *
 ************************************************************************/

let selected_student = null;   

frappe.pages["student-log-dashboard"].on_page_load = function (wrapper) {
	/*───────────────────────────── 1. PAGE & GLOBAL VARS ───────────────────────────*/
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Student Log Dashboard",
		single_column: true,
	});     

	/*───────────────────────────── 2. FILTER FIELDS ───────────────────────────────*/
	const school_field = page.add_field({
		fieldname: "school",
		label: __("School"),
		fieldtype: "Link",
		options: "School",
		change: () => {
			program_field.set_value("");
			selected_student = null;      
			studentInput.value = "";
			fetch_dashboard_data(page);
		},
	});

	const program_field = page.add_field({
		fieldname: "program",
		label: __("Program"),
		fieldtype: "Link",
		options: "Program",
		get_query: () => ({
			filters: { ...(school_field.get_value() && { school: school_field.get_value() }) },
		}),
		change: () => {
			selected_student = null;      
			studentInput.value = "";
			fetch_dashboard_data(page);
		},
	});

	const academic_year_field = page.add_field({
		fieldname: "academic_year",
		label: __("Academic Year"),
		fieldtype: "Link",
		options: "Academic Year",
		change: () => fetch_dashboard_data(page),
	});

	const author_field = page.add_field({
		fieldname: "author",
		label: __("Author"),
		fieldtype: "Link",
		options: "Employee",
		change: () => fetch_dashboard_data(page),
	});

	/*───────────────────────────── 3. MAIN CONTENT HTML ───────────────────────────*/
	$(wrapper).append(`
		<div class="dashboard-overlay" id="dashboard-overlay"></div>

		<div class="dashboard-content container">

			${studentLogDetailCard()}   <!-- single detail card -->

			${createDashboardCard("log-type-count",  "Log Type Count")}
			${createDashboardCard("logs-by-cohort",  "Logs by Cohort")}
			${createDashboardCard("logs-by-program", "Logs by Program")}
			${createDashboardCard("logs-by-author",  "Logs by Author")}
			${createDashboardCard("next-step-types", "Next Step Types")}
			${createDashboardCard("incidents-over-time", "Incidents Over Time")}
			${createDashboardCard("open-follow-ups", "Open Follow-Ups")}
		</div>
	`);

	/*───────────────────────────── 4. CARD HELPERS ───────────────────────────────*/
	function createDashboardCard(id, title) {
		return `
			<div class="dashboard-card" id="${id}">
				<div class="card-title">${title}</div>
				<div id="chart-${id}"></div>
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

	/*───────────────────────────── 5. STUDENT FILTER LOGIC ───────────────────────*/
	const studentInput   = document.getElementById("student-select");
	const dropdownEl     = document.getElementById("student-dropdown");      // ★ CHANGED

	// 5‑a: live suggestions
	studentInput.addEventListener("input", () => {
		const query = studentInput.value.trim();
		if (!query) return hideStudentSuggestions();

		const filters = {
			school: school_field.get_value(),
			program: program_field.get_value(),
			academic_year: academic_year_field.get_value(),
		};

		frappe.call({
			method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_distinct_students",
			args: {
				filters: JSON.stringify(filters),
				search_text: query            
			},
			callback: (r) => {
				if (r.message && !r.message.error) {
					const suggestions = r.message.map(s => `
						<div class="student-suggestion" data-name="${s.student}">
							${s.student} – ${s.student_name}
						</div>`).join("");
					showStudentSuggestions(suggestions);
				}
			},
		});
	});

	// 5‑b: Enter key selects the current text
	studentInput.addEventListener("keydown", (e) => {            
		if (e.key === "Enter") {
			selected_student = studentInput.value.trim();
			hideStudentSuggestions();
			fetch_dashboard_data(page);
		}
	});

	// 5‑c: click inside dropdown
	dropdownEl.addEventListener("click", (e) => {
		const sel = e.target.getAttribute("data-name");
		if (sel) {
			studentInput.value = sel;
			selected_student   = sel;                              
			hideStudentSuggestions();
			fetch_dashboard_data(page);
		}
	});

	// 5‑d: outside click closes dropdown
	document.addEventListener("click", (e) => {
		if (e.target !== studentInput && !dropdownEl.contains(e.target)) {
			hideStudentSuggestions();
		}
	});

	function showStudentSuggestions(html) {
		dropdownEl.innerHTML   = html;
		dropdownEl.style.display = "block";
	}
	function hideStudentSuggestions() {
		dropdownEl.innerHTML   = "";
		dropdownEl.style.display = "none";
	}

	/*───────────────────────────── 6. ZOOM‑ON‑CLICK UX ───────────────────────────*/
	function toggleZoom(card) {
		if (card.classList.contains("zoomed")) {
			card.classList.remove("zoomed");
			document.getElementById("dashboard-overlay").classList.remove("active");
		} else {
			document.querySelectorAll(".dashboard-card.zoomed").forEach(c => {
				if (c !== card) c.classList.remove("zoomed");
			});
			card.classList.add("zoomed");
			document.getElementById("dashboard-overlay").classList.add("active");
		}
	}
	document.querySelectorAll(".dashboard-card").forEach(card => {
		card.addEventListener("click", () => toggleZoom(card));
	});
	document.getElementById("dashboard-overlay").addEventListener("click", () => {
		document.querySelectorAll(".dashboard-card.zoomed").forEach(c => c.classList.remove("zoomed"));
		document.getElementById("dashboard-overlay").classList.remove("active");
	});

	/*───────────────────────────── 7. INITIAL DATA LOAD ──────────────────────────*/
	fetch_dashboard_data(page);
};

/*───────────────────────────── 8. HELPER: FETCH DATA ───────────────────────────*/
function fetch_dashboard_data(page) {
	const filters = {
		school: page.fields_dict.school.get_value(),
		academic_year: page.fields_dict.academic_year.get_value(),
		program: page.fields_dict.program.get_value(),
		student: selected_student,            
		author: page.fields_dict.author.get_value(),
	};

	frappe.call({
		method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_dashboard_data",
		args: { filters },
		callback: (r) => {
			if (r.message) {
				console.log("Dashboard data loaded:", r.message);
				update_charts(r.message);
			}
		},
	});
}

/*───────────────────────────── 9. CHART & TABLE RENDER ─────────────────────────*/
const safe = (arr) => (Array.isArray(arr) ? arr : []);

function update_charts(data) {
	if (data.error) {        // already in your code
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
			const rows = (data[cfg.dataKey] || []).filter(r => r && r.value != null);   // ★ NEW
			if (!rows.length) {
					$(`#chart-${cfg.id}`).empty();      // clear previous chart, if any ★ NEW
					return;                             // skip this chart
			}

			new frappe.Chart(`#chart-${cfg.id}`, {
					data: {
							labels:  rows.map(r => r.label),
							datasets:[{ values: rows.map(r => r.value) }],
					},
					type:   cfg.type || "bar",
					height: 300,
					colors: [cfg.color],
			});
	});

	// Open follow‑ups tile
	$("#chart-open-follow-ups").html(`
			<div class="card full-size">
					<div class="card-body text-center">
							<h2>${data.openFollowUps}</h2>
							<p class="text-muted">Open Follow-Ups</p>
					</div>
			</div>`);

	// Student‑Log detail rows (already working)
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
