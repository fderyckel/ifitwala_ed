frappe.pages["student-log-dashboard"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: "Student Log Dashboard",
    single_column: true,
  });

  /* ─── Filter fields (cascading logic) ───────────────────────── */
  const school_field = page.add_field({
    fieldname: "school",
    label: __("School"),
    fieldtype: "Link",
    options: "School",
    change: () => {
      program_field.set_value("");
      student_field.set_value("");
      fetch_dashboard_data(page);
    },
  });

  const program_field = page.add_field({
    fieldname: "program",
    label: __("Program"),
    fieldtype: "Link",
    options: "Program",
    get_query: () => ({
      filters: {
        ...(school_field.get_value() && { school: school_field.get_value() }),
      },
    }),
    change: () => {
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

	/* ─── Main content containers ───────────────────────────────── */
	$(wrapper).append(`
		<div class="dashboard-overlay" id="dashboard-overlay"></div>
		<div class="dashboard-content container">
				${studentLogDetailCard()}

				${createDashboardCard("log-type-count", "Log Type Count")}
				${createDashboardCard("logs-by-cohort", "Logs by Cohort")}
				${createDashboardCard("logs-by-program", "Logs by Program")}
				${createDashboardCard("logs-by-author", "Logs by Author")}
				${createDashboardCard("next-step-types", "Next Step Types")}
				${createDashboardCard("incidents-over-time", "Incidents Over Time")}
				${createDashboardCard("open-follow-ups", "Open Follow-Ups")}
		</div>
	`);

	/* ─── Card Creation Helper ───────────────────────────────── */
	function createDashboardCard(id, title) {
		return `
				<div class="dashboard-card" id="${id}">
						<div class="card-title">${title}</div>
						<div id="chart-${id}"></div>
				</div>
		`;
	}

	// NEW helper: single detail card, includes missing dropdown div
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


	// Student filter logic
	const studentInput = document.getElementById("student-select");
	studentInput.addEventListener("input", () => {
			const query = studentInput.value.trim();
			if (query.length > 0) {
					const filters = {
							school: page.fields_dict.school.get_value(),
							program: page.fields_dict.program.get_value(),
							academic_year: page.fields_dict.academic_year.get_value(),
					};

					frappe.call({
							method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_distinct_students",
							args: { filters: JSON.stringify(filters) },
							callback: (r) => {
									if (r.message && !r.message.error) {
											const suggestions = r.message.map(s => `
													<div class="student-suggestion" data-name="${s.student}">
															${s.student} - ${s.student_name}
													</div>
											`).join("");
											showStudentSuggestions(suggestions);
									}
							},
					});
			} else {
					hideStudentSuggestions();  // Clear suggestions when input is empty
			}
	});

	function showStudentSuggestions(suggestions) {
			const dropdown = document.getElementById("student-dropdown");
			dropdown.innerHTML = suggestions;
			dropdown.style.display = "block";

			// Handle suggestion click
			dropdown.addEventListener("click", (e) => {
					const selectedStudent = e.target.getAttribute("data-name");
					if (selectedStudent) {
							studentInput.value = selectedStudent;
							fetch_student_logs(selectedStudent);
							hideStudentSuggestions();
					}
			});
	}

	function hideStudentSuggestions() {
			const dropdown = document.getElementById("student-dropdown");
			dropdown.innerHTML = "";
			dropdown.style.display = "none";
	}

	// Close dropdown on outside click
	document.addEventListener("click", (e) => {
    const dropdown = document.getElementById("student-dropdown");
    if (dropdown && e.target !== studentInput && !dropdown.contains(e.target)) {
        hideStudentSuggestions();
    }
	});



	function fetch_student_logs(student_id) {
    frappe.call({
        method: "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_student_logs",
        args: { student_id },
        callback: (r) => {
            if (r.message) {
                const logs = r.message;
                const rows = logs.map(log => `
                    <tr>
                        <td>${log.date}</td>
                        <td>${log.log_type}</td>
                        <td>${log.content}</td>
                        <td>${log.author}</td>
                    </tr>
                `).join("");
                document.getElementById("student-log-table-body").innerHTML = rows;
            }
        },
    });
	}

	// Keep this inside on_page_load
	function toggleZoom(card) {
		if (card.classList.contains('zoomed')) {
			card.classList.remove('zoomed');
			document.getElementById('dashboard-overlay').classList.remove('active');
		} else {
			// Remove zoom from any other card
			document.querySelectorAll('.dashboard-card.zoomed').forEach(c => {
				if (c !== card) c.classList.remove('zoomed');
			});
			card.classList.add('zoomed');
			document.getElementById('dashboard-overlay').classList.add('active');
		}
	}

	// Add event listeners to cards
	document.querySelectorAll('.dashboard-card').forEach(card => {
		card.addEventListener('click', () => toggleZoom(card));
	});

	// Close zoom when overlay is clicked
	const overlay = document.getElementById('dashboard-overlay');
	overlay.addEventListener('click', () => {
		document.querySelectorAll('.dashboard-card.zoomed').forEach(c => c.classList.remove('zoomed'));
		overlay.classList.remove('active');
	});		

  // initial load
  fetch_dashboard_data(page);
};

// ───────────────────────────────────────────────────────────────
// helpers
const safe = (arr) => (Array.isArray(arr) ? arr : []);

// ───────────────────────────────────────────────────────────────
function fetch_dashboard_data(page) {
  const filters = {
    school: page.fields_dict.school.get_value(),
    academic_year: page.fields_dict.academic_year.get_value(),
    program: page.fields_dict.program.get_value(),
    student: page.fields_dict.student ? page.fields_dict.student.get_value() : null,
    author: page.fields_dict.author.get_value(),
  };

  frappe.call({
    method:
      "ifitwala_ed.students.page.student_log_dashboard.student_log_dashboard.get_dashboard_data",
    args: { filters },
    callback: (r) => {
      if (r.message) {
        console.log("Dashboard data loaded:", r.message);
        update_charts(r.message);
      }
    },
  });
}

// ───────────────────────────────────────────────────────────────
// ─── Chart Initialization ─────────────────────────────────
function update_charts(data) {
	const chartConfigs = [
			{ id: "log-type-count", dataKey: "logTypeCount", color: "#007bff" },
			{ id: "logs-by-cohort", dataKey: "logsByCohort", color: "#17a2b8" },
			{ id: "logs-by-program", dataKey: "logsByProgram", color: "#28a745" },
			{ id: "logs-by-author", dataKey: "logsByAuthor", color: "#ffc107" },
			{ id: "next-step-types", dataKey: "nextStepTypes", color: "#fd7e14" },
			{ id: "incidents-over-time", dataKey: "incidentsOverTime", color: "#dc3545", type: "line" },
	];

	chartConfigs.forEach(config => {
			new frappe.Chart(`#chart-${config.id}`, {
					data: {
							labels: safe(data[config.dataKey]).map((i) => i.label),
							datasets: [{ values: safe(data[config.dataKey]).map((i) => i.value) }],
					},
					type: config.type || "bar",
					height: 300,
					colors: [config.color],
					title: "",  // Now handled by card title
			});
	});

	// Handle the open follow-ups separately
	$("#chart-open-follow-ups").html(`
			<div class="card full-size">
					<div class="card-body text-center">
							<h2>${data.openFollowUps}</h2>
							<p class="text-muted">Open Follow-Ups</p>
					</div>
			</div>
	`);
}