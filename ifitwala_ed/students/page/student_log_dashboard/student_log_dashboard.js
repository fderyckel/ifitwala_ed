// Copyright (c) 2025, François de Ryckel and contributors
// For license information, please see license.txt

let selected_student = null;          // global

frappe.pages["student-log-dashboard"].on_page_load = function (wrapper) {
	/*── 1. PAGE  ───────────────────────────────────────────────────────────*/
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: "Student Log Dashboard",
		single_column: true,
	});

	/*── 2. FILTER FIELDS ───────────────────────────────────────────*/
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


	/*── 3. MAIN CONTENT HTML  ──────────────────────────────────────────────*/
	$(wrapper).append(`
		<div class="dashboard-overlay" id="dashboard-overlay"></div>

		<div class="dashboard-content container">

			${createDashboardCard("incidents-over-time", "Incidents Over Time")} 
			${createDashboardCard("log-type-count",  "Log Type Count")}
			${createDashboardCard("logs-by-cohort",  "Logs by Cohort")}
			${createDashboardCard("logs-by-program", "Logs by Program")}
			${createDashboardCard("logs-by-author",  "Logs by Author")}
			${createDashboardCard("next-step-types", "Next Step Types")}

			${studentLogDetailCard()}                  
		
		</div>
	`);

	/*── 4. CARD HELPERS (same as before) ──────────────────────────────────*/
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

	/*── 5. STUDENT FILTER LOGIC ───────────────────────────────────────────*/
	const studentInput = document.getElementById("student-select");
	const dropdownEl   = document.getElementById("student-dropdown");

	// suggestions when typing ------------------------------------------------
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
			args: {
				filters: JSON.stringify(filters),
				search_text: query
			},
			callback: (r) => {
				if (r.message && !r.message.error) {
					const suggestions = r.message.map(s => `
						<div class="student-suggestion"
							 data-id="${s.student}"
							 data-name="${s.student_full_name}">          
							${s.student_full_name} (${s.student})
						</div>`).join("");
					showStudentSuggestions(suggestions);
				}
			},
		});
	});

	// Enter ↵ chooses first suggestion (if any) ------------------------------
	studentInput.addEventListener("keydown", (e) => {
		if (e.key === "Enter") {
			const first = dropdownEl.querySelector(".student-suggestion");
			if (first) first.click();     // mimic click handler
		}
	});

	// click on a suggestion ---------------------------------------------------
	dropdownEl.addEventListener("click", (e) => {
		const target = e.target.closest(".student-suggestion");
		if (!target) return;
		selected_student   = target.dataset.id;           // store ID
		studentInput.value = target.dataset.name;         // show full name ★ CHANGED
		hideStudentSuggestions();
		fetch_dashboard_data(page);
	});

	// close dropdown on outside click
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

	/*── 6. ZOOM UX ─────────────────────────────────────────────────*/
	function toggleZoom(card) {
		const overlay = document.getElementById("dashboard-overlay");

		if (card.classList.contains("zoomed")) {
				card.classList.remove("zoomed");
				overlay.classList.remove("active");
		} else {
				// un‑zoom any other card
				document.querySelectorAll(".dashboard-card.zoomed").forEach(c => {
						if (c !== card) c.classList.remove("zoomed");
				});
				card.classList.add("zoomed");
				overlay.classList.add("active");
		}
	}

	// click to zoom/un‑zoom
	document.querySelectorAll(".dashboard-card").forEach(card => {
		card.addEventListener("click", () => toggleZoom(card));
	});

	// click the dimmed background to close
	document.getElementById("dashboard-overlay").addEventListener("click", () => {
		document.querySelectorAll(".dashboard-card.zoomed").forEach(c => c.classList.remove("zoomed"));
		document.getElementById("dashboard-overlay").classList.remove("active");
	});


	/*── 7. INITIAL LOAD ───────────────────────────────────────────────────*/
	fetch_dashboard_data(page);
};

/*── 8. FETCH DASHBOARD DATA ───────────────────────────────────────────────*/
function fetch_dashboard_data(page) {
	const fd = page.fields_dict;   // shorthand

	// helper: return field value if the widget exists, else null
	const safe = (name) =>
			fd && fd[name] && typeof fd[name].get_value === "function"
					? fd[name].get_value()
					: null;
					
  const filters = {
    school:        safe("school"),
    academic_year: safe("academic_year"),
    program:       safe("program"),
    student:       selected_student,
    author:        safe("author"),
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

/*── 9. CHART & TABLE RENDER ───────────────────────────────────────────────*/
function update_charts(data) {
	if (data.error) {
		console.error("Dashboard error:", data.error);
		frappe.msgprint({
			title: __("Dashboard Error"),
			message: data.error,
			indicator: "red"
		});
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
		// sanitize rows; value must be numeric
		const rows = (data[cfg.dataKey] || []).filter(r =>
			r && r.value != null && !isNaN(Number(r.value))
		);

		if (!rows.length) {
			$(`#chart-${cfg.id}`).empty();                // ★ CHANGED – clear / skip
			return;
		}

		new frappe.Chart(`#chart-${cfg.id}`, {
			data: {
				labels:  rows.map(r => r.label),
				datasets:[{ values: rows.map(r => Number(r.value)) }],
			},
			type:   cfg.type || "bar",
			height: 300,
			colors: [cfg.color],
		});
	});

	// Student‑Log detail rows
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
